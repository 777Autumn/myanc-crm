#!/usr/bin/env python3
"""Confine file tools; permit installed skill reads without policy writes."""

import json
import os
import sys


# This installed, root-owned map is the authority. Neither HOME, a message,
# a hook payload nor the model's cwd selects a different runtime identity.
WORKSPACES = {
    "claude": "/home/claude/ClaudeRemote",
    "claude-owner-group": "/home/claude-owner-group/ClaudeRemote",
    "claude-partner-private": "/home/claude-partner-private/ClaudeRemote",
    "claude-partner-group": "/home/claude-partner-group/ClaudeRemote",
    "claude-test-private": "/home/claude-test-private/ClaudeRemote",
    "claude-test-group": "/home/claude-test-group/ClaudeRemote",
}


def block(message: str) -> None:
    print(f"Workspace guard blocked the file operation: {message}", file=sys.stderr)
    raise SystemExit(2)


try:
    import pwd
    USER = pwd.getpwuid(os.geteuid()).pw_name
    WORKSPACE = WORKSPACES[USER]
except (ImportError, KeyError, OSError):
    block("unregistered runtime identity")
if os.path.realpath(WORKSPACE) != WORKSPACE:
    block("fixed workspace cannot contain symbolic links")
PROTECTED = tuple(os.path.join(WORKSPACE, name) for name in ("CLAUDE.md", ".mcp.json", ".claude"))


try:
    payload = json.load(sys.stdin)
except (json.JSONDecodeError, OSError) as error:
    block(f"invalid hook input ({error})")

if not isinstance(payload, dict):
    block("hook input must be an object")
tool_input = payload.get("tool_input")
if not isinstance(tool_input, dict):
    block("missing tool_input")

candidate = tool_input.get("file_path") or tool_input.get("notebook_path")
if not isinstance(candidate, str) or not candidate.strip():
    block("missing file path")

cwd = payload.get("cwd")
if not isinstance(cwd, str) or not cwd:
    cwd = WORKSPACE
resolved = os.path.realpath(os.path.join(cwd, candidate))
inside_workspace = os.path.commonpath((WORKSPACE, resolved)) == WORKSPACE

if not inside_workspace:
    # Only the two approved private identities have native file work. Derive
    # their separate roots from the OS identity, never the message or cwd.
    base = f"/srv/cc-file-work/{USER}"
    if USER in ("claude", "claude-test-private") and resolved.startswith(base + os.sep):
        parts = os.path.relpath(resolved, base).split(os.sep)
        if (len(parts) >= 3 and len(parts[0]) == 64
                and all(c in "0123456789abcdef" for c in parts[0])
                and (parts[1] == "outputs" or (parts[1] == "inputs" and payload.get("tool_name") == "Read"))):
            raise SystemExit(0)
    block(f"{resolved} is outside {WORKSPACE}")

# Installed skills are data needed for normal tool use, not writable policy.
# Compare the resolved target under the literal managed subtree: a symlink
# escaping it must not expand the exception (nor may '..' reach settings).
skills = os.path.join(WORKSPACE, ".claude", "skills")
if payload.get("tool_name") == "Read" and resolved.startswith(skills + os.sep):
    raise SystemExit(0)

for protected_path in PROTECTED:
    if resolved == protected_path or resolved.startswith(protected_path + os.sep):
        block(f"{resolved} is managed configuration")
