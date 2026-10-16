"""Local fake of the Telegram Bot API used by notifier tests and the blackbox run."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading


class FakeTelegram:
    def __init__(self, reject_html=False):
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
                owner.requests.append({'path': self.path, 'type': self.headers.get('Content-Type', ''), 'body': body})
                # Mimic Telegram's 400 "can't parse entities" so callers can test the plain-text fallback.
                rejected = reject_html and self.path.endswith('/sendMessage') and b'"parse_mode"' in body
                payload = json.dumps({'ok': not rejected, 'result': {}}).encode()
                self.send_response(400 if rejected else 200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_address[1]}'
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()

    def messages(self):
        return [json.loads(r['body'])['text'] for r in self.requests if r['path'].endswith('/sendMessage')]

    def payloads(self):
        return [json.loads(r['body']) for r in self.requests if r['path'].endswith('/sendMessage')]
