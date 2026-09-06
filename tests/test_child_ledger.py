"""Atomic parent/child linking and legacy fingerprint compatibility, offline."""

import copy
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from unittest import mock

from myanc_crm import core
from test_core import CONFIG, NOW, PRINCIPAL, TOKEN, MemoryBackend, stage_command


class ChildLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "ledger.sqlite3"
        self.backend = MemoryBackend()
        with closing(core.Ledger(self.path)) as ledger:
            staged = core.stage_followup(stage_command(), self.backend, ledger, CONFIG,
                                         TOKEN, NOW, trusted_principal=PRINCIPAL)
            self.parent_id = staged["change_id"]
            core.begin_approval({"change_id": self.parent_id, "principal": PRINCIPAL},
                                self.backend, ledger, CONFIG, TOKEN, NOW)
            ledger.finish(self.parent_id, "verified", {"status": "verified"})
            self.parent = ledger.get(self.parent_id)
        with closing(core.Ledger()) as temporary:
            child = core.stage_followup(stage_command(), self.backend, temporary, CONFIG,
                                        TOKEN, NOW + timedelta(minutes=2))
            self.body = json.loads(temporary._db.execute(
                "SELECT body_json FROM staged_changes WHERE change_id = ?",
                (child["change_id"],),
            ).fetchone()[0])

    def test_one_child_under_concurrent_publish_and_restart(self):
        def publish(_):
            with closing(core.Ledger(self.path)) as ledger:
                return ledger.stage_child(self.parent_id, self.body, core._iso(NOW))
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(publish, range(2)))
        self.assertEqual(1, sum(result is not None for result in results))
        with closing(core.Ledger(self.path)) as ledger:
            child = ledger.get(self.body["change_id"])
            self.assertEqual(self.parent_id, child["parent_change_id"])
            self.assertEqual(self.body["expires_at"], child["expires_at"])
            self.assertIsNone(ledger.stage_child(self.parent_id, self.body, core._iso(NOW)))
            approval = ledger.get_approval_for_change(child["change_id"])
            self.assertEqual(core._hash(core._approval_material(child)), approval["preview_hash"])
            self.assertEqual("verified", ledger.get(self.parent_id)["state"])

    def test_newer_intent_before_its_slow_read_blocks_auto_child(self):
        with closing(core.Ledger(self.path)) as ledger:
            ledger.note_write_intent(PRINCIPAL)
            self.assertIsNone(ledger.stage_child(self.parent_id, self.body, core._iso(NOW)))
            self.assertIsNone(ledger.child_change_id(self.parent_id))
            self.assertEqual("verified", ledger.get(self.parent_id)["state"])

    def test_other_sender_intent_and_reads_do_not_block_child(self):
        with closing(core.Ledger(self.path)) as ledger:
            ledger.note_write_intent({**PRINCIPAL, "user_id": "another"})
            ledger.get(self.parent_id)
            self.assertIsNotNone(ledger.stage_child(self.parent_id, self.body, core._iso(NOW)))

    def test_slow_old_plan_cannot_stage_or_bind_after_new_intent(self):
        with closing(core.Ledger(self.path)) as ledger:
            old_version = ledger.note_write_intent(PRINCIPAL)
            body = {**self.body, "principal": PRINCIPAL}
            ledger.note_write_intent(PRINCIPAL)
            with self.assertRaises(ValueError):
                ledger.stage(body, core._action_token_hash(TOKEN), intent_version=old_version)
            version = ledger.note_write_intent(PRINCIPAL)
            ledger.stage(body, core._action_token_hash(TOKEN), intent_version=version)
            ledger.note_write_intent(PRINCIPAL)
            approval, _ = ledger.bind_approval(body["change_id"], core._action_token_hash(TOKEN),
                                              PRINCIPAL, self.parent["actor"], "hash", core._iso(NOW))
            self.assertIsNone(approval)

    def test_legacy_hash_excludes_added_storage_metadata(self):
        legacy_keys = ("change_id", "customer_query", "matched_by", "customer_record_id",
                       "customer_number", "customer_snapshot", "schema_hash", "snapshot_hash",
                       "before", "followup", "customer_patch", "created_at", "expires_at",
                       "principal", "actor")
        original = {key: self.parent.get(key) for key in legacy_keys}
        modified = {**self.parent, "resolved_customer_record_id": "new-id", "intent_version": 42}
        self.assertEqual(core._hash(original), core._hash(core._approval_material(modified)))

    def test_verified_customer_link_does_not_mutate_approved_body(self):
        with closing(core.Ledger(self.path)) as ledger:
            before = core._approval_material(ledger.get(self.parent_id))
            ledger.set_resolved_customer(self.parent_id, "created-record")
            self.assertEqual(before, core._approval_material(ledger.get(self.parent_id)))
            with self.assertRaises(ValueError):
                ledger.set_resolved_customer(self.parent_id, "other-record")

    def test_assignee_cache_is_scoped_and_does_not_grant_approval(self):
        with closing(core.Ledger(self.path)) as ledger:
            ref = ledger.remember_assignee(PRINCIPAL, {"id": "person-1", "name": "同名"})
            same = ledger.remember_assignee(PRINCIPAL, {"id": "person-1", "name": "同名"})
            ledger.remember_assignee(PRINCIPAL, {"id": "person-2", "name": "同名"})
            self.assertEqual(ref, same)
            self.assertEqual(2, len(ledger.find_assignees("同名", PRINCIPAL)))
            self.assertIsNone(ledger.get_assignee(ref, {**PRINCIPAL, "chat_id": "other"}))
            with self.assertRaises(ValueError):
                core._actor_for_principal({**PRINCIPAL, "user_id": "person-1"}, CONFIG)

    def test_child_planner_uses_verified_record_not_renamed_company_lookup(self):
        with closing(core.Ledger(self.path)) as ledger:
            ledger.set_resolved_customer(self.parent_id, "rec-1")
            self.backend.customers["rec-1"]["name"] = "已核验的新公司名"
            before = core._approval_material(ledger.get(self.parent_id))
            with mock.patch.object(self.backend, "find_customers", side_effect=AssertionError("no lookup")):
                receipt, pending = core._prepare_child_followup(
                    ledger.get(self.parent_id), {"status": "verified"}, self.backend,
                    ledger, CONFIG, NOW + timedelta(minutes=3),
                )
            self.assertEqual("verified", receipt["status"])
            self.assertEqual("pending", pending["status"])
            child = ledger.get(pending["change_id"])
            self.assertEqual("rec-1", child["customer_record_id"])
            self.assertEqual("已核验的新公司名", child["customer_snapshot"]["name"])
            self.assertEqual(NOW + timedelta(minutes=13),
                             core._parse_time(child["expires_at"], "expires_at"))
            self.assertEqual(before, core._approval_material(ledger.get(self.parent_id)))
            self.assertEqual([], self.backend.actions)

    def test_child_planning_failure_retains_parent_success(self):
        with closing(core.Ledger(self.path)) as ledger:
            with mock.patch.object(self.backend, "get_customer", side_effect=OSError("offline")):
                receipt, pending = core._prepare_child_followup(
                    ledger.get(self.parent_id), {"status": "verified"}, self.backend,
                    ledger, CONFIG, NOW,
                )
            self.assertEqual("verified", receipt["status"])
            self.assertEqual("unavailable", receipt["next_approval_status"])
            self.assertIsNone(pending)
            self.assertEqual("verified", ledger.get(self.parent_id)["state"])
            self.assertIsNone(ledger.child_change_id(self.parent_id))

    def test_child_cancel_replay_and_result_keep_successful_parent_visible(self):
        from myanc_crm.cli import _change_result
        with closing(core.Ledger(self.path)) as ledger:
            parent_approval = ledger.get_approval_for_change(self.parent_id)
            ledger.finish_approval(parent_approval["approval_id"], "verified", "approve",
                                   core._iso(NOW), {"status": "verified"})
            approval = ledger.stage_child(self.parent_id, self.body, core._iso(NOW))
            principal = {**PRINCIPAL, "message_id": "child-card"}
            core.bind_approval_card({"approval_id": approval["approval_id"], "principal": principal},
                                   ledger, CONFIG)
            for _ in range(2):
                cancelled = core.claim_approval_decision(
                    {"approval_id": approval["approval_id"], "principal": principal, "decision": "cancel"},
                    ledger, CONFIG, NOW,
                )
                self.assertEqual("cancelled", cancelled["status"])
                self.assertEqual("verified", cancelled["parent_operation"]["status"])
            for change_id in (self.parent_id, self.body["change_id"]):
                before = list(ledger._db.iterdump())
                result = _change_result({"change_id": change_id}, PRINCIPAL, ledger)
                self.assertEqual("verified", result["related_operations"]["parent"]["status"])
                self.assertEqual("cancelled", result["related_operations"]["child"]["status"])
                self.assertEqual(before, list(ledger._db.iterdump()))
            self.assertEqual([], self.backend.actions)


if __name__ == "__main__":
    unittest.main()
