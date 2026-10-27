#!/usr/bin/env python3
"""Typecheck the deployed adapter against the pinned real SDK, without executing it."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--sdk-dir', type=Path, required=True)
args = parser.parse_args()
sdk = args.sdk_dir.resolve()
package = sdk / 'node_modules/@opencode/plugin/package.json'
if not package.is_file() or json.loads(package.read_text())['version'] != '2.0.28':
    raise SystemExit('Install SDK 2.0.28 + typescript@5.8.2 + @types/node@22 into SDK_DIR first')
with tempfile.TemporaryDirectory(prefix='agentic-sdk-check-', dir=sdk) as directory:
    directory = Path(directory)
    sources = []
    for source in [ROOT / 'extensions/opencode/hooks/agentic-jev.ts', ROOT / 'extensions/opencode/plugins/agentic-gate.ts']:
        target = directory / source.name
        shutil.copyfile(source, target)
        sources.append(str(target))
    command = ['node', str(sdk / 'node_modules/typescript/bin/tsc'), '--noEmit', '--skipLibCheck',
               '--module', 'NodeNext', '--moduleResolution', 'NodeNext', '--target', 'ES2022',
               '--types', 'node', '--typeRoots', str(sdk / 'node_modules/@types'), *sources]
    raise SystemExit(subprocess.run(command, cwd=directory).returncode)
