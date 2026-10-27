"""Offline tests of the shared quality gate (extensions/codex/hooks/gate/gate.py)."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

import gate

AUTHOR = ['-c', 'user.name=t', '-c', 'user.email=t@localhost']


def project(makefile, changelog=True):
    root = Path(tempfile.mkdtemp(prefix='gate-'))
    (root / 'Makefile').write_text(makefile)
    (root / 'app.py').write_text('x = 1\n')
    if changelog:
        (root / 'CHANGELOG.md').write_text('# Changelog\n\n## Unreleased\n')
    subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
    subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
    subprocess.run(['git', *AUTHOR, 'commit', '-q', '-m', 'init'], cwd=root, check=True)
    return root


def last(root):
    return json.loads((root / '.agentic/gate/last.json').read_text())


GREEN = 'test:\n\t@true\nlint:\n\t@true\n'
RED = 'test:\n\t@echo boom; exit 1\nlint:\n\t@true\n'


class StopGate(unittest.TestCase):
    def test_unchanged_tree_runs_nothing(self):
        root = project(RED)
        self.assertEqual(gate.stop(root, {'session_id': 's'}), {})
        self.assertEqual(json.loads((root / '.agentic/gate/last.json').read_text())['checks'], [])

    def test_install_baseline_is_not_a_change(self):
        root = project(RED)
        (root / 'AGENTS.md').write_text('guide\n')
        (root / '.agentic/gate').mkdir(parents=True)
        digest = hashlib.sha256(b'guide\n').hexdigest()
        (root / '.agentic/gate/baseline.json').write_text(json.dumps({'files': {'AGENTS.md': digest}}))
        self.assertEqual(gate.stop(root, {'session_id': 's'}), {})
        (root / 'AGENTS.md').write_text('edited\n')
        self.assertEqual(gate.stop(root, {'session_id': 's'})['decision'], 'block')

    def test_failed_check_blocks_with_output(self):
        root = project(RED)
        (root / 'app.py').write_text('x = 2\n')
        result = gate.stop(root, {'session_id': 's'})
        self.assertEqual(result['decision'], 'block')
        self.assertIn('make test', result['reason'])
        self.assertIn('boom', result['reason'])

    def test_changelog_is_asked_once(self):
        root = project(GREEN)
        (root / 'app.py').write_text('x = 2\n')
        self.assertIn('CHANGELOG', gate.stop(root, {'session_id': 's'})['reason'])
        self.assertEqual(gate.stop(root, {'session_id': 's'}), {})

    def test_changelog_entry_passes(self):
        root = project(GREEN)
        (root / 'app.py').write_text('x = 2\n')
        (root / 'CHANGELOG.md').write_text('# Changelog\n\n## Unreleased\n\n- Fix x.\n')
        self.assertEqual(gate.stop(root, {'session_id': 's'}), {})
        self.assertTrue(json.loads((root / '.agentic/gate/last.json').read_text())['passed'])

    def test_tests_only_change_needs_no_changelog(self):
        root = project(GREEN)
        (root / 'tests').mkdir()
        (root / 'tests/test_x.py').write_text('')
        self.assertEqual(gate.stop(root, {'session_id': 's'}), {})

    def test_blocks_are_bounded(self):
        root = project(RED, changelog=False)
        (root / 'app.py').write_text('x = 2\n')
        outcomes = [gate.stop(root, {'session_id': 's'}) for _ in range(4)]
        self.assertEqual([bool(o) for o in outcomes], [True, True, True, False])

    def test_settings_override_commands(self):
        root = project(RED, changelog=False)
        (root / '.agent').mkdir()
        (root / '.agent/gate.json').write_text('{"commands": ["true"]}')
        (root / 'app.py').write_text('x = 2\n')
        self.assertEqual(gate.stop(root, {'session_id': 's'}), {})


class AcceptanceRecord(unittest.TestCase):
    def test_no_changes_is_accepted(self):
        root = project(RED)
        gate.stop(root, {'session_id': 's'}, 'claude')
        record = last(root)
        self.assertEqual((record['accepted'], record['reason_code']), (True, 'no_changes'))

    def test_checks_passed(self):
        root = project(GREEN, changelog=False)
        (root / 'app.py').write_text('x = 2\n')
        self.assertEqual(gate.stop(root, {'session_id': 's'}, 'claude'), {})
        record = last(root)
        self.assertEqual((record['accepted'], record['reason_code'], record['passed']), (True, 'checks_passed', True))

    def test_checks_failed(self):
        root = project(RED, changelog=False)
        (root / 'app.py').write_text('x = 2\n')
        self.assertEqual(gate.stop(root, {'session_id': 's'}, 'claude')['decision'], 'block')
        record = last(root)
        self.assertEqual((record['accepted'], record['reason_code']), (False, 'checks_failed'))

    def test_changelog_missing(self):
        root = project(GREEN)
        (root / 'app.py').write_text('x = 2\n')
        gate.stop(root, {'session_id': 's'})
        self.assertEqual((last(root)['accepted'], last(root)['reason_code']), (False, 'changelog_missing'))

    def test_max_blocks_release_is_not_accepted(self):
        root = project(RED, changelog=False)
        (root / 'app.py').write_text('x = 2\n')
        for _ in range(3):
            gate.stop(root, {'session_id': 's'}, 'claude')
        released = gate.stop(root, {'session_id': 's'}, 'claude')
        self.assertEqual(released, {'systemMessage': 'Agentic gate: NOT ACCEPTED (max_blocks)'})
        record = last(root)
        self.assertEqual((record['accepted'], record['reason_code']), (False, 'max_blocks'))
        self.assertIn('released', record)
        state = json.loads((root / '.agentic/gate/state.json').read_text())['s']
        self.assertEqual(state['blocks'], 0)
        self.assertEqual(state['last_release']['cause'], 'checks_failed')
        self.assertEqual(state['last_release']['head'], record['head'])

    def test_system_message_only_on_claude(self):
        for host in ('codex', 'opencode', None):
            root = project(RED, changelog=False)
            (root / 'app.py').write_text('x = 2\n')
            for _ in range(3):
                gate.stop(root, {'session_id': 's'}, host)
            self.assertEqual(gate.stop(root, {'session_id': 's'}, host), {})
            self.assertEqual(last(root)['reason_code'], 'max_blocks')

    def test_head_pack_version_and_profile(self):
        root = project(GREEN, changelog=False)
        head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True).stdout.strip()
        (root / '.agentic.json').write_text(json.dumps({
            '_agentic': {'created_by': 'v2.0.0', 'updated_by': 'v2.2.0'}, 'version': 2,
            'settings': {'profile': 'lean'}}))
        gate.stop(root, {'session_id': 's'})
        record = last(root)
        self.assertEqual((record['head'], record['pack_version'], record['profile']), (head, 'v2.2.0', 'lean'))

    def test_no_git_and_no_manifest_give_nulls(self):
        root = Path(tempfile.mkdtemp(prefix='gate-nogit-'))
        self.assertEqual(gate.stop(root, {'session_id': 's'}), {})
        record = last(root)
        self.assertEqual((record['head'], record['pack_version'], record['profile']), (None, None, None))
        self.assertEqual(record['reason_code'], 'no_changes')

    def test_main_prints_system_message_for_claude_host(self):
        root = project(RED, changelog=False)
        (root / 'app.py').write_text('x = 2\n')
        script = str(Path(gate.__file__).resolve())
        argv = ['python3', script, '--host', 'claude', '--event', 'stop', '--project-dir', str(root)]
        outputs = [subprocess.run(argv, input='{"session_id": "s"}', capture_output=True, text=True).stdout
                   for _ in range(4)]
        self.assertEqual(json.loads(outputs[-1]), {'systemMessage': 'Agentic gate: NOT ACCEPTED (max_blocks)'})


class Guard(unittest.TestCase):
    def deny(self, payload):
        return gate.guard(Path(tempfile.mkdtemp()), payload).get('hookSpecificOutput', {}).get('permissionDecision')

    def test_secret_reads_are_denied(self):
        self.assertEqual(self.deny({'tool_name': 'Read', 'tool_input': {'file_path': '/p/.env'}}), 'deny')
        self.assertEqual(self.deny({'tool_name': 'Bash', 'tool_input': {'command': 'cat config/.env.prod'}}), 'deny')
        self.assertIsNone(self.deny({'tool_name': 'Read', 'tool_input': {'file_path': '/p/.env.example'}}))

    def test_force_push_is_denied(self):
        self.assertEqual(self.deny({'tool_name': 'Bash', 'tool_input': {'command': 'git push -f origin main'}}), 'deny')
        self.assertIsNone(self.deny({'tool_name': 'Bash', 'tool_input': {'command': 'git push --force-with-lease'}}))

    def test_recursive_delete_outside_project_is_denied(self):
        self.assertEqual(self.deny({'tool_name': 'Bash', 'tool_input': {'command': 'rm -rf ~/work'}}), 'deny')
        self.assertIsNone(self.deny({'tool_name': 'Bash', 'tool_input': {'command': 'rm -rf build'}}))

    def test_ordinary_commands_pass(self):
        self.assertIsNone(self.deny({'tool_name': 'Bash', 'tool_input': {'command': 'make test'}}))


def bash(command):
    return {'tool_name': 'Bash', 'tool_input': {'command': command}}


class ConfirmGuard(unittest.TestCase):
    def setUp(self):
        # A fake kubectl on PATH answers `config current-context` from $FAKE_CONTEXT; no cluster, no network.
        self.bin = Path(tempfile.mkdtemp(prefix='gate-bin-'))
        fake = self.bin / 'kubectl'
        fake.write_text('#!/bin/sh\n[ "$1 $2" = "config current-context" ] || exit 3\n'
                        '[ -n "$FAKE_CONTEXT" ] || exit 1\necho "$FAKE_CONTEXT"\n')
        fake.chmod(0o755)
        self.saved = {k: os.environ.get(k) for k in ('PATH', 'FAKE_CONTEXT', 'CLAUDE_PROJECT_DIR')}
        os.environ['PATH'] = f'{self.bin}{os.pathsep}{os.environ.get("PATH", "")}'
        os.environ['FAKE_CONTEXT'] = 'dev-cluster'
        self.root = Path(tempfile.mkdtemp(prefix='gate-guard-'))

    def tearDown(self):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def config(self, data):
        (self.root / '.agent').mkdir(exist_ok=True)
        (self.root / '.agent/gate.json').write_text(json.dumps(data))

    def decide(self, command, host='claude'):
        output = gate.guard(self.root, bash(command), host).get('hookSpecificOutput', {})
        return output.get('permissionDecision'), output.get('permissionDecisionReason', '')

    def test_prod_context_flag_asks(self):
        for command in ('kubectl --context prod-cluster get ns', 'kubectl get ns --context=PROD-eu',
                        'helm --kube-context prod-cluster list', 'oc --context=prod get pods',
                        'cd /srv && /usr/local/bin/kubectl --context prod-cluster get ns | head',
                        'echo start; sudo -u ops kubectl --context prod-cluster get ns',
                        'kubectl config use-context prod-cluster'):
            decision, reason = self.decide(command)
            self.assertEqual(decision, 'ask', command)
            self.assertIn('prod', reason.lower())

    def test_dev_context_flag_passes(self):
        os.environ['FAKE_CONTEXT'] = 'prod-cluster'  # an explicit flag wins over the current context
        self.assertEqual(self.decide('kubectl --context dev-cluster get pods'), (None, ''))
        self.assertEqual(self.decide('helm --kube-context=staging list'), (None, ''))

    def test_current_context_is_checked_without_flag(self):
        self.assertEqual(self.decide('kubectl get pods'), (None, ''))
        os.environ['FAKE_CONTEXT'] = 'prod-cluster'
        decision, reason = self.decide('kubectl get pods')
        self.assertEqual(decision, 'ask')
        self.assertIn('prod-cluster', reason)
        self.assertEqual(self.decide('make test'), (None, ''))

    def test_missing_or_failing_kubectl_is_ignored(self):
        os.environ.pop('FAKE_CONTEXT')
        self.assertEqual(self.decide('kubectl get pods'), (None, ''))
        os.environ['PATH'] = str(self.root)  # no kubectl at all
        self.assertEqual(self.decide('helm list'), (None, ''))

    def test_prod_context_pattern_is_configurable(self):
        self.config({'guard': {'prod_context_pattern': '^live-'}})
        self.assertEqual(self.decide('kubectl --context prod-cluster get ns'), (None, ''))
        self.assertEqual(self.decide('kubectl --context live-eu get ns')[0], 'ask')

    def test_database_hosts(self):
        self.assertEqual(self.decide('psql -h db.example.com -c "select 1"'), (None, ''))
        self.config({'guard': {'prod_hosts': [r'^db\.example\.com$']}})
        for command in ('psql -h db.example.com -c "select 1"', 'pg_dump --host=db.example.com app',
                        'mysql -hdb.example.com app', 'psql postgresql://ro@db.example.com:5432/app',
                        'PGHOST=db.example.com psql app'):
            self.assertEqual(self.decide(command)[0], 'ask', command)
        self.assertEqual(self.decide('psql -h localhost app'), (None, ''))

    def test_custom_rules_add_to_the_defaults(self):
        self.config({'guard': {'confirm': [{'pattern': r'\bterraform\s+apply\b',
                                            'reason': 'terraform apply changes infrastructure'}]}})
        decision, reason = self.decide('terraform apply -auto-approve')
        self.assertEqual(decision, 'ask')
        self.assertIn('terraform apply changes infrastructure', reason)
        self.assertEqual(self.decide('kubectl --context prod-cluster get ns')[0], 'ask')

    def test_empty_confirm_list_keeps_the_defaults(self):
        self.config({'guard': {'confirm': []}})
        self.assertEqual(self.decide('kubectl --context prod-cluster get ns')[0], 'ask')

    def test_defaults_false_turns_the_default_rules_off(self):
        self.config({'guard': {'defaults': False, 'confirm': [{'pattern': 'terraform apply', 'reason': 'infra'}]}})
        self.assertEqual(self.decide('kubectl --context prod-cluster get ns'), (None, ''))
        self.assertEqual(self.decide('terraform apply')[0], 'ask')

    def test_codex_and_unknown_hosts_deny(self):
        for host in ('codex', None):
            decision, reason = self.decide('kubectl --context prod-cluster get ns', host)
            self.assertEqual(decision, 'deny')
            self.assertIn('run it themselves', reason)
        self.assertEqual(self.decide('kubectl --context prod-cluster get ns', 'opencode')[0], 'ask')

    def test_host_detection(self):
        os.environ['CLAUDE_PROJECT_DIR'] = str(self.root)
        self.assertEqual(gate.detect_host(None), 'claude')
        self.assertEqual(gate.detect_host('codex'), 'codex')
        os.environ.pop('CLAUDE_PROJECT_DIR')
        self.assertIsNone(gate.detect_host(None))

    def test_deny_rules_still_win(self):
        self.assertEqual(self.decide('kubectl --context prod-cluster apply -f .env')[0], 'deny')
        self.assertEqual(self.decide('git push -f origin main')[0], 'deny')


FIELD_SCRIPT = '''import psycopg
from dotenv import load_dotenv
load_dotenv("/srv/app/.env", override=True)
import os
dsn = os.environ["DATABASE_URL"]
with psycopg.connect(dsn, options="-c statement_timeout=60000") as conn:
    cur = conn.cursor()
    cur.execute("SET default_transaction_read_only = on")
    cur.execute("EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM orders WHERE status = 'new'")
    print(cur.fetchall())
'''


def heredoc(body):
    return f"cd /srv/app && timeout 300 .venv/bin/python - <<'PY'\n{body}PY"


class DatabaseGuard(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='gate-db-'))
        self.saved = {k: os.environ.pop(k, None) for k in ('PGHOST', 'MYSQL_HOST')}

    def tearDown(self):
        for key, value in self.saved.items():
            if value is not None:
                os.environ[key] = value

    def config(self, data):
        (self.root / '.agent').mkdir(exist_ok=True)
        (self.root / '.agent/gate.json').write_text(json.dumps(data))

    def decide(self, command, host='claude', **payload):
        output = gate.guard(self.root, {**bash(command), **payload}, host).get('hookSpecificOutput', {})
        return output.get('permissionDecision'), output.get('permissionDecisionReason', '')

    def test_env_credentials_read_only_asks(self):
        for host in ('claude', 'opencode'):
            decision, reason = self.decide(heredoc(FIELD_SCRIPT), host)
            self.assertEqual(decision, 'ask', host)
            self.assertIn('configured in the environment (.env)', reason)
        decision, reason = self.decide(heredoc(FIELD_SCRIPT), 'codex')
        self.assertEqual(decision, 'deny')
        self.assertIn('run it themselves', reason)

    def test_maintenance_sql_is_denied_on_every_host(self):
        body = FIELD_SCRIPT.replace('cur.execute("SET default', 'cur.execute("VACUUM (ANALYZE) orders")\n    #')
        for host in ('claude', 'opencode', 'codex', None):
            decision, reason = self.decide(heredoc(body), host)
            self.assertEqual(decision, 'deny', host)
            self.assertIn('VACUUM', reason)
            self.assertIn('let them run it', reason)

    def test_standalone_analyze_is_maintenance(self):
        query = "EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM orders WHERE status = 'new'"
        for statement in ('ANALYZE orders', 'ANALYZE VERBOSE orders;', 'analyze'):
            self.assertEqual(self.decide(heredoc(FIELD_SCRIPT.replace(query, statement)))[0], 'deny', statement)
        for read_only in ('EXPLAIN ANALYZE SELECT 1', 'EXPLAIN (BUFFERS, ANALYZE) SELECT 1',
                          '-- analyze the plan below\nSELECT 1'):
            self.assertEqual(self.decide(heredoc(FIELD_SCRIPT.replace(query, read_only)))[0], 'ask', read_only)

    def test_write_can_ask_instead(self):
        self.config({'guard': {'db': {'write': 'ask'}}})
        body = FIELD_SCRIPT.replace('SET default_transaction_read_only = on', 'DELETE FROM orders')
        decision, reason = self.decide(heredoc(body))
        self.assertEqual(decision, 'ask')
        self.assertIn('DELETE FROM', reason)

    def test_script_file_is_inspected(self):
        scratch = Path(tempfile.mkdtemp(prefix='gate-db-script-'))
        (scratch / 'rel_ab.py').write_text(FIELD_SCRIPT)
        self.assertEqual(self.decide(f'.venv/bin/python {scratch}/rel_ab.py')[0], 'ask')
        (self.root / 'tools').mkdir()
        (self.root / 'tools/fix.py').write_text(FIELD_SCRIPT.replace('SET default_transaction_read_only = on',
                                                                     'UPDATE orders SET status = 1'))
        self.assertEqual(self.decide('python3 tools/fix.py')[0], 'deny')
        self.assertEqual(self.decide(f'cd {self.root}/tools && python3 fix.py --dry-run')[0], 'deny')
        (self.root / 'tools/drop.sql').write_text('DROP TABLE orders;\n')
        self.assertEqual(self.decide('psql "$DATABASE_URL" -f tools/drop.sql')[0], 'deny')
        self.assertEqual(self.decide('python3 tools/missing.py'), (None, ''))

    def test_local_targets_pass(self):
        local = ('import psycopg\nconn = psycopg.connect("postgresql://app@localhost:5432/app")\n'
                 'conn.execute("DROP TABLE orders")\n')
        self.assertEqual(self.decide(heredoc(local)), (None, ''))
        self.assertEqual(self.decide('psql -h 127.0.0.1 app -c "DROP TABLE orders"'), (None, ''))
        self.assertEqual(self.decide('psql app -c "TRUNCATE orders"'), (None, ''))  # default unix socket
        self.assertEqual(self.decide('redis-cli FLUSHALL'), (None, ''))
        sqlite = 'import sqlalchemy\nengine = sqlalchemy.create_engine("sqlite:///app.db")\nDELETE FROM orders\n'
        self.assertEqual(self.decide(heredoc(sqlite)), (None, ''))

    def test_remote_targets(self):
        self.assertEqual(self.decide('psql -h db.example.com app -c "DROP TABLE orders"')[0], 'deny')
        self.assertEqual(self.decide('redis-cli -h cache.example.com FLUSHALL')[0], 'deny')
        self.assertEqual(self.decide('psql -h db.example.com app -c "select 1"'), (None, ''))
        self.assertEqual(self.decide('set -a; . ./config.env; psql -c "select 1"')[0], 'ask')
        unknown = 'import psycopg\nconn = psycopg.connect(make_dsn())\nconn.execute("TRUNCATE orders")\n'
        self.assertEqual(self.decide(heredoc(unknown))[0], 'deny')
        self.assertEqual(self.decide(heredoc(unknown.replace('TRUNCATE orders', 'SELECT 1'))), (None, ''))

    def test_plan_mode_denies_any_non_local_connection(self):
        decision, reason = self.decide(heredoc(FIELD_SCRIPT), permission_mode='plan')
        self.assertEqual(decision, 'deny')
        self.assertIn('plan (read-only) mode', reason)
        self.assertEqual(self.decide(heredoc(FIELD_SCRIPT), 'opencode', agent='plan')[0], 'deny')
        self.assertEqual(self.decide('psql app -c "select 1"', permission_mode='plan'), (None, ''))

    def test_mode_settings(self):
        self.config({'guard': {'db': {'mode': 'off'}}})
        self.assertEqual(self.decide(heredoc(FIELD_SCRIPT.replace('SET default', 'VACUUM; SET default'))), (None, ''))
        self.config({'guard': {'db': {'mode': 'deny'}}})
        self.assertEqual(self.decide(heredoc(FIELD_SCRIPT))[0], 'deny')
        self.config({'guard': {'defaults': False}})
        self.assertEqual(self.decide(heredoc(FIELD_SCRIPT))[0], 'ask')

    def test_large_script_is_fast(self):
        scratch = Path(tempfile.mkdtemp(prefix='gate-db-big-'))
        filler = '# padding line with words: select analyze cluster grant to on from\n'
        (scratch / 'big.py').write_text(FIELD_SCRIPT + filler * (300 * 1024 // len(filler)))
        start = time.perf_counter()
        self.assertEqual(self.decide(f'python3 {scratch}/big.py')[0], 'ask')
        self.assertLess(time.perf_counter() - start, 0.2)


if __name__ == '__main__':
    unittest.main()
