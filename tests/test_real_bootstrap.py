import argparse
import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from ops import bootstrap_base as bootstrap


class RealBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "old-config.json"
        self.output = self.root / "new-config.json"
        self.old_ledger = self.root / "old-ledger.sqlite3"
        self.old_ledger.write_bytes(b"old ledger must remain unchanged")
        self.config = {
            "wrapper_path": "/fixed/crm-writer", "base_token": "oldBase", "base_url": "https://example.feishu.cn/base/old",
            "customer_table_id": "tblOldCustomers", "followup_table_id": "tblOldFollowups",
            "fields": {"customers": {"name": "fldOld"}, "followups": {}},
            "ledger_path": str(self.old_ledger), "host_secret_sha256": "a" * 64,
            "allowed_actors": {"transportOwner": {"display_name": "Owner", "feishu_user_id": "ou_owner"}},
            "ttl_seconds": 600, "identity_summary": {"application_id": "cli_expected"},
        }
        self.source.write_text(json.dumps(self.config), encoding="utf-8")
        self.args = argparse.Namespace(mode="empty-real", lark_cli=str(self.root / "cli"), profile="crm-writer",
            wrapper_path=None, source_config=str(self.source), config_output=str(self.output),
            ledger_path=str(self.root / "new-ledger.sqlite3"), expected_app_id=None,
            confirm_empty_real=False, dry_run=True)

    def test_dry_run_preserves_source_and_creates_nothing_without_subprocesses(self):
        old_source = self.source.read_bytes()
        output = io.StringIO()
        with patch.object(bootstrap, "_run") as run, contextlib.redirect_stdout(output):
            self.assertEqual(0, bootstrap._create_empty_real(self.args, Path(self.args.lark_cli)))
        run.assert_not_called()
        self.assertIn("CRM-", output.getvalue())
        self.assertIn("no customer seeds", output.getvalue())
        self.assertNotIn("cli_expected", output.getvalue())
        self.assertNotIn("ou_owner", output.getvalue())
        self.assertFalse(self.output.exists())
        self.assertFalse(Path(self.args.ledger_path).exists())
        self.assertEqual(old_source, self.source.read_bytes())
        self.assertEqual(b"old ledger must remain unchanged", self.old_ledger.read_bytes())

    def test_real_schema_is_empty_ready_without_mutating_sandbox_schema(self):
        original = copy.deepcopy(bootstrap.CUSTOMER_FIELDS)
        fields = bootstrap._real_customer_fields()
        number = next(row for row in fields if row["name"] == "客户编号")
        self.assertEqual("CRM-", number["style"]["rules"][0]["text"])
        self.assertEqual("text", next(row for row in fields if row["name"] == "建档操作ID")["type"])
        self.assertEqual(original, bootstrap.CUSTOMER_FIELDS)
        self.assertEqual(3, len(bootstrap.SEED_CUSTOMERS))

    def test_explicit_independent_nonexisting_targets_are_required(self):
        with patch.object(bootstrap, "_run") as run:
            for field, value in (("config_output", str(self.source)), ("config_output", str(bootstrap.CONFIG_PATH)),
                                 ("ledger_path", str(self.old_ledger)), ("source_config", "relative.json"),
                                 ("ledger_path", "relative.sqlite3"), ("config_output", None)):
                args = copy.copy(self.args)
                setattr(args, field, value)
                with self.subTest(field=field, value=value), self.assertRaises(bootstrap.BootstrapError):
                    bootstrap._create_empty_real(args, Path(args.lark_cli))
            self.output.write_text("preexisting config", encoding="utf-8")
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap._real_context(self.args)
            self.assertEqual("preexisting config", self.output.read_text(encoding="utf-8"))
            run.assert_not_called()

    def test_source_requires_verified_single_owner_app_and_auth_digest(self):
        for change in ({"_bootstrap_status": "uncertain"}, {"allowed_actors": {}},
                       {"identity_summary": {}}, {"host_secret_sha256": ""}):
            self.source.write_text(json.dumps({**self.config, **change}), encoding="utf-8")
            with self.subTest(change=change), self.assertRaises(bootstrap.BootstrapError):
                bootstrap._real_context(self.args)
        self.source.write_text(json.dumps({**self.config, "identity_summary": {}}), encoding="utf-8")
        self.args.expected_app_id = "cli_explicit"
        config, _, expected = bootstrap._real_context(self.args)
        self.assertEqual("cli_explicit", expected)
        self.assertEqual(self.config["allowed_actors"], config["allowed_actors"])

    def test_execute_requires_confirmation_before_any_identity_or_business_call(self):
        self.args.dry_run = False
        with patch.object(bootstrap, "_run") as run, self.assertRaises(bootstrap.BootstrapError):
            bootstrap._create_empty_real(self.args, Path(self.args.lark_cli))
        run.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_cli_version_check_places_global_profile_before_command(self):
        cli = Path(self.args.lark_cli)
        cli.touch()

        def invoke(argv, **kwargs):
            if "--version" in argv:
                self.assertEqual([str(cli), "--profile", "crm-writer", "--version"], argv)
                return subprocess.CompletedProcess(argv, 0, "lark-cli version 1.0.90\n", "")
            self.assertEqual([str(cli), "--profile", "crm-writer", "whoami", "--as", "bot"], argv)
            return subprocess.CompletedProcess(argv, 0, json.dumps({
                "identity": "bot", "available": True, "appId": "wrong_app"}), "")

        argv = ["bootstrap", "--mode", "empty-real", "--lark-cli", str(cli),
                "--profile", "crm-writer", "--source-config", str(self.source),
                "--config-output", str(self.output), "--ledger-path", self.args.ledger_path,
                "--confirm-empty-real"]
        with patch.object(sys, "argv", argv), patch.object(bootstrap.subprocess, "run", side_effect=invoke) as run:
            with self.assertRaisesRegex(bootstrap.BootstrapError, "not the verified CRM application"):
                bootstrap.main()
        self.assertEqual(2, run.call_count)
        self.assertFalse(self.output.exists())
        self.assertFalse(Path(self.args.ledger_path).exists())

    def fake_run(self, cli, profile, command, label, **kwargs):
        self.calls.append((command, kwargs))
        self.assertNotIn("auth", command)
        self.assertNotEqual("user", kwargs.get("identity"))
        if command == ["--version"]:
            return "lark-cli version 1.0.90\n"
        if command == ["whoami"]:
            return {"identity": "bot", "available": True, "appId": "cli_expected"}
        if command[:2] == ["contact", "+get-user"]:
            return {"ok": True, "identity": "bot", "data": {"user": {"open_id": "ou_owner", "name": "Owner",
                "status": {"is_activated": True, "is_frozen": False, "is_resigned": False}}}}
        action = command[1]
        if action == "+base-create":
            self.assertTrue(self.output.exists())  # checkpoint exists before first remote write
            self.customer_fields = json.loads(command[command.index("--fields") + 1])
            return {"data": {"base_token": "baseNew", "base_url": "https://example.feishu.cn/base/new"}}
        if action == "+base-get":
            return {"data": {"name": "ANC CRM", "base_token": "baseNew"}}
        if action == "+table-list":
            return {"data": {"items": [{"name": "客户", "table_id": "tblCustomers"}]}}
        if action == "+table-create":
            self.followup_fields = json.loads(command[command.index("--fields") + 1])
            return {"data": {"table_id": "tblFollowups"}}
        if action == "+field-list":
            fields = self.customer_fields if command[command.index("--table-id") + 1] == "tblCustomers" else self.followup_fields
            return {"data": {"items": [dict(field, field_id="fld" + str(i)) for i, field in enumerate(fields)]}}
        if action == "+record-list":
            self.assertNotIn("--view-id", command)
            self.assertNotIn("--filter-json", command)
            self.assertEqual("1", command[command.index("--limit") + 1])
            self.assertEqual("ndjson", command[command.index("--format") + 1])
            (kwargs["cwd"] / "empty.ndjson").write_bytes(b"")
            return {"data": {"records_count": 0, "has_more": False}}
        self.fail("Unexpected operation: " + action)

    def test_fake_execute_creates_empty_tables_and_only_new_config_without_seed_or_ledger_copy(self):
        self.args.dry_run = False
        self.args.confirm_empty_real = True
        cli = Path(self.args.lark_cli)
        cli.touch()
        self.calls = []
        old_source = self.source.read_bytes()
        with patch.object(bootstrap, "_run", side_effect=self.fake_run), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, bootstrap._create_empty_real(self.args, cli))
        new = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual("baseNew", new["base_token"])
        self.assertNotIn("_bootstrap_status", new)
        self.assertIn("operation_id", new["fields"]["customers"])
        for key in ("allowed_actors", "host_secret_sha256", "wrapper_path", "identity_summary"):
            self.assertEqual(self.config[key], new[key])
        self.assertEqual(old_source, self.source.read_bytes())
        self.assertFalse(Path(self.args.ledger_path).exists())
        self.assertFalse(any("+record-batch-create" in cmd for cmd, _ in self.calls))

    def test_identity_failure_is_before_new_checkpoint_and_creation(self):
        self.args.dry_run = False
        self.args.confirm_empty_real = True
        cli = Path(self.args.lark_cli)
        cli.touch()
        with patch.object(bootstrap, "_run", side_effect=["lark-cli version 1.0.90", {
                "identity": "bot", "available": True, "appId": "wrong_app"}]) as run:
            with self.assertRaises(bootstrap.BootstrapError):
                bootstrap._create_empty_real(self.args, cli)
        self.assertEqual(2, run.call_count)
        self.assertFalse(self.output.exists())

    def test_parser_defaults_to_original_sandbox_mode(self):
        with patch.object(sys, "argv", ["bootstrap", "--lark-cli", "/fixed/cli", "--profile", "fixture",
                                      "--wrapper-path", "/fixed/writer", "--dry-run"]):
            self.assertEqual("sandbox", bootstrap._parse_args().mode)

    def test_default_sandbox_dry_run_is_unchanged_and_never_calls_feishu(self):
        output = io.StringIO()
        with patch.object(sys, "argv", ["bootstrap", "--lark-cli", str(self.root / "cli"),
                                      "--profile", "fixture", "--wrapper-path", "/fixed/writer", "--dry-run"]), \
                patch.object(bootstrap, "_run") as run, patch.object(bootstrap, "_write_config") as write, \
                contextlib.redirect_stdout(output):
            self.assertEqual(0, bootstrap.main())
        self.assertIn("ANC CRM Sandbox", output.getvalue())
        self.assertIn("seed three fictional customers", output.getvalue())
        run.assert_not_called()
        write.assert_not_called()

    def test_write_config_uses_current_default_not_import_time_path(self):
        target = self.root / "patched-default.json"
        with patch.object(bootstrap, "CONFIG_PATH", target):
            bootstrap._write_config({"fixture": True})
        self.assertEqual({"fixture": True}, json.loads(target.read_text(encoding="utf-8")))

    def test_empty_probe_requires_complete_zero_manifest_and_empty_artifact(self):
        cases = [(0, False, b"", True), (1, False, b"{}\n", False), (0, True, b"", False),
                 (False, False, b"", False), (0, None, b"", False), (0, False, b"{}\n", False),
                 (0, False, None, False)]
        for count, more, content, accepted in cases:
            def probe(*args, **kwargs):
                if content is not None:
                    (kwargs["cwd"] / "empty.ndjson").write_bytes(content)
                return {"data": {"records_count": count, "has_more": more}}
            with self.subTest(count=count, more=more, content=content), \
                    patch.object(bootstrap, "_run", side_effect=probe):
                if accepted:
                    bootstrap._verify_empty_table(Path("/fixed/cli"), "fixture", "baseNew", "tblNew", "fldName")
                else:
                    with self.assertRaises(bootstrap.BootstrapError):
                        bootstrap._verify_empty_table(Path("/fixed/cli"), "fixture", "baseNew", "tblNew", "fldName")

    def test_uncertain_create_retains_checkpoint_and_blocks_blind_retry(self):
        self.args.dry_run = False
        self.args.confirm_empty_real = True
        cli = Path(self.args.lark_cli)
        cli.touch()
        self.calls = []
        def uncertain(*args, **kwargs):
            if args[2][:2] == ["base", "+base-create"]:
                raise bootstrap.BootstrapError("uncertain create")
            return self.fake_run(*args, **kwargs)
        with patch.object(bootstrap, "_run", side_effect=uncertain), self.assertRaises(bootstrap.BootstrapError):
            bootstrap._create_empty_real(self.args, cli)
        self.assertEqual("prepared", json.loads(self.output.read_text(encoding="utf-8"))["_bootstrap_status"])
        with patch.object(bootstrap, "_run") as run, self.assertRaises(bootstrap.BootstrapError):
            bootstrap._create_empty_real(self.args, cli)
        run.assert_not_called()
        self.assertEqual(b"old ledger must remain unchanged", self.old_ledger.read_bytes())


if __name__ == "__main__":
    unittest.main()
