import sys
import time
import getopt
import math
import numpy
import itertools

import numa
from procinfo import StatTracker

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
        self.reader_stats = [StatTracker(t.get_reader().pid) for t in self.tests]
        self.writer_stats = [StatTracker(t.get_writer().pid) for t in self.tests]

    def start(self):
        for test in self.tests:
            test.start()

    def stop(self):
        for test in self.tests:
            test.stop()

    def get_reader_stats(self):
        return [s.poll() for s in self.reader_stats]

    def get_writer_stats(self):
        return [s.poll() for s in self.writer_stats]

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
    def add_sample(self, rate, size, read_cpu, write_cpu, **kw):
        peak = self.stats.get_max_value('rate')
        print '%s %s %.3f %.1f %.1f' % (to_binary(size), to_gbps(rate), rate/peak, read_cpu, write_cpu)


class TextDisplay(object):
    def add_results(self, name, stats, average):
        best = average.get_max_sample('rate')
        print 'Average:', to_binary(best['size']), to_gbps(best['rate'])
        peak = stats.get_max_sample('rate')
        print 'Peak:   ', to_binary(peak['size']), to_gbps(peak['rate'])

    def show(self):
        pass

class PlotDisplay(object):
    def __init__(self):
        from matplotlib import pyplot
        globals()['pyplot'] = pyplot

        self.figure = pyplot.figure()

        # Create a line plot of instantaneous throughput vs. time
        self.line_plot = self.figure.add_subplot(221)
        self.line_plot.set_xlabel('Time (s)')
        self.line_plot.set_ylabel('Throughput (bps)')

        # Create a bar graph of average throughput vs. transfer size
        self.bar_plot = self.figure.add_subplot(223)
        self.bar_plot.set_xlabel('Transfer size')
        self.bar_plot.set_ylabel('Throughput (bps)')

        self.reader_cpu = self.figure.add_subplot(224)
        self.reader_cpu.set_xlabel('Time (s)')
        self.reader_cpu.set_ylabel('Reader CPU (%)')

        self.writer_cpu = self.figure.add_subplot(222)
        self.writer_cpu.set_xlabel('Time (s)')
        self.writer_cpu.set_ylabel('Writer CPU (%)')

        pyplot.show(False)

        self.width = 0.5
        self.offset = 0.0

    def add_results(self, name, stats, average):
        times = stats.get_field('time')
        rates = stats.get_field('rate')
        line, = self.line_plot.plot(times, rates, label=name)
        peak = stats.get_max_sample('rate')
        self.line_plot.axhline(peak['rate'], color=line.get_color())
        best = average.get_max_sample('rate')
        self.line_plot.axhline(best['rate'], color=line.get_color(), linestyle='--')

        for group in stats.get_groups('size'):
            # Display vertical line at size change
            sample = group[0]
            self.line_plot.axvline(sample['time'], color=line.get_color(), linestyle='--')

        sizes = average.get_field('size')
        rates = average.get_field('rate')
        dev = average.get_field('dev')
        self.bar_plot.bar(numpy.arange(len(sizes))+self.offset, rates, color=line.get_color(), width=self.width, yerr=dev, ecolor='black')
        self.bar_plot.set_xticks(numpy.arange(len(sizes))+0.5)
        self.bar_plot.set_xticklabels([to_binary(s) for s in sizes])
        self.offset += self.width

        read_cpu = stats.get_field('read_cpu')
        self.reader_cpu.plot(times, read_cpu, label=name)

        write_cpu = stats.get_field('write_cpu')
        self.writer_cpu.plot(times, write_cpu, label=name)

        pyplot.draw()

    def show(self):
        pyplot.show()


def test_transfer_size(test):
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

        # Aggregate CPU usage
        reader = test.get_reader_stats()
        writer = test.get_writer_stats()
        read_cpu = sum(r['cpu%'] for r in reader)
        write_cpu = sum(r['cpu%'] for r in writer)

        sample = {'time': now-start,
                  'rate': current_rate,
                  'size': transfer_size,
                  'read_cpu': read_cpu,
                  'write_cpu': write_cpu}
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

    if nogui:
        display = TextDisplay()
    else:
        display = PlotDisplay()

    for interface in ('raw', 'corba'):
        if interface == 'raw':
            factory = raw.factory(transport)
        elif interface == 'corba':
            factory = corba.factory(transport)

        numa_policy = numa.NumaPolicy(numa_distance)

        test = AggregateTest(factory, data_format, transfer_size, numa_policy, count)
        try:
            stats, average = test_transfer_size(test)
        finally:
            test.terminate()

        display.add_results(interface, stats, average)

        filename = interface+'.csv'
        with open(filename, 'w') as f:
            print >>f, 'time(s),rate(Bps),transfer size(B),writer cpu(%),reader cpu(%)'
            for s in stats.samples:
                print >>f, '%f,%f,%d,%f,%f' % (s['time'], s['rate'], s['size'], s['write_cpu'], s['read_cpu'])

    display.show()
