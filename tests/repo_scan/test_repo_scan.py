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
    'shared-lib': 'team/pypi/shared-lib',
    'order-service': 'team/example-group/order-service',
    'catalog-lib': 'team/example-group/catalog-lib',
    'bash-scripts': 'team/maintenance/bash-scripts',
    'handbook': 'team/docs/handbook',
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


def rid(name, base=f'https://{HOST}'):
    """Repository identity: the GitLab URL."""
    return f'{base}/{LAYOUT[name]}' if base == f'https://{HOST}' else f'{base}/{LAYOUT[name].split("/", 1)[1]}'


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
        self.assertIn(f'["{HOST}/team/example-group/order-service"]', graph)

    def test_discovery_and_url_identity(self):
        self.assertEqual(set(self.repos), {rid(n) for n in LAYOUT})
        engine = self.repos[rid('order-service')]
        self.assertEqual(engine['id'], f'https://{HOST}/team/example-group/order-service')
        self.assertEqual(engine['url_source'], 'path')
        self.assertTrue(engine['url_verified'])
        self.assertEqual(engine['git']['remote_key'], f'{HOST}/{LAYOUT["order-service"]}')
        self.assertEqual(engine['git']['commits_window'], 1)
        self.assertEqual(Path(engine['local_path']), (self.root / 'example-group/order-service').resolve())

    def test_local_paths_only_in_repositories_json(self):
        for name in ('relationships.json', 'guide-applicability.json', 'graph.mmd'):
            self.assertNotIn(str(self.tmp), (self.out / name).read_text(), name)
        for e in self.rel['edges'] + self.rel['unresolved']:
            self.assertTrue(e['from'].startswith('https://'), e)
        for e in self.rel['edges']:
            self.assertTrue(e['to'].startswith('https://'), e)
        self.assertTrue(all(k.startswith('https://') for k in self.guides['repositories']))

    def test_activity_classes(self):
        classes = {r['name']: r['activity']['class'] for r in self.repos.values()}
        self.assertEqual(classes, {'shared-lib': 'active', 'order-service': 'active', 'catalog-lib': 'active',
                                   'bash-scripts': 'junk', 'handbook': 'docs'})
        self.assertIn('path segment: maintenance', self.repos[rid('bash-scripts')]['activity']['reasons'])

    def test_docs_repo_gets_only_docs_guidance(self):
        docs = self.guides['repositories'][rid('handbook')]
        self.assertEqual(docs['class'], 'docs')
        self.assertEqual({r['id'] for r in docs['rules']},
                         {'software/general/readme-sync-guide', 'software/general/git-workflow-guide'})
        self.assertEqual([w['id'] for w in docs['workflows']], ['software/general/code-review-workflow'])
        self.assertEqual({b for r in docs['rules'] for b in r['because']}, {'documentation'})

    def test_trusted_edges(self):
        stats = self.rel['stats']
        self.assertEqual(stats['trusted_min'], 0.8)
        self.assertEqual(stats['trusted_by_kind'], {'http': 1, 'kafka': 1, 'library': 1})
        self.assertTrue(self.edge('order-service', 'shared-lib', 'library')['trusted'])
        self.assertTrue(all(e['trusted'] == (e['confidence'] >= 0.8) for e in self.rel['edges']))

    def test_metrics_and_manifests(self):
        engine = self.repos[rid('order-service')]
        self.assertEqual(engine['metrics']['tool'], 'builtin')
        self.assertGreater(engine['metrics']['languages']['Python']['code'], 5)
        self.assertEqual(engine['makefile']['targets'], ['build', 'lint', 'test'])
        self.assertEqual(engine['makefile']['name_vars'], {'APPLICATION': 'order-service'})
        self.assertEqual([j['name'] for j in engine['ci']['gitlab']['jobs']], ['test'])
        self.assertFalse(engine['agents']['agents_md'])
        sources = engine['manifests']['pyproject']['sources']
        self.assertEqual(sources[0]['host'], 'registry.example.com')
        env = next(e for e in engine['manifests']['env'] if e['path'] == 'sample.env')
        keys = {k['key']: k for k in env['keys']}
        self.assertEqual(keys['CATALOG_LIB_ENDPOINT'], {'key': 'CATALOG_LIB_ENDPOINT', 'line': 2, 'host': 'catalog-lib'})
        self.assertNotIn('host', keys['API_TOKEN'])

    def test_library_edge_from_pyproject_and_import(self):
        edge = self.edge('order-service', 'shared-lib', 'library')
        self.assertEqual(edge['confidence'], 0.95)
        self.assertEqual(edge['detail']['packages'], ['shared_lib'])
        self.assertEqual(edge['detail']['imports'], ['shared_lib'])
        paths = {(e['repo'], e['path'], e.get('line')) for e in edge['evidence']}
        self.assertIn((rid('order-service'), 'pyproject.toml', 12), paths)
        self.assertIn((rid('order-service'), 'src/api.py', 6), paths)
        self.assertIn((rid('shared-lib'), 'pyproject.toml', 2), paths)

    def test_http_edge_from_sample_env(self):
        edge = self.edge('order-service', 'catalog-lib', 'http')
        self.assertEqual(edge['confidence'], 0.9)
        self.assertIn({'repo': rid('order-service'), 'path': 'sample.env', 'line': 2, 'key': 'CATALOG_LIB_ENDPOINT'},
                      edge['evidence'])

    def test_kafka_edge_with_direction(self):
        edge = self.edge('catalog-lib', 'order-service', 'kafka')
        self.assertEqual(edge['detail'], {'topics': ['rules.decisions'], 'direction': 'consumes-from'})

    def test_unresolved_is_not_guessed(self):
        refs = {(u['kind'], u['ref'], u['reason']) for u in self.rel['unresolved']}
        self.assertIn(('http', 'unknown-service', 'no matching repo'), refs)
        self.assertIn(('library', 'privatelib', 'private source, no publishing repo found'), refs)
        self.assertIn(('ci', 'team/infra/gitlab_ci', 'no matching repo'), refs)
        targets = {(e['from'], e['to']) for e in self.rel['edges']}
        self.assertNotIn((rid('order-service'), rid('order-service')), targets)
        self.assertEqual(self.rel['stats']['skipped_infra_endpoints'], 1)  # DATABASE_URL

    def test_no_secret_values_in_outputs(self):
        for path in self.out.iterdir():
            text = path.read_text()
            for secret in SECRETS:
                self.assertNotIn(secret, text, f'{secret} leaked into {path.name}')
            self.assertNotIn('reader:', text)

    def test_guide_applicability_uses_real_ids(self):
        known = applicability.guide_paths(ROOT)
        engine = self.guides['repositories'][rid('order-service')]
        for kind in ('rules', 'workflows'):
            for entry in engine[kind]:
                self.assertIn((kind, entry['id']), known)
                self.assertTrue((ROOT / entry['path']).is_file())
                self.assertTrue(entry['evidence'])
                self.assertGreater(entry['confidence'], 0)
        rules = {r['id'] for r in engine['rules']}
        workflows = {w['id'] for w in engine['workflows']}
        self.assertIn('software/general/makefile-guide', rules)
        self.assertIn('software/backend/configuration', rules)
        self.assertIn('devops/ci-cd/release-pipeline', workflows)
        self.assertIn('software/general/debug-issue', workflows)  # http-consumer
        library = {r['id'] for r in self.guides['repositories'][rid('shared-lib')]['rules']}
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

    def test_root_url_overrides_inference(self):
        out = Path(self.tmp) / 'out-root-url'
        base = 'https://git.corp.example/af'
        code, _, _ = run_cli('scan', str(self.root), '--out', str(out), '--now', NOW, '--no-scc',
                             '--root-url', f'{self.root}={base}/', '--trusted-min', '0.95')
        self.assertEqual(code, 0)
        repos = {r['id']: r for r in json.loads((out / 'repositories.json').read_text())['repositories']}
        self.assertEqual(set(repos), {rid(n, base) for n in LAYOUT})
        engine = repos[rid('order-service', base)]
        self.assertEqual(engine['url_source'], 'root-url')
        self.assertFalse(engine['url_verified'])  # origin points to gitlab.example.com
        rel = json.loads((out / 'relationships.json').read_text())
        pairs = {(e['from'], e['to'], e['kind'], e['trusted']) for e in rel['edges']}
        self.assertIn((rid('order-service', base), rid('shared-lib', base), 'library', True), pairs)
        self.assertIn((rid('order-service', base), rid('catalog-lib', base), 'http', False), pairs)
        self.assertEqual(rel['stats']['trusted_by_kind'], {'library': 1})
        meta_roots = json.loads((out / 'guide-applicability.json').read_text())['roots']
        self.assertEqual(meta_roots, [{'url': base, 'source': 'root-url'}])
        self.assertIn('-.->|http 0.9|', (out / 'graph.mmd').read_text())

    def test_root_url_rejects_bad_value(self):
        code, _, _ = run_cli('scan', str(self.root), '--out', str(Path(self.tmp) / 'bad'), '--root-url', 'nourl')
        self.assertEqual(code, 2)

    def test_write_repo_artifacts_keeps_repos_clean(self):
        tmp = tempfile.mkdtemp(prefix='repo-scan-artifacts-')
        self.addCleanup(shutil.rmtree, tmp, True)
        root = make_workspace(tmp)
        code, _, _ = run_cli('scan', str(root), '--out', str(Path(tmp) / 'out'), '--now', NOW, '--no-scc',
                             '--write-repo-artifacts')
        self.assertEqual(code, 0)
        repo = root / 'example-group/order-service'
        deps = json.loads((repo / '.agentic/dependencies.json').read_text())
        self.assertEqual({e['to'] for e in deps['outgoing']},
                         {rid('shared-lib'), rid('catalog-lib')})
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
        engine = (self.root / 'example-group/order-service').resolve()
        catalog = (self.root / 'example-group/catalog-lib').resolve()
        code, _, _ = run_cli('gate-propose', str(engine), str(catalog), str(self.root / 'pypi/shared-lib'),
                             '--out', str(out))
        self.assertEqual(code, 0)
        proposals = json.loads((out / 'gate-proposals.json').read_text())['proposals']
        self.assertEqual(set(proposals), {rid('order-service'), rid('catalog-lib'), rid('shared-lib')})
        self.assertEqual(proposals[rid('order-service')]['gate'], {'commands': ['make test', 'make lint'],
                                                                 'changelog': False, 'max_blocks': 3})
        self.assertEqual(proposals[rid('catalog-lib')]['gate']['commands'], ['ruff check .', 'pytest -q'])
        self.assertTrue(proposals[rid('shared-lib')]['gate']['changelog'])
        self.assertFalse((engine / '.agent').exists())

    def test_propose_looks_up_url_and_short_form_in_scan(self):
        scan = Path(self.tmp) / 'scan'
        run_cli('scan', str(self.root), '--out', str(scan), '--now', NOW, '--no-scc')
        code, _, _ = run_cli('gate-propose', rid('shared-lib'), 'example-group/catalog-lib',
                             f'{HOST}/team/example-group/order-service', '--in', str(scan))
        self.assertEqual(code, 0)
        proposals = json.loads((scan / 'gate-proposals.json').read_text())['proposals']
        self.assertEqual(set(proposals), {rid('shared-lib'), rid('catalog-lib'), rid('order-service')})
        with self.assertRaises(SystemExit):
            run_cli('gate-propose', 'no-such-repo', '--in', str(scan))

    def test_verify_keeps_passing_commands_and_stays_untracked(self):
        engine = self.root / 'example-group/order-service'
        scan = Path(self.tmp) / 'scan-verify'
        run_cli('scan', str(self.root), '--out', str(scan), '--now', NOW, '--no-scc')
        code, out, _ = run_cli('gate-verify', rid('order-service'), '--in', str(scan), '--timeout', '30',
                               '--out', str(scan))
        self.assertEqual(code, 0, out)
        report = json.loads((scan / 'gate-verify.json').read_text())['reports'][0]
        self.assertEqual(report['repo'], rid('order-service'))
        gate = json.loads((engine / '.agent/gate.json').read_text())
        self.assertEqual(gate['commands'], ['make test'])
        self.assertIn('.agent/gate.json', (engine / '.git/info/exclude').read_text())
        self.assertEqual(sh('git', 'status', '--porcelain', cwd=engine), '')

    def test_verify_timeout(self):
        from reposcan import gates
        result = gates.run_command(self.root, 'sleep 5', timeout=1)
        self.assertEqual(result['exit'], 124)


class FocusTest(unittest.TestCase):
    """One repository: the context roots are scanned so its links resolve, the output keeps only its view."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='repo-scan-focus-')
        cls.root = make_workspace(cls.tmp)
        cls.env = mock.patch.dict(os.environ, {'XDG_CONFIG_HOME': str(Path(cls.tmp) / 'config')})
        cls.env.start()
        os.environ.pop('REPO_SCAN_CONTEXT_ROOTS', None)

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def scan(self, name, *extra):
        out = Path(self.tmp) / name
        code, _, err = run_cli('scan', *extra, '--out', str(out), '--now', NOW, '--no-scc')
        self.assertEqual(code, 0, err)
        rel = json.loads((out / 'relationships.json').read_text())
        repos = json.loads((out / 'repositories.json').read_text())['repositories']
        guides = json.loads((out / 'guide-applicability.json').read_text())
        return rel, {r['id']: r for r in repos}, guides

    def test_single_repository_resolves_links_from_its_group(self):
        rel, repos, guides = self.scan('one', str(self.root / 'example-group/order-service'))
        engine = rid('order-service')
        self.assertEqual(rel['focus'], [engine])
        pairs = {(e['to'], e['kind']) for e in rel['edges']}
        self.assertIn((rid('shared-lib'), 'library'), pairs)
        self.assertIn((rid('catalog-lib'), 'http'), pairs)
        self.assertTrue(all(engine in (e['from'], e['to']) for e in rel['edges']))
        self.assertEqual(set(repos), {engine, rid('shared-lib'), rid('catalog-lib')})
        self.assertTrue(repos[engine]['focus'] and not repos[rid('shared-lib')]['focus'])
        self.assertEqual(list(guides['repositories']), [engine])

    def test_repository_inside_a_root_is_scanned_once(self):
        rel, repos, _ = self.scan('nested', str(self.root / 'example-group/order-service'),
                                  '--root-url', f'{self.root}=https://{HOST}/team')
        self.assertEqual(rel['focus'], [rid('order-service')])
        self.assertFalse(any('#copy' in rid_ for rid_ in repos))

    def test_no_context_leaves_links_unresolved(self):
        rel, repos, _ = self.scan('alone', str(self.root / 'example-group/order-service'), '--no-context')
        self.assertEqual(list(repos), [rid('order-service')])
        self.assertFalse(any(e['to'] == rid('shared-lib') for e in rel['edges']))

    def test_focus_inside_group_roots(self):
        rel, repos, _ = self.scan('group', str(self.root), '--focus', 'pypi/shared-lib')
        self.assertEqual(rel['focus'], [rid('shared-lib')])
        self.assertIn((rid('order-service'), rid('shared-lib')), {(e['from'], e['to']) for e in rel['edges']})
        self.assertNotIn(rid('handbook'), repos)

    def test_unknown_focus_fails(self):
        code, _, err = run_cli('scan', str(self.root), '--focus', 'no/such-repo', '--out',
                               str(Path(self.tmp) / 'bad'), '--now', NOW, '--no-scc')
        self.assertEqual(code, 2)
        self.assertIn('focus repositories not found', err)


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
        return {'summary': 'Order service.',
                'applicability': [{'id': 'software/general/makefile-guide', 'applies': True, 'confidence': 0.9,
                                   'why': 'Makefile'},
                                  {'id': 'software/invented/workflow', 'applies': True, 'confidence': 0.5, 'why': 'x'}],
                'missing_guides': ['devops/sre/incident-response'], 'risks': ['lint target fails'],
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
                                     '--model', 'haiku', '--repo', 'order-service')
                self.assertEqual(code, 0)
        self.assertEqual(len(calls.read_text().splitlines()), 1, 'second run must hit the cache')
        self.assertIn('-p --model haiku', calls.read_text())
        result = json.loads((out / 'llm-assessment.json').read_text())
        entry = result['assessments'][rid('order-service')]
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
                                 '--model', 'any_provider/coding-agent-default', '--repo', rid('shared-lib'),
                                 '--no-cache')
        self.assertEqual(code, 0)
        self.assertEqual(seen['path'], '/v1/chat/completions')
        self.assertEqual(seen['auth'], 'Bearer test-key')
        self.assertEqual(seen['body']['model'], 'coding-agent-default')
        result = json.loads((out / 'llm-assessment.json').read_text())
        self.assertEqual(result['assessments'][rid('shared-lib')]['status'], 'ok')
        self.assertNotIn('test-key', (out / 'llm-assessment.json').read_text())

    def test_litellm_without_key_reports_error(self):
        out = Path(self.tmp) / 'llm-nokey'
        with mock.patch.dict(os.environ, {'AGENTIC_LLM_API_KEY': ''}):
            code, _, _ = run_cli('llm', '--in', str(self.scan), '--out', str(out), '--provider', 'litellm',
                                 '--repo', rid('shared-lib'), '--no-cache')
        self.assertEqual(code, 1)
        entry = json.loads((out / 'llm-assessment.json').read_text())['assessments'][rid('shared-lib')]
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
        self.assertEqual(discover.classify(('g', 'gitlab-profile'), 'gitlab-profile', facts, False, 0, cfg)[0], 'docs')
        self.assertEqual(discover.classify(('svc',), 'svc', facts, True, 150, cfg, doc_lines=400, doc_files=3)[0],
                         'docs')
        self.assertEqual(discover.classify(('svc',), 'svc', facts, True, 1500, cfg, doc_lines=4000, doc_files=9)[0],
                         'stale')
        # A single GitLab template README is not documentation.
        self.assertEqual(discover.classify(('svc',), 'svc', facts, False, 0, cfg, doc_lines=59, doc_files=1)[0],
                         'junk')

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



class CheckToolsTest(unittest.TestCase):
    """check-tools.sh is plain sh, so it must report a missing or old Python itself."""

    def run_check(self, tools):
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp)
            for name, target in tools.items():
                path = bin_dir / name
                if target is None:
                    path.write_text('#!/bin/sh\ncase "$*" in *version_info*) exit 1;; *) echo 3.9.18;; esac\n')
                    path.chmod(0o755)
                else:
                    path.symlink_to(target)
            env = {'PATH': str(bin_dir), 'REPO_SCAN_NO_PROMPT': '1'}
            return subprocess.run(['/bin/sh', str(TOOL / 'check-tools.sh')], env=env, capture_output=True,
                                  text=True, stdin=subprocess.DEVNULL)

    def base(self):
        return {'dirname': shutil.which('dirname'), 'git': shutil.which('git')}

    def test_missing_python_fails_with_install_hint(self):
        result = self.run_check(self.base())
        self.assertEqual(result.returncode, 1)
        self.assertIn('missing: python3 >= 3.11', result.stderr)

    def test_old_python_fails(self):
        result = self.run_check({**self.base(), 'python3': None})
        self.assertEqual(result.returncode, 1)
        self.assertIn('needs >= 3.11', result.stderr)

    def test_missing_git_fails_and_ok_without_optional_tools(self):
        result = self.run_check({'dirname': shutil.which('dirname'), 'python3': sys.executable})
        self.assertEqual(result.returncode, 1)
        self.assertIn('missing: git', result.stderr)
        result = self.run_check({**self.base(), 'python3': sys.executable})
        self.assertEqual(result.returncode, 0)
        self.assertIn('optional scc is not installed', result.stderr)


if __name__ == '__main__':
    unittest.main()
