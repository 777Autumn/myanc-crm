"""Host-owned Feishu connections. Tokens and refresh remain owned by lark-cli.

Nothing in this module is a model-facing CLI. The gateway supplies the principal;
protected configuration supplies every profile, application and resource route.
"""

from contextlib import ExitStack, contextmanager
from datetime import datetime
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import tempfile
import time
from urllib.parse import urlsplit

from . import core, write_locks, timing


READ_COMMANDS = frozenset({"customer", "customers", "banquet", "banquets", "banquet-context", "handoff"})
HANDOFF_STAGES = frozenset({"stage-handoff-submit", "stage-handoff-accept", "stage-handoff-return"})
BANQUET_STAGES = frozenset({"stage-banquet-create", "stage-banquet-update", "stage-banquet-followup"})
CLI_READ_COMMANDS = frozenset({"+field-list", "+record-list", "+record-get", "+record-search"})
READ_SCOPES = frozenset({"base:field:read", "base:record:read", "offline_access"})
ROUTE_FIELDS = ("platform", "user_id", "chat_id", "project")
MEMBER_ROUTE_FIELDS = {"member_id", "source_app_id", "source_tenant_key"}


class ConnectionBlocked(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _text(value):
    if not isinstance(value, str) or not value or len(value) > 1024 or any(c in value for c in "\x00\r\n"):
        raise ConnectionBlocked("connection_configuration_invalid")
    return value


def _timestamp(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (AttributeError, TypeError, ValueError):
        raise ConnectionBlocked("connection_metadata_invalid") from None


def resolve_member_id(config, principal):
    """Resolve business membership without changing the transport principal."""
    options = config.get("personal_connections", {})
    if "routes" in options:
        matches = [route for route in options["routes"]
                   if all(route.get(key) == principal.get(key) for key in ROUTE_FIELDS)]
        if len(matches) != 1:
            raise ConnectionBlocked("connection_route_denied")
        return matches[0].get("member_id", matches[0]["user_id"])
    return principal["user_id"]


def resolve_actor(config, principal):
    member = resolve_member_id(config, principal)
    actor = config.get("allowed_actors", {}).get(member)
    if not isinstance(actor, dict):
        raise ValueError("principal is not configured")
    return actor


class Connections:
    def __init__(self, config, *, run=subprocess.run, now=time.time):
        self.config = config
        self.options = config["personal_connections"]
        if not isinstance(self.options, dict):
            raise ConnectionBlocked("connection_configuration_invalid")
        self.run, self.now = run, now
        for key in ("app_id", "tenant_key", "source_app_id", "source_tenant_key", "cli_path", "database_path", "cli_home_root"):
            _text(self.options.get(key))
        self.path = Path(self.options["database_path"])
        self.cli = self.options["cli_path"]
        self.home_root = Path(self.options["cli_home_root"])
        if not self.path.is_absolute() or not Path(self.cli).is_absolute() or not self.home_root.is_absolute():
            raise ConnectionBlocked("connection_configuration_invalid")
        if self.options.get("resource_mode") not in {"shared", "restricted"}:
            raise ConnectionBlocked("connection_configuration_invalid")
        profiles = []
        for actor in config["allowed_actors"].values():
            profile = actor.get("connection_profile")
            if profile is not None:
                if not re.fullmatch(r"anc-user-[a-z0-9-]{1,64}", profile):
                    raise ConnectionBlocked("connection_configuration_invalid")
                profiles.append(profile)
        if len(profiles) != len(set(profiles)):
            raise ConnectionBlocked("connection_profile_shared")
        routes = self.options.get("routes")
        if not isinstance(routes, list) or not routes:
            raise ConnectionBlocked("connection_configuration_invalid")
        seen, sources = set(), {}
        for route in routes:
            if not isinstance(route, dict) or set(route) not in ({*ROUTE_FIELDS, "audience"}, {*ROUTE_FIELDS, "audience", *MEMBER_ROUTE_FIELDS}):
                raise ConnectionBlocked("connection_configuration_invalid")
            key = tuple(_text(route.get(field)) for field in ROUTE_FIELDS)
            if key in seen or route["audience"] not in {"private", "shared"}:
                raise ConnectionBlocked("connection_configuration_invalid")
            member = route.get("member_id", route["user_id"])
            if member not in config["allowed_actors"]:
                raise ConnectionBlocked("connection_configuration_invalid")
            source = tuple(_text(route.get(field, self.options[field])) for field in ("source_app_id", "source_tenant_key"))
            if route["project"] in sources and sources[route["project"]] != source:
                raise ConnectionBlocked("connection_configuration_invalid")
            sources[route["project"]] = source
            seen.add(key)

    def route(self, principal):
        matches = [route for route in self.options["routes"]
                   if all(route[key] == principal.get(key) for key in ROUTE_FIELDS)]
        if len(matches) != 1:
            raise ConnectionBlocked("connection_route_denied")
        return matches[0]["audience"]

    def actor(self, principal):
        if self.route(principal) != "private":
            raise ConnectionBlocked("connection_private_chat_required")
        actor = resolve_actor(self.config, principal)
        _text(actor.get("connection_profile"))
        _text(actor.get("feishu_user_id"))
        return actor

    def key(self, principal):
        identity = [self.options[k] for k in ("source_app_id", "source_tenant_key", "app_id", "tenant_key")]
        identity.append(_text(resolve_member_id(self.config, principal)))
        return hashlib.sha256(json.dumps(identity).encode()).hexdigest()

    @contextmanager
    def database(self):
        core._prepare_ledger_parent(self.path.parent)
        if not self.path.exists():
            try:
                core._create_private_file(self.path)
            except FileExistsError:
                pass
        core._validate_private_file(self.path)
        with core._private_umask(), ExitStack() as stack:
            with timing.measure("connection_db_setup"):
                db = sqlite3.connect(self.path, timeout=10)
                stack.callback(db.close)
                db.row_factory = sqlite3.Row
                db.execute("CREATE TABLE IF NOT EXISTS connections (subject TEXT PRIMARY KEY, "
                           "profile TEXT NOT NULL, account TEXT NOT NULL, status TEXT NOT NULL, "
                           "version INTEGER NOT NULL, expires REAL NOT NULL DEFAULT 0, "
                           "refresh_expires REAL NOT NULL DEFAULT 0, retry_at REAL NOT NULL DEFAULT 0, "
                           "failures INTEGER NOT NULL DEFAULT 0, device_code TEXT NOT NULL DEFAULT '', "
                           "flow_expires REAL NOT NULL DEFAULT 0)")
                db.execute("CREATE TABLE IF NOT EXISTS connection_sessions (session TEXT PRIMARY KEY, "
                           "subject TEXT NOT NULL, version INTEGER NOT NULL)")
                db.execute("CREATE TABLE IF NOT EXISTS connection_work (work TEXT PRIMARY KEY, "
                           "subject TEXT NOT NULL, version INTEGER NOT NULL, requires_connection INTEGER NOT NULL)")
                db.execute("CREATE TABLE IF NOT EXISTS connection_work_scope (work TEXT PRIMARY KEY, "
                           "private INTEGER NOT NULL CHECK(private IN (0,1)))")
                db.commit()
            yield db

    @contextmanager
    def locked(self, principal):
        with self.database() as db:
            try:
                with ExitStack() as stack:
                    with timing.measure("connection_lock_wait"):
                        stack.enter_context(write_locks.acquire(self.path.parent, ["connection-" + self.key(principal)]))
                    yield db
            except write_locks.WriteBlocked as exc:
                if exc.code == "crm_write_busy":
                    raise ConnectionBlocked("connection_temporarily_unavailable") from None
                raise

    def _row(self, db, principal):
        actor = self.actor(principal)
        key = self.key(principal)
        db.execute("INSERT OR IGNORE INTO connections(subject,profile,account,status,version) VALUES(?,?,?,'disconnected',0)",
                   (key, actor["connection_profile"], actor["feishu_user_id"]))
        db.commit()
        row = db.execute("SELECT * FROM connections WHERE subject=?", (key,)).fetchone()
        if row["profile"] != actor["connection_profile"] or row["account"] != actor["feishu_user_id"]:
            raise ConnectionBlocked("connection_binding_changed")
        return row

    def _set(self, db, row, status, *, invalidate=False, **values):
        allowed = {"expires", "refresh_expires", "retry_at", "failures", "device_code", "flow_expires"}
        if set(values) - allowed:
            raise ValueError("Unsupported connection state")
        values.update(status=status, version=row["version"] + int(invalidate))
        db.execute("UPDATE connections SET " + ",".join(key + "=?" for key in values) + " WHERE subject=?",
                   (*values.values(), row["subject"]))
        db.commit()

    def environment(self, profile):
        # Never pass inherited credential overrides or model-controlled arguments.
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(("LARK_", "LARKSUITE_", "FEISHU_", "MYANC_CRM_"))}
        # Official Darwin/Linux stores live under HOME. Each person has a native
        # CLI store so a wrong scan cannot replace another profile's app:user token.
        home = self.home_root / profile
        core._validate_parent_chain(home)
        env.update(HOME=str(home), LARKSUITE_CLI_NO_UPDATE_NOTIFIER="1", LARKSUITE_CLI_NO_SKILLS_NOTIFIER="1")
        return env

    def _cli(self, profile, args, *, timeout=10):
        env = self.environment(profile)
        try:
            with timing.measure("connection_cli"):
                completed = self.run([self.cli, *args, "--profile", profile], capture_output=True,
                                     text=True, encoding="utf-8", timeout=timeout, env=env, check=False, shell=False)
            if completed.returncode:
                # This endpoint's native 1.0.90 response distinguishes revoked
                # user tokens from transport failures. Never parse message text.
                if args == ["api", "GET", "/open-apis/authen/v1/user_info", "--as", "user"]:
                    try:
                        data = json.loads(completed.stderr)
                    except (ValueError, TypeError):
                        data = None
                    error = data.get("error") if isinstance(data, dict) else None
                    if isinstance(error, dict) and data.get("ok") is False and data.get("identity") == "user":
                        if (error.get("type") == "api" and type(error.get("code")) is int and error["code"] == 20005
                                or error.get("type") == "authentication" and error.get("subtype") == "token_missing"):
                            raise ConnectionBlocked("connection_required")
                raise ConnectionBlocked("connection_temporarily_unavailable")
            value = json.loads(completed.stdout)
            if not isinstance(value, dict):
                raise ValueError
            return value
        except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
            if isinstance(exc, ConnectionBlocked):
                raise
            raise ConnectionBlocked("connection_temporarily_unavailable") from None

    def validate_source(self, app_id, project=None, tenant_key=None):
        routed = any("member_id" in route for route in self.options["routes"])
        matches = self.options["routes"] if project is None else [route for route in self.options["routes"] if route["project"] == project]
        if (routed and (project is None or tenant_key is None)) or not matches or any(
            route.get("source_app_id", self.options["source_app_id"]) != app_id or
            (tenant_key is not None and route.get("source_tenant_key", self.options["source_tenant_key"]) != tenant_key)
            for route in matches
        ):
            raise ConnectionBlocked("connection_source_app_mismatch")
        result = self.run([self.cli, "--version"], capture_output=True, text=True,
                          encoding="utf-8", timeout=10, check=False, shell=False)
        if result.returncode or not re.fullmatch(r"(?:lark-cli\s+)?(?:version\s+)?v?1\.0\.90\s*", result.stdout):
            raise ConnectionBlocked("connection_cli_version_mismatch")
        result = {"status": "enabled", "users": self.users(members=routed)}
        if project is not None:
            result.update(project=project, source_app_id=app_id, source_tenant_key=tenant_key,
                          bindings=[{**{key: route[key] for key in (*ROUTE_FIELDS, "audience")},
                                     "member_id": route.get("member_id", route["user_id"])} for route in matches])
        return result

    def qrcode(self, profile, uri):
        with tempfile.TemporaryDirectory(prefix="connection-qr-", dir=self.path.parent) as directory:
            result = self.run([self.cli, "auth", "qrcode", uri, "--output", "connection.png", "--profile", profile],
                              cwd=directory, env=self.environment(profile), capture_output=True, text=True,
                              encoding="utf-8", timeout=10, check=False, shell=False)
            path = Path(directory) / "connection.png"
            if result.returncode or not path.is_file() or path.stat().st_size > 100000:
                raise ConnectionBlocked("connection_qrcode_unavailable")
            content = path.read_bytes()
            if not content.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ConnectionBlocked("connection_qrcode_unavailable")
            return base64.b64encode(content).decode("ascii")

    def metadata(self, actor, *, verify=False):
        args = ["auth", "status", "--json"] + (["--verify"] if verify else [])
        data = self._cli(actor["connection_profile"], args)
        if data.get("appId") != self.options["app_id"]:
            raise ConnectionBlocked("connection_identity_mismatch")
        user = data.get("identities", {}).get("user", {})
        if user.get("openId") and user["openId"] != actor["feishu_user_id"]:
            raise ConnectionBlocked("connection_identity_mismatch")
        if user.get("status") in {"missing", "not_configured"}:
            raise ConnectionBlocked("connection_required")
        if user.get("openId") != actor["feishu_user_id"]:
            raise ConnectionBlocked("connection_identity_mismatch")
        if not user.get("available") or (verify and user.get("verified") is not True):
            raise ConnectionBlocked("connection_temporarily_unavailable")
        scopes = user.get("scope")
        if not isinstance(scopes, str) or not READ_SCOPES.issubset(scopes.split()):
            raise ConnectionBlocked("connection_required")
        _timestamp(user.get("expiresAt"))
        _timestamp(user.get("refreshExpiresAt"))
        return user

    def _verify_identity(self, actor):
        try:
            self.metadata(actor, verify=True)
        except ConnectionBlocked as exc:
            if exc.code != "connection_temporarily_unavailable":
                raise
            # --verify collapses network errors and revoked tokens into the same
            # status. Check local binding, then use explicit user API evidence.
            self.metadata(actor)
        info = self._cli(actor["connection_profile"],
                         ["api", "GET", "/open-apis/authen/v1/user_info", "--as", "user"])
        body = info.get("data", {})
        if info.get("ok") is not True or info.get("identity") != "user":
            raise ConnectionBlocked("connection_temporarily_unavailable")
        if body.get("open_id") != actor["feishu_user_id"] or body.get("tenant_key") != self.options["tenant_key"]:
            raise ConnectionBlocked("connection_identity_mismatch")
        # --verify fills expiry fields before refreshing in 1.0.90.
        return self.metadata(actor)

    def command(self, operation, principal):
        actor = self.actor(principal)
        with self.locked(principal) as db:
            row = self._row(db, principal)
            previous_version = row["version"]
            if operation == "disconnect":
                self._set(db, row, "disconnected", invalidate=True, device_code="", flow_expires=0)
            elif operation in {"connect", "reconnect"}:
                # Adopt only a first-use, operator-provisioned native login after
                # the same app/account/tenant verification as interactive enrollment.
                if operation == "connect" and (row["version"] == 0 or row["status"] == "connected"):
                    try:
                        user = self._verify_identity(actor)
                    except ConnectionBlocked as exc:
                        if exc.code != "connection_required":
                            raise
                    else:
                        initial = row["version"] == 0
                        self._set(db, row, "connected", invalidate=initial,
                                  expires=_timestamp(user["expiresAt"]), refresh_expires=_timestamp(user["refreshExpiresAt"]))
                        return {"status": "connected", "version": row["version"] + int(initial), "audience": "private", "reset": initial}
                return self._begin(db, row, actor)
            elif operation == "complete":
                self._complete(db, row, actor)
            elif operation == "status":
                if row["status"] in {"pending", "verifying"}:
                    self._complete(db, row, actor)
                elif row["status"] == "connected":
                    try:
                        self._verify_identity(actor)
                    except ConnectionBlocked as exc:
                        if exc.code not in {"connection_required", "connection_identity_mismatch"}:
                            raise
                        self._set(db, row, "reconnect_required", invalidate=True)
            elif operation != "check":
                raise ConnectionBlocked("connection_operation_denied")
            row = self._row(db, principal)
            return {"status": row["status"], "version": row["version"], "audience": "private",
                    "reset": row["version"] != previous_version}

    def _begin(self, db, row, actor):
        info = self._cli(actor["connection_profile"], ["auth", "status", "--json"])
        if info.get("appId") != self.options["app_id"]:
            raise ConnectionBlocked("connection_identity_mismatch")
        actual_user = info.get("identities", {}).get("user", {}).get("openId")
        if actual_user and actual_user != actor["feishu_user_id"]:
            if row["status"] != "wrong_account":
                raise ConnectionBlocked("connection_identity_mismatch")
            # Only our failed enrollment can clear this isolated CLI store.
            # An externally replaced profile remains blocked for operator review.
        # Clear this person's old native login before starting. This makes a
        # persisted user during pending unambiguously a completed new exchange,
        # including a process killed after the CLI saved it but before we did.
        status = "wrong_account" if row["status"] == "wrong_account" else "disconnected"
        self._set(db, row, status, invalidate=True, device_code="", flow_expires=0)
        row = db.execute("SELECT * FROM connections WHERE subject=?", (row["subject"],)).fetchone()
        if actual_user:
            self._cli(actor["connection_profile"], ["auth", "logout", "--json"])
            check = self._cli(actor["connection_profile"], ["auth", "status", "--json"])
            if check.get("appId") != self.options["app_id"] or check.get("identities", {}).get("user", {}).get("openId"):
                raise ConnectionBlocked("connection_identity_mismatch")
        data = self._cli(actor["connection_profile"], ["auth", "login", "--no-wait", "--json",
                         "--scope", " ".join(sorted(READ_SCOPES))])
        uri = data.get("verification_url")
        parsed = urlsplit(uri or "")
        if parsed.scheme != "https" or parsed.username or parsed.password or not (
                parsed.hostname == "feishu.cn" or (parsed.hostname or "").endswith(".feishu.cn")):
            raise ConnectionBlocked("connection_authorization_url_invalid")
        code = _text(data.get("device_code"))
        ttl = data.get("expires_in")
        if type(ttl) is not int or not 1 <= ttl <= 1800:
            raise ConnectionBlocked("connection_metadata_invalid")
        # Device code is a short-lived flow secret, never a user access/refresh token.
        row = db.execute("SELECT * FROM connections WHERE subject=?", (row["subject"],)).fetchone()
        self._set(db, row, "pending", device_code=code, flow_expires=self.now() + ttl)
        return {"status": "pending", "version": row["version"], "verification_url": uri,
                "qrcode_png": self.qrcode(actor["connection_profile"], uri),
                "expires_in": ttl, "audience": "private", "reset": True}

    def _complete(self, db, row, actor):
        if row["status"] not in {"pending", "verifying"}:
            return
        if row["status"] == "pending":
            info = self._cli(actor["connection_profile"], ["auth", "status", "--json"])
            if info.get("appId") != self.options["app_id"]:
                raise ConnectionBlocked("connection_identity_mismatch")
            if not info.get("identities", {}).get("user", {}).get("openId"):
                if row["flow_expires"] <= self.now():
                    self._set(db, row, "reconnect_required", device_code="", flow_expires=0)
                    return
                self._cli(actor["connection_profile"], ["auth", "login", "--json", "--device-code", row["device_code"]], timeout=12)
            self._set(db, row, "verifying", device_code="", flow_expires=0)
            row = db.execute("SELECT * FROM connections WHERE subject=?", (row["subject"],)).fetchone()
        try:
            user = self._verify_identity(actor)
        except ConnectionBlocked as exc:
            if exc.code == "connection_temporarily_unavailable":
                return
            status = "wrong_account" if exc.code == "connection_identity_mismatch" else "reconnect_required"
            self._set(db, row, status, invalidate=True, device_code="", flow_expires=0)
            return
        self._set(db, row, "connected", invalidate=True, device_code="", flow_expires=0,
                  expires=_timestamp(user["expiresAt"]), refresh_expires=_timestamp(user["refreshExpiresAt"]),
                  failures=0, retry_at=0)

    def require(self, principal, session_token):
        actor = self.actor(principal)
        if not isinstance(session_token, str) or len(session_token) < 32:
            raise ConnectionBlocked("connection_session_invalid")
        with self.locked(principal) as db:
            row = self._row(db, principal)
            if row["status"] != "connected":
                raise ConnectionBlocked("connection_required")
            try:
                self.metadata(actor)
            except ConnectionBlocked as exc:
                if exc.code in {"connection_required", "connection_identity_mismatch"}:
                    self._set(db, row, "reconnect_required", invalidate=True)
                raise
            session = hashlib.sha256(session_token.encode()).hexdigest()
            db.execute("INSERT OR IGNORE INTO connection_sessions VALUES(?,?,?)", (session, row["subject"], row["version"]))
            db.commit()
            bound = db.execute("SELECT * FROM connection_sessions WHERE session=?", (session,)).fetchone()
            if bound["subject"] != row["subject"] or bound["version"] != row["version"]:
                raise ConnectionBlocked("connection_session_expired")
            return dict(profile=row["profile"], version=row["version"], subject=row["subject"])

    def check_version(self, binding, *, require_connected=True):
        with self.database() as db:
            row = db.execute("SELECT * FROM connections WHERE subject=?", (binding["subject"],)).fetchone()
            if not row or (require_connected and row["status"] != "connected") or row["version"] != binding["version"]:
                raise ConnectionBlocked("connection_session_expired")

    def _bind_work(self, principal, work_id, *, private, requires_connection, binding=None):
        if not isinstance(work_id, str) or not work_id:
            raise ConnectionBlocked("personal_work_binding_required")
        with self.locked(principal) as db:
            row = self._row(db, principal)
            if binding and (row["status"] != "connected" or row["subject"] != binding["subject"]
                            or row["version"] != binding["version"]):
                raise ConnectionBlocked("connection_session_expired")
            inserted = db.execute("INSERT OR IGNORE INTO connection_work VALUES(?,?,?,?)",
                                  (work_id, row["subject"], row["version"], int(requires_connection))).rowcount
            bound = db.execute("SELECT * FROM connection_work WHERE work=?", (work_id,)).fetchone()
            if bound["subject"] != row["subject"]:
                raise ConnectionBlocked("personal_work_audience_denied")
            if bound["version"] != row["version"]:
                raise ConnectionBlocked("connection_session_expired")
            # Missing scope belongs to the old private-only schema. Never relabel it.
            if inserted:
                db.execute("INSERT INTO connection_work_scope VALUES(?,?)", (work_id, int(private)))
            elif private:
                db.execute("INSERT OR REPLACE INTO connection_work_scope VALUES(?,1)", (work_id,))
            if requires_connection:
                db.execute("UPDATE connection_work SET requires_connection=1 WHERE work=?", (work_id,))
            db.commit()

    def guard(self, command, principal, token, work_id, knowledge_subject=""):
        audience = self.route(principal)
        private_commands = {*READ_COMMANDS, "work-resume", "work-context", "file-deliver", "file-status",
                            "knowledge_catalog", "knowledge_search", "knowledge_read"}
        # Lifecycle dependence applies to every personal read, even shared data.
        if command in READ_COMMANDS | HANDOFF_STAGES | BANQUET_STAGES and audience == "private":
            if not work_id:
                raise ConnectionBlocked("personal_work_binding_required")
            binding = self.require(principal, token)
            self._bind_work(principal, work_id, private=self.options["resource_mode"] == "restricted",
                            requires_connection=True, binding=binding)
        if command in {"knowledge_catalog", "knowledge_search", "knowledge_read"} and knowledge_subject != "team":
            # The existing knowledge host reserves team for universally shared
            # pages. Other subjects stay private even if their reader can see them.
            if audience != "private" or not work_id:
                raise ConnectionBlocked("personal_work_audience_denied")
            self._bind_work(principal, work_id, private=True, requires_connection=False)
        with self.database() as db:
            bound = db.execute("SELECT w.*, COALESCE(s.private,1) AS private FROM connection_work w "
                               "LEFT JOIN connection_work_scope s ON w.work=s.work WHERE w.work=?", (work_id,)).fetchone()
        if not bound:
            return {"status": "allowed"}
        if audience != "private" or bound["subject"] != self.key(principal):
            raise ConnectionBlocked("personal_work_audience_denied")
        self.check_version(bound, require_connected=bool(bound["requires_connection"]))
        if bound["private"] and command not in private_commands:
            raise ConnectionBlocked("personal_work_sharing_denied")
        if bound["requires_connection"]:
            self.command("status", principal)
            self.check_version(bound)
        return {"status": "allowed", "private": bool(bound["private"])}

    def users(self, *, members=False):
        return list(dict.fromkeys(route.get("member_id", route["user_id"]) if members else route["user_id"]
                                 for route in self.options["routes"] if route["audience"] == "private"))

    def maintain(self, user_id, *, member=False):
        if user_id not in self.users(members=member):
            raise ConnectionBlocked("connection_route_denied")
        routes = [route for route in self.options["routes"] if route["audience"] == "private" and
                  (route.get("member_id", route["user_id"]) if member else route["user_id"]) == user_id]
        if len({route.get("member_id", route["user_id"]) for route in routes}) != 1:
            raise ConnectionBlocked("connection_route_denied")
        route = routes[0]
        with self.locked(route) as db:
            row = self._row(db, route)
            if row["status"] == "connected" and max(row["expires"] - 240, row["retry_at"]) <= self.now():
                try:
                    user = self._verify_identity(self.actor(route))
                    self._set(db, row, "connected", expires=_timestamp(user["expiresAt"]),
                              refresh_expires=_timestamp(user["refreshExpiresAt"]), retry_at=0, failures=0)
                except ConnectionBlocked as exc:
                    if exc.code in {"connection_required", "connection_identity_mismatch"} or row["refresh_expires"] <= self.now():
                        self._set(db, row, "reconnect_required", invalidate=True)
                    else:
                        delay = min(3600, 60 * 2 ** min(row["failures"], 6))
                        self._set(db, row, "connected", failures=row["failures"] + 1, retry_at=self.now() + delay)
            # Deliver the current generation even after a successful reconnect.
            # Consumers compare work bindings; only stale personal work is stopped.
            # Repeating this state survives interrupted calls and gateway restarts.
            row = self._row(db, route)
            return ([{"member_id" if member else "user_id": user_id, "status": row["status"], "version": row["version"]}]
                    if row["version"] else [])


def access(config, command, principal):
    """Run before any backend, navigation, old receipt or approval is opened."""
    if "personal_connections" not in config:
        return None
    connections = Connections(config)
    if not principal:
        if connections.options["resource_mode"] != "shared":
            raise ConnectionBlocked("restricted_resource_operation_denied")
        return None
    audience = connections.route(principal)
    if audience == "private" and command in READ_COMMANDS:
        return connections
    if connections.options["resource_mode"] != "shared" and not command.startswith("case-"):
        raise ConnectionBlocked("restricted_resource_operation_denied")
    if audience == "private" and command in BANQUET_STAGES:
        return connections
    return None


class PersonalReadRunner:
    """Only the existing backend's fixed Base read argv can reach a user CLI."""
    def __init__(self, connections, principal, token):
        self.connections, self.principal, self.token = connections, principal, token
        self.binding = connections.require(principal, token)

    def __call__(self, argv, **kwargs):
        args = list(argv[1:])
        if len(args) < 2 or args[0] != "base" or args[1] not in CLI_READ_COMMANDS:
            raise ConnectionBlocked("personal_read_only")
        if any(arg.split("=", 1)[0] in {"--profile", "--as", "--yes"} for arg in args):
            raise ConnectionBlocked("personal_identity_override_denied")
        self.connections.require(self.principal, self.token)
        self.connections.check_version(self.binding)
        kwargs["env"] = self.connections.environment(self.binding["profile"])
        with timing.measure("resource_cli"):
            completed = self.connections.run([self.connections.cli, *args, "--profile", self.binding["profile"], "--as", "user"], **kwargs)
        self.connections.check_version(self.binding)
        self.connections.require(self.principal, self.token)
        self.connections.check_version(self.binding)
        if completed.returncode:
            # A failed resource call may expose revocation while local expiry
            # metadata still says ready. Use the same identity check as status.
            self.connections.command("status", self.principal)
            self.connections.check_version(self.binding)
            try:
                envelope = json.loads(completed.stderr)
            except (ValueError, TypeError):
                envelope = None
            error = envelope.get("error") if isinstance(envelope, dict) else None
            if isinstance(error, dict):
                if error.get("type") == "authorization" and error.get("subtype") == "missing_scope":
                    with self.connections.locked(self.principal) as db:
                        row = self.connections._row(db, self.principal)
                        if row["version"] != self.binding["version"] or row["status"] != "connected":
                            raise ConnectionBlocked("connection_session_expired")
                        self.connections._set(db, row, "reconnect_required", invalidate=True)
                    raise ConnectionBlocked("connection_required")
                if error.get("type") == "api" and error.get("code") == 91403:
                    raise ConnectionBlocked("personal_read_permission_denied")
        return completed
