import hashlib
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
        self.ledger_path = Path(self.temp.name) / "state" / "ledger.sqlite3"
        self.action_token = "session-action-token-000000000001"
        self.host_secret = "gateway-host-secret-0000000000000001"
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
            "ledger_path": str(self.ledger_path),
            "host_secret_sha256": hashlib.sha256(
                self.host_secret.encode("utf-8")
            ).hexdigest(),
        }
        self.config_path.write_text(
            json.dumps(self.config, ensure_ascii=False), encoding="utf-8"
        )

    def run_cli(self, argv, payload="{}", *, host=False):
        output = io.StringIO()
        environment = {cli.ACTION_TOKEN_ENV: self.action_token}
        if host:
            environment[cli.HOST_SECRET_ENV] = self.host_secret
        with (
            mock.patch.object(cli, "_config_path", return_value=self.config_path),
            mock.patch.dict(os.environ, environment, clear=True),
        ):
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

    def test_open_returns_current_configured_link_without_backend_or_ledger(self):
        principal = dict(platform="feishu", user_id="sender-test", chat_id="chat-test",
                         session_key="session-test", project="project-test", message_id="message-test")
        payload = {"command": "open", "request": {}, "principal": principal}
        with mock.patch.object(cli, "_runtime") as runtime:
            for base in ("sandbox_fixture", "real_fixture"):
                url = f"https://example.invalid/base/{base}"
                self.config["base_url"] = url
                self.config_path.write_text(json.dumps(self.config), encoding="utf-8")
                code, result = self.run_cli(["host-tool"], json.dumps(payload), host=True)
                self.assertEqual((0, "available", url, "base", "mine"),
                                 (code, result["status"], result["url"], result["target"], result["requested_target"]))
                self.assertIn("不是个人视图", result["message"])
            runtime.assert_not_called()
        self.assertFalse(self.ledger_path.exists())

    def test_open_selects_trusted_owner_and_environment_without_crm_io(self):
        principal = dict(platform="feishu", user_id="sender-test", chat_id="chat-test",
                         session_key="session-test", project="project-test", message_id="message-test")
        with mock.patch.object(cli, "_runtime") as runtime:
            for environment in ("sandbox", "real"):
                self.config.update(base_token=environment, base_url=f"https://example.invalid/base/{environment}?record=old&view=old#old")
                owners = {f"ou_{name}": f"vew{environment}{name}" for name in ("test", "owner", "partner")}
                self.config["workbench_views"] = dict(base_token=environment, customer_table_id="tbl_customers",
                                                     owners=owners, team="vewTeam", stages="vewStages", overview="blkOverview")
                self.config["allowed_actors"] = {f"sender-{name}": dict(display_name=name, feishu_user_id=f"ou_{name}")
                                                  for name in ("test", "owner", "partner")}
                self.config_path.write_text(json.dumps(self.config), encoding="utf-8")
                for name in ("test", "owner", "partner"):
                    for chat in ("private", "group"):
                        for request, target, view in (({}, "mine", owners[f"ou_{name}"]),
                                                     ({"target": "mine"}, "mine", owners[f"ou_{name}"]),
                                                     ({"target": "team"}, "team", "vewTeam"),
                                                     ({"target": "stages"}, "stages", "vewStages"),
                                                     ({"target": "overview"}, "overview", "blkOverview")):
                            code, result = self.run_cli(["host-tool"], json.dumps({"command": "open", "request": request,
                                "principal": {**principal, "user_id": f"sender-{name}", "chat_id": chat}}), host=True)
                            query = f"table={view}" if target == "overview" else f"table=tbl_customers&view={view}"
                            self.assertEqual((0, target, f"https://example.invalid/base/{environment}?{query}"),
                                             (code, result["target"], result["url"]))
            runtime.assert_not_called()
        self.assertFalse(self.ledger_path.exists())

    def test_open_missing_mapping_falls_back_but_invalid_config_and_targets_fail_closed(self):
        import copy
        principal = dict(platform="feishu", user_id="sender-test", chat_id="chat-test",
                         session_key="session-test", project="project-test", message_id="message-test")
        views = dict(base_token="base_test", customer_table_id="tbl_customers", owners={})
        self.config["workbench_views"] = views
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")
        for target in ("mine", "team", "stages", "overview"):
            code, result = self.run_cli(["host-tool"], json.dumps({"command": "open", "request": {"target": target}, "principal": principal}), host=True)
            self.assertEqual((0, "base", self.config["base_url"]), (code, result["target"], result["url"]))
        good = copy.deepcopy(self.config)
        invalid_configs = [
            {**views, "base_token": "another_base"}, {**views, "customer_table_id": "another_table"},
            {**views, "owners": []}, {**views, "owners": {"ou_test": "https://other.invalid"}},
            {**views, "team": "vewTeam&record=other"}, {**views, "stages": None},
            *({**views, "overview": value} for value in
              (None, "", [], 123, "vewNotDashboard", "blk", "blkOverview&table=other",
               "https://other.invalid/base/another?table=blkOverview")),
            {**views, "url": "https://other.invalid"}, [],
        ]
        with mock.patch.object(cli, "_runtime") as runtime:
            for config, request in [(good, {"target": value}) for value in ("all", "", None, [], {}, 1)] + [
                ({**good, "workbench_views": value}, {"target": target})
                for value in invalid_configs for target in ("mine", "overview")
            ] + [({**good, "base_url": "https://example.invalid/base/different"}, {"target": "overview"})]:
                self.config_path.write_text(json.dumps(config), encoding="utf-8")
                code, result = self.run_cli(["host-tool"], json.dumps({"command": "open", "request": request, "principal": principal}), host=True)
                self.assertEqual((2, "invalid_local_input"), (code, result["code"]))
                self.assertNotIn("url", result)
            runtime.assert_not_called()

    def test_open_rejects_overrides_and_unauthorized_callers_before_runtime(self):
        principal = dict(platform="feishu", user_id="sender-test", chat_id="chat-test",
                         session_key="session-test", project="project-test", message_id="message-test")
        with mock.patch.object(cli, "_runtime") as runtime:
            for field in ("url", "base_url", "base_token", "project", "actor", "customer_query"):
                payload = {"command": "open", "request": {field: "other"}, "principal": principal}
                code, result = self.run_cli(["host-tool"], json.dumps(payload), host=True)
                self.assertEqual((2, "invalid_local_input"), (code, result["code"]))
            for actor, host in (("sender-test", False), ("unknown", True)):
                payload = {"command": "open", "request": {}, "principal": {**principal, "user_id": actor}}
                code, result = self.run_cli(["host-tool"], json.dumps(payload), host=host)
                self.assertEqual((2, "invalid_local_input"), (code, result["code"]))
            runtime.assert_not_called()

    def test_open_invalid_config_does_not_return_a_link(self):
        principal = dict(platform="feishu", user_id="sender-test", chat_id="chat-test",
                         session_key="session-test", project="project-test", message_id="message-test")
        for url in ("", "javascript:alert(1)", "http://example.invalid/base/test"):
            self.config["base_url"] = url
            self.config_path.write_text(json.dumps(self.config), encoding="utf-8")
            code, result = self.run_cli(["host-tool"], json.dumps(
                {"command": "open", "request": {}, "principal": principal}), host=True)
            self.assertEqual((2, "invalid_local_input"), (code, result["code"]))
            self.assertNotIn("url", result)

    def test_only_fixed_commands_are_accepted_and_no_overrides_exist(self):
        for argv in ([], ["stage", "--profile", "other"], ["--as", "user"]):
            with self.subTest(argv=argv):
                code, result = self.run_cli(argv)
                self.assertEqual(2, code)
                self.assertEqual("usage", result["code"])

    def test_host_prepare_stages_then_binds_with_one_authenticated_token(self):
        staged = {"status": "staged", "change_id": "chg_test"}
        pending = {"status": "pending", "approval_id": "apr_test"}
        principal = {
            "platform": "feishu",
            "user_id": "sender-test",
            "chat_id": "chat-test",
            "session_key": "session-test",
            "project": "project-test",
            "message_id": "message-test",
        }
        request = {"customer_query": "C-001", "content": "test"}
        with (
            mock.patch("myanc_crm.cli.LarkCliBackend") as backend_type,
            mock.patch("myanc_crm.cli.Ledger") as ledger_type,
            mock.patch("myanc_crm.cli.stage_followup", return_value=staged) as stage,
            mock.patch("myanc_crm.cli.begin_approval", return_value=pending) as begin,
        ):
            code, result = self.run_cli(
                ["host-prepare"],
                json.dumps({"request": request, "principal": principal}),
                host=True,
            )

        self.assertEqual(0, code)
        self.assertEqual(pending, result)
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
        ledger_type.assert_called_once_with(self.ledger_path.resolve())
        stage.assert_called_once_with(
            request,
            backend_type.return_value,
            ledger_type.return_value,
            self.config,
            self.action_token,
            trusted_principal=principal,
        )
        begin.assert_called_once_with(
            {"change_id": "chg_test", "principal": principal},
            backend_type.return_value,
            ledger_type.return_value,
            self.config,
            self.action_token,
        )
        ledger_type.return_value.close.assert_called_once_with()

    def test_host_prepare_returns_only_canonical_non_pending_results_without_binding(self):
        payload = {
            "request": {"customer_query": "C-001", "content": "test"},
            "principal": {
                "platform": "feishu",
                "user_id": "sender-test",
                "chat_id": "chat-test",
                "session_key": "session-test",
                "project": "project-test",
                "message_id": "message-test",
            },
        }
        canonical_results = (
            {
                "status": "needs_time",
                "code": "followup_time_required",
                "message": "Ask for the follow-up time before staging; Feishu is unchanged.",
            },
            {
                "status": "needs_selection",
                "code": "customer_ambiguous",
                "candidates": [{"name": "<CRM_DATA>Example</CRM_DATA>"}],
                "message": "Choose one customer.",
            },
            {
                "status": "not_found",
                "code": "customer_not_found",
                "customer_query": "C-001",
                "message": "No customer matched.",
            },
            {
                "status": "blocked",
                "code": "backend_read_failed",
                "message": "CRM could not be read; nothing was staged.",
            },
        )
        for canonical in canonical_results:
            with (
                self.subTest(status=canonical["status"]),
                mock.patch("myanc_crm.cli.LarkCliBackend"),
                mock.patch("myanc_crm.cli.Ledger") as ledger_type,
                mock.patch("myanc_crm.cli.stage_followup", return_value=canonical),
                mock.patch("myanc_crm.cli.begin_approval") as begin,
            ):
                code, result = self.run_cli(
                    ["host-prepare"], json.dumps(payload), host=True
                )

                self.assertEqual(0, code)
                self.assertEqual(canonical, result)
                self.assertNotIn("principal", result)
                self.assertNotIn("action_token", result)
                begin.assert_not_called()
                ledger_type.return_value.close.assert_called_once_with()

    def test_host_prepare_fails_closed_on_an_unknown_stage_status(self):
        payload = {
            "request": {"customer_query": "C-001", "content": "test"},
            "principal": {
                "platform": "feishu",
                "user_id": "sender-test",
                "chat_id": "chat-test",
                "session_key": "session-test",
                "project": "project-test",
                "message_id": "message-test",
            },
        }
        unexpected = {"status": "debug", "internal": "do-not-render"}
        with (
            mock.patch("myanc_crm.cli.LarkCliBackend"),
            mock.patch("myanc_crm.cli.Ledger"),
            mock.patch("myanc_crm.cli.stage_followup", return_value=unexpected),
            mock.patch("myanc_crm.cli.begin_approval") as begin,
        ):
            code, result = self.run_cli(
                ["host-prepare"], json.dumps(payload), host=True
            )

        self.assertEqual(0, code)
        self.assertEqual(("failed", "invalid_stage_result"), (result["status"], result["code"]))
        self.assertNotIn("internal", result)
        begin.assert_not_called()

    def test_host_prepare_rejects_untrusted_shapes_before_constructing_runtime(self):
        principal = {
            "platform": "feishu",
            "user_id": "sender-test",
            "chat_id": "chat-test",
            "session_key": "session-test",
            "project": "project-test",
            "message_id": "message-test",
        }
        payloads = (
            {"request": {}, "principal": principal, "change_id": "chg_attacker"},
            {
                "request": {"customer_query": "C-001", "actor": "attacker"},
                "principal": principal,
            },
            {"request": {}, "principal": {**principal, "profile": "attacker"}},
            {"request": {}, "principal": {**principal, "user_id": "unknown"}},
        )
        for payload in payloads:
            with (
                self.subTest(payload=payload),
                mock.patch("myanc_crm.cli.LarkCliBackend") as backend_type,
                mock.patch("myanc_crm.cli.Ledger") as ledger_type,
            ):
                code, result = self.run_cli(
                    ["host-prepare"], json.dumps(payload), host=True
                )
                self.assertEqual(2, code)
                self.assertEqual(
                    ("failed", "invalid_local_input"),
                    (result["status"], result["code"]),
                )
                backend_type.assert_not_called()
                ledger_type.assert_not_called()

    def test_runtime_rejects_relative_or_working_directory_ledger(self):
        for ledger_path in (
            ".crm-state/ledger.sqlite3",
            str(Path.cwd() / ".crm-state" / "ledger.sqlite3"),
        ):
            with self.subTest(ledger_path=ledger_path):
                self.config["ledger_path"] = ledger_path
                self.config_path.write_text(
                    json.dumps(self.config, ensure_ascii=False), encoding="utf-8"
                )
                code, result = self.run_cli(
                    ["host-prepare"],
                    json.dumps(
                        {
                            "request": {"customer_query": "C-001"},
                            "principal": {
                                "platform": "feishu",
                                "user_id": "sender-test",
                                "chat_id": "chat-test",
                                "session_key": "session-test",
                                "project": "project-test",
                                "message_id": "message-test",
                            },
                        }
                    ),
                    host=True,
                )
                self.assertEqual(2, code)
                self.assertEqual(
                    ("failed", "invalid_local_input"),
                    (result["status"], result["code"]),
                )

    def test_public_stage_and_apply_are_blocked_before_config_or_stdin_is_read(self):
        self.config_path.unlink()
        code, result = self.run_cli(["stage"], "not json and never parsed")
        self.assertEqual(0, code)
        self.assertEqual(
            ("blocked", "host_prepare_required"),
            (result["status"], result["code"]),
        )

        code, result = self.run_cli(["apply"], "not json and never parsed")
        self.assertEqual(0, code)
        self.assertEqual(
            ("blocked", "host_approval_required"),
            (result["status"], result["code"]),
        )

    def test_request_approval_marker_is_exact_harmless_and_needs_no_configuration(self):
        self.config_path.unlink()
        code, result = self.run_cli(["request-approval"], "not json")
        self.assertEqual(0, code)
        self.assertEqual("handoff_only", result["status"])
        self.assertNotIn("change_id", result)

        for argv in (
            ["request-approval", "--change-id", "chg_opaque"],
            ["request-approval", "&&", "touch", "bad"],
        ):
            with self.subTest(argv=argv):
                code, rejected = self.run_cli(argv)
                self.assertEqual(2, code)
                self.assertEqual("usage", rejected["code"])

    def test_host_commands_require_host_secret_and_use_json_stdin(self):
        sentinel = {"status": "pending", "approval_id": "apr_test"}
        with (
            mock.patch("myanc_crm.cli.LarkCliBackend"),
            mock.patch("myanc_crm.cli.Ledger") as ledger_type,
            mock.patch("myanc_crm.cli.begin_approval", return_value=sentinel) as begin,
        ):
            code, result = self.run_cli(
                ["host-begin"],
                '{"change_id":"chg_test","principal":{}}',
                host=True,
            )
        self.assertEqual(0, code)
        self.assertEqual(sentinel, result)
        begin.assert_called_once()
        ledger_type.return_value.close.assert_called_once_with()

        with mock.patch.dict(os.environ, {cli.HOST_SECRET_ENV: "x" * 32}):
            output = io.StringIO()
            with mock.patch.object(cli, "_config_path", return_value=self.config_path):
                code = cli.main(["host-decide"], stdin=io.StringIO("{}"), stdout=output)
        self.assertEqual(2, code)
        self.assertEqual("invalid_local_input", json.loads(output.getvalue())["code"])

    def test_host_bind_card_dispatches_only_through_the_authenticated_boundary(self):
        payload = {
            "approval_id": "apr_test",
            "principal": {
                "platform": "feishu",
                "user_id": "sender-test",
                "chat_id": "chat-test",
                "session_key": "session-test",
                "project": "project-test",
                "message_id": "om_emitted_card",
            },
        }
        sentinel = {"status": "bound", "approval_id": "apr_test"}
        with (
            mock.patch("myanc_crm.cli.LarkCliBackend"),
            mock.patch("myanc_crm.cli.Ledger") as ledger_type,
            mock.patch(
                "myanc_crm.cli.bind_approval_card", return_value=sentinel
            ) as bind,
        ):
            code, result = self.run_cli(
                ["host-bind-card"], json.dumps(payload), host=True
            )

        self.assertEqual(0, code)
        self.assertEqual(sentinel, result)
        bind.assert_called_once_with(payload, ledger_type.return_value, self.config)
        ledger_type.return_value.close.assert_called_once_with()

    def test_bad_json_and_bad_config_never_echo_sensitive_input(self):
        secret = "never-print-this-secret"
        code, result = self.run_cli(["host-prepare"], '{"token":"' + secret, host=True)
        self.assertEqual(2, code)
        self.assertEqual("failed", result["status"])
        self.assertNotIn(secret, json.dumps(result))

        self.config_path.write_text('{"app_secret":"' + secret, encoding="utf-8")
        code, result = self.run_cli(["host-decide"], "{}", host=True)
        self.assertEqual(2, code)
        self.assertEqual("failed", result["status"])
        self.assertNotIn(secret, json.dumps(result))

    def test_host_prepare_requires_both_host_secret_and_action_token(self):
        payload = json.dumps(
            {
                "request": {},
                "principal": {
                    "platform": "feishu",
                    "user_id": "sender-test",
                    "chat_id": "chat-test",
                    "session_key": "session-test",
                    "project": "project-test",
                    "message_id": "message-test",
                },
            }
        )
        for environment in (
            {cli.ACTION_TOKEN_ENV: self.action_token},
            {cli.HOST_SECRET_ENV: self.host_secret},
        ):
            output = io.StringIO()
            with (
                mock.patch.object(cli, "_config_path", return_value=self.config_path),
                mock.patch.dict(os.environ, environment, clear=True),
            ):
                code = cli.main(
                    ["host-prepare"], stdin=io.StringIO(payload), stdout=output
                )
            result = json.loads(output.getvalue())

            self.assertEqual(2, code)
            self.assertEqual(
                ("failed", "invalid_local_input"),
                (result["status"], result["code"]),
            )


if __name__ == "__main__":
    unittest.main()
