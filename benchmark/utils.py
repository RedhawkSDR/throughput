import math

_SI_PREFIXES = ['', 'K', 'M', 'G', 'T']

def _from_si_prefix(value, base):
    if value[-1].isalpha():
        suffix = value[-1].upper()
        value = value[:-1]
        index = _SI_PREFIXES.index(suffix)
        scale = base**index
    else:
        scale = 1
    return value, scale

def _to_si_prefix(value, base):
    index = int(math.floor(math.log(value, base)))
    return (value/math.pow(base, index), _SI_PREFIXES[index])

def from_binary(value):
    value, scale = _from_si_prefix(value, 1024)
    return int(value)*scale

def to_binary(value):
    return '%d%s' % _to_si_prefix(value, 1024)

def time_to_sec(value):
    scale = 1.0
    if value[-1].isalpha():
        suffix = value[-1].lower()
        value = value[:-1]
        if suffix == 'm':
            scale = 60.0
        elif suffix == 's':
            scale = 1.0
    return float(value)*scale

def to_gbps(value):
    return '%.2f' % (value/(1024**3))

def to_percent(value):
    return '%.1f' % (value*100.0)

