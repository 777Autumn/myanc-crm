#!/usr/bin/env python3
"""Keep host-only CRM controls out of Claude Bash commands."""

import json
import re
import shlex
import sys


def block(message: str) -> None:
    print(f"Command guard blocked the operation: {message}", file=sys.stderr)
    raise SystemExit(2)


try:
    payload = json.load(sys.stdin)
except (json.JSONDecodeError, OSError) as error:
    block(f"invalid hook input ({error})")

tool_input = payload.get("tool_input")
if not isinstance(tool_input, dict):
    block("missing tool_input")
command = tool_input.get("command")
if not isinstance(command, str) or not command.strip():
    block("missing command")

blocked_literals = (
    "MYANC_REMINDER_DB",
    "MYANC_OPS_ALERT_DB",
    "MYANC_OPS_ALERT_OWNER_PROJECT",
    "ops-alerts-init",
    "/var/lib/myanc-ops-alerts",
    "/var/lib/myanc-reminders",
    "MYANC_CRM_HOST_SECRET",
    "MYANC_CRM_HOST_SECRET_FILE",
    "MYANC_CRM_ACTION_TOKEN",
    "MYANC_CRM_STAGE_INPUT",
    "/home/claude/.local/bin/lark-cli",
    "/usr/local/libexec/lark-cli-general-1.0.90",
    "/usr/local/libexec/lark-cli-1.0.90",
    "/usr/local/libexec/lark-crm-writer",
    "/home/claude/.cc-connect",
    "/etc/cc-connect",
    "/etc/myanc-crm",
    "/var/lib/cc-connect",
    "/var/lib/myanc-crm",
    "/var/lib/cc-action-inbox",
    "crm-followup apply",
    "crm-followup stage",
    "crm-followup request-approval",
    "crm-followup-stage",
    "myanc-crm-request-writer",
    "crm-followup host-",
)
for value in blocked_literals:
    if value in command:
        block("host-owned CRM control plane is not agent-callable")

# Legacy and relative spellings are blocked too. The canonical ledger now
# lives outside the workspace, but these checks keep an old deployment or a
# copied database from becoming a model-writable approval source.
if re.search(r"(?:^|[\s/\\])ledger\.sqlite3(?:\b|$)", command):
    block("host-owned CRM control plane is not agent-callable")

if re.search(r"(?:^|[;&|()]\s*)lark-cli(?:\s|$)", command):
    block("use the pinned lark-enterprise entry point")

if re.search(r"open-apis/(?:bitable|base)/", command, re.IGNORECASE):
    # A Base URL is not itself the protected CRM. Ordinary native API calls
    # may use the pinned general wrapper; its Feishu resource ACL must exclude
    # CRM. This exception is one literal invocation, never a shell program.
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        # Bash does not start a comment at a '#' inside an existing word.
        # Preserve fragments so a following ';' / '&&' cannot disappear.
        lexer.commenters = ""
        argv = list(lexer)
    except ValueError:
        argv = []
    single_general_call = (
        len(argv) >= 4
        and argv[0] in ("lark-enterprise", "/usr/local/bin/lark-enterprise")
        and argv[1] == "api"
        and not any(char in command for char in ("$", "`", "\n", "\r"))
        and not any(token and all(char in ";&|()<>" for char in token) for token in argv)
    )
    if not single_general_call:
        block("use a standalone pinned lark-enterprise call for Base APIs")
