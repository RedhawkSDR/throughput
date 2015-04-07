import os
import signal
import subprocess

__all__ = ('factory')

class RawThroughputTest(object):
    def __init__(self, transport, transfer_size, numa_policy):
        self.received = 0

        writer_args = numa_policy(['raw/writer', transport, str(transfer_size)])
        self.writer_proc = subprocess.Popen(writer_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        writer_addr = self.writer_proc.stdout.readline().rstrip()

        reader_args = numa_policy(['raw/reader', transport, writer_addr, str(transfer_size)])
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

class RawTestFactory(object):
    def __init__(self, transport):
        self.transport = transport

    def create(self, format, transfer_size, numa_policy):
        return RawThroughputTest(self.transport, transfer_size, numa_policy)

def factory(transport):
    return RawTestFactory(transport)
