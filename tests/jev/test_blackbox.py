"""Independent arithmetic acceptance must reject broken calculators and assertions."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import json
from unittest.mock import patch
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('probe', ROOT / 'scripts/blackbox_calculator_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
blackbox_spec = importlib.util.spec_from_file_location('blackbox', ROOT / 'scripts/blackbox_jev.py')
blackbox = importlib.util.module_from_spec(blackbox_spec)
blackbox_spec.loader.exec_module(blackbox)


class CalculatorAcceptance(unittest.TestCase):
    def test_previous_successful_session_cannot_pass_a_new_native_run(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            journal = project / '.agentic/jev'
            journal.mkdir(parents=True)
            records = [
                {'context':{'kind':'prompt','session_id':'old','task_id':'old-task','prompt':blackbox.PROMPT}, 'result':{'status':'evaluated','workflow':{'id':'wf','path':'.agent/workflows/wf.md'}}},
                {'context':{'kind':'spawn','session_id':'old','task_id':'old-task','agent':'developer'}, 'result':{'status':'evaluated','model':'light'}},
                {'context':{'kind':'observation','session_id':'old','task_id':'old-task','agent':'developer'}, 'result':{'status':'observed','observed_model':'light'}},
            ]
            for index, record in enumerate(records):
                (journal / f'event-{index}.json').write_text(json.dumps(record))
            trace = project / 'trace.jsonl'
            trace.write_text('{"type":"thread.started","thread_id":"new"}\n')
            with patch.object(blackbox.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='{"verified":true}')), patch.object(blackbox, 'key_for', return_value=''):
                result = blackbox.verify(project, trace, 0)
            self.assertFalse(result['checks']['real_jev_workflow'])
            self.assertFalse(result['checks']['model_applied_to_subagent'])

    def test_overlapping_native_runs_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with blackbox.run_lock(root):
                with self.assertRaises(SystemExit):
                    with blackbox.run_lock(root):
                        self.fail('overlapping run admitted')
            self.assertFalse((root / '.active-run').exists())

    def test_trace_redaction_preserves_json_and_removes_secrets(self):
        text = json.dumps({'text': 'JEV_API_KEY="synthetic-secret"; Windows C:\\project\\file'}) + '\n'
        with patch.object(blackbox, 'key_for', return_value='synthetic-secret'):
            cleaned = blackbox.clean(text)
        self.assertNotIn('synthetic-secret', cleaned)
        self.assertIn('C:\\project\\file', json.loads(cleaned)['text'])

    def test_uses_real_calculator_outputs_and_rejects_broken_division(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'calculator.py'
            code = "def calculate(a, operator, b):\n    return {'+': lambda: a+b, '-': lambda: a-b, '*': lambda: a*b, '/': lambda: a/b}[operator]()\n"
            path.write_text(code)
            self.assertTrue(probe.main(directory)['verified'])
            path.write_text(code.replace('a/b', 'a*b'))
            self.assertFalse(probe.main(directory)['verified'])

    def test_self_reported_acceptance_does_not_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'acceptance.json').write_text('{"verified":true}')
            self.assertFalse(probe.main(directory)['verified'])

    def test_javascript_result_objects_are_verified_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'calculator.mjs'
            code = "export function calculate(a, operator, b) { if(operator === '/' && b === 0) return {ok:false,error:'division by zero'}; return {ok:true,value:{'+':a+b,'-':a-b,'*':a*b,'/':a/b}[operator]}; }"
            path.write_text(code)
            self.assertTrue(probe.main(directory)['verified'])
            path.write_text(code.replace("'/':a/b", "'/':a*b"))
            self.assertFalse(probe.main(directory)['verified'])

    def test_classic_browser_calculator_public_api_is_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'calculator.js'
            code = """globalThis.CalculatorEngine = {
createInitialState: () => ({entry:'', error:false}), displayValue: state => state.entry,
transition: (state, action) => {
if(action.type === 'digit') return {...state, entry:state.entry+action.value};
if(action.type === 'operator') return {...state, left:Number(state.entry), op:action.value, entry:''};
if(state.op === '/' && Number(state.entry) === 0) return {...state,error:true,entry:'division by zero'};
const a=state.left,b=Number(state.entry); return {...state,entry:String({'+':a+b,'-':a-b,'*':a*b,'/':a/b}[state.op])};
}};"""
            path.write_text(code)
            self.assertTrue(probe.main(directory)['verified'])
            path.write_text(code.replace("'/':a/b", "'/':a*b"))
            self.assertFalse(probe.main(directory)['verified'])

    def test_mutating_keypad_api_with_typographic_operators_is_verified(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'calculator.js'
            code = """const ops = {'+':(a,b)=>a+b,'−':(a,b)=>a-b,'×':(a,b)=>a*b,'÷':(a,b)=>a/b};
module.exports = {
createCalculator: () => ({display:'0', input:'', left:null, operator:null, error:false}),
enterDigit: (s, d) => { s.input += d; s.display = s.input; return s; },
chooseOperator: (s, op) => { s.left = Number(s.input); s.operator = op; s.input = ''; return s; },
equals: (s) => { const b = Number(s.input);
  if (s.operator === '÷' && b === 0) { s.error = true; s.display = 'Error'; return s; }
  s.display = String(ops[s.operator](s.left, b)); return s; },
};"""
            path.write_text(code)
            self.assertTrue(probe.main(directory)['verified'])
            path.write_text(code.replace("'÷':(a,b)=>a/b", "'÷':(a,b)=>a*b"))
            self.assertFalse(probe.main(directory)['verified'])


class ClaudeBlackboxVerification(unittest.TestCase):
    def test_claude_trace_alias_routing_and_native_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            journal = project / '.agentic/jev'
            journal.mkdir(parents=True)
            skills = project / '.claude/skills/api-design'
            skills.mkdir(parents=True)
            (skills / 'SKILL.md').write_text('---\nname: api-design\ndescription: x\n---\n')
            task = {'session_id': 's1', 'task_id': 't1'}
            records = [
                {'context': {'kind': 'prompt', 'prompt': blackbox.PROMPT, **task}, 'result': {'status': 'evaluated', 'workflow': {'id': 'wf', 'path': '.agent/workflows/wf.md'}}},
                {'context': {'kind': 'tool', 'resources': ['.agent/workflows/wf.md'], **task}, 'result': {'status': 'observed'}},
                {'context': {'kind': 'spawn', 'agent': 'developer', **task}, 'result': {'status': 'evaluated', 'model': 'haiku'}},
                {'context': {'kind': 'observation', 'agent': 'developer', **task}, 'result': {'status': 'observed', 'observed_model': 'claude-haiku-5-5'}},
            ]
            for index, record in enumerate(records):
                (journal / f'event-{index}.json').write_text(json.dumps(record))
            run = project / 'run'
            run.mkdir()
            trace = run / 'trace.jsonl'
            init = {'type': 'system', 'subtype': 'init', 'session_id': 's1', 'agents': list(blackbox.CLAUDE_ROLES) + ['general-purpose'],
                    'slash_commands': ['develop-feature', 'compact'], 'skills': ['api-design']}
            trace.write_text(json.dumps(init) + '\n{"type":"result","subtype":"success"}\n')
            (run / 'instructions.jsonl').write_text(json.dumps({'file_path': str(project / '.claude/rules/testing.md')}) + '\n')
            (run / 'telegram.json').write_text(json.dumps({'messages': ['✅ Задача завершена — p\n\nГотово']}))
            with patch.object(blackbox.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='{"verified":true}')), patch.object(blackbox, 'key_for', return_value=''):
                result = blackbox.verify(project, trace, 0, 'claude')
            self.assertEqual(result['status'], 'passed', result['checks'])
            (run / 'telegram.json').unlink()
            (run / 'instructions.jsonl').unlink()
            with patch.object(blackbox.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='{"verified":true}')), patch.object(blackbox, 'key_for', return_value=''):
                result = blackbox.verify(project, trace, 0, 'claude')
            self.assertFalse(result['checks']['telegram_fired'])
            self.assertFalse(result['checks']['rules_loaded'])
            self.assertEqual(result['status'], 'failed')

    def test_codex_requires_shared_telegram_hook_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / '.agentic/jev').mkdir(parents=True)
            run = project / 'run'
            run.mkdir()
            trace = run / 'trace.jsonl'
            trace.write_text('{"type":"thread.started","thread_id":"t"}\n')
            with patch.object(blackbox.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='{"verified":true}')):
                self.assertFalse(blackbox.verify(project, trace, 0, 'codex')['checks']['telegram_fired'])
                (run / 'telegram.json').write_text(json.dumps({'messages': ['✅ Задача завершена — p\n\nГотово']}))
                self.assertTrue(blackbox.verify(project, trace, 0, 'codex')['checks']['telegram_fired'])
                self.assertTrue(blackbox.verify(project, trace, 0, 'opencode')['checks']['telegram_fired'])


class FollowupTurn(unittest.TestCase):
    def test_each_host_resumes_its_own_session_once(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / 'trace.jsonl'
            trace.write_text('{"type":"step_start","sessionID":"ses_1"}\n')
            command, text = blackbox.followup_turn('opencode', 'opencode', ['opencode', 'run'], trace)
            self.assertEqual((command[-2:], text), (['--session', 'ses_1'], blackbox.FOLLOWUP))
            trace.write_text('{"type":"thread.started","thread_id":"th_1"}\n')
            command, text = blackbox.followup_turn('codex', 'codex', [], trace)
            self.assertEqual((command[2:4], command[-2:], text), (['exec', 'resume'], ['th_1', blackbox.FOLLOWUP], None))
            trace.write_text('')
            self.assertIsNone(blackbox.followup_turn('codex', 'codex', [], trace))


class PackageCalculatorProbe(unittest.TestCase):
    def write_package(self, project, divide):
        package = project / 'src/calc'
        package.mkdir(parents=True)
        (package / '__init__.py').write_text('')
        (package / 'errors.py').write_text('class CalcError(Exception):\n    pass\n')
        (package / 'core.py').write_text(
            'from decimal import Decimal\nfrom .errors import CalcError\n\n'
            'def evaluate(expression):\n'
            '    a, op, b = expression.split()\n'
            '    a, b = Decimal(a), Decimal(b)\n'
            '    if op == "/" and b == 0:\n'
            '        raise CalcError("division by zero")\n'
            f'    return {{"+": a + b, "-": a - b, "*": a * b, "/": {divide}}}[op]\n')

    def test_src_package_with_relative_imports_and_decimal_results(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_package(Path(directory), 'a / b')
            result = probe.main(directory)
            self.assertTrue(result['verified'], result)
            self.assertEqual(result['entrypoint'], 'src/calc/core.py:evaluate')

    def test_src_package_with_wrong_division_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write_package(Path(directory), 'a // b')
            self.assertFalse(probe.main(directory)['verified'])

    def test_typographic_operator_dialect_is_accepted_but_not_mixed(self):
        source = ('def calculate(left, operator, right):\n'
                  '    if operator == "÷" and right == 0:\n'
                  '        raise ValueError("Cannot divide by zero")\n'
                  '    return {"+": left + right, "−": left - right, "×": left * right, "÷": %s}[operator]\n')
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'calc.py').write_text(source % 'left / right')
            self.assertTrue(probe.main(directory)['verified'])
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / 'calc.py').write_text(source % 'left // right')
            self.assertFalse(probe.main(directory)['verified'])
