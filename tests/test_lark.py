import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from myanc_crm.lark import LarkBackendError, LarkCliBackend


def completed(data=None, *, returncode=0, stderr="", identity="bot"):
    stdout = json.dumps({"ok": True, "identity": identity, "data": data or {}})
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)


def artifact_completed(count):
    stdout = json.dumps(
        {
            "format": "ndjson",
            "record_file": "records.ndjson",
            "records_count": count,
            "has_more": False,
        }
    )
    return subprocess.CompletedProcess([], 0, stdout=stdout, stderr="")


def field(name, kind, field_id, *, primary=None, property=None):
    result = {"name": name, "type": kind, "field_id": field_id}
    if primary is not None:
        result["is_primary"] = primary
    if property is not None:
        result["property"] = property
    return result


CUSTOMER_FIELD_IDS = {
    "name": "fldCustomerName",
    "customer_number": "fldCustomerNumber",
    "contact": "fldCustomerContact",
    "phone": "fldCustomerPhone",
    "email": "fldCustomerEmail",
    "stage": "fldCustomerStage",
    "owner": "fldCustomerOwner",
    "last_followup_at": "fldCustomerLastAt",
    "last_followup_content": "fldCustomerLastContent",
    "next_action": "fldCustomerNextAction",
    "next_followup_at": "fldCustomerNextAt",
    "updated_at": "fldCustomerUpdatedAt",
}

FOLLOWUP_FIELD_IDS = {
    "title": "fldFollowupTitle",
    "change_id": "fldFollowupChangeId",
    "customer_record_id": "fldFollowupCustomer",
    "occurred_at": "fldFollowupOccurredAt",
    "channel": "fldFollowupChannel",
    "content": "fldFollowupContent",
    "next_action": "fldFollowupNextAction",
    "next_followup_at": "fldFollowupNextAt",
    "created_by": "fldFollowupCreatedBy",
    "created_at": "fldFollowupCreatedAt",
}

CUSTOMER_FIELDS = [
    field("客户名称", "text", CUSTOMER_FIELD_IDS["name"], primary=True),
    field("客户编号", "auto_number", CUSTOMER_FIELD_IDS["customer_number"]),
    field("联系人", "text", CUSTOMER_FIELD_IDS["contact"]),
    field("电话", "phone", CUSTOMER_FIELD_IDS["phone"]),
    field("邮箱", "email", CUSTOMER_FIELD_IDS["email"]),
    field("阶段", "single_select", CUSTOMER_FIELD_IDS["stage"]),
    field("负责人", "user", CUSTOMER_FIELD_IDS["owner"]),
    field("最近联系时间", "datetime", CUSTOMER_FIELD_IDS["last_followup_at"]),
    field(
        "最近联系摘要", "text", CUSTOMER_FIELD_IDS["last_followup_content"]
    ),
    field("下一步行动", "text", CUSTOMER_FIELD_IDS["next_action"]),
    field("下次跟进时间", "datetime", CUSTOMER_FIELD_IDS["next_followup_at"]),
    field("更新时间", "modified_time", CUSTOMER_FIELD_IDS["updated_at"]),
]

FOLLOWUP_FIELDS = [
    field("跟进标题", "text", FOLLOWUP_FIELD_IDS["title"], primary=True),
    field("操作 ID", "text", FOLLOWUP_FIELD_IDS["change_id"]),
    field(
        "关联客户",
        "link",
        FOLLOWUP_FIELD_IDS["customer_record_id"],
        property={"table_id": "tblCustomers"},
    ),
    field("沟通时间", "datetime", FOLLOWUP_FIELD_IDS["occurred_at"]),
    field("沟通方式", "select", FOLLOWUP_FIELD_IDS["channel"]),
    field("沟通内容", "text", FOLLOWUP_FIELD_IDS["content"]),
    field("下一步行动", "text", FOLLOWUP_FIELD_IDS["next_action"]),
    field("下次跟进时间", "datetime", FOLLOWUP_FIELD_IDS["next_followup_at"]),
    field("跟进人", "user", FOLLOWUP_FIELD_IDS["created_by"]),
    field("创建时间", "created_time", FOLLOWUP_FIELD_IDS["created_at"]),
]


class LarkCliBackendTests(unittest.TestCase):
    def setUp(self):
        self.backend = LarkCliBackend(
            wrapper_path="/home/claude/ClaudeRemote/lark-enterprise",
            base_token="bascnSecretToken",
            customer_table_id="tblCustomers",
            followup_table_id="tblFollowups",
            base_url="https://example.feishu.cn/base/demo?view=vew1",
            fields={
                "customers": CUSTOMER_FIELD_IDS,
                "followups": FOLLOWUP_FIELD_IDS,
            },
        )

    @patch("myanc_crm.lark.subprocess.run")
    def test_read_schema_validates_both_tables_and_uses_fixed_wrapper(self, run):
        run.side_effect = [
            completed({"items": CUSTOMER_FIELDS}),
            completed({"items": FOLLOWUP_FIELDS}),
        ]

        schema = self.backend.read_schema()

        customer_schema = {item["name"]: item for item in schema["customers"]}
        followup_schema = {item["name"]: item for item in schema["followups"]}
        self.assertEqual(
            customer_schema["客户名称"]["field_id"], CUSTOMER_FIELD_IDS["name"]
        )
        self.assertEqual(followup_schema["跟进标题"]["type"], "text")
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            argv = call.args[0]
            self.assertEqual(argv[0], "/home/claude/ClaudeRemote/lark-enterprise")
            self.assertNotIn("--profile", argv)
            self.assertNotIn("--as", argv)
            self.assertFalse(call.kwargs["shell"])
            self.assertEqual(call.kwargs["timeout"], 30)

    @patch("myanc_crm.lark.subprocess.run")
    def test_schema_mismatch_is_structured(self, run):
        run.side_effect = [
            completed({"items": CUSTOMER_FIELDS[:-1]}),
            completed({"items": FOLLOWUP_FIELDS}),
        ]
        with self.assertRaises(LarkBackendError) as raised:
            self.backend.read_schema()
        self.assertEqual(raised.exception.kind, "schema_mismatch")
        self.assertIn("更新时间", raised.exception.details["missing_fields"])

    @patch("myanc_crm.lark.subprocess.run")
    def test_schema_rejects_field_id_drift(self, run):
        drifted = [dict(item) for item in CUSTOMER_FIELDS]
        drifted[0]["field_id"] = "fldUnexpectedName"
        run.side_effect = [
            completed({"items": drifted}),
            completed({"items": FOLLOWUP_FIELDS}),
        ]

        with self.assertRaises(LarkBackendError) as raised:
            self.backend.read_schema()

        self.assertEqual(raised.exception.kind, "schema_mismatch")
        self.assertIn(
            "客户名称",
            {item["field"] for item in raised.exception.details["mismatched_fields"]},
        )

    @patch("myanc_crm.lark.subprocess.run")
    def test_find_customers_reads_relative_ndjson_and_normalizes(self, run):
        def fake(argv, **kwargs):
            self.assertIn("--format", argv)
            self.assertEqual(argv[argv.index("--output") + 1], "records.ndjson")
            self.assertFalse(Path(argv[argv.index("--output") + 1]).is_absolute())
            Path(kwargs["cwd"], "records.ndjson").write_text(
                json.dumps(
                    {
                        "record_id": "recCustomer1",
                        "客户编号": "CUST-001",
                        "客户名称": "示例客户",
                        "阶段": ["意向"],
                        "负责人": [{"id": "ou_owner", "name": "负责人"}],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            return artifact_completed(1)

        run.side_effect = fake
        rows = self.backend.find_customers("示例客户")
        self.assertEqual(rows[0]["record_id"], "recCustomer1")
        self.assertEqual(rows[0]["customer_number"], "CUST-001")
        self.assertEqual(rows[0]["stage"], "意向")
        argv = run.call_args.args[0]
        search_fields = [
            argv[index + 1]
            for index, value in enumerate(argv)
            if value == "--search-field"
        ]
        self.assertEqual(
            [CUSTOMER_FIELD_IDS["customer_number"], CUSTOMER_FIELD_IDS["name"]],
            search_fields,
        )
        self.assertNotIn("--profile", argv)
        self.assertNotIn("--as", argv)

    @patch("myanc_crm.lark.subprocess.run")
    def test_create_followup_uses_relative_json_file_and_expected_cells(self, run):
        captured = {}

        def fake(argv, **kwargs):
            json_arg = argv[argv.index("--json") + 1]
            self.assertEqual(json_arg, "@payload.json")
            self.assertFalse(Path(json_arg[1:]).is_absolute())
            captured.update(
                json.loads(Path(kwargs["cwd"], json_arg[1:]).read_text(encoding="utf-8"))
            )
            return completed({"record_id_list": ["recFollowup1"]})

        run.side_effect = fake
        record_id = self.backend.create_followup(
            {
                "change_id": "chg_123",
                "customer_record_id": "recCustomer1",
                "customer_number": "CUST-001",
                "occurred_at": "2026-09-03 15:00",
                "content": "确认演示安排",
                "channel": "微信",
                "next_action": "发送演示链接",
                "next_followup_at": "2026-09-07 10:00",
                "created_by": "ou_requester",
            }
        )

        self.assertEqual(record_id, "recFollowup1")
        row = captured["create_records"][0]
        self.assertEqual(row[FOLLOWUP_FIELD_IDS["change_id"]], "chg_123")
        self.assertEqual(
            row[FOLLOWUP_FIELD_IDS["customer_record_id"]],
            [{"id": "recCustomer1"}],
        )
        self.assertEqual(row[FOLLOWUP_FIELD_IDS["channel"]], ["微信"])
        self.assertEqual(
            row[FOLLOWUP_FIELD_IDS["created_by"]], [{"id": "ou_requester"}]
        )
        self.assertEqual(run.call_count, 1)
        self.assertFalse(run.call_args.kwargs["shell"])
        self.assertNotIn("--yes", run.call_args.args[0])

    @patch("myanc_crm.lark.subprocess.run")
    def test_create_followup_allows_missing_channel(self, run):
        captured = {}

        def fake(argv, **kwargs):
            json_arg = argv[argv.index("--json") + 1]
            captured.update(
                json.loads(Path(kwargs["cwd"], json_arg[1:]).read_text(encoding="utf-8"))
            )
            return completed({"record_id_list": ["recFollowup1"]})

        run.side_effect = fake
        self.backend.create_followup(
            {
                "change_id": "chg_124",
                "customer_record_id": "recCustomer1",
                "customer_number": "CUST-001",
                "occurred_at": "2026-09-03T15:00:00+08:00",
                "content": "确认演示安排",
                "created_by": "ou_requester",
            }
        )

        self.assertNotIn(
            FOLLOWUP_FIELD_IDS["channel"], captured["create_records"][0]
        )

    @patch("myanc_crm.lark.subprocess.run")
    def test_update_customer_uses_record_specific_patch(self, run):
        captured = {}

        def fake(argv, **kwargs):
            json_arg = argv[argv.index("--json") + 1]
            captured.update(
                json.loads(Path(kwargs["cwd"], json_arg[1:]).read_text(encoding="utf-8"))
            )
            return completed({})

        run.side_effect = fake
        self.backend.update_customer(
            "recCustomer1",
            {
                "last_followup_at": "2026-09-03 15:00",
                "last_followup_content": "确认演示安排",
                "next_action": None,
            },
        )
        self.assertEqual(
            captured,
            {
                "update_records": {
                    "recCustomer1": {
                        CUSTOMER_FIELD_IDS["last_followup_at"]: "2026-09-03 15:00",
                        CUSTOMER_FIELD_IDS["last_followup_content"]: "确认演示安排",
                        CUSTOMER_FIELD_IDS["next_action"]: None,
                    }
                }
            },
        )
        self.assertEqual(run.call_count, 1)

    @patch("myanc_crm.lark.subprocess.run")
    def test_write_failure_is_not_retried_and_stderr_is_redacted(self, run):
        run.return_value = subprocess.CompletedProcess(
            [],
            1,
            stdout="",
            stderr=json.dumps(
                {
                    "ok": False,
                    "error": {
                        "type": "authorization",
                        "subtype": "missing_scope",
                        "code": 99991679,
                        "message": "token bascnSecretToken was rejected",
                        "hint": "use --profile personal",
                    },
                }
            ),
        )
        with self.assertRaises(LarkBackendError) as raised:
            self.backend.update_customer(
                "recCustomer1", {"last_followup_content": "new"}
            )
        self.assertEqual(run.call_count, 1)
        safe = json.dumps(raised.exception.to_dict(), ensure_ascii=False)
        self.assertNotIn("bascnSecretToken", safe)
        self.assertNotIn("personal", safe)
        self.assertEqual(raised.exception.details["error_type"], "authorization")

    @patch("myanc_crm.lark.subprocess.run")
    def test_ignored_create_fields_fail_without_retry(self, run):
        run.return_value = completed(
            {
                "record_id_list": ["recFollowup1"],
                "ignored_fields": ["fldFollowupContent"],
            }
        )

        with self.assertRaises(LarkBackendError) as raised:
            self.backend.create_followup(
                {
                    "change_id": "chg_123",
                    "customer_record_id": "recCustomer1",
                    "customer_number": "CUST-001",
                    "occurred_at": "2026-09-03T15:00:00+08:00",
                    "content": "确认演示安排",
                    "created_by": "ou_requester",
                }
            )

        self.assertEqual(raised.exception.kind, "ignored_fields")
        self.assertEqual(raised.exception.details, {"count": 1})
        self.assertEqual(run.call_count, 1)

    @patch("myanc_crm.lark.subprocess.run")
    def test_confirmation_exit_is_structured_and_never_retried(self, run):
        run.return_value = subprocess.CompletedProcess(
            [],
            10,
            stdout="",
            stderr=json.dumps(
                {
                    "ok": False,
                    "error": {
                        "type": "confirmation",
                        "subtype": "confirmation_required",
                        "risk": "high-risk-write",
                        "hint": "add --yes",
                    },
                }
            ),
        )
        with self.assertRaises(LarkBackendError) as raised:
            self.backend.create_followup(
                {
                    "change_id": "chg_123",
                    "customer_record_id": "recCustomer1",
                    "customer_number": "CUST-001",
                    "occurred_at": "2026-09-03 15:00",
                    "content": "确认演示安排",
                    "channel": "微信",
                    "created_by": "ou_requester",
                }
            )
        self.assertEqual(raised.exception.kind, "confirmation_required")
        self.assertEqual(run.call_count, 1)

    @patch("myanc_crm.lark.subprocess.run")
    def test_success_requires_exit_zero_ok_true_and_bot_identity(self, run):
        run.return_value = subprocess.CompletedProcess(
            [], 0, stdout=json.dumps({"ok": False, "identity": "bot"}), stderr=""
        )
        with self.assertRaises(LarkBackendError) as raised:
            self.backend.update_customer(
                "recCustomer1", {"last_followup_content": "new"}
            )
        self.assertEqual(raised.exception.kind, "protocol_error")

        run.return_value = completed({}, identity="user")
        with self.assertRaises(LarkBackendError) as raised:
            self.backend.update_customer(
                "recCustomer1", {"last_followup_content": "new"}
            )
        self.assertEqual(raised.exception.kind, "identity_mismatch")

    @patch("myanc_crm.lark.subprocess.run")
    def test_rejects_raw_overrides_before_starting_cli(self, run):
        with self.assertRaises(LarkBackendError):
            self.backend.get_customer("--profile")
        with self.assertRaises(LarkBackendError):
            self.backend.find_customers("--as user")
        with self.assertRaises(LarkBackendError):
            self.backend.update_customer("recCustomer1", {"record_id": "recOther"})
        run.assert_not_called()

    @patch("myanc_crm.lark.subprocess.run")
    def test_read_timeout_is_bounded_and_redacted(self, run):
        run.side_effect = subprocess.TimeoutExpired(
            ["wrapper", "token-secret"], 30, stderr="token-secret"
        )
        with self.assertRaises(LarkBackendError) as raised:
            self.backend.find_customers("示例")
        self.assertEqual(raised.exception.kind, "timeout")
        self.assertNotIn("token-secret", str(raised.exception))
        self.assertEqual(run.call_args.kwargs["timeout"], 30)

    def test_record_links_keep_existing_query_and_validate_ids(self):
        url = self.backend.customer_url("recCustomer1")
        self.assertIn("view=vew1", url)
        self.assertIn("table=tblCustomers", url)
        self.assertIn("record=recCustomer1", url)
        with self.assertRaises(LarkBackendError):
            self.backend.followup_url("../record")

    @patch("myanc_crm.lark.subprocess.run")
    def test_get_followup_normalizes_fixed_id_keys_and_user(self, run):
        def fake(argv, **kwargs):
            Path(kwargs["cwd"], "records.ndjson").write_text(
                json.dumps(
                    {
                        "record_id": "recFollowup1",
                        FOLLOWUP_FIELD_IDS["change_id"]: "chg_123",
                        FOLLOWUP_FIELD_IDS["customer_record_id"]: [
                            {"id": "recCustomer1"}
                        ],
                        FOLLOWUP_FIELD_IDS["occurred_at"]: (
                            "2026-09-03T15:00:00.000+08:00"
                        ),
                        FOLLOWUP_FIELD_IDS["content"]: "确认演示安排",
                        FOLLOWUP_FIELD_IDS["created_by"]: [
                            {"id": "ou_requester", "name": "请求人"}
                        ],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            return artifact_completed(1)

        run.side_effect = fake

        result = self.backend.get_followup("recFollowup1")

        self.assertEqual(result["created_by"], "ou_requester")
        self.assertEqual(result["customer_record_id"], "recCustomer1")
        self.assertEqual(
            result["occurred_at"], "2026-09-03T15:00:00.000+08:00"
        )

    def test_configuration_requires_fixed_absolute_wrapper_and_all_field_ids(self):
        common = {
            "base_token": "bascnSecretToken",
            "customer_table_id": "tblCustomers",
            "followup_table_id": "tblFollowups",
            "base_url": "https://example.feishu.cn/base/demo",
        }
        with self.assertRaises(LarkBackendError):
            LarkCliBackend(
                wrapper_path="lark-enterprise",
                fields={
                    "customers": CUSTOMER_FIELD_IDS,
                    "followups": FOLLOWUP_FIELD_IDS,
                },
                **common,
            )
        with self.assertRaises(LarkBackendError):
            LarkCliBackend(
                wrapper_path="/fixed/lark-enterprise",
                fields={
                    "customers": CUSTOMER_FIELD_IDS,
                    "followups": {**FOLLOWUP_FIELD_IDS, "created_at": "bad"},
                },
                **common,
            )


if __name__ == "__main__":
    unittest.main()
