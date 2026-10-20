#!/usr/bin/env python3
"""Refresh reports/coverage-scorecard.jsx from measured data and render images/coverage_scorecard.png.

Sources: the areas/ catalog, reports/area-quality.json (static checks) and the anonymized
docs/jev-integration/epic/pilot-results.json (real runs). Nothing is estimated by hand.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import tempfile
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
JSX = ROOT / 'reports/coverage-scorecard.jsx'
QUALITY = ROOT / 'reports/area-quality.json'
PILOT = ROOT / 'docs/jev-integration/epic/pilot-results.json'
PNG = ROOT / 'images/coverage_scorecard.png'
VERSION = ROOT / 'package.json'
# Hosts whose configs ship with agentic; verified ones additionally appear in the pilot results.
HOSTS = [('Codex', 'CX', 'codex'), ('Claude Code', 'CC', 'claude'), ('OpenCode', 'OC', 'opencode'),
         ('Antigravity', 'AG', None), ('Gemini', 'GM', None), ('Cursor', 'CU', None), ('Kilocode', 'KC', None)]
MODE_TITLES = {'plain': 'Plain agent (no agentic)', 'fixed': 'Agentic, fixed workflow', 'jev': 'Agentic + JEV routing',
               'workflow_only': 'JEV workflow only', 'models_only': 'JEV models only'}
PILOT_FIELDS = ('host', 'host_version', 'task', 'mode', 'status', 'elapsed_s', 'turns', 'uncached', 'cached', 'cost_usd', 'jev_calls', 'jev_tokens')


def export_pilot(runs, versions):
    """Anonymized per-cell results: task labels only, no paths, prompts or outputs."""
    cells = []
    for path in sorted(Path(runs).glob('*/result.json')):
        r = json.loads(path.read_text())
        if 'tokens' not in r:
            continue
        jev = r.get('jev') or {}
        usage = jev.get('usage') or {}
        cells.append({'host': r['host'], 'host_version': versions.get(r['host']), 'task': r['task'], 'mode': r['mode'],
                      'status': r['status'], 'elapsed_s': r.get('elapsed_s'), 'turns': r.get('turns'),
                      'uncached': r['tokens']['uncached'], 'cached': r['tokens']['cached'],
                      'cost_usd': round(r['cost_usd'], 4) if r.get('cost_usd') else None,
                      'jev_calls': jev.get('calls', 0), 'jev_tokens': usage.get('input_tokens', 0) + usage.get('output_tokens', 0)})
    PILOT.write_text(json.dumps({'date': time.strftime('%Y-%m-%d'), 'protocol': 'pilot_acceptance.md', 'cells': cells}, indent=2) + '\n')


def catalog(verified):
    specs = {area: sorted(p.name for p in (ROOT / 'areas' / area).iterdir() if p.is_dir()) for area in ('software', 'devops')}
    return {'specs': sum(map(len, specs.values())), 'software': len(specs['software']), 'devops': len(specs['devops']),
            'roles': len(list((ROOT / 'extensions/claude/agents').glob('*.md'))),
            'skills': len(list((ROOT / 'areas').rglob('SKILL.md'))),
            'workflows': len([p for p in (ROOT / 'areas').rglob('*.md') if p.parent.name == 'workflows']),
            'rules': len([p for p in (ROOT / 'areas').rglob('*.md') if p.parent.name == 'rules']),
            'hosts_verified': len(verified), 'hosts_configured': len(HOSTS)}


def quality():
    rows = json.loads(QUALITY.read_text())
    by_spec = {}
    for row in rows:
        by_spec.setdefault(row['specialization'], []).append(row['score'])
    specs = []
    for spec, scores in sorted(by_spec.items()):
        area, name = spec.split('/')[1:3]
        specs.append({'id': spec, 'area': area, 'name': name, 'score': round(statistics.mean(scores))})
    return {'overall': round(statistics.mean(r['score'] for r in rows)), 'specs': specs}


def pilot(cells):
    modes = []
    for mode, title in MODE_TITLES.items():
        rows = [c for c in cells if c['mode'] == mode]
        if rows:
            modes.append({'mode': mode, 'title': title, 'runs': len(rows), 'accepted': sum(c['status'] == 'accepted' for c in rows),
                          'median_uncached': round(statistics.median(c['uncached'] for c in rows)),
                          'median_seconds': round(statistics.median(c['elapsed_s'] for c in rows))})
    by = {m['mode']: m for m in modes}
    headline = 'No pilot runs yet.'
    if 'plain' in by and 'fixed' in by:
        ratio = by['fixed']['median_uncached'] / max(1, by['plain']['median_uncached'])
        headline = (f"Small, bounded tasks: a plain agent was cheapest. The agentic team used {ratio:.1f}× its tokens — "
                    "the price of shared process and guardrails, not yet a saving.")
    hosts = sorted({c['host'] for c in cells})
    return {'cells': len(cells), 'headline': headline, 'modes': modes,
            'note': f"Hosts: {', '.join(hosts)} · tasks: infra feasibility, code review, calculator · cap 50k uncached tokens and 6 min per run."}


def hosts(cells):
    out = []
    for name, short, key in HOSTS:
        runs = [c for c in cells if c['host'] == key]
        if runs:
            out.append({'name': name, 'short': short, 'status': 'verified',
                        'detail': f"v{runs[0]['host_version']} · {len(runs)} pilot runs · {sum(c['status'] == 'accepted' for c in runs)} accepted"})
        else:
            out.append({'name': name, 'short': short, 'status': 'configs', 'detail': 'agents, rules and workflows ship; no recorded run yet'})
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
        image.crop((0, 0, image.width, min(image.height, bottom + 26))).save(PNG, optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot-runs', type=Path, help='Pilot run directory to export anonymized results from')
    parser.add_argument('--host-versions', default='{}', help='JSON {"codex": "0.163.0", ...} for the export')
    parser.add_argument('--no-render', action='store_true')
    args = parser.parse_args()
    if args.pilot_runs:
        export_pilot(args.pilot_runs, json.loads(args.host_versions))
    cells = json.loads(PILOT.read_text())['cells'] if PILOT.exists() else []
    verified = {c['host'] for c in cells}
    write_jsx({'date': json.loads(PILOT.read_text())['date'] if PILOT.exists() else time.strftime('%Y-%m-%d'),
               'version': json.loads(VERSION.read_text())['version'], 'catalog': catalog(verified), 'hosts': hosts(cells),
               'quality': quality(), 'pilot': pilot(cells)})
    if not args.no_render:
        render()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
