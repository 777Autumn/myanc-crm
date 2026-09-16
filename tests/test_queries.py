"""Business query defaults, identity and stable continuation boundaries."""

import unittest
from datetime import datetime, timezone

from myanc_crm import core, queries
from test_core import PRINCIPAL, customer


class QueryBackend:
    def __init__(self):
        self.calls = []
        self.person = {"id": "ou_other", "name": "已核验同事"}
        self.page = {"items": [customer()], "has_more": True}

    def list_customers(self, **kwargs):
        self.calls.append(kwargs)
        return self.page

    def get_assignee(self, identifier):
        return self.person if identifier == self.person["id"] else None

    def read_customer_history_page(self, record_id, **kwargs):
        self.calls.append((record_id, kwargs))
        return self.page


class BusinessQueryTests(unittest.TestCase):
    def setUp(self):
        self.backend = QueryBackend()
        self.ledger = core.Ledger()
        self.addCleanup(self.ledger.close)
        self.config = {"allowed_actors": {"sender-1": {"display_name": "本人", "feishu_user_id": "ou_self"}}}
        self.now = datetime(2026, 9, 16, 15, 59, tzinfo=timezone.utc)

    def call(self, request, **kwargs):
        return queries.customers(request, self.backend, self.ledger, self.config,
                                 kwargs.get("principal", PRINCIPAL), kwargs.get("now", self.now))

    def test_today_includes_overdue_and_next_page_keeps_first_day_across_midnight(self):
        first = self.call({"due": "today", "keyword": "客户", "stages": ["已成交", "暂缓"]})
        self.assertEqual("found", first["status"])
        self.assertTrue(first["has_more"])
        self.assertEqual("ou_self", self.backend.calls[-1]["owner_id"])
        self.assertIsNone(self.backend.calls[-1]["date_from"])
        self.assertEqual("2026-09-17T00:00:00+08:00", self.backend.calls[-1]["date_to"])
        later = datetime(2026, 9, 17, 2, tzinfo=timezone.utc)
        second = self.call(first["next_request"], now=later)
        self.assertEqual(first["query"]["date_to"], second["query"]["date_to"])
        self.assertEqual(1, self.backend.calls[-1]["offset"])
        self.assertEqual(20, self.backend.calls[-1]["limit"])

    def test_date_range_is_inclusive_by_beijing_calendar_and_overdue_freezes_now(self):
        self.call({"owner": "all", "date_from": "2026-09-01", "date_to": "2026-09-16"})
        call = self.backend.calls[-1]
        self.assertIsNone(call["owner_id"])
        self.assertEqual("2026-09-01T00:00:00+08:00", call["date_from"])
        self.assertEqual("2026-09-17T00:00:00+08:00", call["date_to"])
        self.call({"due": "overdue"})
        self.assertEqual("2026-09-16T23:59:00+08:00", self.backend.calls[-1]["date_to"])
        self.call({"due": "unscheduled"})
        self.assertTrue(self.backend.calls[-1]["unscheduled"])

    def test_owner_ref_requires_same_principal_and_fresh_person(self):
        ref = self.ledger.remember_assignee(PRINCIPAL, self.backend.person)
        self.assertEqual("found", self.call({"owner_ref": ref})["status"])
        self.assertEqual("ou_other", self.backend.calls[-1]["owner_id"])
        self.assertEqual("blocked", self.call({"owner_ref": ref}, principal={**PRINCIPAL, "chat_id": "another"})["status"])
        self.backend.person = {**self.backend.person, "name": "变更名称"}
        self.assertEqual("blocked", self.call({"owner_ref": ref})["status"])

    def test_invalid_or_forged_scope_is_rejected_before_query(self):
        requests = ({"owner_id": "ou_other"}, {"actor": "someone"}, {"owner": "other"},
                    {"owner": "all", "owner_ref": "ref"}, {"offset": True}, {"offset": -1},
                    {"stages": ["新阶段"]}, {"due": "today", "offset": 20},
                    {"due": "unscheduled", "date_to": "2026-09-17"},
                    {"date_from": "2026-09-20", "date_to": "2026-09-19"},
                    {"date_from": "2026-09-16T10:00:00"})
        for request in requests:
            with self.subTest(request=request):
                self.assertEqual("blocked", self.call(request)["status"])
        self.assertEqual([], self.backend.calls)
        self.assertEqual("blocked", self.call({}, principal={**PRINCIPAL, "user_id": "stranger"})["status"])

    def test_malformed_or_failed_page_never_claims_empty_result(self):
        for page in ({"items": [], "has_more": True}, {"items": [], "has_more": "false"},
                     {"items": [customer()] * 21, "has_more": False}, {"items": [{}], "has_more": False}):
            self.backend.page = page
            self.assertEqual("unavailable", self.call({})["status"])

    def test_history_is_bounded_and_cross_customer_page_rejected(self):
        self.backend.page = {"items": [{"record_id": "recHistory", "customer_record_id": "rec-1",
                                        "occurred_at": "2026-09-16T09:00:00+08:00", "content": "沟通"}], "has_more": True}
        page = queries.customer_history("rec-1", self.backend, 10)
        self.assertEqual("available", page["history_status"])
        self.assertTrue(page["truncated"])
        self.assertEqual(11, page["next_offset"])
        self.assertEqual(("rec-1", {"offset": 10, "limit": 10}), self.backend.calls[-1])
        self.backend.page["items"][0]["customer_record_id"] = "other"
        self.assertIsNone(queries.customer_history("rec-1", self.backend)["history"])


if __name__ == "__main__":
    unittest.main()
