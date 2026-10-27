"""Shipped model ids must exist in the host catalogs (JEV-QR AC-20, QR-D11, D6).

Frozen catalogs, captured 2026-10-19. Refresh them when a host catalog changes:
- OpenCode openai: `opencode models | grep '^openai/'`. OpenCode 2.x rejects the provider argument of
  `opencode models openai`.
- Codex: the slugs with `visibility: list` in `~/.codex/models_cache.json` (fetched_at 2026-10-27T07:22:08Z,
  client_version 0.164.0; `gpt-6.1-terra` is new since 2026-10-19).
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXTENSIONS = ROOT / 'extensions'
OPENCODE_OPENAI = frozenset({
    'openai/gpt-5.3-codex-spark', 'openai/gpt-5.5', 'openai/gpt-5.5-fast',
    'openai/gpt-5.6-luna', 'openai/gpt-5.6-luna-fast', 'openai/gpt-5.6-sol', 'openai/gpt-5.6-sol-fast',
    'openai/gpt-5.6-terra', 'openai/gpt-5.6-terra-fast',
    'openai/gpt-6-astra', 'openai/gpt-6-astra-fast', 'openai/gpt-6-astra-ultrafast',
    'openai/gpt-6-luna', 'openai/gpt-6-luna-fast', 'openai/gpt-6-sol', 'openai/gpt-6-sol-fast',
    'openai/gpt-6.1-sol', 'openai/gpt-6.1-sol-fast', 'openai/gpt-6.1-sol-ultrafast',
})
CODEX = frozenset({'gpt-6.1-sol', 'gpt-6.1-terra', 'gpt-6-astra', 'gpt-6-sol', 'gpt-6-luna',
                   'gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna'})
NATIVE_OPENCODE_AGENTS = {'explore', 'general'}
RETIRED = 'gpt-6-terra'
# PO decision 2026-10-19: the Copilot catalog is not verified; its profile is follow-up F1.
RETIRED_EXEMPT = EXTENSIONS / 'opencode/profiles/githubcopilot'
TOML_MODEL = re.compile(r'^model\s*=\s*"([^"]+)"', re.M)


def load(relative):
    return json.loads((EXTENSIONS / relative).read_text(encoding='utf-8'))


def codex_role_models():
    # Helpers (explorer; reviewer for custom profiles) pin no model and inherit the session model.
    profiles = sorted((EXTENSIONS / 'codex/agents').glob('*.toml'))
    found = {p.stem: TOML_MODEL.search(p.read_text(encoding='utf-8')) for p in profiles}
    return {role: match[1] for role, match in found.items() if match}


class LeanHelpers(unittest.TestCase):
    def test_lean_codex_helpers_inherit_the_session_model(self):
        for role in ('explorer', 'reviewer'):
            text = (EXTENSIONS / f'codex/agents/{role}.toml').read_text(encoding='utf-8')
            self.assertIsNone(TOML_MODEL.search(text), role)


class OpenCodeIds(unittest.TestCase):
    def test_openai_profile_ids_are_prefixed_catalog_models(self):
        profile = load('opencode/profiles/openai/opencode.json')
        ids = [profile['small_model']]
        for role, config in profile['agent'].items():
            ids += [config['model'], *config.get('fallback', [])]
        for model in ids:
            self.assertTrue(model.startswith('openai/'), model)
            self.assertIn(model, OPENCODE_OPENAI)

    def test_tier_map_models_are_catalog_models_and_roles_are_known(self):
        tier_map = load('opencode/model-tiers.json')
        for model in tier_map['providers']['openai'].values():
            self.assertIn(model, OPENCODE_OPENAI)
        installed = {p.stem for p in (EXTENSIONS / 'opencode/agents').glob('*.md')}
        self.assertLessEqual(set(tier_map['roles']), installed | NATIVE_OPENCODE_AGENTS)


class CodexIds(unittest.TestCase):
    def test_role_and_tier_models_are_catalog_models(self):
        tiers = load('codex/model-tiers.json')
        for model in [*codex_role_models().values(), *tiers.values()]:
            self.assertIn(model, CODEX)
        for role, model in codex_role_models().items():
            self.assertIn(model, tiers.values(), f'{role} default is not a Codex tier (D6)')

    def test_opencode_role_tiers_mirror_codex_role_defaults(self):
        tier_of = {model: tier for tier, model in load('codex/model-tiers.json').items()}
        opencode_roles = load('opencode/model-tiers.json')['roles']
        for role, model in codex_role_models().items():
            self.assertEqual(opencode_roles.get(role), tier_of[model], role)


class RetiredIds(unittest.TestCase):
    def test_no_retired_model_outside_the_copilot_profile(self):
        hits = [path.relative_to(ROOT).as_posix() for path in EXTENSIONS.rglob('*')
                if path.is_file() and not path.is_relative_to(RETIRED_EXEMPT)
                and RETIRED in path.read_text(encoding='utf-8', errors='ignore')]
        self.assertEqual(hits, [])


if __name__ == '__main__':
    unittest.main()
