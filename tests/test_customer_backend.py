import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from myanc_crm.lark import (
    LarkBackendError, LarkCliBackend, _CUSTOMER_CANONICAL, _CUSTOMER_SCHEMA,
    _FOLLOWUP_CANONICAL, _FOLLOWUP_SCHEMA,
)


def response(data, identity="bot"):
    return subprocess.CompletedProcess([], 0, json.dumps(
        {"ok": True, "identity": identity, "data": data}), "")


def person(user_id="ou_assignee", **status):
    return {"user": {"open_id": user_id, "name": "示例同事", "status": {
        "is_activated": True, "is_frozen": False, "is_resigned": False, **status}}}


class CustomerBackendTests(unittest.TestCase):
    def setUp(self):
        self.fields = {
            "customers": {key: "fldCustomer" + str(i) for i, key in enumerate(_CUSTOMER_CANONICAL)},
            "followups": {key: "fldFollowup" + str(i) for i, key in enumerate(_FOLLOWUP_CANONICAL)},
        }
        self.legacy = self.backend()
        self.fields["customers"]["operation_id"] = "fldCustomerOperation"
        self.subject = self.backend()
        self.run = patch("myanc_crm.lark.subprocess.run").start()
        self.addCleanup(patch.stopall)

    def backend(self):
        return LarkCliBackend(wrapper_path="/fixed/crm-writer", base_token="baseFixture",
                              customer_table_id="tblCustomers", followup_table_id="tblFollowups",
                              base_url="https://example.feishu.cn/base/fixture", fields=self.fields)

    def capture_write(self, argv, **kwargs):
        self.argv = argv
        self.payload = json.loads(Path(kwargs["cwd"], "payload.json").read_text(encoding="utf-8"))
        return response({"record_id_list": ["recNewCustomer"]})

    def values(self):
        return {"name": "示例公司", "contact": "示例联系人", "stage": "新线索",
                "owner": [{"id": "ou_assignee", "name": "示例同事"}], "operation_id": "chg_create1"}

    def test_create_uses_native_autonumber_and_single_verified_person(self):
        self.run.side_effect = self.capture_write
        self.assertEqual("recNewCustomer", self.subject.create_customer(self.values()))
        cells = self.payload["create_records"][0]
        self.assertEqual([{"id": "ou_assignee"}], cells[self.fields["customers"]["owner"]])
        self.assertEqual(["新线索"], cells[self.fields["customers"]["stage"]])
        self.assertEqual("chg_create1", cells["fldCustomerOperation"])
        self.assertNotIn(self.fields["customers"]["customer_number"], cells)
        self.assertEqual("tblCustomers", self.argv[self.argv.index("--table-id") + 1])
        self.assertNotIn("--as", self.argv)
        self.assertNotIn("--profile", self.argv)
        self.assertEqual(1, self.run.call_count)

    def test_create_allows_phone_or_email_without_contact_but_requires_one(self):
        self.run.side_effect = self.capture_write
        for key, value in (("phone", "13800000000"), ("email", "contact@example.com")):
            values = self.values()
            del values["contact"]
            values[key] = value
            self.subject.create_customer(values)
        values = self.values()
        del values["contact"]
        with self.assertRaises(LarkBackendError):
            self.subject.create_customer(values)
        self.assertEqual(2, self.run.call_count)

    def test_create_rejects_missing_required_and_unconfigured_operation_field(self):
        for key in ("name", "stage", "owner", "operation_id"):
            values = self.values()
            del values[key]
            with self.subTest(key=key), self.assertRaises(LarkBackendError):
                self.subject.create_customer(values)
        with self.assertRaises(LarkBackendError):
            self.legacy.create_customer(self.values())
        with self.assertRaises(LarkBackendError):
            self.legacy.find_customer_by_change("chg_create1")
        self.run.assert_not_called()

    def test_profile_update_keeps_summary_and_history_out_of_payload(self):
        self.run.side_effect = self.capture_write
        self.subject.update_customer_profile("recCustomer", {
            "name": "已确认公司名", "phone": None, "contact": "联系人", "email": "new@example.com",
            "stage": "沟通中", "owner": [{"id": "ou_assignee", "name": "示例同事"}],
        })
        cells = self.payload["update_records"]["recCustomer"]
        self.assertEqual(6, len(cells))
        self.assertIsNone(cells[self.fields["customers"]["phone"]])
        self.assertEqual(["沟通中"], cells[self.fields["customers"]["stage"]])
        for key in ("customer_number", "operation_id", "last_followup_content", "next_action", "record_id"):
            with self.subTest(key=key), self.assertRaises(LarkBackendError):
                self.subject.update_customer_profile("recCustomer", {key: "forbidden"})
        for key in ("name", "contact", "phone", "email", "stage", "owner"):
            with self.subTest(summary_field=key), self.assertRaises(LarkBackendError):
                self.subject.update_customer("recCustomer", {key: "forbidden"})
        self.assertEqual(1, self.run.call_count)

    def test_profile_rejects_unknown_stage_and_invalid_owner_and_empty_name(self):
        for fields in ({"stage": "new-stage"}, {"owner": []}, {"owner": [{"id": "ou_a"}]},
                       {"owner": [{"id": "--as", "name": "A"}]}, {"name": None}, {"name": " "}):
            with self.subTest(fields=fields), self.assertRaises(LarkBackendError):
                self.subject.update_customer_profile("recCustomer", fields)
        self.run.assert_not_called()

    def test_creation_lookup_reads_full_customer_and_checks_exact_id_and_duplicates(self):
        rows = [{"record_id": "recCustomer", "客户名称": "公司", "客户编号": "CRM-0001",
                 "建档操作ID": "chg_create1", "负责人": [{"id": "ou_assignee", "name": "同事"}]}]
        def fake(argv, **kwargs):
            self.assertEqual("fldCustomerOperation", argv[argv.index("--search-field") + 1])
            Path(kwargs["cwd"], "records.ndjson").write_text(
                "\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
            return subprocess.CompletedProcess([], 0, json.dumps({"format": "ndjson",
                "record_file": "records.ndjson", "records_count": len(rows)}), "")
        self.run.side_effect = fake
        found = self.subject.find_customer_by_change("chg_create1")
        self.assertEqual("CRM-0001", found["customer_number"])
        self.assertEqual("chg_create1", found["operation_id"])
        self.assertIsNone(self.subject.find_customer_by_change("chg_other"))
        rows.append(dict(rows[0], record_id="recDuplicate"))
        with self.assertRaises(LarkBackendError) as raised:
            self.subject.find_customer_by_change("chg_create1")
        self.assertEqual("duplicate_change_id", raised.exception.kind)

    def schemas(self):
        customer = [{"name": name, "type": _CUSTOMER_SCHEMA[name],
                     "field_id": self.fields["customers"][key]} for key, name in _CUSTOMER_CANONICAL.items()]
        followup = [{"name": name, "type": _FOLLOWUP_SCHEMA[name],
                     "field_id": self.fields["followups"][key]} for key, name in _FOLLOWUP_CANONICAL.items()]
        return customer, followup

    def test_optional_schema_mapping_preserves_legacy_shape_and_enforces_new_field(self):
        customers, followups = self.schemas()
        self.run.side_effect = [response({"items": customers}), response({"items": followups})]
        before = self.legacy.read_schema()
        customers.append({"name": "建档操作ID", "type": "text", "field_id": "fldCustomerOperation"})
        self.run.side_effect = [response({"items": customers}), response({"items": followups})]
        self.assertEqual(before, self.legacy.read_schema())
        self.run.side_effect = [response({"items": customers}), response({"items": followups})]
        self.assertIn("建档操作ID", {item["name"] for item in self.subject.read_schema()["customers"]})
        for broken in (customers[:-1], customers[:-1] + [dict(customers[-1], type="auto_number")],
                       customers[:-1] + [dict(customers[-1], field_id="fldOther")]):
            self.run.side_effect = [response({"items": broken}), response({"items": followups})]
            with self.assertRaises(LarkBackendError):
                self.subject.read_schema()

    def test_profile_schema_fingerprint_carries_stage_options_only_when_enabled(self):
        customers, followups = self.schemas()
        customers.append({"name": "建档操作ID", "type": "text", "field_id": "fldCustomerOperation"})
        next(row for row in customers if row["name"] == "阶段")["options"] = [{"name": "新线索"}]
        self.run.side_effect = [response({"items": customers}), response({"items": followups})]
        before = self.subject.read_schema()
        next(row for row in customers if row["name"] == "阶段")["options"].append({"name": "意外选项"})
        self.run.side_effect = [response({"items": customers}), response({"items": followups})]
        self.assertNotEqual(before, self.subject.read_schema())

    def test_person_readback_ignores_metadata_only_for_new_config(self):
        owner = [{"id": "ou_assignee", "name": "示例同事", "en_name": "Example", "email": "private@example.com"}]
        row = {"record_id": "recCustomer", "客户名称": "公司", "负责人": owner}
        with patch.object(self.subject, "_read_records", return_value=[row]), \
                patch.object(self.legacy, "_read_records", return_value=[row]):
            self.assertEqual([{"id": "ou_assignee", "name": "示例同事"}],
                             self.subject.get_customer("recCustomer")["owner"])
            self.assertEqual(owner, self.legacy.get_customer("recCustomer")["owner"])
            for bad in ([{"name": "无ID"}], [{"id": "ou_a"}], owner * 2, {"id": "ou_a"}):
                row["负责人"] = bad
                with self.subTest(owner=bad), self.assertRaises(LarkBackendError):
                    self.subject.get_customer("recCustomer")
            row["负责人"] = None
            self.assertEqual([], self.subject.get_customer("recCustomer")["owner"])

    def test_resolve_exact_email_or_mobile_uses_writer_bot_and_get_user(self):
        for query, key, echoed in (("Member@example.com", "email", "member@example.com"),
                                   ("+8613800000000", "mobile", "13800000000")):
            self.run.reset_mock()
            self.run.side_effect = [response({"user_list": [{key: echoed, "user_id": "ou_assignee"}]}),
                                    response(person())]
            self.assertEqual([{"id": "ou_assignee", "name": "示例同事"}], self.subject.resolve_assignee(query))
            argv = self.run.call_args_list[0].args[0]
            self.assertEqual(["/fixed/crm-writer", "api", "POST", "/open-apis/contact/v3/users/batch_get_id"], argv[:4])
            self.assertEqual({"user_id_type": "open_id"}, json.loads(argv[argv.index("--params") + 1]))
            data = json.loads(argv[argv.index("--data") + 1])
            self.assertEqual([echoed], data["emails" if key == "email" else "mobiles"])
            self.assertFalse(data["include_resigned"])
            self.assertNotIn("enterprise_email", data)
            self.assertIn("+get-user", self.run.call_args_list[1].args[0])

    def test_resolver_rejects_names_overrides_wrong_echo_or_identity(self):
        for query in ("张三", "ou_assignee", "--profile general", "member@example.com\n--as user"):
            with self.subTest(query=query), self.assertRaises(LarkBackendError):
                self.subject.resolve_assignee(query)
        self.run.assert_not_called()
        self.run.return_value = response({"user_list": [{"email": "other@example.com", "user_id": "ou_other"}]})
        with self.assertRaises(LarkBackendError):
            self.subject.resolve_assignee("member@example.com")
        self.run.return_value = response({"user_list": []}, identity="user")
        with self.assertRaises(LarkBackendError):
            self.subject.resolve_assignee("member@example.com")

    def test_empty_lookup_is_empty_but_missing_permission_and_unknown_status_are_errors(self):
        self.run.return_value = response({"user_list": []})
        self.assertEqual([], self.subject.resolve_assignee("member@example.com"))
        self.run.return_value = response({"user_list": [{"email": "member@example.com", "user_id": ""}]})
        self.assertEqual([], self.subject.resolve_assignee("member@example.com"))
        self.run.return_value = subprocess.CompletedProcess([], 1, "", json.dumps({"ok": False,
            "error": {"type": "authorization", "subtype": "missing_scope", "message": "private-value"}}))
        with self.assertRaises(LarkBackendError) as raised:
            self.subject.resolve_assignee("member@example.com")
        self.assertNotIn("private-value", str(raised.exception))
        for field in ("is_frozen", "is_resigned"):
            self.run.return_value = response(person(**{field: True}))
            self.assertIsNone(self.subject.get_assignee("ou_assignee"))
        self.run.return_value = response(person(is_activated=False))
        self.assertIsNone(self.subject.get_assignee("ou_assignee"))
        invalid = person()
        del invalid["user"]["status"]
        self.run.return_value = response(invalid)
        with self.assertRaises(LarkBackendError):
            self.subject.get_assignee("ou_assignee")

    def test_write_timeout_or_ignored_fields_never_retries(self):
        self.run.side_effect = subprocess.TimeoutExpired(["redacted"], 30)
        with self.assertRaises(LarkBackendError):
            self.subject.create_customer(self.values())
        self.assertEqual(1, self.run.call_count)
        self.run.side_effect = None
        self.run.return_value = response({"record_id_list": ["recCustomer"], "ignored_fields": ["field"]})
        with self.assertRaises(LarkBackendError):
            self.subject.create_customer(self.values())
        self.assertEqual(2, self.run.call_count)


if __name__ == "__main__":
    unittest.main()
