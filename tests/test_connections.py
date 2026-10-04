"""Fictional identities exercise native-user selection and every bot bypass."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from myanc_crm.connections import Connections, ConnectionBlocked, PersonalReadRunner, access


def stamp(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


class FakeCLI:
    def __init__(self):
        self.calls = []
        self.user = None
        self.app = "crm-app"
        self.tenant = "fixture-tenant"
        self.status = "ready"
        self.expires = 10000
        self.refresh_expires = 100000
        self.fail = False
        self.login_user = "crm-manager"
        self.environments = []
        self.scope = "auth:user.id:read base:field:read base:record:read offline_access"
        self.verify_failure = False
        self.api_error = None

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        self.environments.append(kwargs.get("env", {}))
        if argv[1:] == ["--version"]:
            return subprocess.CompletedProcess(argv, 0, "1.0.90\n", "")
        if self.fail:
            raise subprocess.TimeoutExpired(argv, 10)
        if self.api_error and argv[1] in {"api", "base"}:
            return subprocess.CompletedProcess(argv, 1, "", json.dumps(
                {"ok": False, "identity": "user", "error": self.api_error}))
        if argv[1:3] == ["auth", "status"]:
            if "--verify" in argv:
                self.expires += 3600
            value = dict(appId=self.app, identity="bot", verified=True,
                         identities=dict(bot=dict(available=True, verified=True),
                                         user=dict(openId=self.user, status=self.status if self.user else "missing", available=self.status == "ready" and bool(self.user),
                                                   verified=self.status == "ready", scope=self.scope, expiresAt=stamp(self.expires),
                                                   refreshExpiresAt=stamp(self.refresh_expires))))
            if self.verify_failure and "--verify" in argv:
                value["identities"]["user"].update(status="verify_failed", available=False, verified=False)
        elif argv[1:3] == ["auth", "login"]:
            if "--device-code" in argv:
                self.user = self.login_user
            value = dict(verification_url="https://accounts.feishu.cn/oauth/fixture",
                         device_code="fictional-short-lived-device-code", expires_in=600)
        elif argv[1:3] == ["auth", "logout"]:
            self.user = None
            value = dict(loggedOut=True)
        elif argv[1:3] == ["auth", "qrcode"]:
            (Path(kwargs["cwd"])/"connection.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
            value = {}
        elif argv[1] == "api":
            value = dict(ok=True, identity="user", data=dict(open_id=self.user, tenant_key=self.tenant))
        else:
            value = dict(ok=True, identity="user", data={})
        return subprocess.CompletedProcess(argv, 0, json.dumps(value), "")


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.principal = dict(platform="feishu", user_id="bot-manager", chat_id="private-manager",
                              project="manager-private", session_key="private-session", message_id="message")
        private = {k: self.principal[k] for k in ("platform", "user_id", "chat_id", "project")}
        group = dict(private, chat_id="shared-group", project="manager-group", audience="shared")
        self.config = dict(allowed_actors={"bot-manager": dict(display_name="Manager", feishu_user_id="crm-manager",
                                                               connection_profile="anc-user-manager")},
                           personal_connections=dict(app_id="crm-app", tenant_key="fixture-tenant", source_app_id="bot-app",
                                                     source_tenant_key="fixture-tenant", cli_path=str(Path(self.temp.name).resolve()/"cli"),
                                                     database_path=str(Path(self.temp.name).resolve()/"private"/"connections.db"),
                                                     cli_home_root=str(Path(self.temp.name).resolve()/"homes"),
                                                     resource_mode="restricted", routes=[dict(private, audience="private"), group]))
        (Path(self.temp.name).resolve()/"homes"/"anc-user-manager").mkdir(parents=True, mode=0o700)
        self.fake = FakeCLI()
        self.clock = 1000
        self.connections = Connections(self.config, run=self.fake, now=lambda: self.clock)
        self.token = "host-bound-session-token-000000000001"

    def connect(self):
        pending = self.connections.command("connect", self.principal)
        self.assertEqual("pending", pending["status"])
        result = self.connections.command("complete", self.principal)
        self.assertEqual("connected", result["status"])
        return result

    def assertBlocked(self, code, callback):
        with self.assertRaises(ConnectionBlocked) as raised:
            callback()
        self.assertEqual(code, raised.exception.code)

    def test_native_user_read_and_disconnect_invalidate_existing_session(self):
        self.connect()
        runner = PersonalReadRunner(self.connections, self.principal, self.token)
        result = runner(["ignored-wrapper", "base", "+record-get", "--base-token", "fixture"], timeout=10)
        self.assertEqual(0, result.returncode)
        read_call = next(call for call in reversed(self.fake.calls) if call[1] == "base")
        self.assertEqual(["--profile", "anc-user-manager", "--as", "user"], read_call[-4:])
        self.connections.command("disconnect", self.principal)
        self.assertBlocked("connection_session_expired", lambda: self.connections.check_version(runner.binding))
        self.connect()
        self.assertBlocked("connection_session_expired", lambda: self.connections.require(self.principal, self.token))
        self.connections.require(self.principal, self.token + "new")

    def test_missing_user_does_not_accept_verified_bot(self):
        self.connect()
        self.fake.status = "missing"
        self.assertBlocked("connection_required", lambda: self.connections.require(self.principal, self.token))
        self.assertEqual("reconnect_required", self.connections.command("check", self.principal)["status"])

    def test_server_revocation_with_unexpired_local_token_invalidates_each_entry(self):
        # Native CLI 1.0.90: auth status exits zero with verified bot while user
        # verification fails; explicit user_info returns api/unknown code 20005.
        for entry in ("status", "maintain", "read", "work-context", "file-deliver"):
            with self.subTest(entry=entry):
                self.fake.verify_failure, self.fake.api_error = False, None
                self.connections.command("disconnect", self.principal)
                self.connect()
                token, work = self.token + entry, "private-" + entry
                self.connections.guard("customer", self.principal, token, work)
                binding = self.connections.require(self.principal, token)
                runner = PersonalReadRunner(self.connections, self.principal, token)
                self.fake.verify_failure = True
                self.fake.api_error = {"type": "api", "subtype": "unknown", "code": 20005,
                                       "message": "invalid access token"}
                if entry == "status":
                    self.assertEqual("reconnect_required", self.connections.command("status", self.principal)["status"])
                elif entry == "maintain":
                    self.clock = self.fake.expires - 200
                    self.assertEqual("reconnect_required", self.connections.maintain("bot-manager")[0]["status"])
                elif entry == "read":
                    self.assertBlocked("connection_session_expired", lambda: runner(["wrapper", "base", "+record-get"]))
                else:
                    self.assertBlocked("connection_session_expired", lambda: self.connections.guard(entry, self.principal, token, work))
                state = self.connections.command("check", self.principal)
                self.assertEqual("reconnect_required", state["status"])
                self.assertEqual(binding["version"] + 1, state["version"])
                self.assertBlocked("connection_session_expired", lambda: self.connections.check_version(binding))
                self.assertEqual("allowed", self.connections.guard("work-context", self.principal, "", "clean")["status"])

    def test_failed_verification_does_not_guess_revocation_from_status_or_message(self):
        self.connect()
        self.connections.guard("customer", self.principal, self.token, "private")
        original = self.connections.command("check", self.principal)
        self.fake.verify_failure = True
        for error in ({"type": "network", "subtype": "timeout", "message": "invalid access token"},
                      {"type": "api", "subtype": "unknown", "code": 500, "message": "invalid access token"},
                      {"type": "api", "subtype": "unknown", "code": "20005"}):
            with self.subTest(error=error):
                self.fake.api_error = error
                self.assertBlocked("connection_temporarily_unavailable", lambda: self.connections.command("status", self.principal))
                self.assertBlocked("connection_temporarily_unavailable", lambda: self.connections.guard("file-deliver", self.principal, self.token, "private"))
                self.assertEqual(original, self.connections.command("check", self.principal))
        self.fake.api_error = None
        self.assertEqual("connected", self.connections.command("status", self.principal)["status"])
        self.assertEqual("allowed", self.connections.guard("file-deliver", self.principal, self.token, "private")["status"])

    def test_first_login_requests_scopes_required_by_pinned_cli_reads(self):
        self.connections.command("connect", self.principal)
        call = next(call for call in self.fake.calls if call[1:3] == ["auth", "login"])
        requested = set(call[call.index("--scope") + 1].split())
        # Observed 1.0.90 contract: bitable:app:readonly alone fails field/record commands.
        self.assertEqual({"base:field:read", "base:record:read", "offline_access"}, requested)

    def test_missing_read_scope_is_not_adopted_and_revokes_existing_work(self):
        self.fake.user = "crm-manager"
        self.fake.scope = "auth:user.id:read bitable:app:readonly offline_access"
        self.assertEqual("pending", self.connections.command("connect", self.principal)["status"])
        self.assertEqual("reconnect_required", self.connections.command("complete", self.principal)["status"])
        self.fake.scope = "base:field:read base:record:read offline_access"
        self.connect()
        binding = self.connections.require(self.principal, self.token)
        self.fake.scope = "base:field:read offline_access"
        self.assertBlocked("connection_required", lambda: self.connections.require(self.principal, self.token))
        self.assertBlocked("connection_session_expired", lambda: self.connections.check_version(binding))

    def test_wrong_scan_tenant_and_profile_replacement_are_rejected(self):
        self.connections.command("disconnect", self.principal)
        for field, value in (("user", "crm-other"), ("tenant", "other-tenant")):
            with self.subTest(field=field):
                self.fake.user, self.fake.tenant = "crm-manager", "fixture-tenant"
                self.connections.command("connect", self.principal)
                setattr(self.fake, field, value)
                self.assertEqual("wrong_account", self.connections.command("complete", self.principal)["status"])
                self.assertNotEqual("connected", self.connections.command("check", self.principal)["status"])
        self.fake.user, self.fake.tenant = "crm-manager", "fixture-tenant"
        self.connect()
        self.fake.user = "crm-other"
        self.assertBlocked("connection_identity_mismatch", lambda: self.connections.require(self.principal, self.token))

    def test_wrong_app_stops_before_auth_login(self):
        self.fake.app = "different-app"
        self.assertBlocked("connection_identity_mismatch", lambda: self.connections.command("connect", self.principal))
        self.assertFalse(any(call[1:3] == ["auth", "login"] for call in self.fake.calls))

    def test_group_cannot_start_auth_or_use_personal_reader(self):
        group = dict(self.principal, chat_id="shared-group", project="manager-group")
        self.assertBlocked("connection_private_chat_required", lambda: self.connections.command("connect", group))
        self.assertBlocked("connection_private_chat_required", lambda: self.connections.require(group, self.token))
        self.assertEqual([], self.fake.calls)

    def test_all_restricted_bot_bypasses_block_before_backend(self):
        for command in ("stage", "stage-customer-update", "stage-customer-create", "result", "open", "assignee",
                        "host-prepare", "host-begin", "host-bind-card", "host-claim", "host-execute", "host-decide",
                        "host-plan-read", "host-plan-events"):
            with self.subTest(command=command):
                self.assertBlocked("restricted_resource_operation_denied", lambda: access(self.config, command, self.principal))
        self.assertBlocked("restricted_resource_operation_denied", lambda: access(self.config, "host-plan-read", None))
        self.assertIsInstance(access(self.config, "customer", self.principal), Connections)
        self.assertIsInstance(access(self.config, "customers", self.principal), Connections)
        self.config["personal_connections"]["resource_mode"] = "shared"
        for command in ("stage", "result", "host-plan-read", "case-publish"):
            self.assertIsNone(access(self.config, command, self.principal))

    def test_reader_refuses_writes_identity_flags_and_revocation_during_call(self):
        self.connect()
        runner = PersonalReadRunner(self.connections, self.principal, self.token)
        self.assertBlocked("personal_read_only", lambda: runner(["wrapper", "base", "+record-update"]))
        self.assertBlocked("personal_identity_override_denied", lambda: runner(["wrapper", "base", "+record-get", "--as=bot"]))
        original = self.connections.run
        def revoke(argv, **kwargs):
            result = original(argv, **kwargs)
            if argv[1] == "base":
                self.connections.command("disconnect", self.principal)
            return result
        self.connections.run = revoke
        self.assertBlocked("connection_session_expired", lambda: runner(["wrapper", "base", "+record-get"]))

    def test_native_resource_denial_is_explicit_without_returning_cli_content(self):
        self.connect()
        runner = PersonalReadRunner(self.connections, self.principal, self.token)
        original = self.connections.run
        def denied(argv, **kwargs):
            if argv[1] == "base":
                return subprocess.CompletedProcess(argv, 1, "", json.dumps({"ok": False, "identity": "user",
                    "error": {"type": "api", "subtype": "unknown", "code": 91403,
                              "message": "untrusted-private-error-content"}}))
            return original(argv, **kwargs)
        self.connections.run = denied
        self.assertBlocked("personal_read_permission_denied", lambda: runner(["wrapper", "base", "+record-get"]))
        self.assertEqual("connected", self.connections.command("check", self.principal)["status"])
        self.connections.run = original
        self.assertEqual(0, runner(["wrapper", "base", "+record-get"]).returncode)

    def test_scope_loss_during_read_invalidates_private_work_even_with_stale_metadata(self):
        for stale_metadata in (False, True):
            with self.subTest(stale_metadata=stale_metadata):
                self.fake.scope = "base:field:read base:record:read offline_access"
                self.connect()
                token = self.token + str(stale_metadata)
                work = "private-work-" + str(stale_metadata)
                self.connections.guard("customer", self.principal, token, work)
                runner = PersonalReadRunner(self.connections, self.principal, token)
                original = self.connections.run
                def lose_scope(argv, **kwargs):
                    if argv[1] == "base":
                        if not stale_metadata:
                            self.fake.scope = "base:field:read offline_access"
                        return subprocess.CompletedProcess(argv, 3, "", json.dumps({"ok": False,
                            "error": {"type": "authorization", "subtype": "missing_scope"}}))
                    return original(argv, **kwargs)
                self.connections.run = lose_scope
                try:
                    self.assertBlocked("connection_required", lambda: runner(["wrapper", "base", "+record-get"]))
                    self.assertEqual("reconnect_required", self.connections.command("check", self.principal)["status"])
                    self.assertBlocked("connection_session_expired", lambda: self.connections.guard("file-deliver", self.principal, token, work))
                finally:
                    self.connections.run = original

    def test_silent_refresh_uses_new_metadata_and_network_failure_does_not_log_out(self):
        self.connect()
        self.clock = self.fake.expires - 200
        old_expiry = self.fake.expires
        self.assertEqual("connected", self.connections.maintain("bot-manager")[0]["status"])
        with self.connections.database() as db:
            row = self.connections._row(db, self.principal)
            self.assertGreater(row["expires"], old_expiry)
        self.clock = self.fake.expires - 200
        self.fake.fail = True
        self.assertEqual("connected", self.connections.maintain("bot-manager")[0]["status"])
        self.assertEqual("connected", self.connections.command("check", self.principal)["status"])
        self.fake.fail = False
        self.fake.status = "missing"
        self.clock += 4000
        changes = self.connections.maintain("bot-manager")
        self.assertEqual("reconnect_required", changes[0]["status"])
        self.assertEqual(changes, self.connections.maintain("bot-manager"))

    def test_wrong_scan_can_reconnect_using_only_its_own_native_store(self):
        self.connections.command("connect", self.principal)
        self.fake.login_user = "crm-other"
        self.assertEqual("wrong_account", self.connections.command("complete", self.principal)["status"])
        self.fake.login_user = "crm-manager"
        self.connect()
        self.assertEqual("crm-manager", self.fake.user)
        for environment in self.fake.environments:
            self.assertEqual(str(Path(self.temp.name).resolve()/"homes"/"anc-user-manager"), environment["HOME"])

    def test_completed_exchange_survives_host_restart_and_verification_network_failure(self):
        self.connections.command("connect", self.principal)
        self.fake.user = "crm-manager"  # CLI saved a completed exchange, host died before recording it.
        original = self.connections._verify_identity
        self.connections._verify_identity = mock.Mock(side_effect=ConnectionBlocked("connection_temporarily_unavailable"))
        self.assertEqual("verifying", self.connections.command("status", self.principal)["status"])
        self.connections._verify_identity = original
        restarted = Connections(self.config, run=self.fake, now=lambda: self.clock)
        self.assertEqual("connected", restarted.command("status", self.principal)["status"])
        self.assertFalse(any("--device-code" in call for call in self.fake.calls))

    def test_clean_office_work_and_shared_knowledge_stay_usable(self):
        for command in ("reminder-list", "reminder-create", "case-update", "case-publish", "knowledge_propose"):
            self.assertEqual("allowed", self.connections.guard(command, self.principal, self.token, "clean")["status"])
        self.connections.guard("knowledge_read", self.principal, self.token, "team-work", "team")
        self.connections.guard("case-publish", self.principal, self.token, "team-work")
        self.config["personal_connections"]["resource_mode"] = "shared"
        self.connections.guard("knowledge_read", self.principal, self.token, "private-knowledge", "management")
        self.assertBlocked("personal_work_sharing_denied", lambda: self.connections.guard("case-publish", self.principal, self.token, "private-knowledge"))
        self.connections.guard("file-deliver", self.principal, self.token, "private-knowledge")
        group = dict(self.principal, chat_id="shared-group", project="manager-group")
        self.assertBlocked("personal_work_audience_denied", lambda: self.connections.guard("knowledge_search", group, self.token, "group-work", "management"))

    def test_startup_source_and_version_are_checked(self):
        self.assertEqual("enabled", self.connections.validate_source("bot-app")["status"])
        self.assertBlocked("connection_source_app_mismatch", lambda: self.connections.validate_source("other-app"))

    def test_private_work_cannot_publish_or_resume_after_disconnect(self):
        self.connect()
        self.connections.guard("customer", self.principal, self.token, "work-private")
        for command in ("case-publish", "case-update", "knowledge_propose", "stage", "result"):
            self.assertBlocked("personal_work_sharing_denied", lambda: self.connections.guard(command, self.principal, self.token, "work-private"))
        self.connections.guard("file-deliver", self.principal, self.token, "work-private")
        # A later deployment's wider resource mode does not relabel old artifacts.
        self.config["personal_connections"]["resource_mode"] = "shared"
        self.assertBlocked("personal_work_sharing_denied", lambda: self.connections.guard("case-publish", self.principal, self.token, "work-private"))
        self.connections.command("disconnect", self.principal)
        self.assertBlocked("connection_session_expired", lambda: self.connections.guard("work-resume", self.principal, "", "work-private"))
        self.assertEqual("allowed", self.connections.guard("work-resume", self.principal, "", "new-work")["status"])

    def test_no_profile_reuse_between_actors(self):
        config = copy.deepcopy(self.config)
        config["allowed_actors"]["another"] = dict(config["allowed_actors"]["bot-manager"])
        self.assertBlocked("connection_profile_shared", lambda: Connections(config))

    def test_successful_reconnect_delivers_generation_and_expires_both_private_works(self):
        self.connect()
        for work in ("private-one", "private-two"):
            self.connections.guard("customer", self.principal, self.token, work)
        old = self.connections.maintain("bot-manager")[0]
        self.connections.command("reconnect", self.principal)
        self.connections.command("complete", self.principal)
        current = self.connections.maintain("bot-manager")
        self.assertEqual("connected", current[0]["status"])
        self.assertGreater(current[0]["version"], old["version"])
        self.assertEqual(current, self.connections.maintain("bot-manager"))
        for work in ("private-one", "private-two"):
            self.assertBlocked("connection_session_expired", lambda: self.connections.guard("work-resume", self.principal, "", work))
        self.connections.guard("customer", self.principal, "n" * 32, "new-private")
        self.assertEqual("allowed", self.connections.guard("work-resume", self.principal, "", "new-private")["status"])

    def test_first_use_can_adopt_verified_native_login_and_connect_is_idempotent(self):
        self.fake.user = "crm-manager"
        first = self.connections.command("connect", self.principal)
        again = self.connections.command("connect", self.principal)
        self.assertEqual(("connected",1,False), (again["status"],again["version"],again["reset"]))
        self.assertTrue(first["reset"])
        self.assertFalse(any(call[1:3] == ["auth","login"] for call in self.fake.calls))

    def test_synthetic_year_refresh_and_per_account_offline_isolation(self):
        self.connect()
        other_principal = dict(self.principal, user_id="bot-staff", chat_id="private-staff", project="staff-private")
        self.config["allowed_actors"]["bot-staff"] = dict(display_name="Staff",feishu_user_id="crm-staff",connection_profile="anc-user-staff")
        self.config["personal_connections"]["routes"].append({k:other_principal[k] for k in ("platform","user_id","chat_id","project")} | {"audience":"private"})
        (Path(self.temp.name).resolve()/"homes"/"anc-user-staff").mkdir(mode=0o700)
        other_cli=FakeCLI(); other_cli.login_user="crm-staff"
        other=Connections(self.config,run=other_cli,now=lambda:self.clock)
        other.command("connect",other_principal); other.command("complete",other_principal)
        for day in range(1,366):
            self.clock=1000+day*86400
            self.fake.refresh_expires=other_cli.refresh_expires=self.clock+7*86400
            self.fake.expires=other_cli.expires=self.clock+180
            self.assertEqual("connected", self.connections.maintain("bot-manager")[0]["status"])
            self.assertEqual("connected", other.maintain("bot-staff")[0]["status"])
            self.assertEqual("connected", other.command("check",other_principal)["status"])
        self.clock+=3600
        self.fake.fail=True
        self.assertEqual("connected",self.connections.maintain("bot-manager")[0]["status"])
        self.assertEqual("connected",self.connections.command("check",self.principal)["status"])
        self.assertEqual("connected",other.maintain("bot-staff")[0]["status"])
        self.fake.fail=False
        self.fake.status="missing"
        self.clock+=4000
        events=self.connections.maintain("bot-manager")
        self.assertEqual("bot-manager",events[0]["user_id"])
        self.assertEqual("connected",other.command("check",other_principal)["status"])


if __name__ == "__main__":
    unittest.main()
