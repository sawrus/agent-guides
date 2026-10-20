"""Synthetic, explicit usage records; no native session files are read."""
import unittest

from review_usage import summarize


class ReviewUsageTests(unittest.TestCase):
    def record(self, **changes):
        data = dict(agent_id='a', role='developer', model='model-a', source='fixture',
                    cutoff='2026-10-20T10:00:00Z', input_tokens=100, cached_input_tokens=40,
                    output_tokens=20, reasoning_tokens=5, kind='delta', event_id='event-a')
        return dict(data, **changes)

    def test_cache_and_reasoning_are_subsets(self):
        result = summarize([self.record()])
        self.assertEqual(result['rows'][0]['total_tokens'], 120)
        self.assertEqual(result['total_tokens'], 120)
        self.assertFalse(result['partial'])

    def test_missing_usage_is_not_zero(self):
        result = summarize([self.record(input_tokens=None)])
        self.assertIsNone(result['rows'][0]['total_tokens'])
        self.assertIsNone(result['total_tokens'])
        self.assertTrue(result['partial'])

    def test_cumulative_latest_and_duplicate_events_count_once(self):
        first = self.record(kind='cumulative', sequence=1)
        latest = self.record(kind='cumulative', sequence=2, event_id='event-b', input_tokens=150)
        result = summarize([latest, first, latest])
        self.assertEqual(result['total_tokens'], 170)

    def test_instances_models_reviewers_and_partial_total(self):
        records = [self.record(), self.record(agent_id='b', event_id='b'),
                   self.record(model='model-b', event_id='c'),
                   self.record(agent_id='coordinator', role='product-owner', event_id='d'),
                   self.record(agent_id='review-1', role='instruction-reviewer', event_id='e'),
                   self.record(agent_id='review-2', role='memory-curator', event_id='f', output_tokens=None)]
        result = summarize(records)
        self.assertEqual(len(result['rows']), 6)
        self.assertEqual(result['total_tokens'], 600)
        self.assertTrue(result['partial'])

    def test_parent_inclusive_counts_are_not_added_to_children(self):
        parent = self.record(agent_id='parent', scope='includes_children', event_id='parent')
        result = summarize([parent, self.record()])
        self.assertIsNone(next(r for r in result['rows'] if r['agent_id'] == 'parent')['total_tokens'])
        self.assertEqual(result['total_tokens'], 120)
        self.assertTrue(result['partial'])

    def test_jev_is_separate_and_duplicate_request_counts_once(self):
        jev = dict(self.record(agent_id='jev', event_id='j'), channel='jev', request_id='request-a')
        result = summarize([self.record(), jev, jev])
        self.assertEqual(result['total_tokens'], 120)
        self.assertEqual(result['jev']['requests'], 1)
        self.assertEqual(result['jev']['total_tokens'], 120)

    def test_invalid_or_unproven_data_stays_unknown(self):
        for changes in ({'source': ''}, {'cutoff': ''}, {'input_tokens': -1},
                        {'cached_input_tokens': 101}, {'reasoning_tokens': 21},
                        {'input_tokens': True}):
            with self.subTest(changes=changes):
                self.assertIsNone(summarize([self.record(**changes)])['total_tokens'])

    def test_disjoint_deltas_add_and_conflicting_duplicates_do_not(self):
        records = [self.record(), self.record(event_id='b', input_tokens=20,
                                              cached_input_tokens=0)]
        self.assertEqual(summarize(records)['total_tokens'], 160)
        self.assertIsNone(summarize([self.record(), self.record(input_tokens=110)])['total_tokens'])

    def test_counter_contract_cannot_disappear(self):
        from lint_review_pipeline import ROOT, token_accounting_issues
        text = (ROOT / 'REVIEW_PIPELINE.md').read_text()
        self.assertTrue(token_accounting_issues(text.replace('cumulative', 'removed')))
        for path in ('docs/review-pipeline/examples/summary.example.md', 'docs/review-pipeline.md'):
            document = (ROOT / path).read_text()
            self.assertIn('not measured', document)
            self.assertIn('partial', document)
        example = (ROOT / 'docs/review-pipeline/examples/summary.example.md').read_text()
        self.assertLess(example.index('## Token usage'), example.index('## Manual acceptance'))

    def test_mixed_delta_and_cumulative_is_ambiguous(self):
        records = [self.record(), self.record(kind='cumulative', sequence=1, event_id='b')]
        self.assertIsNone(summarize(records)['total_tokens'])

    def test_contract_requires_accounting_before_acceptance(self):
        from lint_review_pipeline import ROOT, token_accounting_issues
        text = (ROOT / 'REVIEW_PIPELINE.md').read_text()
        self.assertEqual(token_accounting_issues(text), [])
        self.assertTrue(token_accounting_issues(text.replace('## Token accounting', '## Removed')))


if __name__ == '__main__':
    unittest.main()
