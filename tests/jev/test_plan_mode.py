"""Plan (read-only) mode: the workflow hint asks for diagnosis and a plan, never for edits or delegation."""
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import adapters
import hook

PLUGIN = Path(__file__).resolve().parents[2] / 'extensions/opencode/hooks/agentic-jev.ts'
WORKFLOW = '.agent/workflows/debug-issue.md'


class PlanMode(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {'HOME': str(self.project / 'home')}, clear=True)
        self.environment.start()
        self.manifest('lean')
        (self.project / '.agent/workflows').mkdir(parents=True)
        (self.project / WORKFLOW).write_text('---\nname: debug-issue\ntype: workflow\ntrigger: /debug-issue\n'
                                             'description: Find and fix a defect\n---\n')

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def manifest(self, profile):
        (self.project / '.agentic.json').write_text(json.dumps({'settings': {'jev': {'enabled': True}, 'profile': profile}}))

    def context(self, adapter, session, **extra):
        payload = {'hook_event_name': 'UserPromptSubmit', 'session_id': session, 'transcript_path': '/dev/null',
                   'cwd': str(self.project), 'prompt': '/debug-issue the export fails', **extra}
        return (adapter(self.project, payload).get('hookSpecificOutput') or {}).get('additionalContext', '')

    def assert_plan(self, context):
        self.assertEqual(context, adapters.plan_context({'id': 'debug-issue', 'path': WORKFLOW}))
        self.assertIn('read-only plan mode', context)
        self.assertIn('Do not edit files', context)
        self.assertNotIn('perform its steps yourself', context)
        self.assertNotRegex(context.lower(), r'\bdelegat')
        self.assertLessEqual(context.count('. '), 1)

    def test_claude_plan_permission_mode_gets_the_read_only_hint(self):
        for profile in ('lean', 'team'):
            self.manifest(profile)
            self.assert_plan(self.context(hook.claude_event, 'plan-' + profile, permission_mode='plan'))

    def test_claude_other_modes_keep_the_normal_hint(self):
        for mode in ('default', 'acceptEdits', None):
            context = self.context(hook.claude_event, f'claude-{mode}', **({'permission_mode': mode} if mode else {}))
            self.assertIn('perform its steps yourself', context)

    def test_codex_without_a_mode_keeps_the_normal_hint(self):
        self.assertIn('perform its steps yourself', self.context(hook.codex_event, 'codex'))

    def test_opencode_plan_flag_returns_the_shared_text(self):
        event = {'kind': 'prompt', 'session_id': 'oc-plan', 'event_id': 'm1', 'prompt': '/debug-issue the export fails'}
        planned = hook.opencode_event(self.project, {**event, 'plan_mode': True})
        self.assertEqual(planned['workflow']['id'], 'debug-issue')
        self.assert_plan(planned['context'])
        normal = hook.opencode_event(self.project, {**event, 'session_id': 'oc-build', 'event_id': 'm2'})
        self.assertEqual(normal['workflow']['id'], 'debug-issue')
        self.assertNotIn('context', normal)

    def test_opencode_plugin_sends_the_plan_agent_and_uses_the_hook_text(self):
        source = PLUGIN.read_text()
        self.assertIn('plan_mode: session.agent === "plan"', source)
        branch = re.search(r'if \(typeof result\.context === "string"\) \{(.*?)\n      \}', source, re.S)
        self.assertIsNotNone(branch)
        self.assertIn('return;', branch.group(1))
        # The plan branch runs before the lean hint and before any agent switch; the text lives only in Python.
        self.assertLess(source.index('typeof result.context'), source.index('await leanProfile()'))
        self.assertLess(source.index('typeof result.context'), source.index('switchAgent'))
        self.assertNotIn('read-only plan mode', source)


if __name__ == '__main__':
    unittest.main()
