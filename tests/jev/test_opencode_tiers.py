"""OpenCode tier map (JEV-QR iteration 4): tier source, provider choice, role defaults and the QR-D2 end-to-end path."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import hook
import routing

ROOT = Path(__file__).resolve().parents[2]
SHIPPED = json.loads((ROOT / 'extensions/opencode/model-tiers.json').read_text())
MAP = routing.load_tier_map(SHIPPED)
LUNA, SOL, ASTRA = 'openai/gpt-6-luna', 'openai/gpt-6.1-sol', 'openai/gpt-6-astra'
NO_DEFAULTS = {'roles': {}, 'tiers': {}}
TWO_PROVIDERS = routing.load_tier_map({'version': 1, 'roles': {'developer': 'balanced'}, 'providers': {
    'alpha': {'fast': 'alpha/f', 'balanced': 'alpha/b'}, 'beta': {'fast': 'beta/f', 'balanced': 'beta/b'}}})


def catalog(ids, prices=None):
    """OpenAI oauth reports `cost: []` (QR-D10) unless a price is given."""
    return [{'id': i, 'prices': (prices or {}).get(i, [])} for i in ids]


def plan(models, tier_map=MAP, **event):
    return routing.plan_spawn({'host': 'opencode', 'agent': 'developer', **event}, models, NO_DEFAULTS, {}, tier_map)


class TierSource(unittest.TestCase):
    def test_unpriced_partial_and_equal_prices_use_the_tier_map(self):
        one = {'input': 1, 'output': 1}
        for prices in (None, {LUNA: one}, {LUNA: one, SOL: one, ASTRA: one}):
            result = plan(catalog([LUNA, SOL, ASTRA], prices))
            self.assertEqual(result['fields']['cost_source'], 'tier_map')
            self.assertEqual(result['pool'], [{'tier': 'fast', 'model': LUNA, 'relative_cost': 1},
                                              {'tier': 'balanced', 'model': SOL, 'relative_cost': 2},
                                              {'tier': 'frontier', 'model': ASTRA, 'relative_cost': 3}])

    def test_complete_distinct_prices_still_use_catalog_price(self):
        prices = {LUNA: {'input': 1, 'output': 1}, SOL: {'input': 2, 'output': 2}, ASTRA: {'input': 5, 'output': 5}}
        result = plan(catalog([LUNA, SOL, ASTRA], prices))
        self.assertEqual(result['fields']['cost_source'], 'catalog_price')
        self.assertEqual([c['relative_cost'] for c in result['pool']], [1.0, 2.0, 5.0])

    def test_map_models_missing_from_the_catalog(self):
        self.assertEqual(plan(catalog([LUNA, SOL]))['tiers'], {'fast': LUNA, 'balanced': SOL})
        single = plan(catalog([LUNA]))
        self.assertEqual((single['result']['reason_code'], single['fields']['model_source']), ('single_eligible_model', 'single_eligible'))
        unrelated = plan(catalog([LUNA, 'openai/custom']), role_default='openai/custom')
        self.assertEqual(unrelated['result']['reason_code'], 'no_tier_routing')
        self.assertEqual((unrelated['role_default'], unrelated['fields']['role_default_source']), ('openai/custom', 'profile'))
        self.assertIsNone(unrelated['fields']['cost_source'])

    def test_override_only_tiers_are_ranked(self):
        tiers, source = routing.spawn_tiers({'host': 'opencode'}, catalog(['x/a', 'x/b']), NO_DEFAULTS,
                                            {'fast': 'x/a', 'frontier': 'x/b', 'balanced': 'x/missing'}, MAP)
        self.assertEqual((tiers, source), ({'fast': 'x/a', 'frontier': 'x/b'}, 'tier_order'))


class ProviderChoice(unittest.TestCase):
    MODELS = catalog(['alpha/f', 'alpha/b', 'beta/f', 'beta/b'])

    def test_environment_then_role_default_provider_then_file_order(self):
        with patch.dict(os.environ, {'AGENTIC_JEV_MODEL_PROVIDER': 'beta'}):
            self.assertEqual(plan(self.MODELS, TWO_PROVIDERS, role_default='alpha/b')['tiers']['fast'], 'beta/f')
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(plan(self.MODELS, TWO_PROVIDERS, role_default='beta/b')['tiers']['fast'], 'beta/f')
            self.assertEqual(plan(self.MODELS, TWO_PROVIDERS)['tiers'], {'fast': 'alpha/f', 'balanced': 'alpha/b'})

    def test_providers_are_never_mixed(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(plan(catalog(['alpha/f', 'beta/f', 'beta/b']), TWO_PROVIDERS)['tiers'], {'fast': 'beta/f', 'balanced': 'beta/b'})
            self.assertEqual(plan(catalog(['alpha/f', 'beta/f', 'beta/b']), TWO_PROVIDERS, role_default='alpha/f')['tiers'], {})
        self.assertIsNone(routing.map_provider(TWO_PROVIDERS, {'alpha/f', 'beta/f'}, 'alpha'))

    def test_role_on_an_unmapped_provider_never_routes_to_map_models(self):
        """P2-1: a github-copilot role default must not be routed to OpenAI map models."""
        with patch.dict(os.environ, {}, clear=True):
            result = plan(catalog([LUNA, SOL, ASTRA, 'github-copilot/x']), role_default='github-copilot/x')
        self.assertEqual((result['tiers'], result['fields']['cost_source']), ({}, None))
        self.assertEqual(result['result']['reason_code'], 'no_tier_routing')
        routing.apply_role_default(result)
        self.assertEqual((result['result']['model'], result['result']['model_source']), ('github-copilot/x', 'role_default'))
        self.assertEqual(result['fields']['role_default_source'], 'profile')


class RoleDefault(unittest.TestCase):
    MODELS = catalog([LUNA, SOL, ASTRA])

    def resolved(self, **event):
        result = plan(self.MODELS, **event)
        return result['role_default'], result['fields']['role_default_source'], result['role_ctx']['role_default']

    def test_profile_model_wins_only_when_in_the_catalog(self):
        self.assertEqual(self.resolved(role_default=ASTRA), (ASTRA, 'profile', {'model': ASTRA, 'tier': 'frontier'}))
        self.assertEqual(self.resolved(role_default='openai/gpt-6-terra')[:2], (SOL, 'role_tier'))
        self.assertEqual(self.resolved(), (SOL, 'role_tier', {'model': SOL, 'tier': 'balanced'}))
        self.assertEqual(self.resolved(agent='analyst')[:2], (LUNA, 'role_tier'))

    def test_native_agents_use_their_type_and_unknown_roles_stay_native(self):
        self.assertEqual(self.resolved(agent=None, native_agent_type='explore')[:2], (LUNA, 'role_tier'))
        self.assertEqual(self.resolved(agent='unmapped')[:2], (None, None))

    def test_codex_and_claude_are_unchanged(self):
        codex = {'roles': {'developer': 'gpt-6.1-sol'}, 'tiers': {}}
        self.assertEqual(routing.role_default_model({'host': 'codex', 'agent': 'developer'}, codex, [{'id': 'gpt-6.1-sol'}]),
                         ('gpt-6.1-sol', 'defaults'))
        claude = {'roles': {'developer': 'claude-sonnet-5'}, 'tiers': {}}
        self.assertEqual(routing.role_default_model({'host': 'claude', 'agent': 'developer'}, claude, [{'id': 'sonnet'}]),
                         ('sonnet', 'defaults'))
        result = routing.plan_spawn({'host': 'codex', 'agent': 'qa'}, [{'id': 'a'}, {'id': 'b'}], codex, {}, MAP)
        self.assertEqual((result['result']['reason_code'], result['fields']['cost_source']), ('no_tier_routing', 'tier_order'))

    def test_pins_are_preserved_without_a_role_default(self):
        result = plan(self.MODELS, pinned_model=ASTRA)
        routing.apply_role_default(result)
        self.assertEqual((result['result']['status'], result['result']['model_source']), ('preserved', 'pinned'))
        self.assertNotIn('model', result['result'])
        self.assertIsNone(result['fields']['role_default_source'])

    def test_reviewer_without_prices_or_lightweight_model_gets_the_fast_tier(self):
        result = plan(self.MODELS, agent='instruction-reviewer')
        self.assertEqual(result['result'], {'status': 'routed', 'model': LUNA, 'reason_code': 'tier_fast_price_unknown'})
        self.assertEqual(result['fields']['model_source'], 'review_model')


class TierMapParsing(unittest.TestCase):
    def test_invalid_maps_load_empty_and_bad_entries_are_dropped(self):
        empty = {'roles': {}, 'providers': {}}
        for data in (None, [], 'x', {}, {'version': 2, 'providers': SHIPPED['providers']}, {'version': True}, {'version': '1'}):
            self.assertEqual(routing.load_tier_map(data), empty)
        loaded = routing.load_tier_map({'version': 1, 'roles': {'qa': 'huge', 'pm': 'fast', 'x': 3}, 'providers': [1]})
        self.assertEqual(loaded, {'roles': {'pm': 'fast'}, 'providers': {}})
        loaded = routing.load_tier_map({'version': 1, 'providers': {'p': {'fast': 'p/a', 'huge': 'p/b', 'balanced': 2}, 'q': 'bad'}})
        self.assertEqual(loaded['providers'], {'p': {'fast': 'p/a'}, 'q': {}})


class EndToEnd(unittest.TestCase):
    """Default OpenCode install: raw role_default null, three unpriced map models (QR-D2, AC-17/AC-18)."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        (self.project / '.agentic.json').write_text(json.dumps({'settings': {'jev': {'enabled': True}}}))
        (self.project / '.opencode/agents').mkdir(parents=True)
        (self.project / '.opencode/agents/developer.md').write_text('---\ndescription: developer\n---\n')
        self.tiers_file = self.project / hook.OPENCODE_TIERS_FILE
        self.tiers_file.parent.mkdir(parents=True)
        self.tiers_file.write_text(json.dumps(SHIPPED))

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def spawn(self, event_id, choice, confidence):
        seen = {}

        def respond(project, settings, request):
            seen['state'] = request['state']
            return {'status': 'evaluated', 'usage': {'cost_usd': .0001},
                    'answers': {'model': {'type': 'choice', 'choice': choice, 'confidence': confidence}}}
        event = {'host': 'opencode', 'kind': 'spawn', 'session_id': 'root', 'event_id': event_id, 'agent': 'developer',
                 'prompt': 'Implement the change', 'role_default': None, 'models': catalog([LUNA, SOL, ASTRA])}
        with patch.object(hook, 'evaluate', side_effect=respond):
            result = hook.run_event(self.project, event)
        return result, seen.get('state'), self.record(event_id)

    def record(self, event_id):
        records = [json.loads(p.read_text()) for p in (self.project / '.agentic/jev').glob('event-*.json')]
        return next(r for r in records if r['context'].get('event_id') == event_id)

    def test_clarify_applies_the_role_tier_default(self):
        result, state, record = self.spawn('s1', 'clarify', .5)
        self.assertEqual((state['cost_source'], len(state['candidates'])), ('tier_map', 3))
        self.assertEqual(state['role_default'], {'model': SOL, 'tier': 'balanced'})
        self.assertEqual((result['model'], result['model_source']), (SOL, 'role_default'))
        self.assertEqual((record['cost_source'], record['role_default_source'], record['outcome']), ('tier_map', 'role_tier', 'role_default_applied'))

    def test_confident_fast_maps_to_the_fast_model(self):
        result, _, record = self.spawn('s2', 'fast', .95)
        self.assertEqual((result['model'], result['model_source'], result['status']), (LUNA, 'jev_tier', 'evaluated'))
        self.assertEqual(record['outcome'], 'jev_applied')

    def test_opencode_spawn_with_assignment_unavailable_still_asks(self):
        """P3-1: the QR-D12 skip is Codex-only."""
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: {'status': 'evaluated', 'usage': {'cost_usd': .0001},
                          'answers': {'model': {'type': 'choice', 'choice': 'fast', 'confidence': .95}}}) as client:
            result = hook.run_event(self.project, {'host': 'opencode', 'kind': 'spawn', 'session_id': 'root', 'event_id': 'flag',
                                                   'agent': 'developer', 'prompt': 'x', 'assignment_unavailable': True,
                                                   'models': catalog([LUNA, SOL, ASTRA])})
        self.assertEqual((client.call_count, result['model'], result['model_source']), (1, LUNA, 'jev_tier'))

    def test_missing_or_malformed_map_keeps_todays_behaviour(self):
        for index, content in enumerate((None, '{broken', json.dumps({**SHIPPED, 'version': 2}), json.dumps({'version': 1, 'providers': 7}))):
            if content is None:
                self.tiers_file.unlink()
            else:
                self.tiers_file.write_text(content)
            result, state, record = self.spawn(f'bad-{index}', 'fast', .95)
            self.assertIsNone(state)
            self.assertEqual((result['reason_code'], result['model_source']), ('no_tier_routing', 'none'))
            self.assertIsNone(record['cost_source'])


if __name__ == '__main__':
    unittest.main()
