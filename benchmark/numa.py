import os
import subprocess
import itertools

def _parse_range(line):
    first, last = line.split('-')
    return range(int(first), int(last)+1)

def _parse_values(line, delim):
    values = []
    for section in line.split(delim):
        if '-' in section:
            values.extend(_parse_range(section))
        else:
            values.append(int(section))
    return values

def get_nodes():
    with open('/sys/devices/system/node/online') as f:
        line = f.readline().strip()
        return _parse_values(line, ',')

def get_cpus(node):
    with open('/sys/devices/system/node/node%d/cpulist'%node) as f:
        line = f.readline().strip()
        return _parse_values(line, ',')

def get_distances(node):
    with open('/sys/devices/system/node/node%d/distance'%node) as f:
        line = f.readline().strip()
        return _parse_values(line, ' ')

def get_distance(node, dest):
    return get_distances(node)[dest]

class NumaWrapper(object):
    def __init__(self, nodes, distance=None):
        if distance is None:
            self.nodes = itertools.repeat(None)
        elif distance == 0:
            self.nodes = itertools.repeat(nodes.next())
        else:
            self.nodes = itertools.islice(nodes, 0, None, distance)

    def __call__(self, command, *args, **kwargs):
        node = self.nodes.next()
        if node is None:
            return command
        else:
            if isinstance(command, basestring):
                command = [command]
            return ['numactl', '--cpunodebind=%d' % node] + command

class NumaPolicy(object):
    def __init__(self, distance=None):
        self.nodes = itertools.cycle(get_nodes())
        self.distance = distance

    def next(self):
        return NumaWrapper(self.nodes, self.distance)
