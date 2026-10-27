#!/usr/bin/env python3
"""Refresh reports/coverage-scorecard.jsx from measured data and render images/coverage_scorecard.png.

Sources: the areas/ catalog, reports/area-quality.json (scripts/assess_area_quality.py), the findings of
scripts/check_artifacts.py, the always-on budget
(scripts/context_budget.py --all-selections, needs `make build`) and reports/bench-round6.json (benchmark round 6,
copied from docs/agentic-v2-lean/results.md). Nothing is estimated by hand.

Rendering needs google-chrome or chromium (headless) with network access to unpkg.com, and Pillow.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
JSX = ROOT / 'reports/coverage-scorecard.jsx'
QUALITY = ROOT / 'reports/area-quality.json'
BENCH = ROOT / 'reports/bench-round6.json'
PNG = ROOT / 'images/coverage_scorecard.png'
VERSION = ROOT / 'package.json'
BUDGET_HOSTS = ('claude', 'codex', 'opencode')
# Hosts whose configs ship with agentic; verified ones have benchmark evidence in BENCH.
HOSTS = [('Codex', 'CX', 'codex'), ('Claude Code', 'CC', 'claude'), ('OpenCode', 'OC', 'opencode'),
         ('Antigravity', 'AG', None), ('Gemini', 'GM', None), ('Cursor', 'CU', None), ('Kilocode', 'KC', None)]


def specs():
    return {area: sorted(p.name for p in (ROOT / 'areas' / area).iterdir() if p.is_dir() and p.name != 'template')
            for area in ('software', 'devops')}


def catalog(budget, verified):
    found = specs()
    return {'specs': sum(map(len, found.values())), 'software': len(found['software']), 'devops': len(found['devops']),
            'rules': len(list((ROOT / 'areas').glob('*/*/rules/*.md'))),
            'skills': len(list((ROOT / 'areas').glob('*/*/skills/*/SKILL.md'))),
            'workflows': len(list((ROOT / 'areas').glob('*/*/workflows/*.md'))),
            'budget': budget, 'hosts_verified': verified, 'hosts_configured': len(HOSTS)}


def always_on(path):
    """Largest always-on estimate per host over every selection of context_budget.py --all-selections."""
    if path is None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'budget.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/context_budget.py'), '--all-selections', '--json', str(path)],
                           check=True, stdout=subprocess.DEVNULL)
            report = json.loads(path.read_text())
    else:
        report = json.loads(Path(path).read_text())
    per_host = {host: max(sel[host]['total'] for sel in report.values()) for host in BUDGET_HOSTS}
    host = max(per_host, key=per_host.get)
    return {'max': per_host[host], 'host': host, 'per_host': per_host, 'selections': len(report)}


def quality():
    rows = json.loads(QUALITY.read_text())
    by_spec = {}
    for row in rows:
        by_spec.setdefault(row['specialization'], []).append(row['score'])
    out = []
    for spec, scores in sorted(by_spec.items()):
        area, name = spec.split('/')[1:3]
        out.append({'id': spec, 'area': area, 'name': name, 'score': round(statistics.mean(scores))})
    environments = len({row['environment'] for row in rows})
    check = subprocess.run([sys.executable, str(ROOT / 'scripts/check_artifacts.py'), '--no-baseline', '--no-budget', '--json'],
                           capture_output=True, text=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    findings = len(json.loads(check.stdout)['findings'])
    return {'overall': round(statistics.mean(r['score'] for r in rows)), 'environments': environments,
            'artifact_findings': findings, 'specs': out}


def bench(data):
    rows = []
    for row in data['rows']:
        per_run = row['cost_usd'] / row['runs'] if row['cost_basis'] == 'total' else row['cost_usd'] * row['accepted'] / row['runs']
        rows.append({k: row[k] for k in ('task', 'host', 'mode', 'accepted', 'runs')} | {'cost_per_run': round(per_run, 3)})
    return {'cells': sum(r['runs'] for r in rows), 'headline': data['headline'], 'models': data['models'],
            'rows': rows, 'notes': data['notes'], 'source': data['source'].split('#')[0]}


def hosts(evidence):
    out = []
    for name, short, key in HOSTS:
        if key in evidence:
            item = evidence[key]
            out.append({'name': name, 'short': short, 'status': 'verified', 'detail': f"v{item['version']} · {item['evidence']}"})
        else:
            out.append({'name': name, 'short': short, 'status': 'configs', 'detail': 'configs ship; no recorded run yet'})
    return out


def write_jsx(data):
    text = JSX.read_text()
    block = '// DATA:BEGIN\nconst DATA = ' + json.dumps(data, indent=2, ensure_ascii=False) + ';\n// DATA:END'
    JSX.write_text(re.sub(r'// DATA:BEGIN.*?// DATA:END', lambda _: block, text, flags=re.S))


def render():
    """Headless Chrome screenshot of the JSX through React and Babel UMD builds; the page background is trimmed."""
    source = JSX.read_text().replace('import React from "react";', '').replace('export default function App', 'function App')
    page = f'''<!doctype html><html><head><meta charset="utf-8">
<script src="https://unpkg.com/react@18.3.1/umd/react.production.min.js"></script>
<script src="https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js"></script>
<script src="https://unpkg.com/@babel/standalone@7.26.4/babel.min.js"></script>
<style>body{{margin:0;background:#0b1020}}</style></head><body><div id="root"></div>
<script type="text/babel">{source}
ReactDOM.createRoot(document.getElementById("root")).render(<App />);</script></body></html>'''
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        raise SystemExit('google-chrome or chromium is required to render the PNG (use --no-render to update the JSX only)')
    with tempfile.TemporaryDirectory() as tmp:
        html, shot = Path(tmp) / 'scorecard.html', Path(tmp) / 'shot.png'
        html.write_text(page)
        subprocess.run([chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1',
                        '--window-size=1400,1400', '--virtual-time-budget=15000', f'--screenshot={shot}', html.as_uri()],
                       check=True, capture_output=True, timeout=120)
        image = Image.open(shot).convert('RGB')
        background = image.getpixel((5, image.height - 5))
        bottom = image.height
        while bottom > 200 and all(image.getpixel((x, bottom - 1)) == background for x in range(0, image.width, 7)):
            bottom -= 1
        if bottom <= 200:
            raise SystemExit('the rendered page is empty; check network access to unpkg.com')
        image.crop((0, 0, image.width, min(image.height, bottom + 26))).save(PNG, optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--budget-json', type=Path, help='Saved context_budget.py --all-selections --json output')
    parser.add_argument('--date', default=time.strftime('%Y-%m-%d'))
    parser.add_argument('--no-render', action='store_true')
    args = parser.parse_args()
    data = json.loads(BENCH.read_text())
    write_jsx({'date': args.date, 'version': json.loads(VERSION.read_text())['version'],
               'catalog': catalog(always_on(args.budget_json), len(data['hosts'])), 'hosts': hosts(data['hosts']),
               'quality': quality(), 'bench': bench(data)})
    if not args.no_render:
        render()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
