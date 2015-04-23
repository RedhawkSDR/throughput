import sys
import os
import time
import subprocess
import getopt
import omniORB
import itertools

import rawdata

__all__ = ('factory')

class CorbaThroughputTest(object):
    def __init__(self, orbargs, orb, format, bufsize, numa_policy):
        reader_args = numa_policy(['corba/reader'] + orbargs)
        self.reader_proc = subprocess.Popen(reader_args, stdout=subprocess.PIPE)
        ior = self.reader_proc.stdout.readline().rstrip()
        self.reader = orb.string_to_object(ior)

        writer_args = numa_policy(['corba/writer'] + orbargs)
        self.writer_proc = subprocess.Popen(writer_args, stdout=subprocess.PIPE)
        ior = self.writer_proc.stdout.readline().rstrip()
        self.writer = orb.string_to_object(ior)

        self.writer.connect(self.reader, format, bufsize)

    def start(self):
        self.writer.start()

    def stop(self):
        self.writer.stop()

    @property
    def received(self):
        return self.reader.received()

    def terminate(self):
        self.reader_proc.terminate()
        self.writer_proc.terminate()

class CorbaTestFactory(object):
    def __init__(self, transport):
        if transport == 'unix':
            self.orbargs = ['-ORBendPoint', 'giop:unix:']
        else:
            self.orbargs = ['-ORBendPoint', 'giop:tcp::']
        self.orbrgs += [ '-ORBgiopMaxMsgSize', str(50*1024*1024)]
        self.orb = omniORB.CORBA.ORB_init()

    def create(self, data_format, transfer_size, numa_policy):
        return CorbaThroughputTest(self.orbargs, self.orb, data_format, transfer_size, numa_policy)

def factory(transport):
    return CorbaTestFactory(transport)
