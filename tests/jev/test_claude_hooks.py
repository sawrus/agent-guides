"""Claude Code adapter: alias-only model routing, workflow context, permissions, reviewer packet."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import hook


class ClaudeHooks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {'HOME': str(self.project / 'home')}, clear=True)
        self.environment.start()
        (self.project / '.agentic.json').write_text(json.dumps({'settings': {'jev': {'enabled': True}}}))
        workflows = self.project / '.agent/workflows'
        workflows.mkdir(parents=True)
        for name, desc in [('develop-feature', 'Implement a feature'), ('code-review', 'Review code')]:
            (workflows / (name + '.md')).write_text(f'---\nname: {name}\ntrigger: /{name}\ndescription: {desc}\nagent: product-owner\n---\n')
        agents = self.project / '.claude/agents'
        agents.mkdir(parents=True)
        (agents / 'developer.md').write_text('---\nname: developer\ndescription: Dev role\ntools: Read\n---\nbody\n')
        (agents / 'qa.md').write_text('---\nname: qa\ndescription: QA role\nmodel: haiku\n---\nbody\n')

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    @staticmethod
    def answer(request, selected, confidence=1):
        name, question = next(iter(request['questions'].items()))
        return {'status': 'evaluated', 'answers': {name: {'type': 'choice', 'choice': selected, 'confidence': confidence,
                'probabilities': {k: int(k == selected) for k in question['criteria']}}}, 'usage': {'cost_usd': .0001}}

    def payload(self, name, **kwargs):
        return {'hook_event_name': name, 'session_id': 'root', 'transcript_path': '/dev/null', 'cwd': str(self.project), **kwargs}

    def test_explicit_workflow_adds_agent_tool_context(self):
        out = hook.claude_event(self.project, self.payload('UserPromptSubmit', prompt='/develop-feature calculator'))
        context = out['hookSpecificOutput']['additionalContext']
        self.assertIn('.agent/workflows/develop-feature.md', context)
        self.assertIn('Agent tool', context)
        self.assertNotIn('spawn_agent', context)

    def test_agent_spawn_routes_only_to_aliases(self):
        hook.claude_event(self.project, self.payload('UserPromptSubmit', prompt='/develop-feature calculator'))
        seen = {}
        def respond(project, settings, request):
            seen['criteria'] = set(request['questions']['model']['criteria'])
            return self.answer(request, 'haiku')
        with patch.object(hook, 'evaluate', side_effect=respond):
            out = hook.claude_event(self.project, self.payload('PreToolUse', tool_name='Agent', tool_use_id='t1',
                                    tool_input={'subagent_type': 'developer', 'description': 'd', 'prompt': 'add sum()'}))
        self.assertEqual(seen['criteria'], {'haiku', 'sonnet', 'opus'})
        specific = out['hookSpecificOutput']
        self.assertEqual(specific['permissionDecision'], 'allow')
        self.assertEqual(specific['updatedInput'], {'subagent_type': 'developer', 'description': 'd', 'prompt': 'add sum()', 'model': 'haiku'})

    def test_full_model_id_answer_is_never_applied(self):
        with patch.object(hook, 'run_event', return_value={'status': 'routed', 'model': 'claude-opus-5-5'}):
            out = hook.claude_event(self.project, self.payload('PreToolUse', tool_name='Task', tool_use_id='t2',
                                    tool_input={'subagent_type': 'developer', 'prompt': 'x'}))
        self.assertEqual(out, {})

    def test_profile_pin_and_explicit_model_are_preserved(self):
        with patch.object(hook, 'evaluate', side_effect=AssertionError('paid call')):
            pinned = hook.claude_event(self.project, self.payload('PreToolUse', tool_name='Agent', tool_use_id='t3',
                                       tool_input={'subagent_type': 'qa', 'prompt': 'x'}))
            explicit = hook.claude_event(self.project, self.payload('PreToolUse', tool_name='Agent', tool_use_id='t4',
                                         tool_input={'subagent_type': 'developer', 'prompt': 'x', 'model': 'opus'}))
        self.assertEqual(pinned, {})
        self.assertEqual(explicit, {})

    def test_legacy_role_name_is_canonical(self):
        hook.claude_event(self.project, self.payload('UserPromptSubmit', prompt='/develop-feature calculator'))
        out = hook.claude_event(self.project, self.payload('SubagentStart', agent_id='a1', agent_type='instruction_reviewer'))
        self.assertIn('.agentic/jev/review-', out['hookSpecificOutput']['additionalContext'])

    def test_permission_decision_shape_and_boundary(self):
        def respond(project, settings, request):
            return self.answer(request, 'allow')
        with patch.object(hook, 'evaluate', side_effect=respond):
            inside = hook.claude_event(self.project, self.payload('PermissionRequest', tool_name='Write', tool_use_id='p1',
                                       tool_input={'file_path': str(self.project / 'calc.py'), 'content': 'x'}))
            outside = hook.claude_event(self.project, self.payload('PermissionRequest', tool_name='Write', tool_use_id='p2',
                                        tool_input={'file_path': '/etc/passwd', 'content': 'x'}))
        self.assertEqual(inside['hookSpecificOutput']['decision']['behavior'], 'allow')
        self.assertEqual(outside, {})

    def test_subagent_stop_records_transcript_model(self):
        transcript = self.project / 'agent.jsonl'
        transcript.write_text('\n'.join([json.dumps({'type': 'user', 'message': {'content': 'go'}}),
                                         json.dumps({'type': 'assistant', 'message': {'model': 'claude-haiku-5-5', 'content': []}})]))
        hook.claude_event(self.project, self.payload('SubagentStop', agent_id='a2', agent_type='developer', agent_transcript_path=str(transcript)))
        records = [json.loads(p.read_text()) for p in (self.project / '.agentic/jev').glob('event-*.json')]
        self.assertTrue(any(r['result'].get('observed_model') == 'claude-haiku-5-5' for r in records))

    def test_workflow_command_reads_are_observed(self):
        result = {}
        with patch.object(hook, 'run_event', side_effect=lambda p, e: result.update(e) or {}):
            hook.claude_event(self.project, self.payload('PostToolUse', tool_name='Read', tool_input={'file_path': str(self.project / '.claude/commands/develop-feature.md')}))
        self.assertEqual(result['resources'], ['.claude/commands/develop-feature.md'])

    def test_subagent_handback_keeps_original_request(self):
        hook.claude_event(self.project, self.payload('UserPromptSubmit', prompt='/develop-feature calculator', prompt_id='u1'))
        with patch.object(hook, 'evaluate', side_effect=AssertionError('paid call')):
            for prompt in ('<agent-message from="a1">\n[Subagent hand-back] report', '<task-notification> done',
                           'Another Claude session sent a message: <agent-message from="a2">x'):
                self.assertEqual(hook.claude_event(self.project, self.payload('UserPromptSubmit', prompt=prompt, prompt_id='h')), {})
        seen = {}
        def respond(project, settings, request):
            seen['original'] = request['state']['original_prompt']
            return self.answer(request, 'haiku')
        with patch.object(hook, 'evaluate', side_effect=respond):
            hook.claude_event(self.project, self.payload('PreToolUse', tool_name='Agent', tool_use_id='t5',
                              tool_input={'subagent_type': 'developer', 'prompt': 'add sum()'}))
        self.assertEqual(seen['original'], '/develop-feature calculator')

    def test_user_dialogs_are_never_sent_as_permissions(self):
        with patch.object(hook, 'evaluate', side_effect=AssertionError('paid call')):
            for tool in ('AskUserQuestion', 'ExitPlanMode'):
                out = hook.claude_event(self.project, self.payload('PermissionRequest', tool_name=tool, tool_use_id='q',
                                        tool_input={'questions': [{'question': 'Which?'}]}))
                self.assertEqual(out, {})
        self.assertFalse(list((self.project / '.agentic/jev').glob('event-*.json')))

    def test_session_model_comes_from_transcript_then_settings(self):
        payload = self.payload('UserPromptSubmit', prompt='x')
        self.assertEqual(hook.claude_session_model(self.project, payload), 'sonnet')
        user = self.project / 'home/.claude'
        user.mkdir(parents=True)
        (user / 'settings.json').write_text(json.dumps({'model': 'opus'}))
        self.assertEqual(hook.claude_session_model(self.project, payload), 'opus')
        (self.project / '.claude/settings.json').write_text(json.dumps({'model': 'claude-haiku-5-5'}))
        self.assertEqual(hook.claude_session_model(self.project, payload), 'haiku')
        transcript = self.project / 'main.jsonl'
        transcript.write_text(json.dumps({'type': 'assistant', 'message': {'model': 'claude-sonnet-5-5', 'content': []}}))
        self.assertEqual(hook.claude_session_model(self.project, {**payload, 'transcript_path': str(transcript)}), 'sonnet')
        with patch.dict(os.environ, {'AGENTIC_JEV_DEFAULT_MODEL': 'opus'}):
            self.assertEqual(hook.claude_session_model(self.project, {**payload, 'transcript_path': str(transcript)}), 'opus')

    def test_low_confidence_spawn_uses_profile_role_default(self):
        (self.project / '.agent/jev').mkdir(parents=True, exist_ok=True)
        (self.project / '.agent/jev/model-defaults.json').write_text(json.dumps({'developer': 'sonnet', 'team-lead': 'opus', 'pm': 'haiku'}))
        hook.claude_event(self.project, self.payload('UserPromptSubmit', prompt='/develop-feature calculator'))
        confidences = iter((.58, .58, .95))
        with patch.object(hook, 'evaluate', side_effect=lambda p, s, r: self.answer(r, 'haiku', next(confidences))):
            low = hook.claude_event(self.project, self.payload('PreToolUse', tool_name='Agent', tool_use_id='t6',
                                    tool_input={'subagent_type': 'developer', 'prompt': 'add sum()'}))
            unknown = hook.claude_event(self.project, self.payload('PreToolUse', tool_name='Agent', tool_use_id='t7',
                                        tool_input={'subagent_type': 'Explore', 'prompt': 'look'}))
            sure = hook.claude_event(self.project, self.payload('PreToolUse', tool_name='Agent', tool_use_id='t8',
                                     tool_input={'subagent_type': 'developer', 'prompt': 'add sum()'}))
        self.assertEqual(low['hookSpecificOutput']['updatedInput']['model'], 'sonnet')
        self.assertIn('Profile default', low['hookSpecificOutput']['permissionDecisionReason'])
        self.assertEqual(unknown, {})
        self.assertEqual(sure['hookSpecificOutput']['updatedInput']['model'], 'haiku')
        records = [json.loads(p.read_text())['result'] for p in (self.project / '.agentic/jev').glob('event-*.json')]
        self.assertIn({'status': 'fallback', 'reason_code': 'low_confidence', 'model': 'sonnet', 'model_source': 'profile_default'},
                      [{k: r.get(k) for k in ('status', 'reason_code', 'model', 'model_source')} for r in records])


if __name__ == '__main__':
    unittest.main()
