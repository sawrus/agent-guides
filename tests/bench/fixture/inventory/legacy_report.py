"""Accounting export. TODO: modernize this module (f-strings, dataclasses, type hints)."""


def report(stock):
    lines = []
    keys = list(stock.levels.keys())
    keys.sort()
    for i in range(0, len(keys)):
        k = keys[i]
        lines.append('%s\t%d\t%d' % (k, stock.levels[k], stock.reserved.get(k, 0)))
    return '\n'.join(lines)
