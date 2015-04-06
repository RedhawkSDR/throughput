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

    writer_args = ['./writer', transport, str(transfer_size)]
    writer_proc = subprocess.Popen(writer_args, stdout=subprocess.PIPE)
    writer_addr = writer_proc.stdout.readline().rstrip()

    reader_args = ['./reader', writer_addr, str(transfer_size)]
    reader_proc = subprocess.Popen(reader_args, stdout=subprocess.PIPE)

    time.sleep(time_period)
    os.kill(writer_proc.pid, signal.SIGINT)
    
    read_count = int(reader_proc.stdout.readline().rstrip())
    print read_count
