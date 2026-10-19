"""Shared Telegram notifier: enablement, credentials fallback, payload parsing, format and redaction."""
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

import telegram
from fake_telegram import FakeTelegram

FIXTURES = Path(__file__).resolve().parent / 'fixtures'


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
            self.run_hook(fake, {'session_id': 's1', 'last_assistant_message': 'Калькулятор готов', 'background_tasks': [],
                                 'agent_type': 'product-owner'})
        self.assertEqual(fake.messages(), ['✅ <b>Задача завершена</b> — calc-app · Claude Code\n🤖 product-owner\n\nКалькулятор готов'])
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
            self.run_hook(fake, {'last_assistant_message': '**done**\n\n\n\nok', 'background_tasks': []})
        self.assertEqual(len(fake.requests), 2)
        self.assertNotIn('parse_mode', fake.payloads()[1])
        self.assertEqual(fake.messages()[1], '✅ Задача завершена — calc-app · Claude Code\n\n**done**\n\nok')
        self.assertIn('sent plain text', (self.project / '.agentic/telegram-debug.log').read_text())

    def test_opencode_session_title_is_shown(self):
        with FakeTelegram() as fake:
            self.run_hook(fake, {'last_assistant_message': 'ok', 'title': 'Калькулятор `calc`', 'final': True, 'agent': 'build',
                                 'model': {'id': 'gpt-6-luna', 'providerID': 'openai'}}, host='opencode')
            self.run_hook(fake, {'last_assistant_message': 'ok', 'title': ' ', 'final': True,
                                 'model': 'openai/gpt-6-luna#high'}, host='opencode')
            self.run_hook(fake, {'last_assistant_message': 'ok', 'agent': 'build'}, host='opencode')
            self.run_hook(fake, {'last_assistant_message': 'ok', 'final': False}, host='opencode')
        first, second, third, fourth = fake.messages()
        self.assertEqual(first, '✅ <b>Задача завершена</b> — calc-app · OpenCode\n🤖 build · gpt-6-luna\n'
                                '<i>Калькулятор <code>calc</code></i>\n\nok')
        self.assertEqual(second, '✅ <b>Задача завершена</b> — calc-app · OpenCode\n🤖 gpt-6-luna\n\nok')
        self.assertEqual(third, '💬 <b>Промежуточный ответ</b> — calc-app · OpenCode\n🤖 build\n\nok')
        self.assertEqual(fourth, '💬 <b>Промежуточный ответ</b> — calc-app · OpenCode\n\nok')

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
            self.run_hook(fake, {'tool_name': 'Bash', 'tool_input': {'command': 'npm test'}, 'model': 'gpt-6-astra'},
                          host='codex', event='waiting')
        self.assertEqual(fake.messages(), ['⏳ <b>Ожидает ввода</b> — calc-app · Claude Code\n\nClaude needs your permission to use Bash',
                                           '⏳ <b>Ожидает ввода</b> — calc-app · Codex\n🤖 gpt-6-astra\n\nBash\n<pre><code>npm test</code></pre>'])

    def test_claude_task_sends_done_mark_once_on_the_final_turn(self):
        lines = (FIXTURES / 'claude_async_agents.jsonl').read_text().splitlines()
        cuts = [i + 1 for i, line in enumerate(lines) if '"stop_reason":"end_turn"' in line and '"isSidechain":false' in line]
        self.assertEqual(len(cuts), 4)
        transcript = self.root / 'session.jsonl'
        with FakeTelegram() as fake:
            for cut in cuts:
                transcript.write_text('\n'.join(lines[:cut]) + '\n')
                reply = json.loads(lines[cut - 1])['message']['content'][0]['text']
                self.run_hook(fake, {'session_id': 's-calc', 'transcript_path': str(transcript), 'last_assistant_message': reply})
        messages = fake.messages()
        self.assertEqual(len(messages), 4)
        self.assertEqual([m for m in messages if 'Задача завершена' in m], [messages[-1]])
        self.assertTrue(messages[-1].startswith('✅ <b>Задача завершена</b> — calc-app · Claude Code\n'))
        for interim in messages[:-1]:
            self.assertTrue(interim.startswith('💬 <b>Промежуточный ответ</b> — calc-app · Claude Code\n'))
            self.assertNotIn('✅', interim)
        for message in messages:
            self.assertEqual(message.split('\n')[1], '🤖 product-owner · claude-opus-5-5')
        self.assertIn('<b>Итог:</b> калькулятор принят.', messages[-1])

    def test_interim_note_completion_does_not_block_a_later_done_mark(self):
        note = '<note>The agent reported back, but it has background work of its own still running.</note>'
        turns = [
            ([{'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': 'launched'}]},
               'toolUseResult': {'isAsync': True, 'status': 'async_launched', 'agentId': 'a1'}}], [{'id': 'a1'}]),
            ([{'type': 'user', 'message': {'content': f'<task-notification><task-id>a1</task-id>'
                                                      f'<status>completed</status>{note}</task-notification>'}}], [{'id': 'a1'}]),
            ([{'type': 'user', 'message': {'content': 'Next task'}}], []),
        ]
        transcript, entries = self.root / 'session.jsonl', [{'type': 'agent-setting', 'agentSetting': 'product-owner'}]
        with FakeTelegram() as fake:
            for added, tasks in turns:
                entries += added + [{'type': 'assistant', 'message': {'model': 'claude-opus-5-5', 'content': 'ok'}}]
                transcript.write_text('\n'.join(json.dumps(entry) for entry in entries) + '\n')
                self.run_hook(fake, {'transcript_path': str(transcript), 'background_tasks': tasks, 'last_assistant_message': 'ok'})
        messages = fake.messages()
        self.assertEqual([m.split(' <b>')[0] for m in messages], ['💬', '💬', '✅'])
        self.assertTrue(all('\n🤖 product-owner · claude-opus-5-5\n' in m for m in messages))

    def test_script_run_leaves_no_bytecode_next_to_it(self):
        notify = self.root / 'installed' / '.agent' / 'notify'
        notify.mkdir(parents=True)
        source = Path(telegram.__file__).resolve().parent
        for name in ('telegram.py', 'telegram_turn.py'):
            shutil.copy(source / name, notify / name)
        env = {key: value for key, value in os.environ.items() if not key.startswith('PYTHON')}
        with FakeTelegram() as fake:
            env.update(AGENTIC_CONFIG_DIR=str(self.config), AGENTIC_TELEGRAM_API_BASE_URL=fake.url)
            subprocess.run([sys.executable, str(notify / 'telegram.py'), '--host', 'claude', '--event', 'stop',
                            '--project-dir', str(self.project), '--sync'], input=b'{"background_tasks": [], "agent_type": "pm"}',
                           env=env, check=True, timeout=30)
        self.assertEqual(fake.messages(), ['✅ <b>Задача завершена</b> — calc-app · Claude Code\n🤖 pm'])
        self.assertFalse((notify / '__pycache__').exists())

    def test_agent_and_model_labels_are_capped(self):
        rich, text = telegram.header('final', 'p · Claude Code', {'agent': 'a' * 100, 'model': '<' * 70})
        self.assertEqual(rich.split('\n')[1], f"🤖 {'a' * 64} · {'&lt;' * 64}")
        self.assertEqual(text.split('\n')[1], f"🤖 {'a' * 64} · {'<' * 64}")

    def test_read_json_refuses_non_regular_files(self):
        fifo = self.root / 'settings.json'
        os.mkfifo(fifo)
        result = []
        reader = threading.Thread(target=lambda: result.append(telegram.read_json(fifo, {'default': True})), daemon=True)
        reader.start()
        reader.join(5)
        self.assertEqual(result, [{'default': True}])

    def test_codex_rollout_decides_the_done_mark(self):
        payload = {'model': 'gpt-6-astra', 'transcript_path': str(FIXTURES / 'codex_rollout.jsonl'), 'last_assistant_message': 'ok'}
        with FakeTelegram() as fake:
            self.run_hook(fake, payload, host='codex')
            self.run_hook(fake, {**payload, 'transcript_path': None}, host='codex')
        self.assertEqual(fake.messages(), ['✅ <b>Задача завершена</b> — calc-app · Codex\n🤖 gpt-6-astra\n\nok',
                                           '💬 <b>Промежуточный ответ</b> — calc-app · Codex\n🤖 gpt-6-astra\n\nok'])

    def test_unknown_facts_or_missing_module_still_send_an_interim_message(self):
        with FakeTelegram() as fake:
            self.run_hook(fake, {'last_assistant_message': 'ok'})
            with patch.object(telegram, 'telegram_turn', None):
                self.run_hook(fake, {'last_assistant_message': 'ok', 'background_tasks': [], 'agent_type': 'pm'})
            with patch.object(telegram.telegram_turn, 'turn_facts', side_effect=RuntimeError('BOT:SECRET broke')):
                self.run_hook(fake, {'last_assistant_message': 'ok', 'background_tasks': []})
        self.assertEqual(fake.messages(), ['💬 <b>Промежуточный ответ</b> — calc-app · Claude Code\n\nok'] * 3)
        log = (self.project / '.agentic/telegram-debug.log').read_text()
        self.assertIn('turn facts failed', log)
        self.assertNotIn('SECRET', log)

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

    def test_hook_mode_detaches_without_reading_turn_facts(self):
        out, child, facts = io.StringIO(), MagicMock(), MagicMock()
        argv = ['telegram.py', '--host', 'claude', '--event', 'stop', '--project-dir', str(self.project)]
        raw = json.dumps({'last_assistant_message': 'ok', 'background_tasks': []})
        with patch.dict(os.environ, {'AGENTIC_CONFIG_DIR': str(self.config)}, clear=True), patch.object(sys, 'argv', argv), \
                patch.object(sys, 'stdin', io.StringIO(raw)), patch.object(sys, 'stdout', out), \
                patch.object(telegram.subprocess, 'Popen', return_value=child) as popen, \
                patch.object(telegram.telegram_turn, 'turn_facts', facts):
            telegram.main()
            sys.stdin = io.StringIO(json.dumps({'stop_hook_active': True}))
            telegram.main()
        self.assertEqual(popen.call_count, 1)
        self.assertIn('--sync', popen.call_args.args[0])
        child.stdin.write.assert_called_once_with(raw.encode('utf-8'))
        facts.assert_not_called()
        self.assertEqual(out.getvalue().split(), ['{}', '{}'])


if __name__ == '__main__':
    unittest.main()
