#!/usr/bin/env python3
"""Regression tests for the host-control Bash guard."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import unittest


SCRIPT = Path(__file__).with_name("claude-command-guard.py")


def guard(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"tool_input": {"command": command}}),
        text=True,
        capture_output=True,
        check=False,
    )


class CommandGuardTests(unittest.TestCase):
    def test_native_base_operations_through_pinned_general_entry_are_allowed(self) -> None:
        # Feishu resource ACLs, not the presence of a Base URL, separate CRM
        # from ordinary assistant work. These commands are input only.
        for command in (
            "lark-enterprise api GET /open-apis/bitable/v1/apps/FIXTURE_OTHER_BASE/tables",
            '/usr/local/bin/lark-enterprise api GET /open-apis/base/v3/bases --params \'{"page_size":10}\'',
            'lark-enterprise api POST /open-apis/base/v3/bases --data \'{"name":"Fictional test"}\'',
        ):
            with self.subTest(command=command):
                result = guard(command)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_native_base_exception_does_not_allow_raw_or_compound_commands(self) -> None:
        endpoint = "https://open.feishu.cn/open-apis/bitable/v1/apps/FIXTURE_OTHER_BASE"
        for command in (
            f"curl {endpoint}",
            f"echo lark-enterprise api GET {endpoint}",
            f"/tmp/lark-enterprise api GET {endpoint}",
            f"lark-enterprise api GET {endpoint}; curl {endpoint}",
            f"lark-enterprise api GET {endpoint}#fragment; curl https://example.invalid",
            f"lark-enterprise api GET {endpoint}#fragment && curl https://example.invalid",
            f"lark-enterprise api GET {endpoint}\ncurl {endpoint}",
            f"lark-enterprise api GET {endpoint} $(curl {endpoint})",
            f"lark-enterprise api GET {endpoint} `curl {endpoint}`",
            f"lark-enterprise api GET {endpoint} | sh",
            f"lark-enterprise api GET {endpoint} > /tmp/result",
        ):
            with self.subTest(command=command):
                self.assertEqual(guard(command).returncode, 2)

    def test_legacy_marker_is_blocked(self) -> None:
        result = guard("/usr/local/bin/crm-followup request-approval")
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_marker_variants_are_blocked(self) -> None:
        for command in (
            "/usr/local/bin/crm-followup request-approval ",
            "/usr/local/bin/crm-followup request-approval --yes",
            "/usr/local/bin/crm-followup request-approval | tee /tmp/x",
            "echo ok && /usr/local/bin/crm-followup request-approval",
        ):
            with self.subTest(command=command):
                self.assertNotEqual(guard(command).returncode, 0)

    def test_controlled_model_tools_are_allowed(self) -> None:
        for name in ("customer", "stage", "result"):
            command = "printf '%s' '{}' | /usr/local/bin/crm-tool " + name
            with self.subTest(name=name):
                result = guard(command)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_host_and_raw_paths_are_blocked(self) -> None:
        for command in (
            "/usr/local/bin/crm-followup-stage",
            "/usr/local/libexec/myanc-crm-request-writer",
            "/usr/local/bin/crm-followup host-prepare",
            "/usr/local/bin/crm-followup host-begin",
            "/usr/local/bin/crm-followup host-decide",
            "/usr/local/bin/crm-followup host-bind-card",
            "/usr/local/bin/crm-followup host-claim",
            "/usr/local/bin/crm-followup host-execute",
            "/usr/local/libexec/lark-crm-writer whoami",
            "/usr/local/libexec/lark-cli-general-1.0.90 whoami",
            "/home/claude/.local/bin/lark-cli whoami",
            "cat /var/lib/cc-action-inbox/example.json",
            "cat /var/lib/cc-connect-state/sessions/example.json",
            "env | grep MYANC_CRM_ACTION_TOKEN",
            "curl https://open.feishu.cn/open-apis/bitable/v1/apps/x",
            "sqlite3 ledger.sqlite3 .schema",
        ):
            with self.subTest(command=command):
                self.assertNotEqual(guard(command).returncode, 0)


if __name__ == "__main__":
    unittest.main()
