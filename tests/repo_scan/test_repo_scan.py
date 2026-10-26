"""Offline tests for tools/repo-scan on four small linked repositories (tests/repo_scan/fixtures).

Git repositories are created at test time in a temporary `work/<host>/<group>/...` tree.
"""
import contextlib
import io
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / 'tools/repo-scan'
sys.path.insert(0, str(TOOL))

from reposcan import applicability, cli, common, discover, metrics  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / 'fixtures'
HOST = 'gitlab.example.com'
LAYOUT = {
    'apiutil': 'team/pypi/apiutil',
    'rule-engine': 'team/antifraud-rules/rule-engine',
    'rule-catalog': 'team/antifraud-rules/rule-catalog',
    'bash-scripts': 'team/maintenance/bash-scripts',
}
NOW = '2026-10-01T00:00:00+00:00'
COMMIT_DATE = '2026-06-01T12:00:00+00:00'
SECRETS = ('fixture-db-pass', 'fixture-token-value-123', 'fixture-readme-secret')


def sh(*args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout


def make_workspace(base):
    work = Path(base) / 'work'
    env = dict(os.environ, GIT_AUTHOR_DATE=COMMIT_DATE, GIT_COMMITTER_DATE=COMMIT_DATE,
               GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.com', GIT_COMMITTER_NAME='t',
               GIT_COMMITTER_EMAIL='t@example.com', GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')
    for name, rel in LAYOUT.items():
        repo = work / HOST / rel
        shutil.copytree(FIXTURES / name, repo)
        sh('git', 'init', '-q', '-b', 'main', cwd=repo, env=env)
        sh('git', 'remote', 'add', 'origin', f'git@{HOST}:{rel}.git', cwd=repo, env=env)
        sh('git', 'add', '-A', cwd=repo, env=env)
        sh('git', 'commit', '-q', '-m', 'init', cwd=repo, env=env)
    return work / HOST / 'team'


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


def rid(name):
    return f'{HOST}/{LAYOUT[name]}'


class ScanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='repo-scan-test-')
        cls.root = make_workspace(cls.tmp)
        cls.out = Path(cls.tmp) / 'out'
        code, cls.stdout, _ = run_cli('scan', str(cls.root), '--out', str(cls.out), '--now', NOW, '--no-scc')
        assert code == 0, cls.stdout
        cls.repos = {r['id']: r for r in json.loads((cls.out / 'repositories.json').read_text())['repositories']}
        cls.rel = json.loads((cls.out / 'relationships.json').read_text())
        cls.guides = json.loads((cls.out / 'guide-applicability.json').read_text())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def edge(self, src, dst, kind):
        found = [e for e in self.rel['edges'] if e['from'] == rid(src) and e['to'] == rid(dst) and e['kind'] == kind]
        self.assertEqual(len(found), 1, json.dumps(self.rel['edges'], indent=1))
        return found[0]

    def test_outputs_exist(self):
        for name in ('repositories.json', 'relationships.json', 'guide-applicability.json', 'graph.mmd'):
            self.assertTrue((self.out / name).is_file(), name)
        graph = (self.out / 'graph.mmd').read_text()
        self.assertIn('flowchart LR', graph)
        self.assertIn('-->|library', graph)

    def test_discovery_and_url_mapping(self):
        self.assertEqual(set(self.repos), {rid(n) for n in LAYOUT})
        engine = self.repos[rid('rule-engine')]
        self.assertEqual(engine['url_expected'], f'https://{HOST}/{LAYOUT["rule-engine"]}')
        self.assertTrue(engine['url_verified'])
        self.assertEqual(engine['git']['remote_key'], rid('rule-engine'))
        self.assertEqual(engine['git']['commits_window'], 1)

    def test_activity_classes(self):
        classes = {r['name']: r['activity']['class'] for r in self.repos.values()}
        self.assertEqual(classes, {'apiutil': 'active', 'rule-engine': 'active', 'rule-catalog': 'active',
                                   'bash-scripts': 'junk'})
        self.assertIn('path segment: maintenance', self.repos[rid('bash-scripts')]['activity']['reasons'])

    def test_metrics_and_manifests(self):
        engine = self.repos[rid('rule-engine')]
        self.assertEqual(engine['metrics']['tool'], 'builtin')
        self.assertGreater(engine['metrics']['languages']['Python']['code'], 5)
        self.assertEqual(engine['makefile']['targets'], ['build', 'lint', 'test'])
        self.assertEqual(engine['makefile']['name_vars'], {'APPLICATION': 'rule-engine'})
        self.assertEqual([j['name'] for j in engine['ci']['gitlab']['jobs']], ['test'])
        self.assertFalse(engine['agents']['agents_md'])
        sources = engine['manifests']['pyproject']['sources']
        self.assertEqual(sources[0]['host'], 'registry.example.com')
        env = next(e for e in engine['manifests']['env'] if e['path'] == 'sample.env')
        keys = {k['key']: k for k in env['keys']}
        self.assertEqual(keys['RULE_CATALOG_ENDPOINT'], {'key': 'RULE_CATALOG_ENDPOINT', 'line': 2, 'host': 'rule-catalog'})
        self.assertNotIn('host', keys['API_TOKEN'])

    def test_library_edge_from_pyproject_and_import(self):
        edge = self.edge('rule-engine', 'apiutil', 'library')
        self.assertEqual(edge['confidence'], 0.95)
        self.assertEqual(edge['detail']['packages'], ['apiutil'])
        self.assertEqual(edge['detail']['imports'], ['apiutil'])
        paths = {(e['repo'], e['path'], e.get('line')) for e in edge['evidence']}
        self.assertIn((rid('rule-engine'), 'pyproject.toml', 12), paths)
        self.assertIn((rid('rule-engine'), 'src/api.py', 6), paths)
        self.assertIn((rid('apiutil'), 'pyproject.toml', 2), paths)

    def test_http_edge_from_sample_env(self):
        edge = self.edge('rule-engine', 'rule-catalog', 'http')
        self.assertEqual(edge['confidence'], 0.9)
        self.assertIn({'repo': rid('rule-engine'), 'path': 'sample.env', 'line': 2, 'key': 'RULE_CATALOG_ENDPOINT'},
                      edge['evidence'])

    def test_kafka_edge_with_direction(self):
        edge = self.edge('rule-catalog', 'rule-engine', 'kafka')
        self.assertEqual(edge['detail'], {'topics': ['rules.decisions'], 'direction': 'consumes-from'})

    def test_unresolved_is_not_guessed(self):
        refs = {(u['kind'], u['ref'], u['reason']) for u in self.rel['unresolved']}
        self.assertIn(('http', 'unknown-service', 'no matching repo'), refs)
        self.assertIn(('library', 'privatelib', 'private source, no publishing repo found'), refs)
        self.assertIn(('ci', 'team/infra/gitlab_ci', 'no matching repo'), refs)
        targets = {(e['from'], e['to']) for e in self.rel['edges']}
        self.assertNotIn((rid('rule-engine'), rid('rule-engine')), targets)
        self.assertEqual(self.rel['stats']['skipped_infra_endpoints'], 1)  # DATABASE_URL

    def test_no_secret_values_in_outputs(self):
        for path in self.out.iterdir():
            text = path.read_text()
            for secret in SECRETS:
                self.assertNotIn(secret, text, f'{secret} leaked into {path.name}')
            self.assertNotIn('reader:', text)

    def test_guide_applicability_uses_real_ids(self):
        known = applicability.guide_paths(ROOT)
        engine = self.guides['repositories'][rid('rule-engine')]
        for kind in ('rules', 'workflows'):
            for entry in engine[kind]:
                self.assertIn((kind, entry['id']), known)
                self.assertTrue((ROOT / entry['path']).is_file())
                self.assertTrue(entry['evidence'])
                self.assertGreater(entry['confidence'], 0)
        rules = {r['id'] for r in engine['rules']}
        workflows = {w['id'] for w in engine['workflows']}
        self.assertIn('software/general/makefile-guide', rules)
        self.assertIn('software/full-stack/env-settings-guide', rules)
        self.assertIn('devops/ci-cd/pipeline-debug', workflows)
        self.assertIn('software/full-stack/debug-issue-fullstack', workflows)  # http-consumer
        library = {r['id'] for r in self.guides['repositories'][rid('apiutil')]['rules']}
        self.assertIn('software/security/dependency-policy', library)  # internal-library: incoming edges
        for task, ids in engine['task_routing'].items():
            self.assertTrue(set(ids) <= workflows, task)
        junk = self.guides['repositories'][rid('bash-scripts')]
        self.assertEqual((junk['rules'], junk['workflows']), ([], []))

    def test_config_rejects_unknown_ids(self):
        cfg = json.loads((TOOL / 'applicability.json').read_text())
        cfg['repo_rules'][0]['workflows'] = ['software/backend/no-such-workflow']
        path = Path(self.tmp) / 'bad.json'
        path.write_text(json.dumps(cfg))
        with self.assertRaises(ValueError):
            applicability.load_config(path, ROOT)

    def test_write_repo_artifacts_keeps_repos_clean(self):
        tmp = tempfile.mkdtemp(prefix='repo-scan-artifacts-')
        self.addCleanup(shutil.rmtree, tmp, True)
        root = make_workspace(tmp)
        code, _, _ = run_cli('scan', str(root), '--out', str(Path(tmp) / 'out'), '--now', NOW, '--no-scc',
                             '--write-repo-artifacts')
        self.assertEqual(code, 0)
        repo = root / 'antifraud-rules/rule-engine'
        deps = json.loads((repo / '.agentic/dependencies.json').read_text())
        self.assertEqual({e['to'] for e in deps['outgoing']},
                         {rid('apiutil'), rid('rule-catalog')})
        self.assertTrue((repo / '.agentic/repo-scan.json').is_file())
        self.assertIn('.agentic/', (repo / '.git/info/exclude').read_text().splitlines())
        self.assertEqual(sh('git', 'status', '--porcelain', cwd=repo), '')
        self.assertEqual(sh('git', 'rev-list', '--count', 'HEAD', cwd=repo).strip(), '1')


class GateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix='repo-scan-gate-')
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = make_workspace(self.tmp)

    def test_propose_reads_makefile_and_ci_without_running(self):
        out = Path(self.tmp) / 'out'
        engine = (self.root / 'antifraud-rules/rule-engine').resolve()
        catalog = (self.root / 'antifraud-rules/rule-catalog').resolve()
        code, _, _ = run_cli('gate-propose', str(engine), str(catalog), str(self.root / 'pypi/apiutil'),
                             '--out', str(out))
        self.assertEqual(code, 0)
        proposals = json.loads((out / 'gate-proposals.json').read_text())['proposals']
        self.assertEqual(proposals[str(engine)]['gate'], {'commands': ['make test', 'make lint'], 'changelog': False,
                                                          'max_blocks': 3})
        self.assertEqual(proposals[str(catalog)]['gate']['commands'], ['ruff check .', 'pytest -q'])
        self.assertTrue(proposals[str((self.root / 'pypi/apiutil').resolve())]['gate']['changelog'])
        self.assertFalse((engine / '.agent').exists())

    def test_verify_keeps_passing_commands_and_stays_untracked(self):
        engine = self.root / 'antifraud-rules/rule-engine'
        code, out, _ = run_cli('gate-verify', str(engine), '--timeout', '30')
        self.assertEqual(code, 0, out)
        gate = json.loads((engine / '.agent/gate.json').read_text())
        self.assertEqual(gate['commands'], ['make test'])
        self.assertIn('.agent/gate.json', (engine / '.git/info/exclude').read_text())
        self.assertEqual(sh('git', 'status', '--porcelain', cwd=engine), '')

    def test_verify_timeout(self):
        from reposcan import gates
        result = gates.run_command(self.root, 'sleep 5', timeout=1)
        self.assertEqual(result['exit'], 124)


class LlmTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='repo-scan-llm-')
        cls.root = make_workspace(cls.tmp)
        cls.scan = Path(cls.tmp) / 'scan'
        run_cli('scan', str(cls.root), '--out', str(cls.scan), '--now', NOW, '--no-scc')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def answer(self):
        return {'summary': 'Rule engine service.',
                'applicability': [{'id': 'software/general/makefile-guide', 'applies': True, 'confidence': 0.9,
                                   'why': 'Makefile'},
                                  {'id': 'software/invented/workflow', 'applies': True, 'confidence': 0.5, 'why': 'x'}],
                'missing_guides': ['devops/sre/postmortem'], 'risks': ['lint target fails'],
                'recommendations': ['add AGENTS.md'], 'gate': {'commands': ['make test'], 'notes': ''}}

    def test_claude_provider_with_cache(self):
        out = Path(self.tmp) / 'llm-claude'
        calls = Path(self.tmp) / 'calls.txt'
        prompt_copy = Path(self.tmp) / 'prompt.txt'
        fake = Path(self.tmp) / 'fake-claude'
        fake.write_text('#!/bin/sh\n'
                        f'cat > "{prompt_copy}"\n'
                        f'echo "$@" >> "{calls}"\n'
                        f"printf '%s' '```json\\n{json.dumps(self.answer())}\\n```'\n")
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        with mock.patch.dict(os.environ, {'AGENTIC_LLM_CLAUDE_BIN': str(fake)}):
            for _ in range(2):
                code, _, _ = run_cli('llm', '--in', str(self.scan), '--out', str(out), '--provider', 'claude',
                                     '--model', 'haiku', '--repo', 'rule-engine')
                self.assertEqual(code, 0)
        self.assertEqual(len(calls.read_text().splitlines()), 1, 'second run must hit the cache')
        self.assertIn('-p --model haiku', calls.read_text())
        result = json.loads((out / 'llm-assessment.json').read_text())
        entry = result['assessments'][rid('rule-engine')]
        self.assertEqual(entry['status'], 'ok')
        ids = [a['id'] for a in entry['assessment']['applicability']]
        self.assertEqual(ids, ['software/general/makefile-guide'])
        self.assertEqual(entry['assessment']['invalid_ids'], ['software/invented/workflow'])
        prompt = prompt_copy.read_text()
        self.assertIn('README.md', prompt)
        self.assertIn('password=***', prompt)
        for secret in SECRETS:
            self.assertNotIn(secret, prompt)
        self.assertEqual(len(list((out / 'llm-cache').iterdir())), 1)

    def test_claude_model_is_validated(self):
        code, _, _ = run_cli('llm', '--in', str(self.scan), '--provider', 'claude', '--model', 'gpt-4')
        self.assertEqual(code, 2)

    def test_litellm_provider(self):
        seen = {}
        answer = self.answer()

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                seen.update(path=self.path, auth=self.headers['Authorization'], body=body)
                data = json.dumps({'choices': [{'message': {'content': json.dumps(answer)}}]}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args):
                pass

        server = HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        out = Path(self.tmp) / 'llm-litellm'
        env = {'AGENTIC_LLM_BASE_URL': f'http://127.0.0.1:{server.server_port}/', 'AGENTIC_LLM_API_KEY': 'test-key'}
        with mock.patch.dict(os.environ, env):
            code, _, _ = run_cli('llm', '--in', str(self.scan), '--out', str(out), '--provider', 'litellm',
                                 '--repo', 'apiutil', '--no-cache')
        self.assertEqual(code, 0)
        self.assertEqual(seen['path'], '/v1/chat/completions')
        self.assertEqual(seen['auth'], 'Bearer test-key')
        self.assertEqual(seen['body']['model'], 'coding-agent-default')
        result = json.loads((out / 'llm-assessment.json').read_text())
        self.assertEqual(result['assessments'][rid('apiutil')]['status'], 'ok')
        self.assertNotIn('test-key', (out / 'llm-assessment.json').read_text())

    def test_litellm_without_key_reports_error(self):
        out = Path(self.tmp) / 'llm-nokey'
        with mock.patch.dict(os.environ, {'AGENTIC_LLM_API_KEY': ''}):
            code, _, _ = run_cli('llm', '--in', str(self.scan), '--out', str(out), '--provider', 'litellm',
                                 '--repo', 'apiutil', '--no-cache')
        self.assertEqual(code, 1)
        entry = json.loads((out / 'llm-assessment.json').read_text())['assessments'][rid('apiutil')]
        self.assertEqual(entry['error'], 'AGENTIC_LLM_API_KEY is not set')


class UnitTest(unittest.TestCase):
    def test_remote_key(self):
        for url in ('git@gitlab.example.com:Team/App.git', 'https://user:tok@gitlab.example.com/team/app.git',
                    'ssh://git@gitlab.example.com:2222/team/app.git', 'https://gitlab.example.com/team/app'):
            self.assertEqual(common.remote_key(url), 'gitlab.example.com/team/app', url)

    def test_sanitize_url_drops_credentials(self):
        self.assertEqual(common.sanitize_url('https://user:tok@host.example.com/a.git'), 'https://host.example.com/a.git')

    def test_expected_url_skips_dotted_user_dir(self):
        path = Path('/home/first.last/work/glb.example.com/team/svc')
        root = Path('/home/first.last/work/glb.example.com/team')
        self.assertEqual(discover.expected_url(path, root)[0], 'glb.example.com/team/svc')
        self.assertEqual(discover.expected_url(path, None, 'glb.example.com')[1], 'https://glb.example.com/team/svc')

    def test_classify_stale_and_archived(self):
        cfg = json.loads((TOOL / 'applicability.json').read_text())['activity']
        facts = {'head': 'abc', 'commits_window': 0}
        self.assertEqual(discover.classify(('svc',), 'svc', facts, True, 500, cfg)[0], 'stale')
        self.assertEqual(discover.classify(('archive', 'svc'), 'svc', facts, True, 500, cfg)[0], 'archived')
        self.assertEqual(discover.classify(('svc',), 'svc', dict(facts, commits_window=2), False, 500, cfg)[0], 'stale')
        self.assertEqual(discover.classify(('svc',), 'svc', dict(facts, commits_window=9), False, 500, cfg)[0], 'active')

    def test_redact(self):
        text = common.redact('DB_PASSWORD=abc\nurl=https://u:p@h.example.com\nkey sk-abcdefghijkl')
        self.assertNotIn('abc\n', text)
        self.assertNotIn('u:p@', text)
        self.assertNotIn('sk-abcdefghijkl', text)

    def test_scc_is_used_when_on_path(self):
        tmp = tempfile.mkdtemp(prefix='repo-scan-scc-')
        self.addCleanup(shutil.rmtree, tmp, True)
        fake = Path(tmp) / 'scc'
        fake.write_text('#!/bin/sh\necho \'[{"Name": "Python", "Count": 3, "Code": 120}]\'\n')
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        with mock.patch.dict(os.environ, {'PATH': f'{tmp}{os.pathsep}{os.environ["PATH"]}'}):
            result = metrics.count(tmp, [])
        self.assertEqual(result['tool'], 'scc')
        self.assertEqual(result['code_lines'], 120)


if __name__ == '__main__':
    unittest.main()
