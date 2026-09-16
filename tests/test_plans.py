"""Customer plans use the real approval/receipt ledger and synthetic Feishu."""

import copy
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

from myanc_crm import core, plans
from myanc_crm.customers import apply_customer, stage_customer
from test_core import CONFIG, NOW, PRINCIPAL, TOKEN, stage_command
from test_customers import CustomerBackend


BINDING = {"user_id": PRINCIPAL["user_id"], "source_chat_id": PRINCIPAL["chat_id"],
           "project": PRINCIPAL["project"], "private_chat_id": "synthetic-private-route"}
PLAN_CONFIG = {**CONFIG, "crm_plan_reminders_enabled": True, "base_token": "synthetic-base",
               "customer_table_id": "synthetic-customers"}


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.backend = CustomerBackend()
        self.ledger = core.Ledger()
        self.addCleanup(self.ledger.close)
        self.config = copy.deepcopy(PLAN_CONFIG)
        timeout = mock.patch.object(core, "READBACK_TIMEOUT_SECONDS", 0)
        timeout.start()
        self.addCleanup(timeout.stop)

    def stage(self, changes, *, request=None, principal=PRINCIPAL, binding=BINDING, token=TOKEN,
              expected=None, config=None, target=None):
        return stage_customer({"customer_query": "C-001", "changes": changes, **(request or {})},
                              "customer_update", self.backend, self.ledger, config or self.config,
                              token, principal, NOW, trusted_plan_binding=binding,
                              trusted_expected_plan_revision=expected, trusted_expected_plan_target=target)

    def apply(self, staged, moment=NOW):
        self.assertEqual("staged", staged["status"], staged)
        return apply_customer(self.ledger.get(staged["change_id"]), self.backend, self.ledger, moment)

    def save_plan(self, at="2026-09-04T15:30:00+08:00", **kwargs):
        staged = self.stage({"next_action": "准备虚构材料", "next_followup_at": at}, **kwargs)
        result = self.apply(staged)
        self.assertEqual("verified", result["status"], result)
        return result

    def queued(self):
        result = plans.events({}, self.ledger, self.config)
        self.assertEqual("ok", result["status"], result)
        return result["events"]

    def read(self, event):
        return plans.read({key: event[key] for key in ("namespace", "customer_id", "revision")},
                          self.backend, self.ledger, self.config)

    def test_plan_change_is_independent_and_verifies_before_queue(self):
        staged = self.stage({"next_action": "准备虚构材料", "next_followup_at": "2026-09-04"})
        self.assertEqual([], self.queued())
        self.assertEqual([], self.backend.actions)
        preview = staged["preview"]["plan_reminder"]
        self.assertEqual("2026-09-04T09:00:00+08:00", preview["at"])
        self.assertEqual("本人私聊", preview["delivery"])
        self.assertEqual("777秋", preview["recipient"])
        result = self.apply(staged)
        self.assertEqual("pending_sync", result["plan_reminder_status"])
        self.assertEqual(["update_customer_profile"], self.backend.actions)
        event, = self.queued()
        self.assertEqual(1, event["revision"])
        self.assertEqual(BINDING, event["reminder_binding"])
        self.assertEqual(PRINCIPAL, event["principal"])
        self.assertEqual("current", self.read(event)["status"])
        self.assertEqual({}, self.backend.followups)

    def test_notification_only_disable_does_not_reject_or_clear_an_overdue_plan(self):
        row = self.backend.customers["rec-1"]
        row["next_followup_at"] = "2026-09-01T09:00:00+08:00"
        row["next_action"] = "仍需完成的旧计划"
        staged = self.stage({}, request={"remind": False})
        self.assertEqual("verified", self.apply(staged)["status"])
        self.assertEqual("2026-09-01T09:00:00+08:00", self.backend.customers["rec-1"]["next_followup_at"])
        self.assertFalse(self.queued()[0]["enabled"])
        self.assertEqual("blocked", self.stage({}, request={"remind": True})["status"])
        self.assertEqual("blocked", self.stage({"next_action": "新计划"}, request={"remind": False})["status"])

    def test_linked_edit_cannot_stage_same_number_in_another_environment_or_record(self):
        target = {"namespace": plans.namespace(self.config), "customer_id": "rec-1"}
        self.assertEqual("staged", self.stage({"next_action": "目标"}, target=target)["status"])
        for target in ({**target, "namespace": "other-base"}, {**target, "customer_id": "rec-other"}):
            self.assertEqual("blocked", self.stage({"next_action": "目标"}, target=target)["status"])
        self.assertEqual([], self.backend.actions)

    def test_environment_change_after_preview_cannot_apply_plan_to_another_base(self):
        staged = self.stage({"next_action": "待批计划", "next_followup_at": "2026-09-04"})
        approval = core.begin_approval({"change_id": staged["change_id"], "principal": PRINCIPAL},
                                       self.backend, self.ledger, self.config, TOKEN, NOW)
        self.ledger.bind_card_message(approval["approval_id"], PRINCIPAL["message_id"])
        command = {"approval_id": approval["approval_id"], "principal": PRINCIPAL, "decision": "approve"}
        claimed = core.claim_approval_decision(command, self.ledger, self.config, NOW, backend=self.backend)
        self.assertTrue(claimed["execute"])
        changed = {**self.config, "base_token": "different-base"}
        result = core.execute_claimed_approval({key: command[key] for key in ("approval_id", "principal")},
                                              self.backend, self.ledger, changed, NOW)
        self.assertEqual("plan_environment_changed", result["code"])
        self.assertEqual([], self.backend.actions)
        self.assertEqual([], self.queued())

    def test_plan_and_verified_receipt_are_atomic_on_storage_failure(self):
        staged = self.stage({"next_followup_at": "2026-09-04"})
        self.ledger._db.execute("CREATE TRIGGER fail_outbox BEFORE INSERT ON plan_outbox "
                                "BEGIN SELECT RAISE(ABORT, 'synthetic storage failure'); END")
        self.ledger._db.commit()
        with self.assertRaises(Exception):
            self.apply(staged)
        # Feishu may have accepted, but no successful durable receipt can lie.
        self.assertIsNone(self.ledger.get(staged["change_id"])["receipt"])
        self.assertEqual([], self.queued())
        self.assertIsNone(plans.current(self.ledger, plans.namespace(self.config), "rec-1"))

    def test_unknown_recipient_only_reconfirmation_stops_old_notification(self):
        self.save_plan()
        event, = self.queued()
        staged = self.stage({}, request={"remind": True})
        self.ledger._db.execute("CREATE TRIGGER fail_outbox BEFORE INSERT ON plan_outbox "
                                "BEGIN SELECT RAISE(ABORT, 'synthetic storage failure'); END")
        self.ledger._db.commit()
        with self.assertRaises(Exception):
            self.apply(staged)
        self.assertEqual("plan_write_unresolved", self.read(event)["code"])

    def test_date_only_modification_preserves_beijing_clock(self):
        self.save_plan()
        result = self.apply(self.stage({"next_followup_at": "2026-09-05"}))
        self.assertEqual("verified", result["status"])
        self.assertEqual("2026-09-05T15:30:00+08:00", self.backend.customers["rec-1"]["next_followup_at"])
        self.assertEqual("准备虚构材料", self.backend.customers["rec-1"]["next_action"])

    def test_timezone_date_and_past_validation(self):
        self.assertEqual("2026-09-05T15:30:00+08:00",
                         plans.normalize_time("2026-09-05", "2026-09-04T07:30:00Z"))
        for at in ("2026-02-30", "2026-09-04T15:00:00", "2026-09-02", "2026-09-03T10:00:00+08:00"):
            with self.subTest(at=at):
                self.assertEqual("blocked", self.stage({"next_followup_at": at})["status"])
        self.assertEqual([], self.backend.actions)

    def test_time_can_expire_between_preview_and_execution(self):
        staged = self.stage({"next_followup_at": (NOW + timedelta(minutes=2)).isoformat()})
        result = self.apply(staged, NOW + timedelta(minutes=3))
        self.assertEqual("plan_time_passed", result["code"])
        self.assertEqual([], self.backend.actions)
        self.assertEqual([], self.queued())

    def test_explicit_clear_cancels_link_but_not_history(self):
        self.save_plan()
        result = self.apply(self.stage({"next_followup_at": None, "next_action": None}))
        self.assertEqual("verified", result["status"])
        event = self.queued()[-1]
        self.assertFalse(event["enabled"])
        self.assertIsNone(event["at"])
        self.assertIsNone(self.backend.customers["rec-1"]["next_action"])
        self.assertEqual("首次沟通", self.backend.customers["rec-1"]["last_followup_content"])

    def test_noop_and_profile_edits_do_not_reenable_notifications(self):
        self.save_plan(request={"remind": False})
        self.assertFalse(self.queued()[0]["enabled"])
        self.apply(self.stage({"phone": "UPDATED-FAKE-PHONE"}))
        self.apply(self.stage({"next_action": "准备虚构材料"}))
        self.assertEqual(1, len(self.queued()))
        confirmed = self.apply(self.stage({}, request={"remind": True}))
        self.assertEqual("verified", confirmed["status"])
        self.assertTrue(self.queued()[-1]["enabled"])
        self.assertEqual(2, self.queued()[-1]["revision"])

    def test_explicit_no_reminder_reconfirmation_is_durable(self):
        self.save_plan()
        self.apply(self.stage({}, request={"remind": False}, binding=None))
        self.assertFalse(self.queued()[-1]["enabled"])
        self.assertEqual("2026-09-04T15:30:00+08:00", self.backend.customers["rec-1"]["next_followup_at"])

    def test_disabled_by_default_does_not_enqueue_legacy_dates(self):
        config = {**self.config, "crm_plan_reminders_enabled": False}
        result = self.apply(self.stage({"next_followup_at": "2026-09-04"}, config=config, binding=None))
        self.assertEqual("disabled", result["plan_reminder_status"])
        self.assertEqual([], self.queued())
        self.assertEqual("disabled", plans.events({}, self.ledger, config)["status"])

    def test_binding_required_only_for_enabled_reminder_and_no_actor_model_override(self):
        self.assertEqual("blocked", self.stage({"next_followup_at": "2026-09-04"}, binding=None)["status"])
        self.assertEqual("staged", self.stage({"next_followup_at": "2026-09-04"}, request={"remind": False}, binding=None)["status"])
        for key in ("namespace", "principal", "reminder_binding", "plan", "expected_revision"):
            self.assertEqual("blocked", self.stage({"next_followup_at": "2026-09-04"}, request={key: "forged"})["status"])
        self.assertEqual("blocked", self.stage({}, request={"remind": "false"})["status"])
        self.assertEqual("blocked", self.stage({}, request={"remind": True})["status"])
        for key in ("user_id", "source_chat_id", "project"):
            forged = {**BINDING, key: "other"}
            self.assertEqual("blocked", self.stage({"next_followup_at": "2026-09-04"}, binding=forged)["status"])

    def test_two_people_share_plan_but_new_plan_routes_to_last_operator(self):
        self.save_plan()
        other = {**PRINCIPAL, "user_id": "other", "chat_id": "other-group", "project": "other-runtime"}
        self.config["allowed_actors"]["other"] = {"display_name": "另一个人", "feishu_user_id": "ou_other"}
        binding = {**BINDING, "user_id": "other", "source_chat_id": "other-group", "project": "other-runtime",
                   "private_chat_id": "other-private"}
        staged = self.stage({"next_followup_at": "2026-09-05"}, principal=other, binding=binding)
        self.assertTrue(staged["preview"]["plan_reminder"]["replaces_previous"])
        self.apply(staged)
        first, second = self.queued()
        self.assertEqual("plan_superseded", self.read(first)["code"])
        self.assertEqual("other", second["principal"]["user_id"])
        self.assertEqual("current", self.read(second)["status"])

    def test_aba_version_prevents_stale_approval_even_when_fields_identical(self):
        self.save_plan()
        stale = self.stage({"next_action": "stale-update"}, token="x" * 32)
        self.apply(self.stage({"next_followup_at": "2026-09-05"}))
        self.apply(self.stage({"next_followup_at": "2026-09-04T15:30:00+08:00"}))
        result = self.apply(stale)
        self.assertEqual("plan_changed", result["code"])
        self.assertEqual("准备虚构材料", self.backend.customers["rec-1"]["next_action"])
        self.assertEqual(3, len(self.queued()))
        self.assertEqual("blocked", self.stage({"next_action": "bad"}, expected=1)["status"])

    def test_duplicate_finish_and_ack_do_not_duplicate_event(self):
        result = self.save_plan()
        self.ledger.finish(result["change_id"], "verified", dict(result))
        event, = self.queued()
        staged = self.ledger.get(result["change_id"])
        self.assertEqual("pending_sync", plans.synchronization(staged, self.ledger)["status"])
        for _ in range(2):
            self.assertEqual("acknowledged", plans.ack({"event_id": event["event_id"]}, self.ledger, self.config)["status"])
        self.assertEqual([], self.queued())
        self.assertEqual("current", self.read(event)["status"])
        self.assertEqual("synchronized", plans.synchronization(staged, self.ledger)["status"])
        self.assertEqual("pending_sync", self.ledger.get(result["change_id"])["receipt"]["plan_reminder_status"])
        self.apply(self.stage({"next_followup_at": "2026-09-05"}))
        self.assertEqual("replaced", plans.synchronization(staged, self.ledger)["status"])

    def test_read_fails_closed_on_external_changes_authorization_or_namespace(self):
        self.save_plan()
        event, = self.queued()
        self.backend.customers["rec-1"]["next_action"] = "changed in table"
        self.assertEqual("plan_customer_changed", self.read(event)["code"])
        self.backend.customers["rec-1"]["next_action"] = event["fields"]["next_action"]
        self.config["allowed_actors"] = {}
        self.assertEqual("blocked", self.read(event)["status"])
        config = {**PLAN_CONFIG, "base_token": "other-environment"}
        self.assertEqual([], plans.events({}, self.ledger, config)["events"])
        self.assertEqual("blocked", plans.read({key: event[key] for key in ("namespace", "customer_id", "revision")},
                                              self.backend, self.ledger, config)["status"])

    def test_host_queue_validation_and_pagination(self):
        self.save_plan()
        self.apply(self.stage({"next_followup_at": "2026-09-05"}))
        page = plans.events({"limit": 1}, self.ledger, self.config)
        self.assertTrue(page["has_more"])
        self.assertEqual(1, len(page["events"]))
        for request in ({"limit": True}, {"limit": 101}, {"namespace": "forged"}):
            self.assertEqual("blocked", plans.events(request, self.ledger, self.config)["status"])

    def test_unknown_write_never_creates_reminder(self):
        self.backend.profile_mode = "raise_before_write"
        result = self.apply(self.stage({"next_followup_at": "2026-09-04"}))
        self.assertEqual("verification_unknown", result["status"])
        self.assertEqual([], self.queued())

    def test_followup_plan_is_only_queued_after_real_host_approval(self):
        staged = core.stage_followup(stage_command(next_action="new plan", next_followup_at="2026-09-05"),
                                     self.backend, self.ledger, self.config, TOKEN, NOW,
                                     trusted_principal=PRINCIPAL, trusted_plan_binding=BINDING)
        self.assertEqual("staged", staged["status"], staged)
        result = self.approve_followup(staged)
        self.assertEqual("verified", result["status"], result)
        self.assertEqual(1, len(self.queued()))
        self.assertEqual(1, len(self.backend.followups))

    def test_parent_then_child_freezes_current_revision_and_route(self):
        self.save_plan()
        staged = self.stage({"phone": "OTHER-FAKE"}, request={"followup": {
            "occurred_at": NOW.isoformat(), "content": "虚构沟通", "next_action": "子审批安排",
            "next_followup_at": "2026-09-06T11:00:00+08:00", "remind": True}})
        parent = self.approve_followup(staged)
        self.assertEqual("verified", parent["status"], parent)
        self.assertEqual("pending", parent["next_approval_status"], parent)
        child = parent["next_approval"]
        frozen = self.ledger.get(child["change_id"])
        self.assertEqual(1, frozen["plan"]["expected_revision"])
        self.assertEqual(BINDING, frozen["plan"]["reminder_binding"])
        self.assertEqual(1, len(self.queued()))
        self.ledger.bind_card_message(child["approval_id"], PRINCIPAL["message_id"])
        result = core.decide_approval({"approval_id": child["approval_id"], "principal": PRINCIPAL,
                                       "decision": "approve"}, self.backend, self.ledger, self.config, NOW)
        self.assertEqual("verified", result["status"], result)
        self.assertEqual(2, self.queued()[-1]["revision"])
        self.assertEqual("子审批安排", self.queued()[-1]["content"])

    def test_parent_child_no_reminder_draft_never_creates_enabled_event(self):
        staged = self.stage({"phone": "OTHER-FAKE"}, request={"followup": {
            "occurred_at": NOW.isoformat(), "content": "虚构沟通", "next_followup_at": "2026-09-06",
            "remind": False}}, binding=None)
        parent = self.approve_followup(staged)
        self.assertEqual("pending", parent["next_approval_status"], parent)
        child = parent["next_approval"]
        self.assertFalse(self.ledger.get(child["change_id"])["plan"]["enabled"])

    def test_exact_number_lookup_does_not_depend_on_bounded_keyword_search(self):
        self.backend.find_customers_by_number = lambda query: [self.backend.get_customer("rec-1")]
        self.backend.find_customers = mock.Mock(side_effect=AssertionError("bounded search must not run"))
        rows, matched = core._resolve_customer("C-001", self.backend)
        self.assertEqual("customer_number", matched)
        self.assertEqual("rec-1", rows[0]["record_id"])
        with self.assertRaises(ValueError):
            core._resolve_customer("C-WRONG", self.backend)

    def test_missing_number_never_falls_back_to_another_companys_name(self):
        other = dict(self.backend.get_customer("rec-1"), customer_number="C-999", name="C-001")
        self.backend.find_customers_by_number = lambda query: []
        self.backend.find_customers = mock.Mock(return_value=[other])
        self.assertEqual(([], "customer_number"), core._resolve_customer("C-001", self.backend))
        self.backend.find_customers.assert_not_called()
        self.backend.find_customers_by_number = None
        self.assertEqual(([], "customer_number"), core._resolve_customer("C-001", self.backend))

    def approve_followup(self, staged):
        approval = core.begin_approval({"change_id": staged["change_id"], "principal": PRINCIPAL},
                                       self.backend, self.ledger, self.config, TOKEN, NOW)
        self.assertEqual("pending", approval["status"], approval)
        self.ledger.bind_card_message(approval["approval_id"], PRINCIPAL["message_id"])
        return core.decide_approval({"approval_id": approval["approval_id"], "principal": PRINCIPAL,
                                     "decision": "approve"}, self.backend, self.ledger, self.config, NOW)

    def test_historical_and_ordinary_followup_cannot_revive_plan(self):
        self.save_plan(request={"remind": False})
        for request in (stage_command(occurred_at="2026-09-01T10:00:00+08:00", next_action="old",
                                      next_followup_at="2026-09-02T09:00:00+08:00", remind=True),
                        stage_command()):
            staged = core.stage_followup(request, self.backend, self.ledger, self.config, TOKEN, NOW,
                                         trusted_principal=PRINCIPAL, trusted_plan_binding=BINDING)
            self.assertEqual("staged", staged["status"], staged)
            self.assertEqual("verified", self.approve_followup(staged)["status"])
        self.assertEqual(1, len(self.queued()))
        self.assertFalse(self.queued()[0]["enabled"])
        self.assertEqual("准备虚构材料", self.backend.customers["rec-1"]["next_action"])

    def test_explicit_first_history_backfill_preserves_plan_and_never_schedules(self):
        row = self.backend.customers["rec-1"]
        row["last_followup_at"] = None
        row["last_followup_content"] = None
        before = {key: row.get(key) for key in plans.FIELDS}
        request = stage_command(backfill=True, next_action="历史当时的安排",
                                next_followup_at="2026-09-01T09:00:00+08:00", remind=True)
        staged = core.stage_followup(request, self.backend, self.ledger, self.config, TOKEN, NOW,
                                     trusted_principal=PRINCIPAL, trusted_plan_binding=BINDING)
        self.assertEqual("staged", staged["status"], staged)
        self.assertEqual("verified", self.approve_followup(staged)["status"])
        self.assertEqual(before, {key: self.backend.customers["rec-1"].get(key) for key in plans.FIELDS})
        self.assertEqual([], self.queued())
        self.assertEqual(1, len(self.backend.followups))
        payload = next(iter(self.backend.followups.values()))
        self.assertNotIn("backfill", payload)
        self.assertNotIn("remind", payload)

    def test_followup_retains_no_reminder_intent_for_repreview(self):
        staged = core.stage_followup(stage_command(remind=False, next_followup_at="2026-09-05"),
                                     self.backend, self.ledger, self.config, TOKEN, NOW,
                                     trusted_principal=PRINCIPAL)
        self.assertEqual("staged", staged["status"], staged)
        self.assertFalse(self.ledger.get(staged["change_id"])["followup"]["remind"])

    def test_receipt_queue_and_disabled_state_survive_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "private" / "ledger.sqlite"
            original = self.ledger
            self.ledger = core.Ledger(path)
            try:
                result = self.save_plan(request={"remind": False})
            finally:
                self.ledger.close()
            self.ledger = core.Ledger(path)
            try:
                event, = self.queued()
                self.assertFalse(event["enabled"])
                self.assertEqual("verified", self.ledger.get(result["change_id"])["receipt"]["status"])
            finally:
                self.ledger.close()
                self.ledger = original


if __name__ == "__main__":
    unittest.main()
