import sys
import time
import getopt
import math
import numpy
import itertools

import numa
from procinfo import CpuInfo, ProcessInfo

from streams import raw, corba, bulkio

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


class Averager(object):
    def __init__(self, window_size):
        self.values = []
        self.window_size = window_size
        self.max_window_size = 2 * self.window_size

    def add_sample(self, value):
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


class TestMonitor(object):
    def test_started(self, **kw):
        pass

    def test_complete(self, **kw):
        pass

    def pass_started(self, **kw):
        pass

    def sample_added(self, **kw):
        pass

    def pass_complete(self, **kw):
        pass


class TextDisplay(TestMonitor):
    def test_started(self, name, **kw):
        self.best_rate = 0.0
        self.peak_rate = 0.0
        print 'Measuring', name

    def test_complete(self, **kw):
        print 'Average:', to_binary(self.best_size), to_gbps(self.best_rate)
        print 'Peak:   ', to_binary(self.peak_size), to_gbps(self.peak_rate)

    def pass_started(self, size, **kw):
        sys.stdout.write(to_binary(size))
        sys.stdout.flush()

    def sample_added(self, size, rate, **kw):
        if rate > self.peak_rate:
            self.peak_size = size
            self.peak_rate = rate
        sys.stdout.write('.')
        sys.stdout.flush()

    def pass_complete(self, size, rate, dev, **kw):
        if rate > self.best_rate:
            self.best_size = size
            self.best_rate = rate
        print '%s GBps (%.1f%%)' % (to_gbps(rate), 100.0*dev/rate)

    def wait(self):
        pass


class CSVOutput(TestMonitor):
    def __init__(self):
        self.fields = []

    def add_field(self, key, header):
        self.fields.append((key, header))

    def test_started(self, name, **kw):
        filename = name.lower() + '.csv'
        self.file = open(filename, 'w')
        print >>self.file, ','.join(title for name, title in self.fields)

    def sample_added(self, **stats):
        print >>self.file, ','.join(str(stats[name]) for name, title in self.fields)

    def test_complete(self, **kw):
        self.file.close()


class BarGraph(TestMonitor):
    def __init__(self, bins):
        from matplotlib import pyplot
        globals()['pyplot'] = pyplot

        self.figure = pyplot.figure()
        self.figure.canvas.set_window_title('REDHAWK Benchmark')

        # Create a bar graph of average throughput vs. transfer size
        self.bar_plot = self.figure.add_subplot(111)
        self.bar_plot.set_xlabel('Transfer size')
        self.bar_plot.set_ylabel('Throughput (Bps)')

        self.width = 1.0/3.0
        self.colors = itertools.cycle('bgrcmyk')

        self.bins = dict((bin, index) for index, bin in enumerate(bins))
        self.bar_plot.set_xticks(numpy.arange(len(self.bins))+0.5)
        self.bar_plot.set_xticklabels([to_binary(b) for b in bins])
        self.bar_plot.set_xbound(0.0, len(self.bins))

        self.series = []

        self.figure.show()

    def test_started(self, name, **kw):
        self.series.append({'name':name, 'color':self.colors.next()})

        # Create an updated legend. There are no bars for this series yet;
        # create an otherwise unused rectangle to provide the color for each
        # series.
        from matplotlib.patches import Rectangle
        bars = [Rectangle((0,0),0,0,facecolor=s['color']) for s in self.series]
        names = [s['name'] for s in self.series]
        self.bar_plot.legend(bars, names, loc='upper left')

    def pass_complete(self, size, rate, dev, **kw):
        offset = len(self.series) - 1
        color = self.series[offset]['color']
        self.draw_bar(size, rate, dev, offset, color)

    def wait(self):
        pyplot.show()

    def update(self):
        self.figure.canvas.flush_events()

    def draw_bar(self, bin, value, dev, offset, color):
        pos = self.bins[bin] + (offset*self.width)
        bar = self.bar_plot.bar([pos], [value], color=color, width=self.width, yerr=dev, ecolor='black')
        self.bar_plot.set_xbound(0.0, len(self.bins))
        self.figure.canvas.draw()


class BenchmarkTest(object):
    def __init__(self):
        self.monitors = []
        self.__idle_tasks = []

    def add_monitor(self, monitor):
        self.monitors.append(monitor)

    def test_started(self, **kw):
        for monitor in self.monitors:
            monitor.test_started(**kw)

    def test_complete(self, **kw):
        for monitor in self.monitors:
            monitor.test_complete(**kw)

    def pass_started(self, **kw):
        for monitor in self.monitors:
            monitor.pass_started(**kw)

    def pass_complete(self, **kw):
        for monitor in self.monitors:
            monitor.pass_complete(**kw)

    def sample_added(self, **kw):
        for monitor in self.monitors:
            monitor.sample_added(**kw)

    def add_idle_task(self, task):
        self.__idle_tasks.append(task)

    def idle_tasks(self):
        for task in self.__idle_tasks:
            task()


class TransferSizeTest(BenchmarkTest):
    def __init__(self, sizes, poll_time, window_size, tolerance):
        BenchmarkTest.__init__(self)
        self.sizes = sizes
        self.poll_time = poll_time
        self.window_size = window_size
        self.tolerance = tolerance

    def run(self, name, stream):
        window = Averager(self.window_size)

        reader_stats = ProcessInfo(stream.get_reader())
        writer_stats = ProcessInfo(stream.get_writer())

        num_cpus = sum(len(numa.get_cpus(n)) for n in numa.get_nodes())
        cpu_info = CpuInfo()

        self.test_started(name=name)

        stream.start()

        start = time.time()
        next = start + self.poll_time

        now = start
        last_time = start
        last_total = 0

        for transfer_size in self.sizes:
            self.pass_started(size=transfer_size)

            stream.transfer_size(transfer_size)
            window.reset()

            # Wait until window is stable (or it's taken long enough that we can
            # assume it will never stabilize) to make decisions
            while not window.is_stable(self.tolerance):
                # Allow UI to update, etc.
                self.idle_tasks()

                # Wait until next scheduled poll time
                sleep_time = next - time.time()
                next += self.poll_time
                if sleep_time > 0.0:
                    time.sleep(sleep_time)

                # Measure time elapsed since last sample
                now = time.time()
                elapsed = now - last_time
                last_time = now

                # Calculate average throughput over the sample period
                current_total = stream.received()
                delta = current_total - last_total
                last_total = current_total
                current_rate = delta / elapsed

                window.add_sample(current_rate)

                # Aggregate CPU usage
                reader = reader_stats.poll()
                writer = writer_stats.poll()

                system = cpu_info.poll()
                sys_cpu = num_cpus * 100.0 / sum(system.values())

                sample = {'time': now-start,
                          'rate': current_rate,
                          'size': transfer_size,
                          'write_cpu': writer['cpu'] * sys_cpu,
                          'write_rss': writer['rss'],
                          'write_majflt': writer['majflt'],
                          'write_minflt': writer['minflt'],
                          'write_threads': writer['threads'],
                          'read_cpu': reader['cpu'] * sys_cpu,
                          'read_rss': reader['rss'],
                          'read_majflt': reader['majflt'],
                          'read_minflt': reader['minflt'],
                          'read_threads': reader['threads'],
                          'cpu_user': system['user'] * sys_cpu,
                          'cpu_system': system['system'] * sys_cpu,
                          'cpu_idle': system['idle'] * sys_cpu,
                          'cpu_iowait': system['iowait'] * sys_cpu,
                          'cpu_irq': system['irq'] * sys_cpu,
                          'cpu_softirq': system['softirq'] * sys_cpu,
                          }
                self.sample_added(**sample)

            # Add the windowed average throughput to the stats
            current_average = window.average()
            # NB: Account for the fact that the variance is normalized
            current_dev = window.variance()*current_average
            sample = {'rate': current_average,
                      'size': transfer_size,
                      'dev':  current_dev}

            self.pass_complete(**sample)

        stream.stop()

        self.test_complete()


if __name__ == '__main__':
    transport = 'unix'
    numa_distance = None
    poll_time = 0.25
    window_size = 5
    tolerance = 0.1
    nogui = False

    opts, args = getopt.getopt(sys.argv[1:], 'w:t:d:', ['transport=', 'numa-distance=', 'no-gui'])
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
        elif key == '--no-gui':
            nogui = True

    # Try powers of two from 16K to 32M
    transfer_sizes = [2**x for x in xrange(14, 26)]
    test = TransferSizeTest(transfer_sizes, poll_time, window_size, tolerance)

    if nogui:
        display = TextDisplay()
    else:
        display = BarGraph(transfer_sizes)
        test.add_idle_task(display.update)
    test.add_monitor(display)

    csv = CSVOutput()
    csv.add_field('time', 'time(s)')
    csv.add_field('rate', 'rate(Bps)')
    csv.add_field('size', 'transfer size(B)')
    csv.add_field('write_cpu', 'writer cpu(%)')
    csv.add_field('write_rss', 'writer rss')
    csv.add_field('write_majflt', 'writer major faults')
    csv.add_field('write_minflt', 'writer minor faults')
    csv.add_field('write_threads', 'writer threads')
    csv.add_field('read_cpu', 'reader cpu(%)')
    csv.add_field('read_rss', 'reader rss')
    csv.add_field('read_majflt', 'reader major faults')
    csv.add_field('read_minflt', 'reader minor faults')
    csv.add_field('read_threads', 'reader threads')
    csv.add_field('cpu_user', 'user CPU(%)')
    csv.add_field('cpu_system', 'system CPU(%)')
    csv.add_field('cpu_idle', 'idle CPU(%)')
    csv.add_field('cpu_iowait', 'I/O wait CPU(%)')
    csv.add_field('cpu_irq', 'IRQ CPU(%)')
    csv.add_field('cpu_softirq', 'soft IRQ CPU(%)')

    test.add_monitor(csv)

    for interface in ('Raw', 'CORBA', 'BulkIO'):
        if interface == 'Raw':
            factory = raw.factory(transport)
        elif interface == 'CORBA':
            factory = corba.factory(transport)
        elif interface == 'BulkIO':
            factory = bulkio.factory(transport)

        numa_policy = numa.NumaPolicy(numa_distance)

        stream = factory.create('octet', numa_policy.next())
        try:
            test.run(interface, stream)
        finally:
            stream.terminate()

    display.wait()
