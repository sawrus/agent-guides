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
