import sys
import signal
import time
import getopt

import numa
import raw

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

if __name__ == '__main__':
    transfer_size = 1024
    transport = 'unix'
    time_period = 10.0
    numa_distance = None
    count = 1

    opts, args = getopt.getopt(sys.argv[1:], 'n:s:t:', ['transport=', 'numa-distance='])
    for key, value in opts:
        if key == '-n':
            count = int(value)
        elif key == '-s':
            transfer_size = samples_to_int(value)
        elif key == '-t':
            time_period = time_to_sec(value)
        elif key == '--transport':
            transport = value
        elif key == '--numa-distance':
            numa_distance = int(value)

    numa_policy = numa.NumaPolicy(numa_distance)

    tests = [raw.RawThroughputTest(transport, transfer_size, numa_policy.next()) for ii in xrange(count)]

    start = time.time()
    for test in tests:
        test.start()
    time.sleep(time_period)
    for test in tests:
        test.stop()
    elapsed = time.time() - start

    aggregate_throughput = 0.0
    for test in tests:
        read_count = test.received
        test.terminate()
        aggregate_throughput += read_count/elapsed

    print 'Elapsed:', elapsed, 'sec'
    print 'Throughput:', aggregate_throughput / (1024**3), 'GBps'

