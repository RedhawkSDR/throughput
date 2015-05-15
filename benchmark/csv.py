from benchmark.tests import TestMonitor

class CSVOutput(TestMonitor):
    def __init__(self):
        self.fields = []

    def add_field(self, key, header=None):
        if header is None:
            header = key
        self.fields.append((key, header))

    def test_started(self, name, **kw):
        filename = name.lower() + '.csv'
        self.file = open(filename, 'w')
        print >>self.file, ','.join(title for name, title in self.fields)

    def sample_added(self, **stats):
        print >>self.file, ','.join(str(stats[name]) for name, title in self.fields)

    def test_complete(self, **kw):
        self.file.close()
