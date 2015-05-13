class AggregateStream(object):
    def __init__(self, factory, data_format, transfer_size, numa_policy, count):
        self.streams = [factory.create(data_format, transfer_size, numa_policy.next()) for ii in xrange(count)]
        self.reader_stats = [ProcessInfo(s.get_reader()) for s in self.streams]
        self.writer_stats = [ProcessInfo(s.get_writer()) for s in self.streams]

    def start(self):
        for stream in self.streams:
            stream.start()

    def stop(self):
        for stream in self.streams:
            stream.stop()

    def get_reader_stats(self):
        return [s.poll() for s in self.reader_stats]

    def get_writer_stats(self):
        return [s.poll() for s in self.writer_stats]

    def received(self):
        return sum(stream.received for stream in self.streams)

    def transfer_size(self, length):
        for stream in self.streams:
            stream.transfer_size(length)

    def terminate(self):
        for stream in self.streams:
            stream.terminate()
