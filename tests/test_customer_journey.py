"""Real controlled CLI/SQLite journey, faking only config and external Feishu."""

import copy
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from unittest import mock

from myanc_crm import core
import test_host_tools as host_tools
from test_host_tools import HistoryBackend, PRINCIPAL


class CustomerBackend(HistoryBackend):
    def __init__(self):
        super().__init__()
        self.people = {"ou_member": {"id": "ou_member", "name": "示例同事"}}
        self.customers["rec-1"].update(stage="新线索", owner=[self.people["ou_member"]])
        self.schema["customers"].append("operation_id")
        self.profile_mode = "normal"

    def resolve_assignee(self, query):
        return [copy.deepcopy(self.people["ou_member"])] if query == "member@example.com" else []

    def get_assignee(self, user_id):
        return copy.deepcopy(self.people.get(user_id))

    def create_customer(self, fields):
        self.actions.append("create_customer")
        record_id = f"rec-created-{len(self.customers)}"
        self.customers[record_id] = {"record_id": record_id,
                                    "customer_number": f"CRM-{len(self.customers):04d}",
                                    **copy.deepcopy(fields)}
        return record_id

    def find_customer_by_change(self, change_id):
        return next((copy.deepcopy(row) for row in self.customers.values()
                     if row.get("operation_id") == change_id), None)

    def update_customer_profile(self, record_id, fields):
        self.actions.append("update_customer_profile")
        if self.profile_mode == "raise":
            raise OSError("synthetic update failure")
        self.customers[record_id].update(copy.deepcopy(fields))


class CustomerJourneyTests(unittest.TestCase):
    call = host_tools.HostToolTests.call
    bind_card = host_tools.HostToolTests.bind_card

    def setUp(self):
        host_tools.HostToolTests.setUp(self)
        self.backend = CustomerBackend()

    def create_request(self, *, with_followup=True):
        _, person = self.call("assignee", {"query": "member@example.com"})
        self.assertEqual("resolved", person["status"])
        request = {"name": "虚构评测公司", "contact": "示例甲", "stage": "新线索",
                   "owner_ref": person["owner_ref"]}
        if with_followup:
            request["followup"] = {"occurred_at": "2026-09-06T10:00:00+08:00",
                                   "content": "明确要求演示", "next_action": "准备演示"}
        return request

    def execute(self, staged, card_id):
        approval = self.bind_card(staged, card_id)
        _, claimed = self.call("", {**approval, "decision": "approve"}, host_command="host-claim")
        self.assertTrue(claimed["execute"])
        code, completed = self.call("", approval, host_command="host-execute")
        self.assertEqual(0, code, completed)
        return approval, completed

    def test_create_then_followup_each_needs_its_own_approval_and_discussion_is_read_only(self):
        _, parent = self.call("stage-customer-create", self.create_request())
        self.assertEqual("pending", parent["status"], parent)
        self.assertEqual([], self.backend.actions)
        parent_approval, completed = self.execute(parent, "parent-card")
        self.assertEqual("verified", completed["status"], completed)
        self.assertEqual(["create_customer"], self.backend.actions)
        child = completed["next_approval"]
        self.assertEqual("pending", child["status"])
        _, replay = self.call("", parent_approval, host_command="host-execute")
        self.assertNotIn("next_approval", replay)
        _, final = self.execute(child, "child-card")
        self.assertEqual("verified", final["status"], final)
        self.assertEqual(1, len(self.backend.followups))
        self.assertEqual(["create_customer", "create_followup", "update_customer"], self.backend.actions)
        _, result = self.call("result", {"change_id": parent["change_id"]})
        self.assertEqual("verified", result["related_operations"]["child"]["status"])
        row = next(row for row in self.backend.customers.values() if row["name"] == "虚构评测公司")
        before = copy.deepcopy(self.backend.actions)
        _, facts = self.call("customer", {"customer_query": row["customer_number"]})
        self.assertEqual("found", facts["status"])
        self.assertEqual(1, len(facts["history"]))
        self.assertEqual(before, self.backend.actions)

    def test_update_parent_success_and_child_cancellation_remain_separate_after_restart(self):
        request = {"customer_query": "C-001", "changes": {"stage": "沟通中"},
                   "followup": {"occurred_at": "2026-09-06T11:00:00+08:00", "content": "演示完成"}}
        _, parent = self.call("stage-customer-update", request)
        _, completed = self.execute(parent, "profile-card")
        child = completed["next_approval"]
        approval = self.bind_card(child, "cancel-child-card")
        _, cancelled = self.call("", {**approval, "decision": "cancel"}, host_command="host-claim")
        self.assertEqual("cancelled", cancelled["status"])
        self.assertEqual("verified", cancelled["parent_operation"]["status"])
        _, result = self.call("result", {"change_id": child["change_id"]})
        self.assertEqual("verified", result["related_operations"]["parent"]["status"])
        self.assertEqual("cancelled", result["related_operations"]["child"]["status"])
        self.assertEqual("沟通中", self.backend.customers["rec-1"]["stage"])
        self.assertEqual([], list(self.backend.followups))

    def test_parent_without_followup_does_not_generate_another_card(self):
        _, parent = self.call("stage-customer-create", self.create_request(with_followup=False))
        _, completed = self.execute(parent, "only-customer-card")
        self.assertEqual("verified", completed["status"])
        self.assertNotIn("next_approval", completed)
        self.assertEqual(["create_customer"], self.backend.actions)

    def test_child_ttl_starts_after_slow_parent_write_not_at_parent_execution(self):
        clock = [datetime(2026, 9, 6, 3, tzinfo=timezone.utc)]
        create = self.backend.create_customer

        def slow_create(fields):
            clock[0] += timedelta(minutes=4)
            return create(fields)

        with mock.patch.object(core, "_now", side_effect=lambda value: value or clock[0]):
            _, parent = self.call("stage-customer-create", self.create_request())
            with mock.patch.object(self.backend, "create_customer", side_effect=slow_create):
                _, completed = self.execute(parent, "slow-parent-card")
        child_id = completed["next_approval"]["change_id"]
        with closing(core.Ledger(self.path)) as ledger:
            child = ledger.get(child_id)
        self.assertEqual(clock[0] + timedelta(minutes=10),
                         core._parse_time(child["expires_at"], "expires_at"))

    def test_later_user_intent_during_parent_write_prevents_automatic_followup_card(self):
        _, parent = self.call("stage-customer-create", self.create_request())
        create = self.backend.create_customer
        def new_intent_then_create(fields):
            with closing(core.Ledger(self.path)) as ledger:
                ledger.note_write_intent(PRINCIPAL)
            return create(fields)
        with mock.patch.object(self.backend, "create_customer", side_effect=new_intent_then_create):
            _, completed = self.execute(parent, "slow-parent-card")
        self.assertEqual("verified", completed["status"])
        self.assertNotIn("next_approval", completed)
        self.assertEqual("not_published", completed["next_approval_status"])
        self.assertEqual(["create_customer"], self.backend.actions)

    def test_caller_cannot_smuggle_identity_or_record_ids_in_new_commands(self):
        for command, request in (
            ("assignee", {"query": "member@example.com", "profile": "override"}),
            ("stage-customer-create", {"name": "虚构公司", "actor": "other"}),
            ("stage-customer-update", {"customer_query": "C-001", "record_id": "other"}),
            ("stage-customer-update", {"customer_query": "C-001", "changes": {"record_id": "other"}}),
        ):
            with self.subTest(command=command, request=request):
                _, result = self.call(command, request)
                self.assertIn(result["status"], {"blocked", "failed"}, result)
                self.assertEqual([], self.backend.actions)
