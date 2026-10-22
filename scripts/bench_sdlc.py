#!/usr/bin/env python3
"""Opt-in paid SDLC benchmark: plain host vs v1 pack vs lean pack (docs/agentic-v2-lean/README.md).

Every cell copies tests/bench/fixture into a fresh Git project outside any repository, installs the arm,
runs one native turn (plus at most one follow-up), and grades the result with deterministic checks:
hidden tests, the existing suite, lint, CHANGELOG, allowed files, and exact answers. Never bypasses
native trust or permissions.
"""
import argparse
import json
from pathlib import Path
import re
import shutil
import signal
import statistics
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import blackbox_jev  # noqa: E402
import pilot_jev  # noqa: E402
from pilot_jev import Meter, claude_cost, command, git, host_env, opencode_children, turn  # noqa: E402

BENCH = ROOT / 'tests/bench'
TASKS = json.loads((BENCH / 'tasks.json').read_text())
MODES = ('plain', 'v1', 'lean')
HOSTS = ('claude', 'codex', 'opencode')
SELECTION = ('software', 'software.backend,software.general')
# Per-mode medians compare the same task set; seeded tasks (T5) run on plain/lean only and get their own table.
SUMMARY_TASKS = tuple(t for t in TASKS if not TASKS[t].get('seed'))
# Outside any repository, so no parent AGENTS.md/CLAUDE.md leaks into a run; Codex trusts hooks per path.
PROJECTS = Path('/tmp/agentic-bench')
RUN_SECONDS = 480
RUN_UNCACHED_TOKENS = 80_000
EDIT_TOOLS = {'edit', 'write', 'multiedit', 'notebookedit', 'patch', 'apply_patch'}
SPAWN_TOOLS = {'agent', 'task', 'subagent'}
CHECK_COMMAND = re.compile(r'make (test|lint)|unittest|pytest|tools/lint\.py')
IGNORED = ('.agentic/', '.agentic-blackbox/', '.reviews/', '.review/')
AUTHOR = ['-c', 'user.name=Agentic Bench', '-c', 'user.email=bench@localhost']


def binary(mode, args):
    return args.v1_binary if mode == 'v1' else ROOT / 'target/debug/agentic'


def copy_fixture(task, project):
    """Fresh Git project from the shared fixture plus the task's optional seed overlay."""
    if project.exists():
        shutil.rmtree(project)
    shutil.copytree(BENCH / 'fixture', project, ignore=shutil.ignore_patterns('__pycache__'))
    if TASKS[task].get('seed'):
        shutil.copytree(BENCH / TASKS[task]['seed'], project, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__'))
    git(project, 'init', '-q')
    git(project, 'add', '-A')
    git(project, *AUTHOR, 'commit', '-q', '-m', 'bench: fixture')


def prepare(host, task, mode, args):
    project = PROJECTS / f'{host}-{task}-{mode}'
    copy_fixture(task, project)
    if mode != 'plain':
        result = subprocess.run([str(binary(mode, args)), 'install', '--project-dir', str(project), '--agent-os', host,
                                 '--areas', SELECTION[0], '--specializations', SELECTION[1], '--no-doctor'],
                                capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError('agentic install failed: ' + result.stderr[-400:])
        git(project, 'add', '-A')
        git(project, *AUTHOR, 'commit', '-q', '-m', 'bench: agentic install')
    return project


def run_make(project, target):
    result = subprocess.run(['make', '-s', target], cwd=project, capture_output=True, text=True, timeout=120,
                            env={**pilot_jev.os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    return result.returncode == 0, (result.stdout + result.stderr)[-600:]


def changed_files(project):
    out = git(project, 'status', '--porcelain', '--untracked-files=all')
    files = [line[3:].strip('"') for line in out.splitlines()]
    return [f for f in files if '__pycache__/' not in f and not f.endswith('.pyc')]


def unreleased(text):
    match = re.search(r'^## Unreleased\n(.*?)(?=^## |\Z)', text, re.S | re.M)
    return [line for line in (match.group(1) if match else '').splitlines() if line.strip().startswith(('-', '*'))]


def grade(task, project, final_text):
    """Deterministic acceptance; hidden tests are copied in only after the agent finished."""
    spec = TASKS[task]
    changed = changed_files(project)
    scoped = [f for f in changed if not f.startswith(IGNORED)]
    checks = {}
    green_test, test_log = run_make(project, 'test')
    green_lint, lint_log = run_make(project, 'lint')
    delivered_green = green_test and green_lint
    for check in spec['checks']:
        if check == 'suite':
            checks[check] = green_test
        elif check == 'lint':
            checks[check] = green_lint
        elif check == 'changelog':
            checks[check] = len(unreleased((project / 'CHANGELOG.md').read_text())) > 0
        elif check == 'allowlist':
            checks[check] = all(f.startswith(tuple(spec['allowlist'])) for f in scoped)
        elif check == 'untouched':
            untouched = not any(f in scoped for f in spec.get('untouched', []))
            kept = all(symbol in (project / path).read_text() for path, symbols in spec.get('keep_symbols', {}).items()
                       for symbol in symbols)
            checks[check] = untouched and kept
        elif check == 'answer':
            checks[check] = all(word.split('/')[-1] in final_text for word in spec['answer'])
        elif check == 'no_changes':
            checks[check] = not scoped
    if 'hidden_tests' in spec['checks']:
        for test in (BENCH / spec['hidden']).glob('*.py'):
            shutil.copy2(test, project / 'tests' / test.name)
        hidden = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.', '-p', 'test_hidden_*.py'],
                                cwd=project, capture_output=True, text=True, timeout=120,
                                env={**pilot_jev.os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        checks['hidden_tests'] = hidden.returncode == 0
        test_log += hidden.stderr[-600:]
    return {'accepted': all(checks.values()), 'checks': checks, 'delivered_green': delivered_green,
            'changed': changed[:30], 'outside_allowlist': [f for f in scoped if 'allowlist' in spec and not f.startswith(tuple(spec['allowlist']))],
            'log': (test_log + lint_log)[-1200:]}


def trace_events(host, trace):
    """Ordered (kind, detail) actions of the top-level session: edit, command, spawn; plus the final text."""
    events, texts = [], []
    for raw in trace.read_text(errors='replace').splitlines():
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        if host == 'claude':
            if event.get('type') == 'assistant' and not event.get('parent_tool_use_id'):
                for block in (event.get('message') or {}).get('content') or []:
                    if block.get('type') == 'tool_use':
                        name, data = block.get('name', '').lower(), block.get('input') or {}
                        events.append(classify(name, data.get('command', '')))
                    elif block.get('type') == 'text':
                        texts.append(block.get('text', ''))
            if event.get('type') == 'result' and event.get('result'):
                texts.append(event['result'])
        elif host == 'codex':
            item = event.get('item') or {}
            if event.get('type') == 'item.completed':
                if item.get('type') == 'command_execution':
                    events.append(('command', item.get('command', '')))
                elif item.get('type') == 'file_change':
                    events.append(('edit', ''))
                elif item.get('type') == 'agent_message':
                    texts.append(item.get('text', ''))
                elif item.get('type') == 'collab_tool_call' or 'spawn' in str(item.get('tool', '')):
                    events.append(('spawn', ''))
        else:
            part = event.get('part') or {}
            if part.get('type') == 'tool':
                data = (part.get('state') or {}).get('input') or {}
                events.append(classify(part.get('tool', '').lower(), data.get('command', '')))
            elif part.get('type') == 'text':
                texts.append(part.get('text', ''))
    return [e for e in events if e], '\n'.join(texts)


def classify(name, cmd):
    if name in EDIT_TOOLS:
        return ('edit', '')
    if name in SPAWN_TOOLS:
        return ('spawn', '')
    if name in ('bash', 'shell'):
        return ('command', cmd)
    return None


def verified_after_edit(events):
    """Did the top-level session run a test or lint command after its last edit (or edit nothing)?"""
    last_edit = max((i for i, (kind, _) in enumerate(events) if kind == 'edit'), default=-1)
    return last_edit < 0 or any(kind == 'command' and CHECK_COMMAND.search(detail) for kind, detail in events[last_edit + 1:])


def start_opencode(project, env, name):
    port = 4800 + abs(hash(name)) % 500
    server = f'http://127.0.0.1:{port}'
    process = subprocess.Popen(['opencode', 'serve', '--hostname', '127.0.0.1', '--port', str(port)], cwd=project, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    for _ in range(60):
        try:
            urllib.request.urlopen(server + '/', timeout=1)
            break
        except OSError:
            time.sleep(.5)
    return process, server


def run_cell(host, task, mode, args):
    cell = args.out / f'{host}-{task}-{mode}'
    cell.mkdir(parents=True, exist_ok=True)
    project = prepare(host, task, mode, args)
    env, trace, server_process, server = host_env(host, project), cell / 'trace.jsonl', None, None
    trace.write_text('')
    if host == 'opencode':
        server_process, server = start_opencode(project, env, cell.name)
    started = time.time()
    meter, deadline = Meter(host, project, started), time.monotonic() + args.seconds
    argv = command(host, project, server)
    if host == 'claude':
        # Account connectors (claude.ai MCP) attach unevenly between runs; keep every arm on the same tools.
        argv = [*argv, '--strict-mcp-config']
    text = TASKS[task]['prompt']
    code, reason = turn(argv + ([text] if host == 'codex' else []), None if host == 'codex' else text, project, env, trace, meter, deadline)
    turns = 1
    events, final_text = trace_events(host, trace)
    stopped_early = not changed_files(project) and TASKS[task]['kind'] != 'question'
    if not reason and stopped_early and time.monotonic() < deadline - 30:
        # The coordinator stopped for approval without changing anything; answer it once.
        followup = blackbox_jev.followup_turn(host, shutil.which(host), argv, trace)
        if followup:
            if host == 'codex':
                followup = ([followup[0][0], '--no-daemon', 'exec', 'resume', '--json', '--skip-git-repo-check',
                             '-c', 'sandbox_mode="danger-full-access"', *followup[0][-2:]], None)
            turns += 1
            code, reason = turn(*followup, project, env, trace, meter, deadline)
            events, final_text = trace_events(host, trace)
    if host == 'opencode':
        opencode_children(trace, server, env, meter)
        pilot_jev.os.killpg(server_process.pid, signal.SIGKILL)
    if pilot_jev.QUOTA.search(trace.read_text(errors='replace')):
        result = {'host': host, 'task': task, 'mode': mode, 'status': 'quota_exhausted', 'elapsed_s': round(time.time() - started, 1)}
        (cell / 'result.json').write_text(json.dumps(result, indent=2))
        return result
    verdict = grade(task, project, final_text)
    rows = meter.rows()
    measured = [r for r in rows if r.get('uncached') is not None]
    subagents = sum(1 for kind, _ in events if kind == 'spawn')
    if host == 'codex':
        subagents = max(subagents, sum(1 for r in rows if r.get('agent_path', '/root') != '/root'))
    if host == 'opencode':
        subagents = max(subagents, len(meter.sessions))
    result = {'host': host, 'task': task, 'mode': mode, 'status': 'accepted' if verdict['accepted'] else (reason or 'rejected'),
              'cap': reason, 'exit': code, 'turns': turns, 'elapsed_s': round(time.time() - started, 1), 'acceptance': verdict,
              'verified_after_edit': verified_after_edit(events), 'subagents': subagents,
              'tokens': {'uncached': sum(r['uncached'] for r in measured), 'cached': sum(r['cached'] for r in measured),
                         'complete': len(measured) == len(rows) and bool(rows), 'agents': rows},
              'cost_usd': claude_cost(trace) if host == 'claude' else None}
    (cell / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def regrade(out):
    """Grade saved cells again with the current tasks.json; hidden tests copied by the first grading are removed."""
    for path in sorted(Path(out).glob('*/result.json')):
        result = json.loads(path.read_text())
        project = PROJECTS / path.parent.name
        if 'acceptance' not in result or not project.is_dir():
            continue
        for copied in (project / 'tests').glob('test_hidden_*.py'):
            copied.unlink()
        events, final_text = trace_events(result['host'], path.parent / 'trace.jsonl')
        result['acceptance'] = grade(result['task'], project, final_text)
        result['verified_after_edit'] = verified_after_edit(events)
        result['subagents'] = max(result.get('subagents') or 0, sum(1 for kind, _ in events if kind == 'spawn'))
        result['status'] = 'accepted' if result['acceptance']['accepted'] else (result.get('cap') or 'rejected')
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(json.dumps({'cell': path.parent.name, 'status': result['status']}), flush=True)


def selftest():
    """Offline grader check: the untouched fixture fails every task; the reference solutions pass."""
    failures = []
    for task in TASKS:
        for solved in (False, True):
            project = PROJECTS / f'selftest-{task}-{int(solved)}'
            copy_fixture(task, project)
            answer = ''
            if solved:
                reference = BENCH / 'reference' / task
                for source in reference.rglob('*'):
                    if source.is_file() and source.name != 'answer.txt':
                        target = project / source.relative_to(reference)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, target)
                answer = (reference / 'answer.txt').read_text() if (reference / 'answer.txt').is_file() else ''
            verdict = grade(task, project, answer)
            if verdict['accepted'] != solved:
                failures.append(f'{task} solved={solved}: {verdict["checks"]}')
            shutil.rmtree(project)
    print('\n'.join(failures) or f'bench selftest: ok ({len(TASKS)} tasks)')
    return 1 if failures else 0


def input_tokens(tokens):
    return (tokens.get('uncached') or 0) + (tokens.get('cached') or 0) if tokens.get('uncached') is not None else ''


def median(values):
    values = [v for v in values if v is not None]
    return statistics.median(values) if values else None


def report(out, path):
    """Markdown table per host/task/mode plus the K-criteria summary of docs/agentic-v2-lean/README.md."""
    cells = [json.loads(p.read_text()) for p in sorted(Path(out).glob('*/result.json'))]
    # Uncached alone depends on prompt-cache hits between runs; Input (uncached + cached) is the context size.
    lines = ['| Host | Task | Mode | Status | Input | Uncached | Cached | Cost $ | Turns | Subagents | Green | Verified | Failed checks |',
             '|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for c in sorted(cells, key=lambda c: (c['host'], c['task'], MODES.index(c['mode']))):
        acceptance = c.get('acceptance') or {}
        failed = [k for k, v in (acceptance.get('checks') or {}).items() if not v]
        tokens = c.get('tokens') or {}
        cost = c.get('cost_usd')
        lines.append(f"| {c['host']} | {c['task']} | {c['mode']} | {c['status']} | {input_tokens(tokens)} | {tokens.get('uncached', '')} | {tokens.get('cached', '')} | "
                     f"{'' if cost is None else round(cost, 3)} | {c.get('turns', '')} | {c.get('subagents', '')} | "
                     f"{acceptance.get('delivered_green', '')} | {c.get('verified_after_edit', '')} | {', '.join(failed)} |")
    lines += ['', '| Host | Mode | Accepted | Green | Median input | Median uncached | Median cost $ |',
              '|---|---|---|---|---|---|---|']
    for host in HOSTS:
        for mode in MODES:
            group = [c for c in cells if c['host'] == host and c['mode'] == mode and c['status'] != 'quota_exhausted'
                     and c['task'] in SUMMARY_TASKS]
            if group:
                accepted = sum(c['status'] == 'accepted' for c in group)
                green = sum(bool((c.get('acceptance') or {}).get('delivered_green')) for c in group)
                full = median([input_tokens(c.get('tokens') or {}) or None for c in group])
                tokens = median([(c.get('tokens') or {}).get('uncached') for c in group])
                cost = median([c.get('cost_usd') for c in group])
                lines.append(f"| {host} | {mode} | {accepted}/{len(group)} | {green}/{len(group)} | {full} | {tokens} | "
                             f"{'' if cost is None else round(cost, 3)} |")
    seeded = [c for c in cells if c['task'] not in SUMMARY_TASKS and c['status'] != 'quota_exhausted']
    if seeded:
        lines += ['', '| Seeded task | Host | Mode | Status | Green | Input |', '|---|---|---|---|---|---|']
        for c in sorted(seeded, key=lambda c: (c['task'], c['host'], MODES.index(c['mode']))):
            lines.append(f"| {c['task']} | {c['host']} | {c['mode']} | {c['status']} | "
                         f"{(c.get('acceptance') or {}).get('delivered_green', '')} | {input_tokens(c.get('tokens') or {})} |")
    Path(path).write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / '.agentic-blackbox/bench')
    parser.add_argument('--hosts', default=','.join(HOSTS))
    parser.add_argument('--tasks', default=','.join(TASKS))
    parser.add_argument('--modes', default=','.join(MODES))
    parser.add_argument('--v1-binary', type=Path, default=ROOT / 'target/bench-v1/target/debug/agentic')
    parser.add_argument('--model', action='append', default=[], help='host=model override, for example claude=opus')
    parser.add_argument('--seconds', type=int, default=RUN_SECONDS)
    parser.add_argument('--cap', type=int, default=RUN_UNCACHED_TOKENS, help='Uncached tokens per cell')
    parser.add_argument('--prepare-only', action='store_true', help='Create copies and installs; no model calls')
    parser.add_argument('--selftest', action='store_true', help='Check graders against tests/bench/reference; no model calls')
    parser.add_argument('--report', type=Path, help='Write the Markdown report from --out and exit')
    parser.add_argument('--regrade', action='store_true', help='Grade saved cells again with the current tasks.json')
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    if args.regrade:
        regrade(args.out)
        return 0
    if args.report:
        report(args.out, args.report)
        return 0
    pilot_jev.RUN_UNCACHED_TOKENS = args.cap
    for override in args.model:
        host, _, model = override.partition('=')
        pilot_jev.COORDINATOR[host] = model
    modes = args.modes.split(',')
    if 'v1' in modes and not args.v1_binary.is_file():
        sys.exit(f'[bench] missing v1 binary {args.v1_binary}; run `make bench-v1`')
    for host in args.hosts.split(','):
        for task in args.tasks.split(','):
            for mode in modes:
                name = f'{host}-{task}-{mode}'
                if args.prepare_only:
                    print(json.dumps({'cell': name, 'project': str(prepare(host, task, mode, args))}), flush=True)
                    continue
                previous = args.out / name / 'result.json'
                if previous.exists() and json.loads(previous.read_text()).get('status') != 'quota_exhausted':
                    continue  # never repeat a completed cell for a preferred result
                try:
                    result = run_cell(host, task, mode, args)
                except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                    result = {'host': host, 'task': task, 'mode': mode, 'status': 'harness_error', 'reason': str(error)[-400:]}
                    (args.out / name).mkdir(parents=True, exist_ok=True)
                    (args.out / name / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
                print(json.dumps({k: result.get(k) for k in ('host', 'task', 'mode', 'status', 'elapsed_s', 'turns', 'subagents')}
                                 | {'uncached': (result.get('tokens') or {}).get('uncached')}, ensure_ascii=False), flush=True)
                if result.get('status') == 'quota_exhausted':
                    break
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
