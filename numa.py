import os

def _parse_range(line):
    first, last = line.split('-')
    return range(int(first), int(last)+1)

def _parse_values(line):
    values = []
    for section in line.split(','):
        values.extend(_parse_range(section))
    return values

def get_nodes():
    with open('/sys/devices/system/node/online') as f:
        line = f.readline().strip()
        return _parse_values(line)

def get_cpus(node):
    with open('/sys/devices/system/node/node%d/cpulist'%node) as f:
        line = f.readline().strip()
        return _parse_values(line)
