"""JEV-EPIC: capability maps, never price rank, determine eligible tiers."""
import os
import unittest
from unittest.mock import patch

import routing


class CapabilityRouting(unittest.TestCase):
    def setUp(self):
        self.defaults = {'roles': {}, 'tiers': {}}
        self.mapping = routing.load_tier_map({'version': 1, 'providers': {
            'a': {'fast': 'a/small', 'frontier': 'a/strong'},
            'b': {'fast': 'b/small', 'frontier': 'b/strong'}}})

    def plan(self, models, settings=None, **event):
        with patch.dict(os.environ, {}, clear=True):
            return routing.plan_spawn({'host': 'opencode', 'agent': 'developer', **event},
                                      models, self.defaults, settings or {}, self.mapping)

    @staticmethod
    def model(name, cost=None):
        return {'id': name, 'prices': {'input': cost, 'output': cost} if cost is not None else None}

    def test_stronger_cheaper_model_keeps_its_capability(self):
        plan = self.plan([self.model('a/small', 10), self.model('a/strong', 1)])
        self.assertEqual(plan['tiers'], {'fast': 'a/small', 'frontier': 'a/strong'})
        self.assertEqual([c['relative_cost'] for c in plan['pool']], [10.0, 1.0])

    def test_priced_providers_keep_role_provider_preference(self):
        models = [self.model('a/small', 1), self.model('a/strong', 20),
                  self.model('b/small', 2), self.model('b/strong', 3)]
        self.assertEqual(self.plan(models, role_default='b/small')['tiers'],
                         {'fast': 'b/small', 'frontier': 'b/strong'})

    def test_unknown_models_do_not_acquire_tiers_from_prices(self):
        plan = self.plan([self.model('unknown/small', 1), self.model('unknown/large', 20)])
        self.assertEqual(plan['result']['reason_code'], 'no_tier_routing')
        self.assertEqual(plan['tiers'], {})

    def test_unknown_prices_are_not_capability_rank_cost(self):
        plan = self.plan([self.model('a/small'), self.model('a/strong')])
        self.assertEqual([c['relative_cost'] for c in plan['pool']], [None, None])

    def test_equal_prices_preserve_capabilities_and_equal_cost(self):
        plan = self.plan([self.model('a/small', 1), self.model('a/strong', 1)])
        self.assertEqual(plan['tiers'], {'fast': 'a/small', 'frontier': 'a/strong'})
        self.assertEqual([c['relative_cost'] for c in plan['pool']], [1.0, 1.0])

    def test_explicit_overrides_and_user_pin_win(self):
        models = [self.model('unknown/a', 20), self.model('unknown/b', 1)]
        settings = {'tiers': {'fast': 'unknown/a', 'frontier': 'unknown/b', 'balanced': 'missing'}}
        self.assertEqual(self.plan(models, settings)['tiers'], {'fast': 'unknown/a', 'frontier': 'unknown/b'})
        pinned = self.plan(models, settings, pinned_model='unknown/a')
        self.assertEqual(pinned['result']['status'], 'preserved')
        self.assertTrue(pinned['keep_native'])

    def test_incomplete_zero_and_nonfinite_prices_are_unknown(self):
        for cost in (None, 0, float('nan'), float('inf')):
            with self.subTest(cost=cost):
                plan = self.plan([self.model('a/small', 1), self.model('a/strong', cost)])
                self.assertEqual(plan['tiers'], {'fast': 'a/small', 'frontier': 'a/strong'})
                self.assertEqual([c['relative_cost'] for c in plan['pool']], [None, None])

    def test_priced_provider_environment_precedes_role_default(self):
        models = [self.model('a/small', 1), self.model('a/strong', 20),
                  self.model('b/small', 2), self.model('b/strong', 3)]
        with patch.dict(os.environ, {'AGENTIC_JEV_MODEL_PROVIDER': 'b'}):
            tiers, _ = routing.spawn_tiers({'host': 'opencode', 'role_default': 'a/small'},
                                           models, self.defaults, None, self.mapping)
        self.assertEqual(tiers, {'fast': 'b/small', 'frontier': 'b/strong'})
