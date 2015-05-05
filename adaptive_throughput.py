import sys
import time
import getopt
import math
import numpy

import numa
import raw
import corba

def samples_to_int(value):
    scale = 1
    if value[-1].isalpha():
        suffix = value[-1].lower()
        value = value[:-1]
        if suffix == 'k':
            scale = 1024
        elif suffix == 'm':
            scale = 1024**2
    return int(value)*scale

def time_to_sec(value):
    scale = 1.0
    if value[-1].isalpha():
        suffix = value[-1].lower()
        value = value[:-1]
        if suffix == 'm':
            scale = 60.0
        elif suffix == 's':
            scale = 1.0
    return float(value)*scale

def to_gbps(value):
    return '%.2f' % (value/(1024**3))

def to_percent(value):
    return '%.1f' % (value*100.0)

def to_binary(value):
    suffixes = [ '', 'KB', 'MB', 'GB' ]
    index = int(math.floor(math.log(value, 1024)))
    return '%d%s' % (value/math.pow(1024, index), suffixes[index])

class AggregateTest(object):
    def __init__(self, factory, data_format, transfer_size, numa_policy, count):
        self.tests = [factory.create(data_format, transfer_size, numa_policy.next()) for ii in xrange(count)]

    def start(self):
        for test in self.tests:
            test.start()

    def stop(self):
        for test in self.tests:
            test.stop()

    def received(self):
        return sum(test.received for test in self.tests)

    def transfer_size(self, length):
        for test in self.tests:
            test.transfer_size(length)

    def terminate(self):
        for test in self.tests:
            test.terminate()


class Statistics(object):

    class Listener(object):
        def __init__(self, stats):
            self.stats = stats
            stats.add_listener(self)

        def add_sample(self, timestamp, rate):
            pass

        def set_size(self, transfer_size):
            pass

    def __init__(self):
        self.samples = []
        self.listeners = []
        self.peak_rate = 0.0
        self.peak_size = 0
        self.transfer_size = 0

    def add_listener(self, listener):
        self.listeners.append(listener)

    def add_sample(self, timestamp, value):
        sample = {'time': timestamp,
                  'rate': value,
                  'size': self.transfer_size}
        self.samples.append(sample)

        for listener in self.listeners:
            listener.add_sample(timestamp, value)

    def set_size(self, size):
        self.transfer_size = size
        for listener in self.listeners:
            listener.set_size(size)

    def get_peak(self):
        return max(self.samples, key=lambda s:s['rate'])

    def get_times(self):
        return [s['time'] for s in self.samples]

    def get_rates(self):
        return [s['rate'] for s in self.samples]

    def get_sizes(self):
        sizes = set()
        for sample in self.samples:
            if not sample['size'] in sizes:
                yield sample
            sizes.add(sample['size'])

    def get_samples(self, size):
        return [s for s in self.samples if s['size'] == size]


class Averager(Statistics.Listener):
    def __init__(self, stats, window_size):
        Statistics.Listener.__init__(self, stats)
        self.values = []
        self.window_size = window_size
        self.max_window_size = 2 * self.window_size

    def add_sample(self, timestamp, value):
        self.values.append(value)

    def reset(self):
        self.values = []

    def is_stable(self, tolerance):
        if len(self.values) < self.window_size:
            return False
        elif len(self.values) >= self.max_window_size:
            return True

        return self.variance() <= tolerance

    def get_data(self):
        return self.values

    def average(self):
        return numpy.average(self.get_data())

    def variance(self):
        data = self.get_data()
        return numpy.std(data)/numpy.average(data)

    def length(self):
        return len(self.values)


class TextPlotter(Statistics.Listener):
    def add_sample(self, timestamp, rate):
        peak = self.stats.get_peak()['rate']
        print '%s %.3f' % (to_gbps(rate), rate/peak)

    def set_size(self, transfer_size):
        print 'Transfer size', to_binary(transfer_size)


if __name__ == '__main__':
    transfer_size = 16*1024
    interface = 'raw'
    transport = 'unix'
    numa_distance = None
    data_format = 'octet'
    poll_time = 0.1
    window_size = 10
    tolerance = 0.1
    count = 1
    nogui = False

    opts, args = getopt.getopt(sys.argv[1:], 'w:t:d:', ['transport=', 'interface=', 'numa-distance=',
                                                        'no-gui'])
    for key, value in opts:
        if key == '-w':
            window_size = int(value)
        elif key == '-t':
            poll_time = float(value)
        elif key == '-d':
            tolerance = float(value)
        elif key == '--transport':
            transport = value
        elif key == '--numa-distance':
            numa_distance = int(value)
        elif key == '--interface':
            interface = value
        elif key == '--no-gui':
            nogui = True

    numa_policy = numa.NumaPolicy(numa_distance)

    if interface == 'raw':
        factory = raw.factory(transport)
    elif interface == 'corba':
        factory = corba.factory(transport)
    else:
        raise SystemExit('No interface '+interface)

    stats = Statistics()
    window = Averager(stats, window_size)
    plotter = TextPlotter(stats)

    stats.set_size(transfer_size)

    test = AggregateTest(factory, data_format, transfer_size, numa_policy, count)
    test.start()

    start = time.time()
    next = start + poll_time

    now = start
    last_time = start
    last_total = 0

    best_rate = 0.0
    best_size = 0

    while transfer_size < (64*1024*1024):
        # Wait until next scheduled poll time
        sleep_time = next - time.time()
        next += poll_time
        if sleep_time > 0.0:
            time.sleep(sleep_time)

        # Measure time elapsed since last sample
        now = time.time()
        elapsed = now - last_time
        last_time = now

        # Calculate average throughput over the sample period
        current_total = test.received()
        delta = current_total - last_total
        last_total = current_total
        current_rate = delta / elapsed
        stats.add_sample(now-start, current_rate)

        # Wait until window is stable (or it's taken long enough that we can
        # assume it will never stabilize) to make decisions
        if not window.is_stable(tolerance):
            continue

        average = window.average()
        if average >= best_rate:
            best_rate = average
            best_size = transfer_size

        # Get the normalized standard deviation
        if best_rate > 0.0:
            best_ratio = average/best_rate
        else:
            best_ratio = 1.0
        if best_ratio < 0.90:
            break

        # Adapt transfer size
        transfer_size *= 2
        test.transfer_size(transfer_size)
        stats.set_size(transfer_size)
        window.reset()

    test.stop()
    test.terminate()

    print 'Average:', to_binary(best_size), to_gbps(best_rate)
    peak = stats.get_peak()
    print 'Peak:   ', to_binary(peak['size']), to_gbps(peak['rate'])

    if nogui:
        sys.exit(0)

    from matplotlib import pyplot

    # Create a line plot of instantaneous throughput vs. time
    pyplot.subplot(211)
    times = stats.get_times()
    rates = stats.get_rates()
    pyplot.plot(times, rates)
    pyplot.xlabel('Time (s)')
    pyplot.ylabel('Throughput (bps)')
    pyplot.axhline(peak['rate'], color='red')
    pyplot.axhline(best_rate, color='red', linestyle='--')

    for sample in stats.get_sizes():
        # Display vertical line at size change
        pyplot.axvline(sample['time'], linestyle='--')

    # Create a bar graph of average throughput vs. transfer size
    pyplot.subplot(212)
    sizes = [s['size'] for s in stats.get_sizes()]
    averages = [numpy.average([s['rate'] for s in stats.get_samples(size)]) for size in sizes]
    dev = [numpy.std([s['rate'] for s in stats.get_samples(size)]) for size in sizes]
    pyplot.bar(numpy.arange(len(sizes)), averages, yerr=dev, ecolor='black')
    pyplot.xticks(numpy.arange(len(sizes))+0.35, [to_binary(s) for s in sizes])
    pyplot.xlabel('Transfer size')
    pyplot.ylabel('Throughput (bps)')

    pyplot.show()
