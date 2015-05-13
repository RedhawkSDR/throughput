import os

__all__ = ('factory')

PATH = os.path.dirname(__file__)

class NumaLauncher(object):
    def __init__(self, policy):
        self.policy = policy

    def isInteractive(self):
        return False

    def modifiesCommand(self):
        return True

    def canAttach(self):
        return False

    def wrap(self, command, arguments):
        command = self.policy([command] + arguments)
        return command[0], command[1:]


class BulkioStream(object):
    def __init__(self, format, numa_policy):
        launcher = NumaLauncher(numa_policy)
        self.writer = sb.launch(os.path.join(PATH, 'writer/writer.spd.xml'), debugger=launcher)
        self.reader = sb.launch(os.path.join(PATH, 'reader/reader.spd.xml'), debugger=launcher)
        self.writer.connect(self.reader)

    def start(self):
        sb.start()

    def stop(self):
        sb.stop()

    def get_reader(self):
        return self.reader._process.pid()

    def get_writer(self):
        return self.writer._process.pid()

    def transfer_size(self, size):
        self.writer.transfer_length = size

    def received(self):
        return int(self.reader.received)

    def terminate(self):
        self.writer.releaseObject()
        self.reader.releaseObject()

class BulkioStreamFactory(object):
    def __init__(self, transport):
        configfile = 'config/omniORB-%s.cfg' % transport
        os.environ['OMNIORB_CONFIG'] = os.path.join(PATH, configfile)
        from ossie.utils import sb
        globals()['sb'] = sb

    def create(self, format, numa_policy):
        return BulkioStream(format, numa_policy)

    def cleanup(self):
        pass

def factory(transport):
    return BulkioStreamFactory(transport)
