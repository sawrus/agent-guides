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
        self.assertEqual(fake.messages(), ['✅ <b>Задача завершена</b> — calc-app · Claude Code\n\nКалькулятор готов'])
        self.assertEqual(fake.payloads()[0]['parse_mode'], 'HTML')
        self.assertIn('/botBOT:SECRET/sendMessage', fake.requests[0]['path'])

    def test_markdown_is_rendered_as_telegram_html(self):
        reply = ('Готово (`aed7058`):\n\n- **Снял** <x> & y\n\n## Итог\n| A | B |\n|---|---|\n| make | ✅ |\n\n'
                 '```sh\nmake test\n```\n[MR](https://example.com/6) и [сводка](.reviews/s.md), snake_case_name')
        with FakeTelegram() as fake:
            self.run_hook(fake, {'last_assistant_message': reply}, host='codex')
        text = fake.messages()[0]
        for fragment in ('<code>aed7058</code>', '• <b>Снял</b> &lt;x&gt; &amp; y', '<b>Итог</b>', '<pre>A    │ B',
                         '<pre><code class="language-sh">make test</code></pre>', '<a href="https://example.com/6">MR</a>',
                         'сводка (<code>.reviews/s.md</code>)', 'snake_case_name', '— calc-app · Codex'):
            self.assertIn(fragment, text)

    def test_rejected_markup_falls_back_to_plain_text(self):
        with FakeTelegram(reject_html=True) as fake:
            self.run_hook(fake, {'last_assistant_message': '**done**\n\n\n\nok'})
        self.assertEqual(len(fake.requests), 2)
        self.assertNotIn('parse_mode', fake.payloads()[1])
        self.assertEqual(fake.messages()[1], '✅ Задача завершена — calc-app · Claude Code\n\n**done**\n\nok')
        self.assertIn('sent plain text', (self.project / '.agentic/telegram-debug.log').read_text())

    def test_opencode_session_title_is_shown(self):
        with FakeTelegram() as fake:
            self.run_hook(fake, {'last_assistant_message': 'ok', 'title': 'Калькулятор `calc`'}, host='opencode')
            self.run_hook(fake, {'last_assistant_message': 'ok', 'title': ' '}, host='opencode')
        first, second = fake.messages()
        self.assertEqual(first, '✅ <b>Задача завершена</b> — calc-app · OpenCode\n<i>Калькулятор <code>calc</code></i>\n\nok')
        self.assertEqual(second, '✅ <b>Задача завершена</b> — calc-app · OpenCode\n\nok')

    def test_long_reply_sends_document_and_preview(self):
        with FakeTelegram() as fake:
            self.run_hook(fake, {'session_id': 'abcdefgh123', 'last_assistant_message': 'x' * 5000})
        self.assertTrue(fake.requests[0]['path'].endswith('/sendDocument'))
        self.assertIn(b'filename="response-abcdefgh.md"', fake.requests[0]['body'])
        text = fake.messages()[0]
        self.assertIn('Полный ответ во вложении (5000 символов)', text)
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
        self.assertEqual(fake.messages(), ['✅ <b>Задача завершена</b> — calc-app · Claude Code\n\nPart 1\nPart 2'])

    def test_waiting_events_for_both_hosts(self):
        with FakeTelegram() as fake:
            self.run_hook(fake, {'message': 'Claude needs your permission to use Bash'}, event='waiting')
            self.run_hook(fake, {'tool_name': 'Bash', 'tool_input': {'command': 'npm test'}}, host='codex', event='waiting')
        self.assertEqual(fake.messages(), ['⏳ <b>Ожидает ввода</b> — calc-app · Claude Code\n\nClaude needs your permission to use Bash',
                                           '⏳ <b>Ожидает ввода</b> — calc-app · Codex\n\nBash\n<pre><code>npm test</code></pre>'])

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
