"""Offline checks for the comparative pilot runner: matrix, prompts and frozen acceptance. No model calls."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import pilot_jev  # noqa: E402


class Pilot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        subprocess.run(['git', 'init', '-q', str(self.project)], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self):
        subprocess.run(['git', '-C', str(self.project), 'add', '-A'], check=True)
        subprocess.run(['git', '-C', str(self.project), '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'base'], check=True)

    def test_matrix_has_27_primary_and_12_ablation_cells(self):
        cells = pilot_jev.matrix(('codex', 'claude', 'opencode'), ('A', 'B', 'C'))
        self.assertEqual(len(cells), 39)
        self.assertEqual(sum(mode in pilot_jev.ABLATIONS for _, _, mode in cells), 12)
        self.assertFalse(any(task == 'B' and mode in pilot_jev.ABLATIONS for _, task, mode in cells))

    def test_only_fixed_and_models_only_name_the_workflow(self):
        for mode in pilot_jev.MODES + pilot_jev.ABLATIONS:
            named = pilot_jev.WORKFLOWS['C'] in pilot_jev.prompt('C', mode)
            self.assertEqual(named, mode in ('fixed', 'models_only'), mode)
            self.assertIn('50,000 tokens', pilot_jev.prompt('C', mode))

    def test_task_a_acceptance(self):
        grafana = self.project / 'configurations/grafana'
        grafana.mkdir(parents=True)
        for name in ('one.json', 'two.json', 'three.json'):
            (grafana / name).write_text('{}')
        self.commit()
        report = self.project / 'GRAFANA_FEASIBILITY.md'
        report.write_text('VERDICT: FEASIBLE\nImport one.json, two.json and three.json through provisioning.\n')
        self.assertTrue(pilot_jev.accept('A', self.project)['accepted'])
        report.write_text('Feasible.\none.json two.json three.json\n')
        self.assertFalse(pilot_jev.accept('A', self.project)['checks']['verdict_line'])
        report.write_text('VERDICT: FEASIBLE\none.json two.json three.json\n')
        (grafana / 'one.json').write_text('{"changed": true}')
        self.assertFalse(pilot_jev.accept('A', self.project)['checks']['only_report_changed'])

    def test_task_b_acceptance_requires_existing_lines(self):
        (self.project / 'src').mkdir()
        (self.project / 'src/app.py').write_text('a = 1\nb = 2\nc = 3\n')
        self.commit()
        (self.project / 'REVIEW.md').write_text('src/app.py:1 x\nsrc/app.py:2 y\nsrc/app.py:3 z\n')
        self.assertTrue(pilot_jev.accept('B', self.project)['accepted'])
        (self.project / 'REVIEW.md').write_text('src/app.py:1 x\nsrc/app.py:2 y\nsrc/app.py:99 z\nsrc/missing.py:1 w\n')
        self.assertFalse(pilot_jev.accept('B', self.project)['accepted'])

    def test_runtime_output_is_not_a_changed_file(self):
        self.commit()
        (self.project / '.agentic/jev').mkdir(parents=True)
        (self.project / '.agentic/jev/event-1.json').write_text('{}')
        self.assertEqual(pilot_jev.changed_files(self.project), [])

    def test_meter_counts_uncached_once_per_claude_message(self):
        meter = pilot_jev.Meter('claude', self.project, 0)
        event = {'type': 'assistant', 'message': {'id': 'm1', 'model': 'sonnet', 'usage': {
            'input_tokens': 10, 'cache_creation_input_tokens': 100, 'cache_read_input_tokens': 1000, 'output_tokens': 5}}}
        meter.line(event)
        meter.line(event)
        self.assertEqual(meter.uncached(), 115)
        self.assertEqual(meter.rows()[0]['cached'], 1000)

    def test_meter_reads_codex_rollouts_of_this_project_only(self):
        home = Path(self.tmp.name) / 'home'
        day = home / '.codex/sessions/2026/10/20'
        day.mkdir(parents=True)
        for name, cwd in (('own', str(self.project)), ('other', '/elsewhere')):
            lines = [{'type': 'session_meta', 'payload': {'id': name, 'cwd': cwd}},
                     {'type': 'event_msg', 'payload': {'type': 'token_count', 'info': {'total_token_usage': {
                         'input_tokens': 1000, 'cached_input_tokens': 900, 'output_tokens': 20}}}}]
            (day / f'rollout-{name}.jsonl').write_text('\n'.join(json.dumps(line) for line in lines) + '\n')
        meter = pilot_jev.Meter('codex', self.project, 0)
        with unittest.mock.patch.object(pilot_jev.Path, 'home', return_value=home), \
                unittest.mock.patch.object(pilot_jev.time, 'strftime', return_value='2026/10/20'):
            self.assertEqual(meter.uncached(), 120)


if __name__ == '__main__':
    unittest.main()
