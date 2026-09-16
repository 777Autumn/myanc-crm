"""Exercise native query arguments and artifact pagination without Feishu."""

import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from myanc_crm.lark import LarkBackendError, LarkCliBackend
from test_lark import CUSTOMER_FIELD_IDS, FOLLOWUP_FIELD_IDS, CUSTOMER_FIELDS, FOLLOWUP_FIELDS, completed


class QueryAdapterTests(unittest.TestCase):
    def setUp(self):
        self.backend = LarkCliBackend(wrapper_path="/fixed/writer", base_token="baseFixture",
            customer_table_id="tblCustomers", followup_table_id="tblFollowups",
            base_url="https://example.feishu.cn/base/fixture",
            fields={"customers": CUSTOMER_FIELD_IDS, "followups": FOLLOWUP_FIELD_IDS})
        self.rows = [{"record_id": "recCustomer1", "客户编号": "CRM-0001", "客户名称": "示例"}]
        self.manifest = {"format": "ndjson", "record_file": "records.ndjson", "records_count": 1, "has_more": True}
        self.paginate = False
        self.run = patch("myanc_crm.lark.subprocess.run", side_effect=self.fake).start()
        self.addCleanup(patch.stopall)

    def fake(self, argv, **kwargs):
        if "+field-list" in argv:
            fields = FOLLOWUP_FIELDS if "tblFollowups" in argv else CUSTOMER_FIELDS
            return completed({"items": fields})
        self.argv = argv
        rows, manifest = self.rows, self.manifest
        if self.paginate:
            offset, limit = int(self.value("--offset")), int(self.value("--limit"))
            rows = rows[offset:offset + limit]
            manifest = {**manifest, "records_count": len(rows), "has_more": offset + limit < len(self.rows)}
        Path(kwargs["cwd"], "records.ndjson").write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
        return subprocess.CompletedProcess([], 0, json.dumps(manifest), "")

    def value(self, flag):
        return self.argv[self.argv.index(flag) + 1]

    def test_keyword_filters_and_pagination_use_native_single_page(self):
        page = self.backend.list_customers(keyword="示例", owner_id="ou_owner", stages=["沟通中"],
            date_from="2026-09-16T00:00:00+08:00", date_to="2026-09-17T00:00:00+08:00", offset=20)
        self.assertTrue(page["has_more"])
        self.assertEqual("CRM-0001", page["items"][0]["customer_number"])
        self.assertIn("+record-search", self.argv)
        self.assertEqual("20", self.value("--offset"))
        self.assertEqual("20", self.value("--limit"))
        fields = [self.argv[i + 1] for i, value in enumerate(self.argv) if value == "--search-field"]
        self.assertEqual([CUSTOMER_FIELD_IDS[key] for key in ("name", "customer_number", "contact", "phone", "email")], fields)
        self.assertEqual({"logic": "and", "conditions": [
            ["负责人", "intersects", [{"id": "ou_owner"}]], ["阶段", "intersects", ["沟通中"]],
            ["下次跟进时间", "non_empty"],
            ["下次跟进时间", ">", "ExactDate(2026-09-15T23:59:59.999+08:00)"],
            ["下次跟进时间", "<", "ExactDate(2026-09-17T00:00:00.000+08:00)"]]}, json.loads(self.value("--filter-json")))
        self.assertEqual([{"field": "下次跟进时间", "desc": False}, {"field": "客户编号", "desc": False}],
                         json.loads(self.value("--sort-json")))

    def test_unscheduled_query_and_invalid_boundaries(self):
        self.backend.list_customers(unscheduled=True)
        self.assertIn("+record-list", self.argv)
        self.assertEqual([["下次跟进时间", "empty"]], json.loads(self.value("--filter-json"))["conditions"])
        self.assertEqual([{"field": "客户编号", "desc": False}], json.loads(self.value("--sort-json")))
        self.run.reset_mock()
        for kwargs in ({"offset": True}, {"limit": 21}, {"offset": -1}, {"owner_id": "other"},
                       {"stages": ["不存在"]}, {"unscheduled": True, "date_to": "2026-09-17T00:00:00+08:00"}):
            with self.subTest(kwargs=kwargs), self.assertRaises((LarkBackendError, ValueError)):
                self.backend.list_customers(**kwargs)
        self.run.assert_not_called()

    def test_default_customer_sort_is_followup_time_then_unique_number(self):
        self.backend.list_customers()
        self.assertEqual([{"field": "下次跟进时间", "desc": False}, {"field": "客户编号", "desc": False}],
                         json.loads(self.value("--sort-json")))

    def test_exact_number_uses_numeric_filter_and_checks_whole_identifier(self):
        self.manifest["has_more"] = False
        for number in ("CRM-0001", "ANC-001", "C-001"):
            self.rows[0]["客户编号"] = number
            self.assertEqual(1, len(self.backend.find_customers_by_number(number.lower())))
            self.assertIn("+record-list", self.argv)
            self.assertEqual([["客户编号", "==", 1]], json.loads(self.value("--filter-json"))["conditions"])
            self.assertEqual("2", self.value("--limit"))
        self.assertEqual([], self.backend.find_customers_by_number("WRONG-001"))
        self.manifest["has_more"] = True
        with self.assertRaises(LarkBackendError):
            self.backend.find_customers_by_number("C-001")
        self.backend.find_customers("C-001")
        self.assertIn("+record-search", self.argv)

    @staticmethod
    def history_row(index, occurred_at="2026-09-16T09:00:00+08:00"):
        return {"record_id": f"recFollowup{index:04}", "关联客户": [{"id": "recCustomer1"}],
                "沟通时间": occurred_at, "操作 ID": "duplicate" if index % 2 else None}

    def test_history_pages_sort_complete_data_by_timestamp_then_real_record_id(self):
        # Operation IDs are deliberately blank/duplicate, and equivalent instants
        # use different offsets so neither field nor timestamp text defines order.
        self.rows = [self.history_row(i, "2026-09-16T01:00:00Z" if i % 2 else "2026-09-16T09:00:00+08:00")
                     for i in reversed(range(23))]
        self.rows.append(self.history_row(23, "2026-09-17T09:00:00+08:00"))
        self.paginate = True
        page = self.backend.read_customer_history_page("recCustomer1", offset=10)
        self.assertTrue(page["has_more"])
        self.assertEqual([f"recFollowup{i:04}" for i in range(9, 19)], [row["record_id"] for row in page["items"]])
        self.assertEqual("0", self.value("--offset"))
        self.assertEqual("2000", self.value("--limit"))
        self.assertNotIn("--sort-json", self.argv)
        first = self.backend.read_customer_history_page("recCustomer1")
        self.assertEqual("recFollowup0023", first["items"][0]["record_id"])
        last = self.backend.read_customer_history_page("recCustomer1", offset=20)
        self.assertFalse(last["has_more"])
        self.assertEqual([f"recFollowup{i:04}" for i in range(19, 23)], [row["record_id"] for row in last["items"]])

    def test_history_reads_past_cli_2000_limit_without_scanning_other_customers(self):
        self.rows = [self.history_row(i) for i in reversed(range(2001))]
        self.paginate = True
        page = self.backend.read_customer_history_page("recCustomer1", offset=1990)
        self.assertEqual(10, len(page["items"]))
        self.assertTrue(page["has_more"])
        commands = [call.args[0] for call in self.run.call_args_list if "+record-list" in call.args[0]]
        self.assertEqual(["0", "2000"], [args[args.index("--offset") + 1] for args in commands])
        for args in commands:
            self.assertEqual([["关联客户", "intersects", [{"id": "recCustomer1"}]]],
                             json.loads(args[args.index("--filter-json") + 1])["conditions"])
        last = self.backend.read_customer_history_page("recCustomer1", offset=2000)
        self.assertEqual(["recFollowup2000"], [row["record_id"] for row in last["items"]])
        self.assertFalse(last["has_more"])

    def test_history_rejects_incomplete_or_corrupt_collection(self):
        good = self.history_row(1)
        cases = [([], True), ([good, good], False),
                 ([{**good, "关联客户": [{"id": "recOther"}]}], False),
                 ([{**good, "record_id": ""}], False), ([{**good, "沟通时间": None}], False)]
        for rows, more in cases:
            self.rows = rows
            self.manifest.update(records_count=len(rows), has_more=more)
            with self.subTest(rows=rows, more=more), self.assertRaises(LarkBackendError) as caught:
                self.backend.read_customer_history_page("recCustomer1")
            self.assertEqual("protocol_error", caught.exception.kind)

    def test_history_later_page_failure_never_returns_partial_page(self):
        self.rows = [self.history_row(1)]
        def fail_later(argv, **kwargs):
            if "--offset" in argv and argv[argv.index("--offset") + 1] != "0":
                raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
            return self.fake(argv, **kwargs)
        self.run.side_effect = fail_later
        with self.assertRaises(LarkBackendError) as caught:
            self.backend.read_customer_history_page("recCustomer1")
        self.assertEqual("timeout", caught.exception.kind)

    def test_history_entire_collection_has_one_time_budget(self):
        self.rows = [self.history_row(1)]
        with patch("myanc_crm.lark.time.monotonic", side_effect=[0, 1, 31]):
            with self.assertRaises(LarkBackendError) as caught:
                self.backend.read_customer_history_page("recCustomer1")
        self.assertEqual("timeout", caught.exception.kind)
        self.assertEqual(2, self.run.call_count)  # Schema and first chunk only.
        self.assertEqual(29, self.run.call_args.kwargs["timeout"])

    def test_invalid_manifest_cannot_look_like_last_page(self):
        for changes in ({"has_more": "false"}, {"records_count": 0}, {"records_count": True}):
            self.manifest.update(has_more=False, records_count=1)
            self.manifest.update(changes)
            with self.subTest(changes=changes), self.assertRaises(LarkBackendError):
                self.backend.list_customers()
        self.manifest.pop("has_more")
        self.manifest["records_count"] = 1
        with self.assertRaises(LarkBackendError):
            self.backend.list_customers()


if __name__ == "__main__":
    unittest.main()
