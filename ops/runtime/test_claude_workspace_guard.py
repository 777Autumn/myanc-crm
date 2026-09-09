#!/usr/bin/env python3
"""Small regression check for the managed workspace file hook."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


GUARD = Path(__file__).with_name("claude-workspace-guard.py")


def invoke(path: str, tool: str = "Read", user: str = "claude", cwd: str = "/home/claude/ClaudeRemote") -> subprocess.CompletedProcess[str]:
    # Mock only the OS identity lookup; the actual file-hook logic is executed.
    harness = "import os,sys,types,runpy; os.geteuid=lambda:1000; sys.modules['pwd']=types.SimpleNamespace(getpwuid=lambda _:types.SimpleNamespace(pw_name=sys.argv[2])); runpy.run_path(sys.argv[1],run_name='__main__')"
    return subprocess.run(
        [sys.executable, "-c", harness, str(GUARD), user],
        input=json.dumps(
            {"tool_name": tool, "tool_input": {"file_path": path}, "cwd": cwd}
        ),
        capture_output=True,
        text=True,
        check=False,
    )


@unittest.skipUnless(os.name == "posix", "managed Unix file hook; run this suite on Linux")
class WorkspaceGuardTests(unittest.TestCase):
    def test_partner_identity_cannot_be_switched_by_cwd(self) -> None:
        users = ("claude", "claude-owner-group", "claude-partner-private", "claude-partner-group", "claude-test-private", "claude-test-group")
        for user in users:
            own = f"/home/{user}/ClaudeRemote"
            self.assertEqual(0, invoke("notes.txt", user=user, cwd=own).returncode)
            for other in users:
                if other != user:
                    self.assertEqual(2, invoke("notes.txt", user=user, cwd=f"/home/{other}/ClaudeRemote").returncode)
            self.assertEqual(2, invoke("CLAUDE.md", "Write", user=user, cwd=own).returncode)
        self.assertEqual(2, invoke("notes.txt", user="unregistered").returncode)

    def test_allows_installed_skill_and_reference_reads(self) -> None:
        for path in (
            ".claude/skills/lark-base/SKILL.md",
            ".claude/skills/lark-base/references/records.md",
        ):
            with self.subTest(path=path):
                result = invoke(path)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_read_exception_does_not_allow_policy_reads_or_skill_writes(self) -> None:
        for path, tool in (
            (".claude/settings.json", "Read"),
            (".claude/skills/../settings.json", "Read"),
            (".claude/skills-extra/secret", "Read"),
            (".claude/skills/lark-base/SKILL.md", "Write"),
            (".claude/skills/lark-base/SKILL.md", "Edit"),
            (".claude/skills/lark-base/SKILL.md", "NotebookEdit"),
            (".claude/skills/lark-base/SKILL.md", ""),
            ("/home/claude/.claude/credentials.json", "Read"),
            ("/var/lib/myanc-crm/ledger.sqlite3", "Read"),
        ):
            with self.subTest(path=path, tool=tool):
                self.assertEqual(invoke(path, tool).returncode, 2)

    def test_allows_ordinary_workspace_file(self) -> None:
        self.assertEqual(0, invoke("notes.txt").returncode)

    def test_blocks_outside_workspace(self) -> None:
        self.assertEqual(2, invoke("/etc/passwd").returncode)

    def test_blocks_managed_inbox(self) -> None:
        self.assertEqual(
            2, invoke("/var/lib/cc-action-inbox/request.json").returncode
        )


if __name__ == "__main__":
    unittest.main()
