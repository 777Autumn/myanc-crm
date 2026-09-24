#!/usr/bin/env python3
"""Agent-side CRM reads/staging through Claude's native loopback proxy."""

import http.client
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ENDPOINT = "http://127.0.0.1:18743/tool"
TIMEOUT_SECONDS = 35
MAX_INPUT_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
FIELDS = {
    "case-list": {"query"},
    "case-read": {"case_name"},
    "case-update": {"case_name", "expected_revision", "changes", "source_message_id"},
    "reminder-create": {"content", "at"},
    "reminder-list": {"all", "id"},
    "reminder-update": {"id", "version", "content", "at"},
    "reminder-cancel": {"id", "version"},
    "open": {"target"},
    "customer": {"customer_query", "history_offset"},
    "customers": {"keyword", "owner", "owner_ref", "stages", "due", "date_from", "date_to", "offset"},
    "stage": {"customer_query", "occurred_at", "channel", "content", "next_action", "next_followup_at", "remind", "backfill"},
    "result": {"change_id"},
    "assignee": {"query"},
    "stage-customer-create": {"name", "contact", "phone", "email", "stage", "owner_ref",
                              "allow_same_name", "followup"},
    "stage-customer-update": {"customer_query", "changes", "allow_same_name", "followup", "remind"},
}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("non-JSON number")


def _emit(stdout, result, code):
    print(json.dumps(result, ensure_ascii=False), file=stdout)
    return code


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args, **_kwargs):
        return None


def _sandbox_opener():
    proxy = os.environ.get("http_proxy") or os.environ.get("HTTP_PROXY", "")
    parsed = urllib.parse.urlsplit(proxy)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or not parsed.port or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
            or any(ord(c) <= 32 or ord(c) >= 127 for c in proxy)):
        raise ValueError("native loopback proxy required")
    # Native sandbox sets both to include localhost. Clear only in this short-
    # lived client, not in the gateway/native proxy's own parent environment.
    os.environ.pop("NO_PROXY", None)
    os.environ.pop("no_proxy", None)
    return urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy}), _NoRedirect())


def main(argv=None, *, stdin=None, stdout=None):
    argv = sys.argv[1:] if argv is None else argv
    stdin = sys.stdin.buffer if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    if len(argv) != 1 or argv[0] not in FIELDS:
        return _emit(stdout, {"status": "blocked", "code": "invalid_command"}, 2)
    token = os.environ.get("MYANC_CRM_ACTION_TOKEN", "")
    if not token or len(token) > 1024 or any(ord(c) <= 32 or ord(c) >= 127 for c in token):
        return _emit(stdout, {"status": "blocked", "code": "invalid_session"}, 2)
    try:
        raw = stdin.read(MAX_INPUT_BYTES + 1)
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError("input too large")
        request = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        if not isinstance(request, dict) or set(request) - FIELDS[argv[0]]:
            raise ValueError("unexpected business field")
        body = b'{"command":' + json.dumps(argv[0]).encode("ascii") + b',"input":' + raw + b'}'
        if len(body) > MAX_INPUT_BYTES:
            raise ValueError("envelope too large")
    except (ValueError, OSError, RecursionError):
        return _emit(stdout, {"status": "blocked", "code": "invalid_input"}, 2)
    try:
        opener = _sandbox_opener()
    except ValueError:
        return _emit(stdout, {"status": "unavailable", "code": "sandbox_proxy_required"}, 1)
    response = None
    try:
        request = urllib.request.Request(ENDPOINT, body, {
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        })
        try:
            response = opener.open(request, timeout=TIMEOUT_SECONDS)
        except urllib.error.HTTPError as error:
            response = error  # Preserve structured host refusal, never follow a redirect.
        raw_result = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw_result) > MAX_RESPONSE_BYTES or response.headers.get_content_type() != "application/json":
            raise ValueError("invalid host response")
        result = json.loads(raw_result.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        if not isinstance(result, dict) or not isinstance(result.get("status"), str) or not result["status"]:
            raise ValueError("invalid host response")
        if response.status != 200 and (response.status < 400 or result["status"] not in {"blocked", "unavailable"}):
            raise ValueError("unexpected HTTP result")
        code = 0 if response.status == 200 else 1
    except (OSError, http.client.HTTPException):
        return _emit(stdout, {"status": "unavailable", "code": "transport_unavailable"}, 1)
    except (ValueError, RecursionError):
        return _emit(stdout, {"status": "unavailable", "code": "invalid_response"}, 1)
    finally:
        if response is not None:
            response.close()
    return _emit(stdout, result, code)


if __name__ == "__main__":
    raise SystemExit(main())
