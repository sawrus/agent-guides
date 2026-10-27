"""R&D question fixtures use the runtime builders, stay within the request limit and analyze offline."""
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

import api
import questions

ROOT = Path(__file__).resolve().parents[2]
RND = ROOT / 'docs/jev-rnd'
REQUEST_LIMIT = 32768
CYRILLIC = re.compile('[а-яА-ЯёЁ]')


def load(name):
    spec = importlib.util.spec_from_file_location('rnd_' + name, RND / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixtures_module = load('question_fixtures')
analyze = load('analyze')


class QuestionFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = fixtures_module.fixtures()

    def family(self, name):
        return [c for c in self.cases if c['family'] == name]

    def test_families_have_the_planned_size_and_languages(self):
        routing, tiers = self.family('workflow_routing'), self.family('model_tier')
        self.assertEqual((len(routing), len(tiers)), (12, 8))
        prompts = [c['state']['original_request'] for c in routing]
        self.assertTrue(any(CYRILLIC.search(p) for p in prompts))
        self.assertTrue(any(not CYRILLIC.search(p) for p in prompts))
        self.assertEqual(len({c['id'] for c in self.cases}), len(self.cases))

    def test_requests_are_valid_bounded_and_built_by_the_runtime(self):
        for case in self.cases:
            request = {'state': case['state'], 'questions': case['questions']}
            api.validate(request)
            self.assertLess(len(json.dumps({'model': 'jev-1.13.0', **request}, ensure_ascii=False).encode()), REQUEST_LIMIT, case['id'])
            question = next(iter(case['questions'].values()))
            self.assertTrue(set(case['expected']) <= set(question['criteria']), case['id'])
        instructions = {next(iter(c['questions'].values()))['instructions'] for c in self.cases}
        self.assertEqual(instructions, {questions.WORKFLOW_INSTRUCTIONS, questions.MODEL_INSTRUCTIONS})

    def test_routing_family_holds_out_the_failing_request_and_offers_the_general_option(self):
        text = json.dumps(self.family('workflow_routing'), ensure_ascii=False)
        self.assertIsNone(re.search(r'calculator|калькулятор|crud', text, re.I))
        criteria = self.family('workflow_routing')[0]['questions']['workflow']['criteria']
        self.assertTrue(criteria['develop-feature'].startswith('GENERAL. '))
        self.assertIn('add-migration', criteria)

    def test_experiment_selects_the_questions_suite(self):
        sys.path.insert(0, str(RND))
        try:
            experiment = load('experiment')
            with patch.dict(os.environ, {'JEV_RND_SUITE': 'questions'}):
                suite, cases = experiment.suite_cases()
            with patch.dict(os.environ, {'JEV_RND_SUITE': 'other'}), self.assertRaises(RuntimeError):
                experiment.suite_cases()
        finally:
            sys.path.remove(str(RND))
        self.assertEqual((suite, len(cases)), ('questions', 20))
        self.assertTrue(experiment.RESULTS['questions'].endswith('questions-results.json'))


class QuestionsSuiteClient(unittest.TestCase):
    """The paid questions suite reuses the hook client, endpoint and key; no network here."""

    def setUp(self):
        sys.path.insert(0, str(RND))
        self.experiment = load('experiment')
        sys.path.remove(str(RND))
        self.loader = patch.object(self.experiment.question_fixtures, 'load_runtime', return_value=api)
        self.loader.start()
        self.addCleanup(self.loader.stop)

    def test_official_endpoint_uses_the_typesafe_key_through_api_evaluate(self):
        response = {'model': 'jev-1.13.0', 'answers': {}, 'usage': {'cost_usd': None}}
        with patch.dict(os.environ, {'TYPESAFE_API_KEY': 'synthetic'}, clear=True), \
                patch.object(api, 'read_json', return_value={}), \
                patch.object(api, 'evaluate', return_value={'status': 'evaluated', 'response': response}) as client:
            endpoint, send = self.experiment.hook_client_sender()
            self.assertEqual(send({'model': 'jev-1.13.0', 'state': {'a': 1}, 'questions': {'q': {}}}), response)
        self.assertEqual(endpoint, api.PROVIDERS['typesafe'][0])
        self.assertEqual(client.call_args.args[2], {'state': {'a': 1}, 'questions': {'q': {}}})

    def test_missing_key_and_client_fallback_stop_before_or_at_the_call(self):
        with patch.dict(os.environ, {'JEV_API_URL': 'https://jevtypesafeai.com/api/v1/decide'}, clear=True), \
                patch.object(api, 'read_json', return_value={}), patch.object(api, 'key_for', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'JEV_API_KEY missing'):
                self.experiment.hook_client_sender()
        with patch.dict(os.environ, {'TYPESAFE_API_KEY': 'synthetic'}, clear=True), patch.object(api, 'read_json', return_value={}), \
                patch.object(api, 'evaluate', return_value={'status': 'fallback', 'reason_code': 'request_too_large'}):
            _, send = self.experiment.hook_client_sender()
            with self.assertRaisesRegex(RuntimeError, 'request_too_large'):
                send({'state': {}, 'questions': {}})


class AnalyzeQuestions(unittest.TestCase):
    def test_list_expectations_are_scored_and_validated(self):
        case = next(c for c in fixtures_module.fixtures() if c['id'] == 'tier_small_program')
        criteria = case['questions']['model']['criteria']
        def run(choice, latency):
            answer = {'type': 'choice', 'choice': choice, 'confidence': .8, 'probabilities': {k: float(k == choice) for k in criteria}}
            return {'case_id': case['id'], 'variant': 'normal', 'family': case['family'], 'expected': case['expected'],
                    'request': {'state': case['state'], 'questions': case['questions']}, 'model': 'jev-1.13.0',
                    'answers': {'model': answer}, 'input_tokens': 100, 'cost_usd': .001, 'latency_ms': latency}
        result = {'runs': [run('balanced', 10), run('frontier', 20)], 'total_cost_usd': .002}
        summary = analyze.summarize(result)
        self.assertEqual(summary['families'], {'model_tier': {'calls': 2, 'agreed': 1}})
        result['runs'][0]['answers']['model']['choice'] = 'unknown'
        with self.assertRaises(AssertionError):
            analyze.summarize(result)

    def test_offline_verify_does_not_require_the_questions_results_file(self):
        self.assertEqual(analyze.QUESTIONS_RESULTS.name, 'questions-results.json')
        if not analyze.QUESTIONS_RESULTS.is_file():
            core = json.loads(analyze.CORE_RESULTS.read_text())
            self.assertNotIn('questions', analyze.summarize(core))


if __name__ == '__main__':
    unittest.main()
