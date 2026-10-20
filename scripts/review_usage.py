#!/usr/bin/env python3
"""Summarize explicitly supplied usage records; never discover native session data.

Each bounded record describes one agent instance/model or one JEV request. Adapters
must map native counters to this schema and mark child-inclusive totals explicitly.
Unknown counters remain None. This helper does not collect telemetry.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict

COUNTERS = ('input_tokens', 'cached_input_tokens', 'output_tokens', 'reasoning_tokens')


def measured(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def usage_row(records):
    """Count only proven, disjoint counters for an instance and model."""
    first = records[0]
    row = {key: first.get(key) for key in ('agent_id', 'role', 'model')}
    row.update(source=sorted({str(r.get('source', '')) for r in records}),
               cutoff=sorted({str(r.get('cutoff', '')) for r in records}))
    unknown = dict.fromkeys((*COUNTERS, 'total_tokens'))
    row.update(unknown)
    seen = {}
    for record in records:
        identity = record.get('event_id')
        if not identity or not record.get('source') or not record.get('cutoff'):
            return row
        if identity in seen and seen[identity] != record:
            return row
        seen[identity] = record
    records = list(seen.values())
    kinds = {r.get('kind') for r in records}
    if kinds == {'cumulative'}:
        if not all(measured(r.get('sequence')) for r in records):
            return row
        latest = max(r['sequence'] for r in records)
        selected = [r for r in records if r['sequence'] == latest]
        if len(selected) != 1:
            return row
        records = selected
    elif kinds != {'delta'}:
        return row
    if any(r.get('scope', 'self') != 'self' for r in records):
        row['limitation'] = 'child-inclusive or unknown scope; excluded to avoid double counting'
        return row
    for record in records:
        if any(record.get(key) is not None and not measured(record[key]) for key in COUNTERS):
            return row
        for subset, total in (('cached_input_tokens', 'input_tokens'),
                              ('reasoning_tokens', 'output_tokens')):
            if (record.get(subset) is not None and record.get(total) is not None
                    and record[subset] > record[total]):
                return row
    for key in COUNTERS:
        values = [r.get(key) for r in records]
        row[key] = sum(values) if all(measured(v) for v in values) else None
    if measured(row['input_tokens']) and measured(row['output_tokens']):
        row['total_tokens'] = row['input_tokens'] + row['output_tokens']
    return row


def totals(rows):
    values = [row['total_tokens'] for row in rows if measured(row['total_tokens'])]
    return dict(total_tokens=sum(values) if values else None,
                partial=any(row['total_tokens'] is None for row in rows))


def summarize(records):
    """Return per-instance/model rows and separate JEV usage without estimates."""
    groups = defaultdict(list)
    jev = defaultdict(list)
    for record in records:
        if record.get('channel') == 'jev':
            # Request IDs, never role or temporal proximity, identify API calls.
            identity = record.get('request_id')
            if not identity:
                raise ValueError('JEV records require request_id')
            jev[identity].append(record)
        else:
            if not all(record.get(key) for key in ('agent_id', 'role', 'model')):
                raise ValueError('usage records require agent_id, role and model')
            groups[(record['agent_id'], record['model'])].append(record)
    rows = [usage_row(group) for group in groups.values()]
    jev_rows = [usage_row(group) for group in jev.values()]
    return dict(rows=rows, **totals(rows),
                jev=dict(requests=len(jev), rows=jev_rows, **totals(jev_rows)))


if __name__ == '__main__':
    json.dump(summarize(json.load(sys.stdin)), sys.stdout, indent=2)
    sys.stdout.write('\n')
