import os
import sys
import signal
import subprocess
import time
import getopt

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

class IpcThroughputTest(object):
    def __init__(self, transport, transfer_size):
        self.received = 0

        writer_args = ['./writer', transport, str(transfer_size)]
        self.writer_proc = subprocess.Popen(writer_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        writer_addr = self.writer_proc.stdout.readline().rstrip()

        reader_args = ['./reader', transport, writer_addr, str(transfer_size)]
        self.reader_proc = subprocess.Popen(reader_args, stdout=subprocess.PIPE)

    def start(self):
        self.writer_proc.stdin.write('\n')

    def stop(self):
        os.kill(self.writer_proc.pid, signal.SIGINT)
        self.received = int(self.reader_proc.stdout.readline().rstrip())

    def terminate(self):
        # Assuming stop() was already called, the reader and writer should have
        # already exited
        self.writer_proc.kill()
        self.reader_proc.kill()

if __name__ == '__main__':
    transfer_size = 1024
    transport = 'unix'
    time_period = 10.0
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

    tests = [IpcThroughputTest(transport, transfer_size) for ii in xrange(count)]

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

