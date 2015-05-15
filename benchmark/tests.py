class TestMonitor(object):
    def test_started(self, **kw):
        pass

    def test_complete(self, **kw):
        pass

    def pass_started(self, **kw):
        pass

    def sample_added(self, **kw):
        pass

    def pass_complete(self, **kw):
        pass


class BenchmarkTest(object):
    def __init__(self):
        self.monitors = []
        self.__idle_tasks = []

    def add_monitor(self, monitor):
        self.monitors.append(monitor)

    def test_started(self, **kw):
        for monitor in self.monitors:
            monitor.test_started(**kw)

    def test_complete(self, **kw):
        for monitor in self.monitors:
            monitor.test_complete(**kw)

    def pass_started(self, **kw):
        for monitor in self.monitors:
            monitor.pass_started(**kw)

    def pass_complete(self, **kw):
        for monitor in self.monitors:
            monitor.pass_complete(**kw)

    def sample_added(self, **kw):
        for monitor in self.monitors:
            monitor.sample_added(**kw)

    def add_idle_task(self, task):
        self.__idle_tasks.append(task)

    def idle_tasks(self):
        for task in self.__idle_tasks:
            task()
