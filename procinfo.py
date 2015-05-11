__all__ = ('CpuInfo', 'ProcessInfo')

class CpuInfo(object):
    FIELDS = [
        ('user', int),
        ('nice', int),
        ('system', int),
        ('idle', int),
        ('iowait', int),
        ('irq', int),
        ('softirq', int),
        ('steal', int),
        ('guest', int)
        ]

    def __init__(self):
        self._last = self._scan()  

    def _scan(self):
        with open('/proc/stat', 'r') as f:
            # Skip the first field, which is just "cpu"
            status = f.readline().strip().split()[1:]
        results = {}
        for (name, format), value in zip(self.FIELDS, status):
            results[name] = format(value)
        return results

    def poll(self):
        stats = self._scan()

        results = {}
        for (name, _) in self.FIELDS:
            results[name] = stats[name] - self._last[name]

        self._last = stats

        return results


class ProcessInfo(object):
    FIELDS = [
        ('pid', int),
        ('comm', str),
        ('state', str),
        ('ppid', int),
        ('pgrp', int),
        ('session', int),
        ('tty_nr', str),
        ('tpgid', str),
        ('flags', str),
        ('minflt', int),
        ('cminflt', int),
        ('majflt', int),
        ('cmajflt', int),
        ('utime', int),
        ('stime', int),
        ('cutime', int),
        ('cstime', int),
        ('priority', int),
        ('nice', int),
        ('num_threads', int),
        ('itrealvalue', str),
        ('starttime', int),
        ('vsize', int),
        ('rss', int),
        ('rsslim', int),
        ('startcode', int),
        ('endcode', int),
        ('startstack', int),
        ('kstkesp', str),
        ('kstkeip', str),
        ('signal', int),
        ('blocked', int),
        ('sigignore', str),
        ('sigcatch', str),
        ('wchan', str),
        ('nswap', str),
        ('cnswap', str),
        ('exit_signal', str),
        ('processor', int),
        ('rt_priority', int),
        ('policy', str),
        ('delayacct_blkio_ticks', str),
        ('guest_time', str),
        ('cguest_time', str)
    ]

    def __init__(self, pid):
        self._pid = pid
        self._statfile = '/proc/%d/stat' % (pid,)
        self._last = self._scan()

    def _scan(self):
        with open(self._statfile, 'r') as f:
            status = f.readline().strip().split()
        results = {}
        for (name, format), value in zip(self.FIELDS, status):
            results[name] = format(value)
        return results

    def poll(self):
        status = self._scan()

        # Calculate CPU usage
        d_utime = status['utime'] - self._last['utime']
        d_stime = status['stime'] - self._last['stime']
        d_majflt = status['majflt'] - self._last['majflt']
        d_minflt = status['minflt'] - self._last['minflt']

        results = {
            'utime': d_utime,
            'stime': d_stime,
            'cpu': d_utime+d_stime,
            'rss' : status['rss'],
            'majflt': d_majflt,
            'minflt': d_minflt,
            'threads': status['num_threads']
        }

        # Update last measurements
        self._last = status

        return results
