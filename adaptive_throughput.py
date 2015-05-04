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


class SampleWindow(object):
    def __init__(self, window_size, tolerance):
        self.values = []
        self.window_size = window_size
        self.max_window_size = 2 * self.window_size
        self.tolerance = tolerance

    def add_sample(self, value):
        self.values.append(value)

    def is_stable(self):
        if len(self.values) < self.window_size:
            return False
        elif len(self.values) >= self.max_window_size:
            return True

        return self.variance() <= self.tolerance

    def average(self):
        return numpy.average(self.values)

    def variance(self):
        return numpy.std(self.values)/self.average()

    def reset(self):
        self.values = []


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

    stats = SampleWindow(window_size, tolerance)

    test = AggregateTest(factory, data_format, transfer_size, numa_policy, count)
    test.start()

    start = time.time()

    now = start
    last_time = start
    last_total = 0

    best_rate = 0.0
    best_size = 0

    peak_rate = 0.0
    peak_size = 0

    times = []
    rates = []
    sizes = [(transfer_size, 0)]

    while transfer_size < (64*1024*1024):
        time.sleep(poll_time)
        now = time.time()
        elapsed = now - last_time
        last_time = now

        current_total = test.received()
        delta = current_total - last_total
        last_total = current_total
        current_rate = delta / elapsed
        stats.add_sample(current_rate)

        times.append(now-start)
        rates.append(current_rate)

        if current_rate > peak_rate:
            peak_rate = current_rate
            peak_size = transfer_size

        average = stats.average()
        ratio = current_rate / average
        # Get the normalized standard deviation
        if best_rate > 0.0:
            best_ratio = average/best_rate
        else:
            best_ratio = 1.0
        print to_gbps(current_rate), to_gbps(average), '%.2f' % best_ratio, '%.3f' % stats.variance()
        if not stats.is_stable():
            continue
        elif average >= best_rate:
            best_rate = average
            best_size = transfer_size
        if best_ratio < 0.90:
            break
        stats.reset()

        # Adapt transfer size
        transfer_size *= 2
        test.transfer_size(transfer_size)
        sizes.append((transfer_size, len(times)))
        print 'Transfer size', to_binary(transfer_size)

    test.stop()
    test.terminate()

    print 'Average:', to_binary(best_size), to_gbps(best_rate)
    print 'Peak:   ', to_binary(peak_size), to_gbps(peak_rate)

    if nogui:
        sys.exit(0)

    from matplotlib import pyplot

    pyplot.plot(times, rates)
    pyplot.xlabel('Time (s)')
    pyplot.ylabel('Throughput (bps)')
    for size, index in sizes:
        # Display vertical line at size change
        pyplot.axvline(times[index], linestyle='--')
    pyplot.show()
