import subprocess
import omniORB

import rawdata

__all__ = ('factory')

class CorbaThroughputTest(object):
    def __init__(self, orbargs, orb, format, numa_policy):
        reader_args = numa_policy(['corba/reader'] + orbargs)
        self.reader_proc = subprocess.Popen(reader_args, stdout=subprocess.PIPE)
        ior = self.reader_proc.stdout.readline().rstrip()
        self.reader = orb.string_to_object(ior)

        writer_args = numa_policy(['corba/writer'] + orbargs)
        self.writer_proc = subprocess.Popen(writer_args, stdout=subprocess.PIPE)
        ior = self.writer_proc.stdout.readline().rstrip()
        self.writer = orb.string_to_object(ior)

        self.writer.connect(self.reader, format)

    def start(self):
        self.writer.start()

    def stop(self):
        self.writer.stop()

    def get_reader(self):
        return self.reader_proc.pid

    def get_writer(self):
        return self.writer_proc.pid

    def transfer_size(self, size):
        self.writer.transfer_length(size)

    @property
    def received(self):
        return self.reader.received()

    def terminate(self):
        self.reader_proc.terminate()
        self.writer_proc.terminate()
        self.reader_proc.kill()
        self.writer_proc.kill()
        self.reader_proc.wait()
        self.reader_proc.wait()

class CorbaTestFactory(object):
    def __init__(self, transport):
        if transport == 'unix':
            self.orbargs = ['-ORBendPoint', 'giop:unix:']
        else:
            self.orbargs = ['-ORBendPoint', 'giop:tcp::']
        self.orbargs += [ '-ORBgiopMaxMsgSize', str(50*1024*1024)]
        self.orb = omniORB.CORBA.ORB_init()

    def create(self, data_format, numa_policy):
        return CorbaThroughputTest(self.orbargs, self.orb, data_format, numa_policy)

    def cleanup(self):
        self.orb.destroy()

def factory(transport):
    return CorbaTestFactory(transport)
