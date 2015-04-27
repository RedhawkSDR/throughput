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

if __name__ == '__main__':
    transfer_size = 16*1024
    interface = 'raw'
    transport = 'unix'
    numa_distance = None
    data_format = 'octet'
    poll_time = 0.1
    window_size = 10
    tolerance = 0.1

    opts, args = getopt.getopt(sys.argv[1:], 'w:t:d:', ['transport=', 'interface=', 'numa-distance='])
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

    numa_policy = numa.NumaPolicy(numa_distance)
    max_window_size = window_size*2

    if interface == 'raw':
        factory = raw.factory(transport)
    elif interface == 'corba':
        factory = corba.factory(transport)
    else:
        raise SystemExit('No interface '+interface)

    test = factory.create(data_format, transfer_size, numa_policy.next())
    test.start()

    start = time.time()

    now = start
    last_time = start
    last_total = 0

    current = []

    best_rate = 0.0
    best_size = 0

    peak_rate = 0.0
    peak_size = 0

    while transfer_size < (64*1024*1024):
        time.sleep(poll_time)
        now = time.time()
        elapsed = now - last_time
        last_time = now

        current_total = test.received
        delta = current_total - last_total
        last_total = current_total
        current_rate = delta / elapsed
        current.append(current_rate)

        if current_rate > peak_rate:
            peak_rate = current_rate
            peak_size = transfer_size

        # Adapt transfer rate
        current = current[-window_size:]
        average = numpy.average(current)
        ratio = current_rate / average
        # Get the normalized standard deviation
        dev = numpy.std(current)/average
        if best_rate > 0.0:
            best_ratio = average/best_rate
        else:
            best_ratio = 1.0
        print to_gbps(current_rate), to_gbps(average), '%.2f' % best_ratio, '%.3f' % dev
        if len(current) < window_size:
            # Require minimum number of samples
            continue
        if len(current) < max_window_size and dev > tolerance:
            # Try to wait for measurements to stabilize
            continue
        if average > best_rate:
            best_rate = average
            best_size = transfer_size
        if len(current) >= max_window_size:
            break
        if best_ratio < 0.90:
            break
        current = []
        transfer_size *= 2
        test.transfer_size(transfer_size)
        print 'Transfer size', to_binary(transfer_size)

    print 'Average:', to_binary(best_size), to_gbps(best_rate)
    print 'Peak:   ', to_binary(peak_size), to_gbps(peak_rate)

    test.stop()
    test.terminate()
