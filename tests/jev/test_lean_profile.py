"""Lean + JEV: the workflow is a checklist for the native session, never a delegation to absent role agents."""
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import adapters
import hook

ROLES = ('product-owner', 'developer', 'qa', 'team-lead', 'instruction-reviewer')
PLUGIN = Path(__file__).resolve().parents[2] / 'extensions/opencode/hooks/agentic-jev.ts'


class LeanProfile(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {'HOME': str(self.project / 'home')}, clear=True)
        self.environment.start()
        self.manifest('lean')
        workflows = self.project / '.agent/workflows'
        workflows.mkdir(parents=True)
        (workflows / 'develop-feature.md').write_text(
            '---\nname: develop-feature\ntype: workflow\ntrigger: /develop-feature\ndescription: Implement a feature\n'
            'roles:\n  - developer\n  - qa\nexecution:\n  initiator: product-owner\n---\n')
        for folder, suffix in (('.claude/agents', '.md'), ('.codex/agents', '.toml')):
            (self.project / folder).mkdir(parents=True)
            for name in ('explorer', 'reviewer'):
                (self.project / folder / (name + suffix)).write_text(f'---\nname: {name}\ndescription: {name}\n---\n'
                                                                     if suffix == '.md' else f'description = "{name}"\n')

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def manifest(self, profile):
        settings = {'jev': {'enabled': True}}
        if profile:
            settings['profile'] = profile
        (self.project / '.agentic.json').write_text(json.dumps({'settings': settings}))

    def payload(self, name, session='root', **kwargs):
        return {'hook_event_name': name, 'session_id': session, 'transcript_path': '/dev/null', 'cwd': str(self.project), **kwargs}

    @staticmethod
    def answer(request, selected):
        name, question = next(iter(request['questions'].items()))
        return {'status': 'evaluated', 'answers': {name: {'type': 'choice', 'choice': selected, 'confidence': 1,
                'probabilities': {k: int(k == selected) for k in question['criteria']}}}, 'usage': {'input_tokens': 100}}

    def context(self, adapter, prompt, session='root'):
        out = adapter(self.project, self.payload('UserPromptSubmit', session=session, prompt=prompt))
        return (out.get('hookSpecificOutput') or {}).get('additionalContext', '')

    def assert_lean(self, context):
        self.assertIn('.agent/workflows/develop-feature.md', context)
        self.assertIn('perform its steps yourself', context)
        self.assertNotRegex(context.lower(), r'\bdelegat')
        for role in ROLES:
            self.assertNotIn(role, context)
        self.assertNotIn('REVIEW_PIPELINE', context)
        self.assertNotIn('--prepare-spawn', context)

    def test_lean_workflow_context_on_codex_and_claude(self):
        self.assert_lean(self.context(hook.codex_event, '/develop-feature calculator'))
        self.assert_lean(self.context(hook.claude_event, '/develop-feature calculator', session='claude'))

    def test_team_and_legacy_manifests_keep_role_delegation(self):
        for profile in ('team', None):
            self.manifest(profile)
            codex = self.context(hook.codex_event, '/develop-feature calculator', session=f'codex-{profile}')
            claude = self.context(hook.claude_event, '/develop-feature calculator', session=f'claude-{profile}')
            self.assertIn('Delegate repository exploration', codex)
            self.assertIn('--prepare-spawn', codex)
            self.assertIn('Agent tool', claude)
            self.assertIn('REVIEW_PIPELINE', claude)

    def test_native_answer_adds_no_context_and_turns_the_session_off(self):
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'native')) as client:
            self.assertEqual(hook.codex_event(self.project, self.payload('UserPromptSubmit', prompt='Where is restock?')), {})
            self.assertEqual(hook.claude_event(self.project, self.payload('UserPromptSubmit', session='c', prompt='Where is restock?')), {})
        self.assertEqual(client.call_count, 2)  # one JEV call per session, nothing injected
        with patch.object(hook, 'evaluate', side_effect=AssertionError('session is off')):
            self.assertEqual(hook.codex_event(self.project, self.payload('UserPromptSubmit', prompt='and fix it')), {})

    def test_lean_helper_spawn_is_routed(self):
        hook.claude_event(self.project, self.payload('UserPromptSubmit', prompt='/develop-feature calculator'))
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'fast')):
            out = hook.claude_event(self.project, self.payload('PreToolUse', tool_name='Agent', tool_use_id='t1',
                                    tool_input={'subagent_type': 'explorer', 'prompt': 'find the pricing code'}))
        self.assertEqual(out['hookSpecificOutput']['updatedInput']['model'], 'haiku')

    def test_install_profile_defaults_to_team_for_old_manifests(self):
        self.manifest(None)
        self.assertEqual(adapters.install_profile(self.project), 'team')
        (self.project / '.agentic.json').write_text('{broken')
        self.assertEqual(adapters.install_profile(self.project), 'team')
        self.manifest('lean')
        self.assertEqual(adapters.install_profile(self.project), 'lean')

    def test_opencode_plugin_lean_branch_skips_initiator_and_delegation(self):
        source = PLUGIN.read_text()
        branch = re.search(r'if \(await leanProfile\(\)\) \{(.*?)\n      \}', source, re.S)
        self.assertIsNotNone(branch)
        body = branch.group(1)
        injected = re.search(r'`(.*)`', body).group(1)
        self.assertIn('perform its steps yourself', injected)
        self.assertNotRegex(injected.lower(), r'\bdelegat')
        self.assertIn('return;', body)
        self.assertNotIn('switchAgent', body)
        self.assertLess(source.index('await leanProfile()'), source.index('switchAgent'))


if __name__ == '__main__':
    unittest.main()
