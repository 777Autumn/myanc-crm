import io
import http.server
import json
import os
import socket
import threading
import unittest
from unittest import mock

from ops import crm_tool


class ProxyPeer:
    """External HTTP peer; the real stdlib request/response parser still runs."""

    def __init__(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.response = (
            f"HTTP/1.1 {status} Test\r\nContent-Type: application/json\r\n"
            f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body
        )
        self.sent = bytearray()
        self.address = None
        self.timeout = None
        self.closed = False

    def settimeout(self, value):
        self.timeout = value

    def setsockopt(self, *_args):
        pass

    def connect(self, address):
        self.address = address

    def sendall(self, data):
        self.sent.extend(data)

    def makefile(self, *_args):
        return io.BytesIO(self.response)

    def close(self):
        self.closed = True


class CrmToolClientTests(unittest.TestCase):
    def invoke(self, argv, body, peer, *, token="test-session-token", proxy="http://127.0.0.1:19091"):
        output = io.StringIO()
        environment = {} if token is None else {"MYANC_CRM_ACTION_TOKEN": token}
        if proxy is not None:
            environment["http_proxy"] = proxy
        environment.update({"NO_PROXY": "*", "no_proxy": "127.0.0.1,localhost"})
        with (
            mock.patch.dict(os.environ, environment, clear=True),
            mock.patch.object(socket, "create_connection", return_value=peer) as factory,
        ):
            code = crm_tool.main(argv, stdin=io.BytesIO(body), stdout=output)
        return code, json.loads(output.getvalue()), factory

    def test_customer_query_uses_fixed_local_transport_and_preserves_host_result(self):
        expected = {"status": "found", "customer": {"name": "<CRM_DATA>演示客户</CRM_DATA>"}}
        peer = ProxyPeer(expected)
        code, result, factory = self.invoke(["customer"], b'{"customer_query":"ANC-0001"}', peer)
        self.assertEqual((0, expected), (code, result))
        self.assertEqual(("127.0.0.1", 19091), factory.call_args.args[0])
        headers, body = bytes(peer.sent).split(b"\r\n\r\n", 1)
        self.assertTrue(headers.startswith(b"POST http://127.0.0.1:18743/tool HTTP/1.1\r\n"))
        self.assertIn(b"Authorization: Bearer test-session-token\r\n", headers + b"\r\n")
        self.assertEqual({"command": "customer", "input": {"customer_query": "ANC-0001"}}, json.loads(body))
        self.assertLessEqual(factory.call_args.args[1], 35)
        self.assertTrue(peer.closed)

    def test_handoff_read_allows_bounded_multi_file_authorization(self):
        expected = {"status": "found", "materials_imported": True}
        peer = ProxyPeer(expected)
        code, result, factory = self.invoke(["handoff"], b'{"banquet_id":"YAN-0001"}', peer)
        self.assertEqual((0, expected), (code, result))
        self.assertEqual(185, factory.call_args.args[1])
        self.assertTrue(peer.closed)

    def test_only_business_commands_and_fields_reach_the_host(self):
        cases = [
            (["open"], b'{"url":"https://other.invalid"}', "invalid_input"),
            (["open"], b'{"actor":"other"}', "invalid_input"),
            ([], b'{}', "invalid_command"),
            (["apply"], b'{"change_id":"chg_test"}', "invalid_command"),
            (["approve"], b'{}', "invalid_command"),
            (["stage", "--socket", "/other.sock"], b'{}', "invalid_command"),
            (["result", "--token", "other"], b'{}', "invalid_command"),
            (["customer", "http://remote/tool"], b'{}', "invalid_command"),
            (["customer"], b'{"customer_query":"A","actor":"other"}', "invalid_input"),
            (["banquet-context"], b'{"banquet_id":"recTest","profile":"other"}', "invalid_input"),
            (["handoff"], b'{"banquet_id":"recTest","reference_only":false}', "invalid_input"),
            (["stage"], b'{"content":"A","profile":"other"}', "invalid_input"),
            (["stage"], b'{"content":"A","approved":true}', "invalid_input"),
            (["result"], b'{"change_id":"chg_test","principal":{}}', "invalid_input"),
            (["case-publish"], b'{"case_name":"fixture","publication_files":[]}', "invalid_input"),
            (["case-publish"], b'{"case_name":"fixture","confirmation":{}}', "invalid_input"),
            (["case-access"], b'{"publication_id":"casepub_fixture"}', "invalid_command"),
            (["assignee"], b'{"query":"member@example.com","profile":"other"}', "invalid_input"),
            (["stage-customer-create"], b'{"name":"test","approved":true}', "invalid_input"),
            (["stage-customer-update"], b'{"customer_query":"C-001","record_id":"other"}', "invalid_input"),
            (["customer"], b'{"customer_query":"A","customer_query":"B"}', "invalid_input"),
            (["stage"], b'{"content":{"text":"A","text":"B"}}', "invalid_input"),
            (["stage"], b'{"content":NaN}', "invalid_input"),
            (["stage"], b'{"content":"A"} {}', "invalid_input"),
            (["stage"], b'[]', "invalid_input"),
            (["stage"], b'\xff', "invalid_input"),
            (["stage"], b'{"content":"' + b'A' * 65536 + b'"}', "invalid_input"),
            # Input alone fits, but the complete transport envelope does not.
            (["stage"], b'{"content":"' + b'A' * 65500 + b'"}', "invalid_input"),
        ]
        for argv, body, expected in cases:
            with self.subTest(argv=argv, code=expected, size=len(body)):
                code, result, factory = self.invoke(argv, body, ProxyPeer({}))
                self.assertEqual((2, {"status": "blocked", "code": expected}), (code, result))
                factory.assert_not_called()

    def test_publish_sends_only_selection_and_preserves_pending_confirmation(self):
        request = dict(case_name='fixture', expected_revision=2, delivery_ids=['accepted-file'])
        expected = dict(status='awaiting_confirmation', question='Confirm selected file?')
        peer = ProxyPeer(expected)
        code, result, factory = self.invoke(['case-publish'], json.dumps(request).encode(), peer)
        self.assertEqual((0, expected), (code, result))
        self.assertEqual(1, factory.call_count)
        self.assertEqual({'command': 'case-publish', 'input': request},
                         json.loads(bytes(peer.sent).split(b'\r\n\r\n', 1)[1]))

    def test_context_and_revision_forward_only_business_fields(self):
        for command, request in (('banquet-context', {'banquet_id': 'YAN-0001'}),
                                 ('handoff', {'banquet_id': 'YAN-0001', 'purpose': 'revision'})):
            peer = ProxyPeer({'status': 'partial', 'materials_read': False})
            code, result, _ = self.invoke([command], json.dumps(request).encode(), peer)
            self.assertEqual(0, code)
            self.assertEqual({'command': command, 'input': request},
                             json.loads(bytes(peer.sent).split(b'\r\n\r\n', 1)[1]))

    def test_missing_or_invalid_session_token_never_opens_a_socket(self):
        for token in (None, "", "bad\r\nInjected: yes", "token space", "非ASCII", "A" * 1025):
            with self.subTest(token_length=len(token or "")):
                code, result, factory = self.invoke(["customer"], b'{"customer_query":"A"}', ProxyPeer({}), token=token)
                self.assertEqual((2, {"status": "blocked", "code": "invalid_session"}), (code, result))
                factory.assert_not_called()

    def test_stage_clarification_and_result_partial_are_not_reinterpreted(self):
        for command, request, expected in (
            ("open", {}, {"status": "available", "url": "https://example.invalid/base/fixture"}),
            ("open", {"target": "mine"}, {"status": "available", "target": "base", "label": "CRM 总表", "url": "https://example.invalid/base/fixture"}),
            ("open", {"target": "team"}, {"status": "available", "target": "team", "url": "https://example.invalid/base/fixture?view=vewTeam"}),
            ("open", {"target": "stages"}, {"status": "available", "target": "stages", "url": "https://example.invalid/base/fixture?view=vewStages"}),
            ("open", {"target": "overview"}, {"status": "available", "target": "overview", "url": "https://example.invalid/base/fixture?table=blkOverview"}),
            ("stage", {"customer_query": "演示客户", "content": "确认了需求"}, {"status": "needs_time", "question": "When?"}),
            ("result", {"change_id": "chg_test"}, {"status": "partial", "followup": "verified", "customer_update": "failed"}),
            ("assignee", {"query": "member@example.com"}, {"status": "resolved", "owner_ref": "own_fixture", "name": "示例同事"}),
            ("stage-customer-create", {"name": "虚构公司"}, {"status": "needs_input", "missing": ["stage", "owner_ref", "contact_detail"]}),
            ("stage-customer-update", {"customer_query": "C-001", "changes": {"stage": "沟通中"}}, {"status": "pending", "change_id": "chg_fixture"}),
            ("customers", {"keyword": "虚构", "owner": "me", "due": "today"}, {"status": "found", "customers": [], "has_more": False}),
            ("customer", {"customer_query": "C-001", "history_offset": 10}, {"status": "found", "history": [], "has_more": False}),
            ("stage-customer-update", {"customer_query": "C-001", "changes": {"next_action": None, "next_followup_at": None}, "remind": False}, {"status": "pending", "change_id": "chg_fixture"}),
        ):
            with self.subTest(command=command):
                peer = ProxyPeer(expected)
                code, result, _ = self.invoke([command], json.dumps(request).encode(), peer)
                self.assertEqual((0, expected), (code, result))
                self.assertEqual({"command": command, "input": request}, json.loads(bytes(peer.sent).split(b"\r\n\r\n", 1)[1]))

    def test_transport_failure_is_unknown_without_leaking_details_or_retry(self):
        peer = ProxyPeer({})
        peer.sendall = mock.Mock(side_effect=OSError("private-token server/path secret"))
        code, result, factory = self.invoke(["stage"], b'{"content":"A"}', peer)
        self.assertEqual((1, {"status": "unavailable", "code": "transport_unavailable"}), (code, result))
        self.assertEqual(1, factory.call_count)
        self.assertTrue(peer.closed)

    def test_invalid_or_oversized_responses_never_become_business_receipts(self):
        for response in (
            b'HTTP/1.1 200 OK\r\nContent-Length: 6\r\n\r\nsecret',
            b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n[]',
            b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}',
            ProxyPeer({"status": "verified"}, 500).response,
            ProxyPeer({"status": "verified"}, 302).response,
            ProxyPeer({"status": "found", "content": "A" * (1024 * 1024)}).response,
        ):
            with self.subTest(response_length=len(response)):
                peer = ProxyPeer({})
                peer.response = response
                code, result, _ = self.invoke(["result"], b'{"change_id":"chg_test"}', peer)
                self.assertEqual((1, {"status": "unavailable", "code": "invalid_response"}), (code, result))

    def test_host_refusal_and_delivery_unknown_keep_their_status_and_reference(self):
        for status, expected in (
            (401, {"status": "blocked", "code": "invalid_session"}),
            (503, {"status": "unavailable", "code": "tool_or_delivery_failed", "change_id": "chg_test"}),
        ):
            with self.subTest(status=status):
                code, result, _ = self.invoke(["stage"], b'{"content":"A"}', ProxyPeer(expected, status))
                self.assertEqual((1, expected), (code, result))

    def test_no_direct_fallback_or_external_proxy_is_allowed(self):
        for proxy in (None, "", "http://external.invalid:8080", "socks5://127.0.0.1:1234", "http://127.0.0.1:0", "http://127.0.0.1:1/path"):
            with self.subTest(proxy=proxy):
                code, result, factory = self.invoke(["customer"], b'{}', ProxyPeer({}), proxy=proxy)
                self.assertEqual((1, {"status": "unavailable", "code": "sandbox_proxy_required"}), (code, result))
                factory.assert_not_called()

    def test_proxy_auth_is_preserved_and_redirect_never_forwards_bearer(self):
        peer = ProxyPeer({"status": "found"})
        code, _, _ = self.invoke(["customer"], b'{}', peer, proxy="http://test:pass@127.0.0.1:19091")
        self.assertEqual(0, code)
        self.assertIn(b"Proxy-Authorization: Basic dGVzdDpwYXNz\r\n", peer.sent)
        peer = ProxyPeer({})
        peer.response = b'HTTP/1.1 307 Redirect\r\nLocation: http://other.invalid/\r\nContent-Length: 0\r\n\r\n'
        code, result, factory = self.invoke(["customer"], b'{}', peer)
        self.assertEqual((1, {"status": "unavailable", "code": "invalid_response"}), (code, result))
        self.assertEqual(1, factory.call_count)

    def test_actual_proxy_http_round_trip(self):
        observed = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                observed.append((self.path, self.headers["Authorization"], json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                body = b'{"status":"pending","change_id":"chg_test"}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        with http.server.HTTPServer(("127.0.0.1", 0), Handler) as server:
            server.timeout = 2
            worker = threading.Thread(target=server.handle_request, daemon=True)
            worker.start()
            output = io.StringIO()
            with mock.patch.dict(os.environ, {
                "MYANC_CRM_ACTION_TOKEN": "test-session-token",
                "http_proxy": f"http://127.0.0.1:{server.server_port}",
                "NO_PROXY": "*", "no_proxy": "*",
            }, clear=True):
                code = crm_tool.main(["result"], stdin=io.BytesIO(b'{"change_id":"chg_test"}'), stdout=output)
            worker.join(timeout=3)
            self.assertFalse(worker.is_alive())
        self.assertEqual((0, {"status": "pending", "change_id": "chg_test"}), (code, json.loads(output.getvalue())))
        self.assertEqual([("http://127.0.0.1:18743/tool", "Bearer test-session-token", {"command": "result", "input": {"change_id": "chg_test"}})], observed)


if __name__ == "__main__":
    unittest.main()
