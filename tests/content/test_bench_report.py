"""Offline checks of the SDLC benchmark arms and report statistics (scripts/bench_sdlc.py)."""
import json
import tempfile
import unittest
from pathlib import Path

import bench_sdlc


def cell(host, task, mode, status='accepted', uncached=1000, cached=4000, output=100, cost=None, rep=1, **extra):
    return {'host': host, 'task': task, 'mode': mode, 'rep': rep, 'status': status, 'model': 'm', 'cost_usd': cost,
            'subagents': 0, 'acceptance': {'delivered_green': status == 'accepted', 'checks': {}},
            'tokens': {'uncached': uncached, 'cached': cached, 'output': output,
                       'agents': [{'model': 'm', 'uncached': uncached, 'cached': cached, 'output': output}]}, **extra}


class BenchArms(unittest.TestCase):
    def test_install_flags_per_mode(self):
        self.assertEqual(bench_sdlc.install_flags('plain'), [])
        self.assertEqual(bench_sdlc.install_flags('v1'), [])
        self.assertEqual(bench_sdlc.install_flags('lean'), ['--profile', 'lean'])
        self.assertEqual(bench_sdlc.install_flags('lean-jev')[:3], ['--profile', 'lean', '--enable-jev'])
        self.assertEqual(bench_sdlc.install_flags('team-jev')[:3], ['--profile', 'team', '--enable-jev'])
        self.assertTrue(set(bench_sdlc.DEFAULT_MODES) <= set(bench_sdlc.MODES))

    def test_codex_usage_limit_is_a_quota_stop(self):
        message = "You've hit your usage limit. Upgrade to Pro or try again at 7:22 PM."
        self.assertTrue(bench_sdlc.pilot_jev.QUOTA.search(message))

    def test_codex_effort_override(self):
        self.assertEqual(bench_sdlc.pilot_jev.codex_effort(), [])
        bench_sdlc.pilot_jev.EFFORT['codex'] = 'low'
        try:
            self.assertEqual(bench_sdlc.pilot_jev.codex_effort(), ['-c', 'model_reasoning_effort="low"'])
        finally:
            bench_sdlc.pilot_jev.EFFORT.clear()

    def test_projects_are_stable_per_host_and_mode(self):
        self.assertEqual(bench_sdlc.project_path('codex', 'lean-jev').name, 'codex-lean-jev')
        self.assertEqual(bench_sdlc.cell_name('codex', 'T1', 'lean-jev', 2), 'codex-T1-lean-jev-r2')

    def test_every_task_has_a_reference_and_hidden_tests(self):
        for task, spec in bench_sdlc.TASKS.items():
            self.assertTrue((bench_sdlc.BENCH / 'reference' / task).is_dir(), task)
            if 'hidden_tests' in spec['checks']:
                self.assertTrue(any((bench_sdlc.BENCH / spec['hidden']).glob('test_hidden_*.py')), task)


class BenchStatistics(unittest.TestCase):
    def test_wilson_interval(self):
        low, high = bench_sdlc.wilson(9, 9)
        self.assertEqual(high, 1.0)
        self.assertAlmostEqual(low, 0.701, places=3)
        self.assertIsNone(bench_sdlc.wilson(0, 0))

    def test_quantiles_ignore_missing_values(self):
        self.assertEqual(bench_sdlc.quantiles([None, 5]), (5, 5, 5))
        self.assertEqual(bench_sdlc.quantiles([1, 2, 3, 4, 5])[0], 3)
        self.assertIsNone(bench_sdlc.quantiles([None]))

    def test_cost_uses_host_cost_or_price_table(self):
        self.assertEqual(bench_sdlc.estimated_cost(cell('claude', 'T1', 'lean', cost=0.5), {}), 0.5)
        prices = {'m': {'input': 1.0, 'cached_input': 0.1, 'output': 10.0}}
        # (1000 - 100) uncached input + 4000 cached + 100 output, per 1M tokens.
        self.assertAlmostEqual(bench_sdlc.estimated_cost(cell('codex', 'T1', 'lean'), prices), 0.0023)
        self.assertIsNone(bench_sdlc.estimated_cost(cell('codex', 'T1', 'lean'), {'m': {'input': None}}))
        routed = cell('codex', 'T1', 'lean-jev')
        routed['tokens']['agents'].append({'model': 'unpriced', 'uncached': 10, 'cached': 0, 'output': 1})
        self.assertIsNone(bench_sdlc.host_cost(routed, prices))
        jev = {'calls': 1, 'usage': {'input_tokens': 1_000_000, 'output_tokens': 10}}
        priced = {**prices, 'typesafe/jev': {'input': 0.042, 'output': 0.0}}
        self.assertAlmostEqual(bench_sdlc.estimated_cost(cell('claude', 'T1', 'lean-jev', cost=0.5, jev=jev), priced), 0.542)
        self.assertIsNone(bench_sdlc.estimated_cost(cell('claude', 'T1', 'lean-jev', cost=0.5, jev=jev), prices))

    def test_summary_uses_common_tasks_and_counts_harness_errors_apart(self):
        cells = [cell('codex', 'T1', 'plain', cost=0.1), cell('codex', 'T2', 'plain', status='rejected', cost=0.1),
                 cell('codex', 'T1', 'lean-jev', cost=0.3, jev={'calls': 1, 'usage': {'input_tokens': 50, 'output_tokens': 5}}),
                 cell('codex', 'T2', 'lean-jev', status='harness_error')]
        rows = {r['mode']: r for r in bench_sdlc.summarize(cells, {'typesafe/jev': {'input': 0.042, 'output': 0.0}})}
        self.assertEqual(rows['plain']['tasks'], ['T1'])
        self.assertEqual((rows['plain']['n'], rows['plain']['accepted']), (1, 1))
        self.assertEqual(rows['lean-jev']['harness_errors'], 1)
        self.assertAlmostEqual(rows['lean-jev']['cost_per_success'], 0.3 + 50 * 0.042 / 1e6)
        self.assertEqual((rows['lean-jev']['jev_calls_mean'], rows['lean-jev']['jev_tokens']), (1, 55))
        self.assertIsNone(rows['plain']['jev_calls_mean'])

    def test_report_writes_markdown_and_summary_json(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            for c in (cell('claude', 'T1', 'lean', cost=0.2), cell('claude', 'T1', 'plain', status='rejected', cost=0.1)):
                (out / bench_sdlc.cell_name(c['host'], c['task'], c['mode'], 1)).mkdir()
                (out / bench_sdlc.cell_name(c['host'], c['task'], c['mode'], 1) / 'result.json').write_text(json.dumps(c))
            bench_sdlc.report(out, out / 'report.md')
            summary = json.loads((out / 'summary.json').read_text())
            self.assertEqual({r['mode']: r['accepted'] for r in summary}, {'plain': 0, 'lean': 1})
            self.assertIn('Cost per success', (out / 'report.md').read_text())


if __name__ == '__main__':
    unittest.main()
