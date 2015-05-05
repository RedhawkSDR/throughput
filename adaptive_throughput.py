import sys
import time
import getopt
import math
import numpy
import itertools

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

        def add_sample(self, **sample):
            pass

    def __init__(self):
        self.samples = []
        self.listeners = []

    def add_listener(self, listener):
        self.listeners.append(listener)

    def add_sample(self, sample):
        self.samples.append(sample)

        for listener in self.listeners:
            listener.add_sample(**sample)

    def get_max_sample(self, field):
        return max(self.samples, key=lambda s:s[field])

    def get_max_value(self, field):
        return self.get_max_sample(field)[field]

    def get_field(self, field):
        return [s[field] for s in self.samples]

    def get_groups(self, field):
        return [list(g) for k, g in itertools.groupby(self.samples, lambda s:s[field])]


class Averager(Statistics.Listener):
    def __init__(self, stats, window_size):
        Statistics.Listener.__init__(self, stats)
        self.values = []
        self.window_size = window_size
        self.max_window_size = 2 * self.window_size

    def add_sample(self, rate, **kw):
        self.values.append(rate)

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
    def add_sample(self, rate, size, **kw):
        peak = self.stats.get_max_value('rate')
        print '%s %s %.3f' % (to_binary(size), to_gbps(rate), rate/peak)


def test_transfer_size(test):
    test.start()

    transfer_size = 16*1024

    stats = Statistics()
    window = Averager(stats, window_size)
    plotter = TextPlotter(stats)

    average = Statistics()

    test.start()

    start = time.time()
    next = start + poll_time

    now = start
    last_time = start
    last_total = 0

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
        sample = {'time': now-start,
                  'rate': current_rate,
                  'size': transfer_size}
        stats.add_sample(sample)

        # Wait until window is stable (or it's taken long enough that we can
        # assume it will never stabilize) to make decisions
        if not window.is_stable(tolerance):
            continue

        # Add the windowed average throughput to the stats
        current_average = window.average()
        # NB: Account for the fact that the variance is normalized
        current_dev = window.variance()*current_average
        sample = {'rate': current_average,
                  'size': transfer_size,
                  'dev':  current_dev}
        average.add_sample(sample)

        # Get the normalized standard deviation
        best_rate = average.get_max_value('rate')
        best_ratio = current_average / best_rate
        if best_ratio < 0.90:
            break

        # Adapt transfer size
        transfer_size *= 2
        test.transfer_size(transfer_size)
        window.reset()

    test.stop()
    
    return stats, average


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

    test = AggregateTest(factory, data_format, transfer_size, numa_policy, count)
    try:
        stats, average = test_transfer_size(test)
    finally:
        test.terminate()

    best = average.get_max_sample('rate')
    print 'Average:', to_binary(best['size']), to_gbps(best['rate'])
    peak = stats.get_max_sample('rate')
    print 'Peak:   ', to_binary(peak['size']), to_gbps(peak['rate'])

    if nogui:
        sys.exit(0)

    from matplotlib import pyplot

    # Create a line plot of instantaneous throughput vs. time
    pyplot.subplot(211)
    times = stats.get_field('time')
    rates = stats.get_field('rate')
    pyplot.plot(times, rates)
    pyplot.xlabel('Time (s)')
    pyplot.ylabel('Throughput (bps)')
    pyplot.axhline(peak['rate'], color='red')
    pyplot.axhline(best['rate'], color='red', linestyle='--')

    for group in stats.get_groups('size'):
        # Display vertical line at size change
        sample = group[0]
        pyplot.axvline(sample['time'], linestyle='--')

    # Create a bar graph of average throughput vs. transfer size
    pyplot.subplot(212)
    sizes = average.get_field('size')
    rates = average.get_field('rate')
    dev = average.get_field('dev')
    pyplot.bar(numpy.arange(len(sizes)), rates, yerr=dev, ecolor='black')
    pyplot.xticks(numpy.arange(len(sizes))+0.35, [to_binary(s) for s in sizes])
    pyplot.xlabel('Transfer size')
    pyplot.ylabel('Throughput (bps)')

    pyplot.show()
