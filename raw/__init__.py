import os
import signal
import subprocess
import mmap
import tempfile
import ctypes

__all__ = ('factory')

class control(object):
    def __init__(self, transfer_size):
        fd, self.filename = tempfile.mkstemp()
        os.ftruncate(fd, 12)
        self.buf = mmap.mmap(fd, 12, mmap.MAP_SHARED, mmap.PROT_WRITE)
        os.close(fd)
        self.total_bytes = ctypes.c_uint64.from_buffer(self.buf)
        self.total_bytes.value = 0
        self.transfer_size = ctypes.c_uint32.from_buffer(self.buf, 8)
        self.transfer_size.value = transfer_size

    def __del__(self):
        os.unlink(self.filename)


class RawThroughputTest(object):
    def __init__(self, transport, numa_policy):
        self.writer_control = control(16384)
        writer_args = numa_policy(['raw/writer', transport, self.writer_control.filename])
        self.writer_proc = subprocess.Popen(writer_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        writer_addr = self.writer_proc.stdout.readline().rstrip()

        self.reader_control = control(16384)
        reader_args = numa_policy(['raw/reader', transport, writer_addr, self.reader_control.filename])
        self.reader_proc = subprocess.Popen(reader_args)

    def start(self):
        self.writer_proc.stdin.write('\n')

    def stop(self):
        os.kill(self.writer_proc.pid, signal.SIGINT)

    def get_reader(self):
        return self.reader_proc.pid

    def get_writer(self):
        return self.writer_proc.pid

    def transfer_size(self, size):
        self.writer_control.transfer_size.value = size
        self.reader_control.transfer_size.value = size

    @property
    def received(self):
        return self.reader_control.total_bytes.value

    def terminate(self):
        # Assuming stop() was already called, the reader and writer should have
        # already exited
        self.writer_proc.kill()
        self.reader_proc.kill()
        self.writer_proc.wait()
        self.reader_proc.wait()

class RawTestFactory(object):
    def __init__(self, transport):
        self.transport = transport

    def create(self, format, numa_policy):
        return RawThroughputTest(self.transport, numa_policy)

    def cleanup(self):
        pass

def factory(transport):
    return RawTestFactory(transport)
