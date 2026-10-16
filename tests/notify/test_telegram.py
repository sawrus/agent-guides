"""Shared Telegram notifier: enablement, credentials fallback, payload parsing, format and redaction."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import telegram
from fake_telegram import FakeTelegram


class Notifier(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / 'calc-app'
        self.project.mkdir()
        self.config = self.root / 'config'
        self.config.mkdir()
        self.settings({'notifications': {'telegram': {'enabled': True}}})
        self.credentials({'notifications': {'telegram': {'botToken': 'BOT:SECRET', 'chatId': '4242'}}})

    def tearDown(self):
        self.temp.cleanup()

    def settings(self, settings):
        (self.project / '.agentic.json').write_text(json.dumps({'settings': settings}))

    def credentials(self, data):
        (self.config / 'config.json').write_text(json.dumps(data))

    def run_hook(self, fake, payload, host='claude', event='stop'):
        argv = ['telegram.py', '--host', host, '--event', event, '--project-dir', str(self.project), '--sync']
        env = {'AGENTIC_CONFIG_DIR': str(self.config), 'AGENTIC_TELEGRAM_API_BASE_URL': fake.url}
        with patch.dict(os.environ, env, clear=True), patch.object(sys, 'argv', argv), \
                patch.object(sys, 'stdin', io.StringIO(json.dumps(payload))):
            telegram.main()

    def test_short_reply_matches_plugin_format(self):
        with FakeTelegram() as fake:
            self.run_hook(fake, {'session_id': 's1', 'last_assistant_message': 'Калькулятор готов'})
        self.assertEqual(fake.messages(), ['✅ Задача завершена — calc-app\n\nКалькулятор готов'])
        self.assertIn('/botBOT:SECRET/sendMessage', fake.requests[0]['path'])

    def test_long_reply_sends_document_and_preview(self):
        with FakeTelegram() as fake:
            self.run_hook(fake, {'session_id': 'abcdefgh123', 'last_assistant_message': 'x' * 5000})
        self.assertTrue(fake.requests[0]['path'].endswith('/sendDocument'))
        self.assertIn(b'filename="response-abcdefgh.md"', fake.requests[0]['body'])
        text = fake.messages()[0]
        self.assertIn('Полный ответ в attachment (5000 символов)', text)
        self.assertLessEqual(len(text), 4096)

    def test_disabled_or_missing_credentials_send_nothing(self):
        self.settings({'notifications': {'telegram': {'enabled': False}}})
        with FakeTelegram() as fake:
            self.run_hook(fake, {'last_assistant_message': 'done'})
        self.assertEqual(fake.requests, [])
        self.settings({'notifications': {'telegram': {'enabled': True}}})
        self.credentials({})
        with FakeTelegram() as fake:
            self.run_hook(fake, {'last_assistant_message': 'done'})
        self.assertEqual(fake.requests, [])
        log = (self.project / '.agentic/telegram-debug.log').read_text()
        self.assertIn('credentials missing', log)

    def test_legacy_opencode_keys_are_accepted(self):
        self.settings({'opencode_plugins': {'telegram': {'enabled': True}}})
        self.credentials({'opencode': {'plugins': {'telegram': {'botToken': 'LEGACY', 'chatId': '1'}}}})
        with FakeTelegram() as fake:
            self.run_hook(fake, {'last_assistant_message': 'ok'}, host='codex')
        self.assertIn('/botLEGACY/', fake.requests[0]['path'])

    def test_claude_transcript_fallback_and_stop_loop_guard(self):
        transcript = self.root / 't.jsonl'
        lines = [{'type': 'user', 'message': {'content': 'build calc'}},
                 {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'Part 1'}]}},
                 {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': 'ok'}]}},
                 {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Bash'}, {'type': 'text', 'text': 'Part 2'}]}}]
        transcript.write_text('\n'.join(json.dumps(line) for line in lines))
        with FakeTelegram() as fake:
            self.run_hook(fake, {'transcript_path': str(transcript)})
            self.run_hook(fake, {'transcript_path': str(transcript), 'stop_hook_active': True})
        self.assertEqual(fake.messages(), ['✅ Задача завершена — calc-app\n\nPart 1\nPart 2'])

    def test_waiting_events_for_both_hosts(self):
        with FakeTelegram() as fake:
            self.run_hook(fake, {'message': 'Claude needs your permission to use Bash'}, event='waiting')
            self.run_hook(fake, {'tool_name': 'Bash', 'tool_input': {'command': 'npm test'}}, host='codex', event='waiting')
        self.assertEqual(fake.messages(), ['⏳ Ожидает ввода — calc-app\n\nClaude needs your permission to use Bash',
                                           '⏳ Ожидает ввода — calc-app\n\nBash: npm test'])

    def test_failures_are_logged_with_secrets_redacted(self):
        env = {'AGENTIC_CONFIG_DIR': str(self.config), 'AGENTIC_TELEGRAM_API_BASE_URL': 'http://127.0.0.1:9'}
        argv = ['telegram.py', '--host', 'claude', '--event', 'stop', '--project-dir', str(self.project), '--sync']
        with patch.dict(os.environ, env, clear=True), patch.object(sys, 'argv', argv), \
                patch.object(sys, 'stdin', io.StringIO('{"last_assistant_message":"x"}')):
            telegram.main()
        log = (self.project / '.agentic/telegram-debug.log').read_text()
        self.assertIn('send failed', log)
        self.assertNotIn('SECRET', log)

    def test_hook_mode_prints_empty_json_and_detaches(self):
        out = io.StringIO()
        argv = ['telegram.py', '--host', 'claude', '--event', 'stop', '--project-dir', str(self.project)]
        with patch.dict(os.environ, {'AGENTIC_TELEGRAM': '0'}, clear=True), patch.object(sys, 'argv', argv), \
                patch.object(sys, 'stdin', io.StringIO('{}')), patch.object(sys, 'stdout', out), \
                patch.object(telegram.subprocess, 'Popen', side_effect=AssertionError('disabled must not spawn')):
            telegram.main()
        self.assertEqual(out.getvalue().strip(), '{}')


if __name__ == '__main__':
    unittest.main()
