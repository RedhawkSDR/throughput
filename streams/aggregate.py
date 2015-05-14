class AggregateStream(object):
    def __init__(self, factory, data_format, numa_policy, count):
        self.streams = [factory.create(data_format, numa_policy.next()) for ii in xrange(count)]

    def start(self):
        for stream in self.streams:
            stream.start()

    def stop(self):
        for stream in self.streams:
            stream.stop()

    def received(self):
        return sum(stream.received() for stream in self.streams)

    def transfer_size(self, length):
        for stream in self.streams:
            stream.transfer_size(length)

    def terminate(self):
        for stream in self.streams:
            stream.terminate()
