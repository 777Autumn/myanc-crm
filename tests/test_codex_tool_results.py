"""Pinned native tools and real delayed HTTP reads; no credentials or live model."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


TEMPLATE = Path(__file__).resolve().parents[1] / 'ops/runtime/codex.config.example.toml'


class CodexToolResultsTests(unittest.TestCase):
    def test_native_commands_bypass_lossy_code_wrappers(self):
        config = tomllib.loads(TEMPLATE.read_text(encoding='utf-8'))
        self.assertIn('functions', config['features'].get('code_mode', {}).get('direct_only_tool_namespaces', []))

    @unittest.skipUnless(sys.platform == 'darwin' and os.environ.get('ANC_CODEX_BIN'),
                         'requires pinned native Mac CLI; fictional local Responses server')
    def test_slow_query_preserves_handle_and_terminal_status(self):
        cli = os.environ['ANC_CODEX_BIN']
        self.assertNotEqual(os.geteuid(), 0)
        self.assertEqual(subprocess.check_output([cli, '--version'], text=True).strip(), 'codex-cli 0.157.1')
        outputs, reads, errors = {}, [], []
        session = None
        query_complete = threading.Event()

        def call(name, arguments, call_id):
            return dict(type='function_call', namespace='functions', name=name,
                        arguments=json.dumps(arguments), call_id=call_id)

        def wrapper(code, call_id):
            return dict(type='custom_tool_call', namespace='functions', name='exec', input=code, call_id=call_id)

        finished = dict(type='message', id='done', role='assistant', content=[dict(type='output_text', text='fixture complete')])

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_GET(self):
                reads.append(self.path)
                # Exceeds exec_command's longest normal initial wait, with no stdout.
                time.sleep(32 if self.path == '/slow' else 2)
                body = b'{"status":"ok","value":"fictional-query-complete"}'
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass  # The red case loses its handle and ends the native turn.
                finally:
                    query_complete.set()

            def do_POST(self):
                nonlocal session
                try:
                    request = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                    for item in request['input']:
                        if item['type'].endswith('call_output'):
                            value = item['output']
                            outputs[item['call_id']] = value if isinstance(value, str) else '\n'.join(x.get('text', '') for x in value)
                    last = next(reversed(outputs), None)
                    if last is None:
                        item = wrapper('const r = await tools.exec_command(' + json.dumps(slow_args) + '); text(r.output);', 'bad-exec')
                    elif last == 'bad-exec':
                        item = call('exec_command', slow_args, 'slow') if 'not a function' in outputs[last] else finished
                    elif last == 'slow':
                        match = re.search(r'Process running with session ID (\d+)', outputs[last])
                        if not match:
                            raise AssertionError('slow query did not expose a running session: ' + outputs[last])
                        session = int(match[1])
                        item = wrapper('const r = await tools.write_stdin(' + json.dumps(dict(session_id=session, chars='', yield_time_ms=1000)) + '); text(r.output);', 'bad-poll')
                    elif last == 'bad-poll' or 'Process running with session ID' in outputs[last]:
                        match = re.search(r'Process running with session ID (\d+)', outputs[last])
                        if match:
                            session = int(match[1])
                        if len(outputs) > 12:
                            raise AssertionError('query exceeded bounded poll count')
                        prefix = 'partial-poll-' if last.startswith('partial') else 'poll-'
                        item = call('write_stdin', dict(session_id=session, chars='', yield_time_ms=1000), prefix + str(len(outputs)))
                    elif last.startswith('poll-'):
                        item = call('exec_command', dict(cmd="printf 'partial-body\\n'; " + query('/partial') + '; exit 7',
                                                        yield_time_ms=1000, max_output_tokens=200), 'partial')
                    else:
                        item = finished
                except Exception as exc:
                    errors.append(repr(exc))
                    item = finished
                events = [dict(type='response.created', response=dict(id='fixture-response')),
                          dict(type='response.output_item.done', item=item),
                          dict(type='response.completed', response=dict(id='fixture-response', usage=dict(input_tokens=0, output_tokens=0, total_tokens=0)))]
                body = ''.join('event: ' + e['type'] + '\ndata: ' + json.dumps(e) + '\n\n' for e in events).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server, tempfile.TemporaryDirectory(prefix='anc-native-query-') as tmp:
            root = Path(tmp).resolve()
            home, work = root / 'home', root / 'work'
            home.mkdir(mode=0o700)
            work.mkdir(mode=0o700)
            base_url = 'http://127.0.0.1:' + str(server.server_port)

            def query(path):
                return "/usr/bin/curl --fail --silent --show-error --noproxy '' " + base_url + path

            slow_args = dict(cmd=query('/slow'), yield_time_ms=30000, max_output_tokens=200)
            config = 'model_provider = "fixture"\n' + TEMPLATE.read_text(encoding='utf-8')
            config += '\n[model_providers.fixture]\nname = "Local fictional fixture"\nbase_url = "' + base_url + '/v1"\nwire_api = "responses"\nrequires_openai_auth = false\n'
            (home / 'config.toml').write_text(config, encoding='utf-8')
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                result = subprocess.run([cli, 'exec', '--skip-git-repo-check', '--json', 'Run the fictional query fixture.'],
                                        cwd=work, env=dict(HOME=str(root), CODEX_HOME=str(home), PATH='/usr/bin:/bin'),
                                        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
                if reads:
                    self.assertTrue(query_complete.wait(40), 'HTTP query did not finish')
                print(json.dumps(dict(native_tool_results=outputs, reads=reads, errors=errors)), flush=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(errors, [])
                self.assertIn('tools.exec_command is not a function', outputs['bad-exec'])
                self.assertIn('tools.write_stdin is not a function', outputs['bad-poll'])
                self.assertEqual(reads, ['/slow', '/partial'], 'each read must execute exactly once')
                self.assertRegex(outputs['slow'], r'Process running with session ID \d+')
                self.assertNotIn('fictional-query-complete', outputs['slow'])
                slow_terminal = [v for k, v in outputs.items() if k.startswith('poll-')][-1]
                self.assertIn('Process exited with code 0', slow_terminal)
                self.assertIn('fictional-query-complete', slow_terminal)
                self.assertIn('partial-body', outputs['partial'])
                partial_terminal = [v for k, v in outputs.items() if k.startswith('partial-poll-')][-1]
                self.assertIn('Process exited with code 7', partial_terminal)
                self.assertIn('fictional-query-complete', partial_terminal)
            finally:
                server.shutdown()
                worker.join(timeout=5)
