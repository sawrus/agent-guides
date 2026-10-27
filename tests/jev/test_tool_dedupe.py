"""OpenCode code mode: one MCP call id yields one tool record under the concrete tool name."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import hook

PLUGIN = Path(__file__).resolve().parents[2] / 'extensions/opencode/hooks/agentic-jev.ts'


class ToolDedupe(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {'HOME': str(self.project / 'home')}, clear=True)
        self.environment.start()
        (self.project / '.agentic.json').write_text(json.dumps({'settings': {'jev': {'enabled': True}, 'profile': 'lean'}}))

    def tearDown(self):
        self.environment.stop()
        self.temp.cleanup()

    def tool(self, action, call='call-1', **data):
        return hook.opencode_event(self.project, {'kind': 'tool', 'session_id': 's', 'event_id': call, 'action': action,
                                                  'input': data, 'status': 'completed'})

    def records(self):
        found = [json.loads(p.read_text()) for p in (self.project / '.agentic/jev').glob('event-*.json')]
        return sorted(r['context']['action'] for r in found if r['context']['kind'] == 'tool')

    def test_wrapper_then_concrete_keeps_the_concrete_name(self):
        self.tool('execute', code='await db_list()')
        self.tool('srv_db_list', limit=1)
        self.assertEqual(self.records(), ['srv_db_list'])

    def test_concrete_then_wrapper_keeps_the_concrete_name(self):
        self.tool('srv_db_list', limit=1)
        self.tool('execute', code='await db_list()')
        self.assertEqual(self.records(), ['srv_db_list'])

    def test_distinct_call_ids_stay_distinct(self):
        self.tool('read', call='a')
        self.tool('read', call='b')
        self.tool('execute', call='c')
        self.assertEqual(self.records(), ['execute', 'read', 'read'])

    def test_plugin_keys_calls_by_id_and_prefers_the_concrete_name(self):
        source = PLUGIN.read_text()
        self.assertIn('const CODE_MODE = "execute";', source)
        self.assertIn('known.action === CODE_MODE', source)
        self.assertIn('recordedTools.has(key)', source)
        self.assertIn('event.tool === CODE_MODE && known && known.action !== CODE_MODE', source)


if __name__ == '__main__':
    unittest.main()
