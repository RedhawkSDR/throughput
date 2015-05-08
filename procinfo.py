import time
import commands

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

NUM_CPUS = int(commands.getoutput('nproc'))

__all__ = ('StatTracker',)

class StatTracker(object):
    def __init__(self, pid):
        self._pid = pid
        self._statfile = '/proc/%d/stat' % (pid,)

        self._lastStatus, self._lastCputime = self._scan()

    def _scan(self):
        with open(self._statfile, 'r') as f:
            status = f.readline().strip().split()
        with open('/proc/stat', 'r') as f:
            cputime = sum(int(x) for x in f.readline().strip().split()[1:])
        if len(status) > len(FIELDS):
            status = status[:len(FIELDS)]
        results = {}
        for (name, format), value in zip(FIELDS[:len(status)], status):
            results[name] = format(value)
        return results, cputime

    def poll(self):
        status, cputime = self._scan()

        # Calculate CPU usage
        d_utime = status['utime'] - self._lastStatus['utime']
        d_stime = status['stime'] - self._lastStatus['stime']
        d_cputime = cputime - self._lastCputime
        if d_cputime > 0:
            utime = 100.0 * d_utime / d_cputime * NUM_CPUS
            stime = 100.0 * d_stime / d_cputime * NUM_CPUS
        else:
            utime = 0.0
            stime = 0.0

        d_majflt = status['majflt'] - self._lastStatus['majflt']
        d_minflt = status['minflt'] - self._lastStatus['minflt']

        results = {
            'utime%': utime,
            'stime%': stime,
            'cpu%': utime+stime,
            'rss' : status['rss'],
            'majflt': d_majflt,
            'minflt': d_minflt,
            'threads': status['num_threads']
        }

        # Update last measurements
        self._lastStatus = status
        self._lastCputime = cputime

        return results
