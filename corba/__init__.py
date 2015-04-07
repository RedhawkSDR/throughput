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
    def __init__(self, endpoint, orb, format, bufsize, numa_policy):
        reader_args = numa_policy(['corba/reader'] + endpoint)
        self.reader_proc = subprocess.Popen(reader_args, stdout=subprocess.PIPE)
        ior = self.reader_proc.stdout.readline().rstrip()
        self.reader = orb.string_to_object(ior)

        writer_args = numa_policy(['corba/writer'] + endpoint)
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
            self.endpoint = ['-ORBendPoint', 'giop:unix:']
        else:
            self.endpoint = ['-ORBendPoint', 'giop:tcp::']
        self.orb = omniORB.CORBA.ORB_init()

    def create(self, data_format, transfer_size, numa_policy):
        return CorbaThroughputTest(self.endpoint, self.orb, data_format, transfer_size, numa_policy)

def factory(transport):
    return CorbaTestFactory(transport)
