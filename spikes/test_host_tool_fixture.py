"""Offline fixture checks, separate from model semantic grading."""

import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from host_tool_fixture import PersistentFakeFeishu
from test_host_tools import PRINCIPAL, SECRET, TOKEN


class OwnerFixtureTests(unittest.TestCase):
    def test_first_exact_roster_name_uses_real_host_without_cached_lookup(self):
        for seed, status in (("customer-roster", "resolved"),
                             ("customer-roster-ambiguous", "needs_input")):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as path:
                payload = {"command": "assignee", "request": {"query": "示例同事"},
                           "principal": PRINCIPAL}
                result = subprocess.run(
                    [sys.executable, "-B", str(Path(__file__).with_name("host_tool_fixture.py")), "host-tool"],
                    input=json.dumps(payload), text=True, encoding="utf-8", capture_output=True,
                    env={**os.environ, "MYANC_SPIKE_DIR": path, "MYANC_SPIKE_SEED": seed,
                         "MYANC_CRM_HOST_SECRET": SECRET, "MYANC_CRM_ACTION_TOKEN": TOKEN},
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                response = json.loads(result.stdout)
                self.assertEqual(status, response["status"])
                if status == "resolved":
                    self.assertTrue(response["owner_ref"].startswith("own_"))
                    self.assertIn("示例同事", response["name"])
                else:
                    self.assertEqual("assignee_ambiguous", response["code"])
                    self.assertNotIn("owner_ref", response)
                self.assertEqual([], PersistentFakeFeishu(Path(path)).actions)

    def test_paired_term_seeds_are_persistent_facts_not_business_writes(self):
        for seed in ("term-ambiguous", "term-defined"):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as path:
                with mock.patch.dict(os.environ, {"MYANC_SPIKE_SEED": seed}):
                    first = PersistentFakeFeishu(Path(path))
                with mock.patch.dict(os.environ, {"MYANC_SPIKE_SEED": ""}):
                    reopened = PersistentFakeFeishu(Path(path))
                self.assertEqual(first.customers, reopened.customers)
                self.assertEqual([], reopened.actions)
                rows = reopened.read_customer_history("rec-1", 10)
                self.assertEqual(1, len(rows))
                self.assertEqual(reopened.customers["rec-1"]["last_followup_content"],
                                 rows[0]["content"])
                self.assertEqual(seed == "term-defined", "5%" in rows[0]["content"])

    def test_unknown_seed_is_rejected_instead_of_silently_changing_a_case(self):
        with tempfile.TemporaryDirectory() as path:
            with mock.patch.dict(os.environ, {"MYANC_SPIKE_SEED": "typo"}):
                with self.assertRaises(ValueError):
                    PersistentFakeFeishu(Path(path))


if __name__ == "__main__":
    unittest.main()
