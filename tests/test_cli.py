import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from myanc_crm import cli


FIELD_IDS = {
    "customers": {
        "name": "fld_customer_name",
        "customer_number": "fld_customer_number",
        "contact": "fld_contact",
        "phone": "fld_phone",
        "email": "fld_email",
        "stage": "fld_stage",
        "owner": "fld_owner",
        "last_followup_at": "fld_last_followup_at",
        "last_followup_content": "fld_last_followup_content",
        "next_action": "fld_next_action",
        "next_followup_at": "fld_next_followup_at",
        "updated_at": "fld_updated_at",
    },
    "followups": {
        "title": "fld_title",
        "change_id": "fld_change_id",
        "customer_record_id": "fld_customer",
        "occurred_at": "fld_occurred_at",
        "channel": "fld_channel",
        "content": "fld_content",
        "next_action": "fld_next_action",
        "next_followup_at": "fld_next_followup_at",
        "created_by": "fld_actor",
        "created_at": "fld_created_at",
    },
}


class CliBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config_path = Path(self.temp.name) / "config.json"
        self.config = {
            "wrapper_path": "/opt/myanc/lark-enterprise",
            "base_token": "base_test",
            "customer_table_id": "tbl_customers",
            "followup_table_id": "tbl_followups",
            "base_url": "https://example.invalid/base/base_test",
            "fields": FIELD_IDS,
            "allowed_actors": {
                "sender-test": {
                    "display_name": "测试 Owner",
                    "feishu_user_id": "ou_test",
                }
            },
            "ttl_seconds": 600,
            "ledger_path": ".crm-state/ledger.sqlite3",
        }
        self.config_path.write_text(
            json.dumps(self.config, ensure_ascii=False), encoding="utf-8"
        )

    def run_cli(self, argv, payload="{}"):
        output = io.StringIO()
        with mock.patch.object(cli, "_config_path", return_value=self.config_path):
            code = cli.main(argv, stdin=io.StringIO(payload), stdout=output)
        lines = output.getvalue().splitlines()
        self.assertEqual(1, len(lines))
        return code, json.loads(lines[0])

    def test_environment_cannot_override_the_protected_config_path(self):
        attacker_path = Path(self.temp.name) / "attacker.json"
        with mock.patch.dict(
            os.environ, {"MYANC_CRM_CONFIG": str(attacker_path)}, clear=False
        ):
            selected = cli._config_path()

        self.assertNotEqual(attacker_path.resolve(), selected)

    def test_only_stage_or_apply_is_accepted_and_no_overrides_exist(self):
        for argv in ([], ["stage", "--profile", "other"], ["--as", "user"]):
            with self.subTest(argv=argv):
                code, result = self.run_cli(argv)
                self.assertEqual(2, code)
                self.assertEqual("usage", result["code"])

    def test_stage_passes_complete_production_field_map_and_resolves_ledger(self):
        sentinel = {"status": "staged", "change_id": "chg_test"}
        with (
            mock.patch("myanc_crm.cli.LarkCliBackend") as backend_type,
            mock.patch("myanc_crm.cli.Ledger") as ledger_type,
            mock.patch("myanc_crm.cli.stage_followup", return_value=sentinel) as stage,
        ):
            code, result = self.run_cli("stage".split(), '{"actor":{}}')

        self.assertEqual(0, code)
        self.assertEqual(sentinel, result)
        backend_type.assert_called_once_with(
            wrapper_path=self.config["wrapper_path"],
            base_token=self.config["base_token"],
            customer_table_id=self.config["customer_table_id"],
            followup_table_id=self.config["followup_table_id"],
            base_url=self.config["base_url"],
            fields=FIELD_IDS,
        )
        self.assertEqual(backend_type.call_args.kwargs["fields"], self.config["fields"])
        self.assertEqual(
            set(backend_type.call_args.kwargs["fields"]["followups"]),
            {
                "title",
                "change_id",
                "customer_record_id",
                "occurred_at",
                "channel",
                "content",
                "next_action",
                "next_followup_at",
                "created_by",
                "created_at",
            },
        )
        ledger_type.assert_called_once_with(
            self.config_path.parent / ".crm-state/ledger.sqlite3"
        )
        stage.assert_called_once()
        ledger_type.return_value.close.assert_called_once_with()

    def test_apply_uses_the_same_json_boundary(self):
        sentinel = {"status": "verified", "change_id": "chg_test"}
        with (
            mock.patch("myanc_crm.cli.LarkCliBackend"),
            mock.patch("myanc_crm.cli.Ledger") as ledger_type,
            mock.patch("myanc_crm.cli.apply_followup", return_value=sentinel) as apply,
        ):
            code, result = self.run_cli(
                ["apply"], '{"actor":{"sender_id":"sender-test"},"change_id":"chg_test"}'
            )

        self.assertEqual(0, code)
        self.assertEqual(sentinel, result)
        apply.assert_called_once()
        ledger_type.return_value.close.assert_called_once_with()

    def test_bad_json_and_bad_config_never_echo_sensitive_input(self):
        secret = "never-print-this-secret"
        code, result = self.run_cli(["stage"], '{"token":"' + secret)
        self.assertEqual(2, code)
        self.assertEqual("blocked", result["status"])
        self.assertNotIn(secret, json.dumps(result))

        self.config_path.write_text('{"app_secret":"' + secret, encoding="utf-8")
        code, result = self.run_cli(["apply"], "{}")
        self.assertEqual(2, code)
        self.assertEqual("failed", result["status"])
        self.assertNotIn(secret, json.dumps(result))


if __name__ == "__main__":
    unittest.main()
