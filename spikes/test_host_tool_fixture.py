"""Offline fixture checks, separate from model semantic grading."""

import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from unittest import mock

from host_tool_fixture import PersistentFakeFeishu, PersistentSalesStore
from myanc_crm import banquet, core
from test_core import NOW
from test_host_tools import CONFIG, PRINCIPAL, SECRET, TOKEN


class OwnerFixtureTests(unittest.TestCase):
    def test_banquet_read_accepts_production_get_contract_and_returns_copies(self):
        with tempfile.TemporaryDirectory() as path, mock.patch.dict(
                os.environ, {"MYANC_SPIKE_SEED": "customer-trial"}):
            backend = PersistentFakeFeishu(Path(path))
            store = PersistentSalesStore(backend)
            identifier = store.write("banquets", None, {
                "name": "Fictional banquet", "estimated_tables": 20,
                "owner": [{"id": "ou_member", "name": "Fixture owner"}],
            })
            with mock.patch.object(banquet, "Store", side_effect=PersistentSalesStore):
                result = banquet.read("banquet", {"banquet_id": identifier},
                                      backend, CONFIG, PRINCIPAL)
            self.assertEqual("found", result["status"])
            self.assertEqual(20, result["banquet"]["estimated_tables"])
            self.assertEqual([], result["history"])
            copied = store.get("banquets", identifier, recheck=False)
            copied["estimated_tables"] = 99
            copied["owner"][0]["name"] = "Caller edit"
            for options in ({}, {"recheck": True}, {"recheck": False}):
                with self.subTest(options=options):
                    fresh = store.get("banquets", identifier, **options)
                    self.assertEqual(20, fresh["estimated_tables"])
                    self.assertEqual("Fixture owner", fresh["owner"][0]["name"])

    def test_daily_history_without_change_ids_allows_approved_backfill(self):
        with tempfile.TemporaryDirectory() as path, mock.patch.dict(
                os.environ, {"MYANC_SPIKE_SEED": "daily-followup"}):
            backend = PersistentFakeFeishu(Path(path))
            before = dict(backend.customers["rec-2"])
            with closing(core.Ledger()) as ledger:
                staged = core.stage_followup({
                    "customer_query": "C-002", "occurred_at": "2026-09-01T09:00:00+08:00",
                    "content": "讨论了虚构演示", "backfill": True, "remind": False,
                }, backend, ledger, CONFIG, TOKEN, NOW)
                approval = core.begin_approval({
                    "change_id": staged["change_id"], "principal": PRINCIPAL,
                }, backend, ledger, CONFIG, TOKEN, NOW)
                core.bind_approval_card({
                    "approval_id": approval["approval_id"], "principal": PRINCIPAL,
                }, ledger, CONFIG)
                result = core.decide_approval({
                    "approval_id": approval["approval_id"], "decision": "approve",
                    "principal": PRINCIPAL,
                }, backend, ledger, CONFIG, NOW)
                replay = core.decide_approval({
                    "approval_id": approval["approval_id"], "decision": "approve",
                    "principal": PRINCIPAL,
                }, backend, ledger, CONFIG, NOW)
                self.assertEqual("verified", replay["status"], replay)
                self.assertEqual(0, ledger._db.execute("SELECT count(*) FROM plan_outbox").fetchone()[0])
            self.assertEqual("verified", result["status"], result)
            reopened = PersistentFakeFeishu(Path(path))
            self.assertEqual(before, reopened.customers["rec-2"])
            self.assertEqual(13, len(reopened.followups))
            self.assertEqual(["create_followup"], reopened.actions)
            self.assertEqual("讨论了虚构演示",
                             reopened.find_followup_by_change(staged["change_id"])["content"])

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
