"""Deterministic staged follow-up workflow with host-owned approval."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import stat
import threading
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Protocol, Sequence

from . import write_locks


READBACK_TIMEOUT_SECONDS = 30.0
READBACK_INTERVAL_SECONDS = 1.0
CUSTOMER_TEXT_LIMITS = {"name": 256, "contact": 256, "phone": 64, "email": 254}
# After this interval an unfinished execution should be treated as operationally
# uncertain, but it is never reclaimed automatically. The old worker may still
# be inside a Feishu request, so starting a replacement cannot safely fence the
# external side effect.
APPROVAL_EXECUTION_UNCERTAIN_SECONDS = 15 * 60
_PRIVATE_DIR_MODE = 0o700
_PRIVATE_FILE_MODE = 0o600
_UMASK_LOCK = threading.Lock()


@contextmanager
def _private_umask() -> Iterator[None]:
    """Serialize the process-global umask while SQLite creates its files."""

    if os.name == "nt":
        yield
        return
    with _UMASK_LOCK:
        previous = os.umask(0o077)
        try:
            yield
        finally:
            os.umask(previous)


def _path_chain(path: Path) -> Iterator[Path]:
    current = Path(path.anchor)
    yield current
    for part in path.parts[1:]:
        current /= part
        yield current


def _validate_parent_chain(parent: Path, *, require_private_leaf: bool = True) -> None:
    """Reject replaceable/symlinked parents; require a private ledger leaf."""

    current_uid = os.geteuid() if hasattr(os, "geteuid") else None
    for component in _path_chain(parent):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("CRM ledger directory chain is not trustworthy.")
        if current_uid is None:
            continue
        mode = stat.S_IMODE(info.st_mode)
        if info.st_uid not in {0, current_uid}:
            raise ValueError("CRM ledger directory has an unexpected owner.")
        if mode & 0o022 and not mode & stat.S_ISVTX:
            raise ValueError("CRM ledger directory chain is replaceable.")
    leaf = parent.lstat()
    if require_private_leaf and current_uid is not None and (
        leaf.st_uid != current_uid or stat.S_IMODE(leaf.st_mode) != _PRIVATE_DIR_MODE
    ):
        raise ValueError("CRM ledger directory must be service-owned with mode 0700.")


def _prepare_ledger_parent(parent: Path) -> None:
    if parent.exists() or parent.is_symlink():
        _validate_parent_chain(parent)
        return
    # Create only the private leaf. Provisioning owns any broader hierarchy.
    if not parent.parent.is_dir():
        raise ValueError("CRM ledger parent hierarchy must already exist.")
    _validate_parent_chain(parent.parent, require_private_leaf=False)
    with _private_umask():
        parent.mkdir(mode=_PRIVATE_DIR_MODE, exist_ok=True)
    _validate_parent_chain(parent)


def _validate_private_file(path: Path) -> None:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError("CRM ledger storage must be a regular file.")
    if getattr(info, "st_nlink", 1) != 1:
        raise ValueError("CRM ledger storage must not have hard links.")
    if hasattr(os, "geteuid") and (
        info.st_uid != os.geteuid()
        or stat.S_IMODE(info.st_mode) != _PRIVATE_FILE_MODE
    ):
        raise ValueError("CRM ledger storage must be service-owned with mode 0600.")


def _create_private_file(path: Path) -> None:
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    flags |= getattr(os, "O_NOFOLLOW", 0)
    with _private_umask():
        descriptor = os.open(path, flags, _PRIVATE_FILE_MODE)
    os.close(descriptor)
    _validate_private_file(path)


class Backend(Protocol):
    """The small internal seam implemented by the Feishu and in-memory adapters."""

    def read_schema(self) -> Mapping[str, Any]: ...

    def find_customers(self, query: str) -> Sequence[Mapping[str, Any]]: ...

    def get_customer(self, record_id: str) -> Mapping[str, Any] | None: ...

    def find_followup_by_change(self, change_id: str) -> Mapping[str, Any] | None: ...

    def create_followup(self, fields: Mapping[str, Any]) -> str | Mapping[str, Any]: ...

    def update_customer(
        self, record_id: str, fields: Mapping[str, Any]
    ) -> Mapping[str, Any] | None: ...

    def get_followup(self, record_id: str) -> Mapping[str, Any] | None: ...

    def customer_url(self, record_id: str) -> str: ...

    def followup_url(self, record_id: str) -> str: ...


class Ledger:
    """SQLite staging ledger shared by successive one-shot CLI invocations."""

    def __init__(self, path: str | os.PathLike[str] = ":memory:") -> None:
        value = os.fspath(path)
        self._storage_path: Path | None = None
        self._owned_write_fences: set[str] = set()
        if value != ":memory:":
            storage_path = Path(value)
            if not storage_path.is_absolute():
                raise ValueError("CRM ledger path must be absolute.")
            _prepare_ledger_parent(storage_path.parent)
            if storage_path.exists() or storage_path.is_symlink():
                _validate_private_file(storage_path)
            else:
                _create_private_file(storage_path)
            self._storage_path = storage_path
        with _private_umask():
            self._db = sqlite3.connect(value, timeout=10)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        if self._storage_path is not None:
            # WAL sidecars are created while the private umask is active and
            # remain available for this one-shot process's later transactions.
            with _private_umask():
                self._db.execute("PRAGMA journal_mode = WAL")
        self._db.execute("PRAGMA synchronous = FULL")
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS staged_changes (
                change_id TEXT PRIMARY KEY,
                sender_id TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                action_token_hash TEXT,
                state TEXT NOT NULL,
                body_json TEXT NOT NULL,
                receipt_json TEXT
            )
            """
        )
        columns = {
            row["name"]
            for row in self._db.execute("PRAGMA table_info(staged_changes)")
        }
        if "action_token_hash" not in columns:
            self._db.execute(
                "ALTER TABLE staged_changes ADD COLUMN action_token_hash TEXT"
            )
        for name, declaration in (
            ("parent_change_id", "TEXT"),
            ("resolved_customer_record_id", "TEXT"),
            ("intent_version", "INTEGER"),
        ):
            if name not in columns:
                self._db.execute(f"ALTER TABLE staged_changes ADD COLUMN {name} {declaration}")
        self._db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS one_child_per_parent "
            "ON staged_changes(parent_change_id) WHERE parent_change_id IS NOT NULL"
        )
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS write_intents "
            "(scope TEXT PRIMARY KEY, generation INTEGER NOT NULL)"
        )
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS verified_assignees "
            "(ref TEXT PRIMARY KEY, scope TEXT NOT NULL, user_id TEXT NOT NULL, "
            "person_json TEXT NOT NULL, UNIQUE(scope, user_id))"
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS approvals (
                approval_id TEXT PRIMARY KEY,
                change_id TEXT NOT NULL,
                state TEXT NOT NULL,
                principal_json TEXT NOT NULL,
                preview_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                decided_at TEXT,
                decision TEXT,
                receipt_json TEXT,
                superseded_by TEXT,
                card_message_id TEXT,
                FOREIGN KEY (change_id) REFERENCES staged_changes(change_id)
            )
            """
        )
        approval_columns = {
            row["name"] for row in self._db.execute("PRAGMA table_info(approvals)")
        }
        if "card_message_id" not in approval_columns:
            self._db.execute(
                "ALTER TABLE approvals ADD COLUMN card_message_id TEXT"
            )
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS write_fences "
            "(scope_key TEXT PRIMARY KEY, change_id TEXT NOT NULL, "
            "FOREIGN KEY(change_id) REFERENCES staged_changes(change_id))"
        )
        from . import plans
        plans.initialize(self._db)
        self._db.commit()
        self._validate_storage()

    def stage(
        self, body: Mapping[str, Any], action_token_hash: str,
        *, intent_version: int | None = None,
    ) -> list[str]:
        encoded = _json(body)
        with self._immediate():
            principal = body.get("principal")
            if intent_version is not None and (
                not principal or self._intent_version(principal) != intent_version
            ):
                raise ValueError("A newer write intent superseded this request.")
            superseded_approvals = [
                row["approval_id"]
                for row in self._db.execute(
                    """
                    SELECT approvals.approval_id
                      FROM approvals
                      JOIN staged_changes USING (change_id)
                     WHERE staged_changes.action_token_hash = ?
                       AND (
                            approvals.state = 'pending'
                            OR (
                                approvals.state = 'superseded'
                                AND approvals.decision IS NULL
                                AND approvals.receipt_json IS NULL
                            )
                       )
                    """,
                    (action_token_hash,),
                )
            ]
            if superseded_approvals:
                placeholders = ",".join("?" for _ in superseded_approvals)
                self._db.execute(
                    f"""
                    UPDATE approvals
                       SET state = 'superseded', superseded_by = ?
                     WHERE approval_id IN ({placeholders})
                    """,
                    (body["change_id"], *superseded_approvals),
                )
            self._db.execute(
                """
                UPDATE staged_changes
                   SET state = 'superseded'
                 WHERE action_token_hash = ? AND state = 'staged'
                """,
                (action_token_hash,),
            )
            self._db.execute(
                """
                INSERT INTO staged_changes
                    (change_id, sender_id, chat_id, action_token_hash, state, body_json)
                VALUES (?, '', '', ?, 'staged', ?)
                """,
                (body["change_id"], action_token_hash, encoded),
            )
            self._db.execute(
                "UPDATE staged_changes SET intent_version = ? "
                "WHERE change_id = ?",
                (intent_version, body["change_id"]),
            )
        return superseded_approvals

    def get(self, change_id: str) -> dict[str, Any] | None:
        row = self._db.execute(
            """
            SELECT state, body_json, receipt_json, action_token_hash,
                   parent_change_id, resolved_customer_record_id, intent_version
              FROM staged_changes WHERE change_id = ?
            """,
            (change_id,),
        ).fetchone()
        if row is None:
            return None
        body = json.loads(row["body_json"])
        body["state"] = row["state"]
        body["receipt"] = json.loads(row["receipt_json"]) if row["receipt_json"] else None
        body["action_token_hash"] = row["action_token_hash"]
        for key in ("parent_change_id", "resolved_customer_record_id", "intent_version"):
            if row[key] is not None:
                body[key] = row[key]
        return body

    def planned_body(self, change_id: str) -> dict[str, Any] | None:
        """Return the immutable proposal without execution/storage metadata."""
        row = self._db.execute(
            "SELECT body_json FROM staged_changes WHERE change_id = ?", (change_id,),
        ).fetchone()
        return json.loads(row[0]) if row is not None else None

    def note_write_intent(self, principal: Mapping[str, str]) -> int:
        """Record a new user write request before potentially slow backend reads."""
        scope = self._principal_scope(principal)
        with self._immediate():
            self._db.execute(
                "INSERT INTO write_intents VALUES (?, 1) "
                "ON CONFLICT(scope) DO UPDATE SET generation = generation + 1", (scope,),
            )
            return self._intent_version(principal)

    @staticmethod
    def _principal_scope(principal: Mapping[str, str]) -> str:
        return _hash({key: principal[key] for key in _PRINCIPAL_BINDING_KEYS})

    def _intent_version(self, principal: Mapping[str, str]) -> int:
        row = self._db.execute(
            "SELECT generation FROM write_intents WHERE scope = ?",
            (self._principal_scope(principal),),
        ).fetchone()
        return 0 if row is None else row[0]

    def remember_assignee(self, principal: Mapping[str, str], person: Mapping[str, str]) -> str:
        scope = self._principal_scope(principal)
        user_id = _required_text(person.get("id"), "assignee.id")
        name = _required_text(person.get("name"), "assignee.name")
        with self._immediate():
            self._db.execute(
                "INSERT INTO verified_assignees VALUES (?, ?, ?, ?) "
                "ON CONFLICT(scope, user_id) DO UPDATE SET person_json = excluded.person_json",
                ("own_" + secrets.token_urlsafe(18), scope, user_id,
                 _json({"id": user_id, "name": name})),
            )
            return self._db.execute(
                "SELECT ref FROM verified_assignees WHERE scope = ? AND user_id = ?",
                (scope, user_id),
            ).fetchone()[0]

    def get_assignee(self, ref: str, principal: Mapping[str, str]) -> dict[str, str] | None:
        row = self._db.execute(
            "SELECT person_json FROM verified_assignees WHERE ref = ? AND scope = ?",
            (ref, self._principal_scope(principal)),
        ).fetchone()
        return None if row is None else json.loads(row[0])

    def find_assignees(self, query: str, principal: Mapping[str, str]) -> list[dict[str, str]]:
        rows = self._db.execute(
            "SELECT ref, person_json FROM verified_assignees WHERE scope = ? ORDER BY ref",
            (self._principal_scope(principal),),
        ).fetchall()
        result = []
        for row in rows:
            person = json.loads(row["person_json"])
            if _normal(query) == _normal(person["name"]):
                result.append({"ref": row["ref"], **person})
        return result

    def set_resolved_customer(self, change_id: str, record_id: str) -> None:
        record_id = _required_text(record_id, "record_id")
        with self._immediate():
            row = self._db.execute(
                "SELECT resolved_customer_record_id FROM staged_changes WHERE change_id = ?",
                (change_id,),
            ).fetchone()
            if row is None or row[0] not in (None, record_id):
                raise ValueError("The verified customer binding cannot be replaced.")
            self._db.execute(
                "UPDATE staged_changes SET resolved_customer_record_id = ? WHERE change_id = ?",
                (record_id, change_id),
            )

    def child_change_id(self, parent_change_id: str) -> str | None:
        row = self._db.execute(
            "SELECT change_id FROM staged_changes WHERE parent_change_id = ?", (parent_change_id,),
        ).fetchone()
        return None if row is None else row[0]

    def stage_child(
        self, parent_change_id: str, body: Mapping[str, Any], now: str,
    ) -> dict[str, Any] | None:
        """Publish one frozen child; never supersede a later user write intent."""
        with self._immediate():
            parent = self.get(parent_change_id)
            if parent is None or parent["state"] != "verified":
                raise ValueError("A verified parent is required.")
            if self.child_change_id(parent_change_id) is not None:
                return None  # Replays do not publish a second card.
            principal = parent["principal"]
            if parent.get("intent_version") != self._intent_version(principal):
                return None
            child = {**body, "parent_change_id": parent_change_id,
                     "principal": principal, "actor": parent["actor"]}
            approval_id = "apr_" + secrets.token_urlsafe(18)
            self._db.execute(
                "INSERT INTO staged_changes "
                "(change_id,sender_id,chat_id,action_token_hash,state,body_json,"
                "parent_change_id,intent_version) VALUES (?,?,?,?,'staged',?,?,?)",
                (child["change_id"], principal["user_id"], principal["chat_id"],
                 parent["action_token_hash"], _json(child), parent_change_id,
                 parent["intent_version"]),
            )
            self._db.execute(
                "INSERT INTO approvals (approval_id,change_id,state,principal_json,"
                "preview_hash,created_at,expires_at) VALUES (?,?,'pending',?,?,?,?)",
                (approval_id, child["change_id"], _json(principal),
                 _hash(_approval_material(child)), now, child["expires_at"]),
            )
            return self.get_approval(approval_id)

    def bind_approval(
        self,
        change_id: str,
        action_token_hash: str,
        principal: Mapping[str, str],
        actor: Mapping[str, str],
        preview_hash: str,
        now: str,
    ) -> tuple[dict[str, Any] | None, list[str]]:
        """Bind a staged change to one host-authenticated principal, once."""

        with self._immediate():
            row = self._db.execute(
                "SELECT * FROM staged_changes WHERE change_id = ?", (change_id,)
            ).fetchone()
            if row is None or row["action_token_hash"] is None:
                return None, []
            if not hmac.compare_digest(row["action_token_hash"], action_token_hash):
                return None, []
            existing = self._db.execute(
                """
                SELECT * FROM approvals WHERE change_id = ?
                 ORDER BY rowid DESC LIMIT 1
                """,
                (change_id,),
            ).fetchone()
            if existing is not None:
                existing_approval = self._approval_row(existing)
                return existing_approval, self._superseded_by(change_id)
            if row["state"] != "staged":
                return None, self._superseded_by(change_id)
            if row["intent_version"] is not None and (
                row["intent_version"] != self._intent_version(principal)
            ):
                return None, self._superseded_by(change_id)

            self._supersede_other_approvals(change_id, principal)
            body = json.loads(row["body_json"])
            body["principal"] = dict(principal)
            body["actor"] = dict(actor)
            approval_id = "apr_" + secrets.token_urlsafe(18)
            self._db.execute(
                """
                UPDATE staged_changes
                   SET sender_id = ?, chat_id = ?, body_json = ?
                 WHERE change_id = ? AND state = 'staged'
                """,
                (principal["user_id"], principal["chat_id"], _json(body), change_id),
            )
            self._db.execute(
                """
                INSERT INTO approvals
                    (approval_id, change_id, state, principal_json, preview_hash,
                     created_at, expires_at)
                VALUES (?, ?, 'pending', ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    change_id,
                    _json(principal),
                    preview_hash,
                    now,
                    body["expires_at"],
                ),
            )
            created = self._db.execute(
                "SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)
            ).fetchone()
        return self._approval_row(created), self._superseded_by(change_id)

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        row = self._db.execute(
            "SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)
        ).fetchone()
        return None if row is None else self._approval_row(row)

    def get_approval_for_change(self, change_id: str) -> dict[str, Any] | None:
        row = self._db.execute(
            """
            SELECT * FROM approvals WHERE change_id = ?
             ORDER BY rowid DESC LIMIT 1
            """,
            (change_id,),
        ).fetchone()
        return None if row is None else self._approval_row(row)

    def latest_change_for_customer(
        self, principal: Mapping[str, str], customer_record_id: str
    ) -> str | None:
        """Latest created change for this customer and transport principal, not event time."""

        # ponytail: JSON predicates scan the small private ledger; index bound columns if it grows.
        row = self._db.execute(
            """
            SELECT staged.change_id
              FROM staged_changes AS staged
              JOIN approvals AS approval ON approval.change_id = staged.change_id
             WHERE COALESCE(staged.resolved_customer_record_id,
                            json_extract(staged.body_json, '$.customer_record_id')) = ?
               AND json_extract(approval.principal_json, '$.platform') = ?
               AND json_extract(approval.principal_json, '$.user_id') = ?
               AND json_extract(approval.principal_json, '$.chat_id') = ?
               AND json_extract(approval.principal_json, '$.session_key') = ?
               AND json_extract(approval.principal_json, '$.project') = ?
             ORDER BY staged.rowid DESC, approval.rowid DESC LIMIT 1
            """,
            (customer_record_id, *(principal[key] for key in _PRINCIPAL_BINDING_KEYS)),
        ).fetchone()
        return None if row is None else row["change_id"]

    def claim_approval(self, approval_id: str, decided_at: str) -> bool:
        with self._db:
            cursor = self._db.execute(
                """
                UPDATE approvals
                   SET state = 'executing', decision = 'approve', decided_at = ?
                 WHERE approval_id = ? AND state = 'pending'
                """,
                (decided_at, approval_id),
            )
        return cursor.rowcount == 1

    def bind_card_message(self, approval_id: str, message_id: str) -> bool:
        """Persist the first trusted card message ID and reject another card."""

        with self._immediate():
            row = self._db.execute(
                "SELECT card_message_id FROM approvals WHERE approval_id = ?",
                (approval_id,),
            ).fetchone()
            if row is None:
                return False
            current = row["card_message_id"]
            if current is not None:
                return hmac.compare_digest(current, message_id)
            cursor = self._db.execute(
                """
                UPDATE approvals SET card_message_id = ?
                 WHERE approval_id = ? AND card_message_id IS NULL
                """,
                (message_id, approval_id),
            )
            return cursor.rowcount == 1

    def create_repair_approval(
        self,
        change_id: str,
        principal: Mapping[str, str],
        action_token_hash: str,
        preview_hash: str,
        created_at: str,
        expires_at: str,
    ) -> tuple[dict[str, Any] | None, bool]:
        with self._immediate():
            latest = self._db.execute(
                """
                SELECT * FROM approvals WHERE change_id = ?
                 ORDER BY rowid DESC LIMIT 1
                """,
                (change_id,),
            ).fetchone()
            if latest is None or not _same_principal(
                json.loads(latest["principal_json"]), principal
            ):
                return None, False
            rebound = self._db.execute(
                """
                UPDATE staged_changes
                   SET action_token_hash = ?
                 WHERE change_id = ? AND state = 'partial'
                """,
                (action_token_hash, change_id),
            )
            if rebound.rowcount != 1:
                return None, False
            if latest["state"] == "pending":
                return self._approval_row(latest), False
            if latest["state"] not in {
                "partial",
                "cancelled",
                "superseded",
                "expired",
            }:
                return None, False
            approval_id = "apr_" + secrets.token_urlsafe(18)
            self._db.execute(
                """
                INSERT INTO approvals
                    (approval_id, change_id, state, principal_json, preview_hash,
                     created_at, expires_at)
                VALUES (?, ?, 'pending', ?, ?, ?, ?)
                """,
                (
                    approval_id,
                    change_id,
                    _json(principal),
                    preview_hash,
                    created_at,
                    expires_at,
                ),
            )
            created = self._db.execute(
                "SELECT * FROM approvals WHERE approval_id = ?", (approval_id,)
            ).fetchone()
        return self._approval_row(created), True

    def finish_approval(
        self,
        approval_id: str,
        state: str,
        decision: str,
        decided_at: str,
        receipt: Mapping[str, Any],
    ) -> None:
        with self._db:
            self._db.execute(
                """
                UPDATE approvals
                   SET state = ?, decision = ?, decided_at = ?, receipt_json = ?
                 WHERE approval_id = ?
                """,
                (state, decision, decided_at, _json(receipt), approval_id),
            )

    def close_approval(
        self,
        approval_id: str,
        state: str,
        decision: str,
        decided_at: str,
        receipt: Mapping[str, Any],
    ) -> bool:
        with self._db:
            cursor = self._db.execute(
                """
                UPDATE approvals
                   SET state = ?, decision = ?, decided_at = ?, receipt_json = ?
                 WHERE approval_id = ? AND state = 'pending'
                """,
                (state, decision, decided_at, _json(receipt), approval_id),
            )
        return cursor.rowcount == 1

    def expire_approval(self, approval_id: str, decided_at: str) -> bool:
        with self._db:
            cursor = self._db.execute(
                """
                UPDATE approvals
                   SET state = 'expired', decided_at = ?
                 WHERE approval_id = ? AND state = 'pending'
                """,
                (decided_at, approval_id),
            )
        return cursor.rowcount == 1

    def _superseded_by(self, change_id: str) -> list[str]:
        return [
            row["approval_id"]
            for row in self._db.execute(
                "SELECT approval_id FROM approvals WHERE superseded_by = ?",
                (change_id,),
            )
        ]

    def _supersede_other_approvals(
        self, current_change_id: str, principal: Mapping[str, str]
    ) -> None:
        """Close unresolved cards for this transport principal inside the caller's txn."""

        candidates = self._db.execute(
            """
            SELECT approval_id, change_id, principal_json
              FROM approvals
             WHERE change_id != ?
               AND (
                    state = 'pending'
                    OR (
                        state = 'superseded'
                        AND decision IS NULL
                        AND receipt_json IS NULL
                    )
               )
            """,
            (current_change_id,),
        )
        stale = [
            row
            for row in candidates
            if _same_principal(json.loads(row["principal_json"]), principal)
        ]
        if not stale:
            return
        approval_ids = [row["approval_id"] for row in stale]
        approval_slots = ",".join("?" for _ in approval_ids)
        self._db.execute(
            f"""
            UPDATE approvals
               SET state = 'superseded', superseded_by = ?
             WHERE approval_id IN ({approval_slots})
            """,
            (current_change_id, *approval_ids),
        )
        change_ids = list({row["change_id"] for row in stale})
        change_slots = ",".join("?" for _ in change_ids)
        self._db.execute(
            f"""
            UPDATE staged_changes
               SET state = 'superseded'
             WHERE state = 'staged' AND change_id IN ({change_slots})
            """,
            change_ids,
        )

    @staticmethod
    def _approval_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "approval_id": row["approval_id"],
            "change_id": row["change_id"],
            "state": row["state"],
            "principal": json.loads(row["principal_json"]),
            "preview_hash": row["preview_hash"],
            "created_at": row["created_at"],
            "expires_at": row["expires_at"],
            "decided_at": row["decided_at"],
            "decision": row["decision"],
            "receipt": json.loads(row["receipt_json"]) if row["receipt_json"] else None,
            "superseded_by": row["superseded_by"],
            "card_message_id": row["card_message_id"],
        }

    def claim(self, change_id: str) -> bool:
        with self._db:
            cursor = self._db.execute(
                """
                UPDATE staged_changes SET state = 'applying'
                 WHERE change_id = ? AND state = 'staged'
                """,
                (change_id,),
            )
        return cursor.rowcount == 1

    def finish(self, change_id: str, state: str, receipt: Mapping[str, Any]) -> None:
        with self._immediate():
            if state == "verified":
                from . import plans
                staged = self.get(change_id)
                if staged is not None:
                    plans.finish(self, staged, receipt)
            self._db.execute(
                """
                UPDATE staged_changes SET state = ?, receipt_json = ?
                 WHERE change_id = ?
                """,
                (state, _json(receipt), change_id),
            )
            approval_state = _approval_terminal_state(state)
            self._db.execute(
                "UPDATE approvals SET state = ?, receipt_json = ? "
                "WHERE change_id = ? AND state = 'executing' AND decision = 'approve'",
                (approval_state, _json(receipt), change_id),
            )
            if change_id in self._owned_write_fences and state in {
                "verified", "failed", "replan_required", "expired",
            }:
                self._db.execute("DELETE FROM write_fences WHERE change_id = ?", (change_id,))

    @contextmanager
    def customer_write(self, staged: Mapping[str, Any]) -> Iterator[None]:
        """A process owns a fence only if it created it while holding all OS locks."""
        scopes = _write_scopes(staged)
        directory = None
        try:
            if self._storage_path is not None:
                directory = self._storage_path.with_name(self._storage_path.name + ".locks")
                _prepare_ledger_parent(directory)
            locks = write_locks.acquire(directory, scopes)
            locks.__enter__()
        except write_locks.WriteBlocked:
            raise
        except (OSError, ValueError) as exc:
            raise write_locks.WriteBlocked("crm_write_lock_unavailable", "CRM write protection is unavailable; no write was started.") from exc
        try:
            with self._immediate():
                slots = ",".join("?" for _ in scopes)
                if self._db.execute(f"SELECT 1 FROM write_fences WHERE scope_key IN ({slots}) LIMIT 1", scopes).fetchone():
                    raise write_locks.WriteBlocked("crm_write_unresolved", "A previous operation needs operator verification; this operation has not written anything.")
                self._db.executemany("INSERT INTO write_fences(scope_key, change_id) VALUES (?, ?)",
                                     [(scope, staged["change_id"]) for scope in scopes])
            self._owned_write_fences.add(staged["change_id"])
            yield
        finally:
            self._owned_write_fences.discard(staged["change_id"])
            locks.__exit__(None, None, None)

    def close(self) -> None:
        self._db.close()
        self._validate_storage()

    @contextmanager
    def _immediate(self) -> Iterator[None]:
        self._validate_storage()
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self._db.rollback()
            self._validate_storage()
            raise
        else:
            self._db.commit()
            self._validate_storage()

    def _validate_storage(self) -> None:
        if self._storage_path is None:
            return
        _validate_parent_chain(self._storage_path.parent)
        _validate_private_file(self._storage_path)
        for suffix in ("-journal", "-wal", "-shm"):
            sidecar = Path(os.fspath(self._storage_path) + suffix)
            if sidecar.exists() or sidecar.is_symlink():
                _validate_private_file(sidecar)


_DISPLAY_FIELDS = (
    "customer_number",
    "name",
    "contact",
    "phone",
    "email",
    "stage",
    "owner",
    "last_followup_at",
    "last_followup_content",
    "next_action",
    "next_followup_at",
    "updated_at",
)
_UNTOUCHED_FIELDS = ("contact", "phone", "email", "stage", "owner")
_CHANNELS = frozenset({"电话", "微信", "飞书", "邮件", "面谈", "其他"})
_FENCE_OPEN = "<CRM_DATA>"
_FENCE_CLOSE = "</CRM_DATA>"
_FORGED_TAG = re.compile(
    r"</?(?:crm_data|system|assistant|user|tool|tool_result|tool_use)(?:\s[^>]*)?>",
    re.IGNORECASE,
)
# The ASCII, small and fullwidth forms are the NFKC equivalents of < and >.
# Consume an unterminated suffix too, avoiding repeated scans of nested openers.
_TAG_LIKE = re.compile(r"[<﹤＜][^>﹥＞]*(?:[>﹥＞]|$)")
_PRINCIPAL_KEYS = {
    "platform",
    "user_id",
    "chat_id",
    "session_key",
    "project",
    "message_id",
}
_PRINCIPAL_BINDING_KEYS = (
    "platform",
    "user_id",
    "chat_id",
    "session_key",
    "project",
)


def stage_followup(
    command: Mapping[str, Any],
    backend: Backend,
    ledger: Ledger,
    config: Mapping[str, Any],
    action_token: str,
    now: datetime | None = None,
    *,
    trusted_principal: Mapping[str, str] | None = None,
    trusted_record_id: str | None = None,
    trusted_plan_binding: Mapping[str, str] | None = None,
    trusted_expected_plan_revision: int | None = None,
    trusted_expected_plan_target: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Read and stage one follow-up.  This function never writes to Feishu."""

    intent_version = None
    if trusted_principal is not None:
        try:
            trusted_principal = _principal(trusted_principal)
            _actor_for_principal(trusted_principal, config)
            intent_version = ledger.note_write_intent(trusted_principal)
        except (TypeError, ValueError):
            return _blocked("invalid_principal", "The transport identity is not configured.")
    try:
        moment = _now(now)
        _only_keys(
            command,
            {
                "customer_query",
                "occurred_at",
                "channel",
                "content",
                "next_action",
                "next_followup_at",
                "remind",
                "backfill",
            },
        )
        action_token_hash = _action_token_hash(action_token)
        query = _required_text(command.get("customer_query"), "customer_query", 256)
        if not command.get("occurred_at"):
            return {
                "status": "needs_time",
                "code": "followup_time_required",
                "message": "Ask for the follow-up time before staging; Feishu is unchanged.",
            }
        followup = _followup(
            {
                key: command[key]
                for key in (
                    "occurred_at",
                    "channel",
                    "content",
                    "next_action",
                    "next_followup_at",
                    "remind",
                    "backfill",
                )
                if key in command
            }
        )
        ttl = int(config.get("ttl_seconds", 600))
        if ttl <= 0:
            raise ValueError("ttl_seconds must be positive")
    except (TypeError, ValueError) as exc:
        return _blocked("invalid_request", str(exc))

    try:
        schema = _mapping(backend.read_schema(), "schema")
        if trusted_record_id is None:
            matches, matched_by = _resolve_customer(query, backend)
        else:
            # Only the host's verified parent can supply this internal argument.
            selected = backend.get_customer(trusted_record_id)
            matches, matched_by = ([] if selected is None else [selected]), "verified_parent"
    except Exception:
        return _blocked("backend_read_failed", "CRM could not be read; nothing was staged.")

    if not matches:
        return {
            "status": "not_found",
            "code": "customer_not_found",
            "customer_query": query,
            "message": "No exact customer number or normalized customer name matched.",
        }
    if len(matches) > 1:
        return {
            "status": "needs_selection",
            "code": "customer_ambiguous",
            "matched_by": matched_by,
            "candidates": [_display_customer(row, backend) for row in matches],
            "message": "Use one exact customer number or an unambiguous exact name.",
        }

    candidate = matches[0]
    record_id = _record_id(candidate)
    try:
        customer = backend.get_customer(record_id)
        customer = _mapping(customer, "customer") if customer is not None else None
        if customer is None:
            return _blocked("customer_disappeared", "The selected customer no longer exists.")
        _validate_customer(customer)
        canonical_snapshot = _snapshot(customer)
        patch = _customer_patch(customer, followup)
        from . import plans
        if "next_followup_at" in patch:
            patch["next_followup_at"] = plans.normalize_time(command["next_followup_at"], customer.get("next_followup_at"))
            followup["next_followup_at"] = patch["next_followup_at"]
        plan = plans.freeze(customer, patch, command, ledger, config, moment,
                            binding=trusted_plan_binding, expected_revision=trusted_expected_plan_revision,
                            expected_target=trusted_expected_plan_target,
                            historical=bool(followup.get("backfill")) or not patch)
        if trusted_principal is not None:
            plans.verify_binding(plan, trusted_principal)
        change_id = "chg_" + secrets.token_urlsafe(18)
        created_at = _iso(moment)
        expires_at = _iso(moment + timedelta(seconds=ttl))
        body = {
            "change_id": change_id,
            "customer_query": query,
            "matched_by": matched_by,
            "customer_record_id": record_id,
            "customer_number": customer.get("customer_number"),
            "customer_snapshot": {
                "record_id": record_id,
                **canonical_snapshot,
            },
            "schema_hash": _hash(schema),
            "snapshot_hash": _hash(canonical_snapshot),
            "before": {field: canonical_snapshot.get(field) for field in patch},
            "followup": followup,
            "customer_patch": patch,
            "created_at": created_at,
            "expires_at": expires_at,
        }
        if trusted_principal is not None:
            body["principal"] = dict(trusted_principal)
        if plan is not None:
            body["plan"] = plan
        ledger.stage(body, action_token_hash, intent_version=intent_version)
    except (TypeError, ValueError) as exc:
        return _blocked("invalid_backend_data", str(exc))
    except Exception:
        return _blocked("staging_failed", "The preview could not be staged; Feishu is unchanged.")

    return {
        "status": "staged",
        "change_id": change_id,
        "expires_at": expires_at,
        "matched_by": matched_by,
        "customer": _display_customer(customer, backend),
        "effects": {
            "followup": {"action": "create", "after": followup},
            "customer": {
                "action": "update" if patch else "no_change",
                "changes": _field_changes(canonical_snapshot, patch),
            },
        },
        "untouched_fields": list(_UNTOUCHED_FIELDS),
        "message": "Staged only. Feishu has not been changed.",
        **plans.preview(body),
    }


def apply_followup(
    command: Mapping[str, Any],
    backend: Backend,
    ledger: Ledger,
    config: Mapping[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """The model-visible apply path is permanently closed."""

    return _blocked(
        "host_approval_required",
        "Only the authenticated gateway host can apply a staged CRM change.",
    )


def begin_approval(
    command: Mapping[str, Any],
    backend: Backend,
    ledger: Ledger,
    config: Mapping[str, Any],
    action_token: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Bind one staged preview to a host-authenticated transport principal."""

    try:
        moment = _now(now)
        _only_keys(command, {"change_id", "principal"})
        change_id = _opaque_id(command.get("change_id"), "change_id", "chg_")
        principal = _principal(command.get("principal"))
        actor = _actor_for_principal(principal, config)
        token_hash = _action_token_hash(action_token)
    except (TypeError, ValueError) as exc:
        return _blocked("invalid_host_request", str(exc))

    try:
        staged = ledger.get(change_id)
    except Exception:
        return _blocked("ledger_unavailable", "The staged change could not be read.")
    if staged is None:
        return _blocked("unknown_change", "Stage this follow-up again.")
    if staged["state"] == "partial":
        approval = ledger.get_approval_for_change(change_id)
        if (
            approval is None
            or not _same_principal(approval["principal"], principal)
            or staged.get("actor") != actor
        ):
            return _blocked(
                "principal_mismatch",
                "Only the original sender can approve repair of this partial change.",
            )
        if approval["state"] in {"partial", "cancelled", "superseded", "expired"}:
            try:
                ttl = int(config.get("ttl_seconds", 600))
                if ttl <= 0:
                    raise ValueError("ttl_seconds must be positive")
                preview_hash = _hash(_approval_material(staged))
                approval, created = ledger.create_repair_approval(
                    change_id,
                    principal,
                    token_hash,
                    preview_hash,
                    _iso(moment),
                    _iso(moment + timedelta(seconds=ttl)),
                )
            except (TypeError, ValueError):
                return _blocked("invalid_configuration", "Approval TTL is invalid.")
            except Exception:
                return _blocked("ledger_unavailable", "The repair approval could not be persisted.")
            if approval is None or approval["state"] != "pending":
                return _blocked("approval_bind_failed", "The repair approval was not reopened.")
            replayed = not created
        elif approval["state"] != "pending":
            return _blocked(
                "change_not_pending", "This partial change is not awaiting repair approval."
            )
        else:
            replayed = True
        return _approval_begin_result(approval, staged, backend, [], replayed)
    if not isinstance(staged.get("action_token_hash"), str) or not hmac.compare_digest(
        staged["action_token_hash"], token_hash
    ):
        return _blocked(
            "session_mismatch",
            "The staged change does not belong to this gateway session.",
        )
    if staged["state"] != "staged":
        return _blocked(
            "change_not_pending", "This staged change is no longer available for approval."
        )
    if moment > _parse_time(staged["expires_at"], "expires_at"):
        result = _blocked("expired", "The preview expired; stage this follow-up again.")
        ledger.finish(change_id, "expired", result)
        return result

    bound = {**staged, "principal": principal, "actor": actor}
    try:
        from . import plans
        plans.verify_binding(staged.get("plan"), principal)
    except (ValueError, TypeError) as exc:
        return _blocked("plan_route_mismatch", str(exc))
    preview_hash = _hash(_approval_material(bound))
    try:
        replayed = ledger.get_approval_for_change(change_id) is not None
        approval, superseded = ledger.bind_approval(
            change_id,
            token_hash,
            principal,
            actor,
            preview_hash,
            _iso(moment),
        )
        staged = ledger.get(change_id)
    except Exception:
        return _blocked("ledger_unavailable", "The approval could not be persisted.")
    if approval is None or staged is None:
        return _blocked("approval_bind_failed", "The staged change was not bound.")
    if not _same_principal(approval["principal"], principal):
        return _blocked(
            "principal_mismatch",
            "This change is already bound to a different sender or conversation.",
        )
    if approval["preview_hash"] != _hash(_approval_material(staged)):
        return _blocked("preview_changed", "The stored preview changed before approval.")
    return _approval_begin_result(approval, staged, backend, superseded, replayed)


def claim_approval_decision(
    command: Mapping[str, Any],
    ledger: Ledger,
    config: Mapping[str, Any],
    now: datetime | None = None,
    *,
    backend: Backend | None = None,
) -> dict[str, Any]:
    """Authorize one card decision and atomically claim an approved write."""

    try:
        moment = _now(now)
        _only_keys(command, {"approval_id", "decision", "principal"})
        approval_id = _opaque_id(command.get("approval_id"), "approval_id", "apr_")
        decision = _required_text(command.get("decision"), "decision")
        if decision not in {"approve", "modify", "cancel"}:
            raise ValueError("decision must be approve, modify, or cancel")
        principal = _principal(command.get("principal"))
        actor = _actor_for_principal(principal, config)
    except (TypeError, ValueError) as exc:
        return _blocked("invalid_host_request", str(exc))

    try:
        approval = ledger.get_approval(approval_id)
    except Exception:
        return _failed("ledger_unavailable", "The approval could not be read.")
    if approval is None:
        return _blocked("unknown_approval", "This approval does not exist.")
    if not _same_principal(approval["principal"], principal):
        return _blocked(
            "principal_mismatch",
            "Only the same sender in the same conversation may decide this approval.",
        )
    staged = ledger.get(approval["change_id"])
    if staged is None or staged.get("actor") != actor:
        return _blocked("binding_changed", "The bound CRM actor is no longer valid.")
    card_message_id = approval.get("card_message_id")
    if not isinstance(card_message_id, str) or not card_message_id:
        return _blocked(
            "card_unbound",
            "The gateway has not bound this approval to an emitted card.",
        )
    if not hmac.compare_digest(card_message_id, principal["message_id"]):
        return _blocked(
            "card_mismatch",
            "This decision did not come from the original approval card.",
        )
    if approval["state"] in {"cancelled", "superseded", "expired"}:
        return {
            **(approval["receipt"] or {}),
            "status": approval["state"],
            "approval_id": approval_id,
            "change_id": approval["change_id"],
            "replayed": True,
            "message": "This approval is already closed; Feishu was not changed.",
            **_closed_approval_context(staged, ledger),
        }
    if approval["receipt"] is not None:
        return {
            **approval["receipt"],
            "approval_id": approval_id,
            "approval_state": approval["state"],
            "replayed": True,
        }
    resuming = approval["state"] == "executing"
    if resuming:
        started = _parse_time(approval["decided_at"], "decided_at")
        uncertain = moment >= started + timedelta(
            seconds=APPROVAL_EXECUTION_UNCERTAIN_SECONDS
        )
        return {
            "status": "executing",
            "code": (
                "execution_result_unknown" if uncertain else "apply_in_progress"
            ),
            "approval_id": approval_id,
            "approval_state": "executing",
            "change_id": approval["change_id"],
            "execute": False,
            "message": (
                "The original worker has not produced a receipt; reconcile the CRM before any retry."
                if uncertain
                else "The approved write is already executing and can no longer be changed or cancelled."
            ),
        }
    if not resuming and moment > _parse_time(approval["expires_at"], "expires_at"):
        if not ledger.expire_approval(approval_id, _iso(moment)):
            return claim_approval_decision(command, ledger, config, moment, backend=backend)
        if staged["state"] != "partial":
            ledger.finish(
                approval["change_id"],
                "expired",
                _replan(approval["change_id"], "expired", "Stage this follow-up again."),
            )
        return {
            "status": "expired",
            "approval_id": approval_id,
            "change_id": approval["change_id"],
            "message": "The approval expired; Feishu was not changed.",
            **_closed_approval_context(staged, ledger),
        }
    if approval["preview_hash"] != _hash(_approval_material(staged)):
        return _blocked("preview_changed", "The approved preview no longer matches the ledger.")

    if decision != "approve":
        state = "superseded" if decision == "modify" else "cancelled"
        result = {
            "status": state,
            "approval_id": approval_id,
            "change_id": approval["change_id"],
            "message": "Feishu was not changed.",
        }
        result.update(_closed_approval_context(staged, ledger))
        if not ledger.close_approval(
            approval_id, state, decision, _iso(moment), result
        ):
            return claim_approval_decision(command, ledger, config, moment, backend=backend)
        if staged["state"] != "partial":
            ledger.finish(approval["change_id"], state, result)
        return result

    # Pure presentation from fingerprint-checked ledger fields. Backend is
    # used only for local record-link formatting, never for a fresh read.
    preview = _approval_preview(staged, backend)
    if approval["state"] == "pending" and not ledger.claim_approval(
        approval_id, _iso(moment)
    ):
        return claim_approval_decision(command, ledger, config, moment, backend=backend)
    if approval["state"] not in {"pending", "executing"}:
        return _blocked("approval_not_pending", "This approval cannot be executed.")

    file_check = {}
    if staged.get("operation_type", "").startswith("banquet_handoff_"):
        from .handoffs import file_check as handoff_file_check
        file_check = {"file_check": handoff_file_check(staged)}
    return {
        "status": "executing",
        "approval_id": approval_id,
        "approval_state": "executing",
        "change_id": approval["change_id"],
        "execute": True,
        "preview": preview,
        **file_check,
        "message": "The approval was accepted and the original plan is executing.",
    }


def _closed_approval_context(staged, ledger):
    context = {}
    if staged.get("parent_change_id"):
        parent = ledger.get(staged["parent_change_id"])
        if parent is None:
            context["message"] = "本次跟进审批已关闭；无法读取关联客户操作结果，请人工核对。"
        else:
            context.update(
                message="客户操作已成功；本次跟进审批已关闭，不撤销已完成的客户操作。",
                parent_operation={"change_id": parent["change_id"], "status": parent["state"],
                                  "receipt": parent["receipt"]},
            )
    if staged["state"] == "partial":
        receipt = staged.get("receipt") or {}
        context.update({key: receipt[key] for key in ("followup", "customer", "customer_changes") if key in receipt})
        context.update(code="repair_closed_partial", durable_change_state="partial",
                       durable_change_receipt=receipt,
                       message="本次补救审批已关闭；已写入的跟进保留，客户摘要仍待人工处理。")
    return context


def bind_approval_card(
    command: Mapping[str, Any],
    ledger: Ledger,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a pending approval to the exact card emitted by the trusted host."""

    try:
        _only_keys(command, {"approval_id", "principal"})
        approval_id = _opaque_id(command.get("approval_id"), "approval_id", "apr_")
        principal = _principal(command.get("principal"))
        _actor_for_principal(principal, config)
    except (TypeError, ValueError) as exc:
        return _blocked("invalid_host_request", str(exc))

    try:
        approval = ledger.get_approval(approval_id)
    except Exception:
        return _failed("ledger_unavailable", "The approval could not be read.")
    if approval is None:
        return _blocked("unknown_approval", "This approval does not exist.")
    if not _same_principal(approval["principal"], principal):
        return _blocked(
            "principal_mismatch",
            "The emitted card does not belong to this sender or conversation.",
        )
    if approval["state"] != "pending" or approval["receipt"] is not None:
        return _blocked(
            "approval_not_pending",
            "Only a pending approval can be bound to an approval card.",
        )
    try:
        bound = ledger.bind_card_message(approval_id, principal["message_id"])
    except Exception:
        return _failed("ledger_unavailable", "The approval card could not be recorded.")
    if not bound:
        return _blocked(
            "card_mismatch",
            "This approval is already bound to a different card.",
        )
    return {
        "status": "bound",
        "approval_id": approval_id,
        "change_id": approval["change_id"],
        "message": "The emitted approval card is now bound to this pending change.",
    }


def execute_claimed_approval(
    command: Mapping[str, Any],
    backend: Backend,
    ledger: Ledger,
    config: Mapping[str, Any],
    now: datetime | None = None,
    *, personal_backend=None, handoff_files_verified=False,
) -> dict[str, Any]:
    """Execute only an approval already claimed by the authenticated host."""

    started = time.monotonic()
    try:
        moment = _now(now)
        _only_keys(command, {"approval_id", "principal"})
        approval_id = _opaque_id(command.get("approval_id"), "approval_id", "apr_")
        principal = _principal(command.get("principal"))
        actor = _actor_for_principal(principal, config)
    except (TypeError, ValueError) as exc:
        return _blocked("invalid_host_request", str(exc))

    try:
        approval = ledger.get_approval(approval_id)
    except Exception:
        return _failed("ledger_unavailable", "The approval could not be read.")
    if approval is None:
        return _blocked("unknown_approval", "This approval does not exist.")
    if not _same_principal(approval["principal"], principal):
        return _blocked(
            "principal_mismatch",
            "Only the same sender in the same conversation may execute this approval.",
        )
    if approval["card_message_id"] != principal["message_id"]:
        return _blocked(
            "card_mismatch",
            "This execution did not come from the original approval card.",
        )
    staged = ledger.get(approval["change_id"])
    if staged is None or staged.get("actor") != actor:
        return _blocked("binding_changed", "The bound CRM actor is no longer valid.")
    if approval["receipt"] is not None:
        return {
            **approval["receipt"],
            "approval_id": approval_id,
            "approval_state": approval["state"],
            "replayed": True,
        }
    if approval["state"] != "executing" or approval["decision"] != "approve":
        return _blocked(
            "host_approval_required",
            "No executing host approval was found.",
        )
    from . import plans
    environment_changed = staged.get("plan") is not None and staged["plan"]["namespace"] != plans.namespace(config)
    if environment_changed or approval["preview_hash"] != _hash(_approval_material(staged)):
        result = _replan(
            approval["change_id"],
            "plan_environment_changed" if environment_changed else "preview_changed",
            "The CRM environment changed; preview again." if environment_changed else "Stage this follow-up again.",
        )
        ledger.finish_approval(
            approval_id, "failed", "approve", _iso(moment), result
        )
        if staged["state"] != "partial":
            ledger.finish(approval["change_id"], "failed", result)
        return {
            **result,
            "approval_id": approval_id,
            "approval_state": "failed",
        }

    customer_operation = staged.get("operation_type") in {"customer_create", "customer_update"}
    if staged.get("operation_type", "").startswith("banquet_handoff_"):
        from .handoffs import apply
        result = apply(staged, backend, ledger, moment, personal_backend=personal_backend,
                       files_verified=handoff_files_verified, started=started)
    elif staged.get("operation_type", "").startswith("banquet_"):
        from .banquet import apply
        result = apply(staged, backend, ledger, moment, personal_backend=personal_backend, started=started)
    elif customer_operation:
        from .customers import apply_customer
        result = apply_customer(staged, backend, ledger, moment, started=started)
    else:
        result = _apply_approved_followup(
            approval["change_id"], approval_id, backend, ledger, moment, started
        )
    if result.get("code") == "apply_in_progress":
        return {**result, "approval_id": approval_id, "approval_state": "executing"}
    approval_state = _approval_terminal_state(result["status"])
    # Persist the parent outcome before attempting any second-card preparation.
    ledger.finish_approval(
        approval_id, approval_state, "approve", _iso(moment), result
    )
    next_approval = None
    if customer_operation and result["status"] == "verified" and staged.get("followup") and not result.get("replayed"):
        child_moment = _now(now)
        result, next_approval = _prepare_child_followup(staged, result, backend, ledger, config, child_moment)
        ledger.finish(approval["change_id"], "verified", result)
        ledger.finish_approval(approval_id, "verified", "approve", _iso(child_moment), result)
    return {
        **result,
        "approval_id": approval_id,
        "approval_state": approval_state,
        **({"next_approval": next_approval} if next_approval is not None else {}),
    }


def _prepare_child_followup(staged, receipt, backend, ledger, config, moment):
    """One narrow handoff, with no model call, write retry, or recovery worker."""
    result = {**receipt, "next_approval_status": "unavailable",
              "followup_message": "客户操作已成功；跟进尚未提交，请人工重新发起跟进。"}
    try:
        parent = ledger.get(staged["change_id"])
        record_id = parent.get("resolved_customer_record_id") or parent.get("customer_record_id")
        customer = _mapping(backend.get_customer(record_id), "verified customer")
        _validate_customer(customer)
        # Reuse the follow-up planner in temporary memory without superseding
        # persistent user intents. The final insert+intent check is one transaction.
        temporary = Ledger()
        try:
            preview = stage_followup(
                {"customer_query": customer["customer_number"], **staged["followup"]},
                backend, temporary, config, secrets.token_urlsafe(32), moment,
                trusted_record_id=record_id,
                trusted_plan_binding=staged.get("plan_reminder_binding"),
            )
            if preview.get("status") != "staged":
                return result, None
            body = temporary.planned_body(preview["change_id"])
        finally:
            temporary.close()
        if body is not None:
            from . import plans
            plan = plans.freeze(customer, body["customer_patch"], staged["followup"], ledger, config, moment,
                                binding=staged.get("plan_reminder_binding"),
                                historical=bool(staged["followup"].get("backfill")) or not body["customer_patch"])
            plans.verify_binding(plan, staged["principal"])
            if plan is not None:
                body["plan"] = plan
        approval = ledger.stage_child(staged["change_id"], body, _iso(moment))
        if approval is None:
            result["next_approval_status"] = "not_published"
            result["followup_message"] = "客户操作已成功；已有后续写入意图或子方案，未另发跟进卡。"
            return result, None
        result.update(child_change_id=body["change_id"], next_approval_status="pending",
                      followup_message="客户操作已成功；跟进需要单独批准，尚未写入。")
        child = ledger.get(body["change_id"])
        return result, _approval_begin_result(approval, child, backend, [], False)
    except Exception:
        # The first write remains verified even if reading/staging the child fails.
        return result, None


def decide_approval(
    command: Mapping[str, Any],
    backend: Backend,
    ledger: Ledger,
    config: Mapping[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compatibility one-shot used by tests; production uses claim then execute."""

    claimed = claim_approval_decision(command, ledger, config, now, backend=backend)
    should_execute = claimed.pop("execute", False)
    if not should_execute:
        if claimed.get("status") == "executing":
            claimed["status"] = "verification_unknown"
        return claimed
    return execute_claimed_approval(
        {
            "approval_id": claimed["approval_id"],
            "principal": command.get("principal"),
        },
        backend,
        ledger,
        config,
        now,
    )


def _apply_approved_followup(
    change_id: str,
    approval_id: str,
    backend: Backend,
    ledger: Ledger,
    moment: datetime,
    started: float,
) -> dict[str, Any]:
    """Apply one host-approved change and verify the observable CRM state."""

    approval = ledger.get_approval(approval_id)
    if (
        approval is None
        or approval["change_id"] != change_id
        or approval["state"] != "executing"
    ):
        return _failed("host_approval_required", "No executing host approval was found.")
    staged = ledger.get(change_id)
    if staged is None:
        return _replan(change_id, "unknown_change", "Stage this follow-up again.")

    state = staged["state"]
    if state == "partial":
        # Reapproval, restart, and expiry cannot resolve a prior business effect.
        # This also protects legacy partial rows created before write fences.
        return {**staged["receipt"], "code": "crm_write_unresolved",
                "message": "Previous effects require operator verification; no new write was started."}
    if staged.get("receipt") and state not in {"staged", "applying"}:
        return {**staged["receipt"], "replayed": True}
    if state == "superseded":
        return _replan(change_id, "superseded", "A newer plan replaced this change.")
    if state == "applying":
        return {
            "status": "verification_unknown",
            "code": "apply_in_progress",
            "change_id": change_id,
            "message": "Another apply attempt owns this change; no second write was started.",
        }
    if state != "staged":
        return _replan(change_id, "change_not_pending", "Stage this follow-up again.")
    if moment > _parse_time(staged["expires_at"], "expires_at"):
        result = _replan(change_id, "expired", "The ten-minute preview expired; stage again.")
        ledger.finish(change_id, "expired", result)
        return result
    try:
        claimed = ledger.claim(change_id)
    except Exception:
        return _failed("ledger_unavailable", "The staged change could not be claimed.")
    if not claimed:
        return {
            "status": "verification_unknown",
            "code": "apply_in_progress",
            "change_id": change_id,
            "message": "The change was claimed concurrently; no second write was started.",
        }

    return _run_customer_write(staged, ledger, moment,
                               lambda effective: _apply_claimed_followup(staged, backend, ledger, effective), started)


def _apply_claimed_followup(staged, backend, ledger, moment):
    change_id = staged["change_id"]
    try:
        from . import plans
        plan_error = plans.check(staged, ledger, moment)
        if plan_error is not None:
            return _finish(ledger, change_id, "replan_required", plan_error)
        schema = _mapping(backend.read_schema(), "schema")
        if _hash(schema) != staged["schema_hash"]:
            return _finish(
                ledger,
                change_id,
                "replan_required",
                _replan(change_id, "schema_changed", "CRM schema changed after preview."),
            )
        matches, _ = _resolve_customer(staged["customer_query"], backend)
        if len(matches) != 1 or _record_id(matches[0]) != staged["customer_record_id"]:
            return _finish(
                ledger,
                change_id,
                "replan_required",
                _replan(change_id, "customer_match_changed", "Customer matching changed."),
            )
        customer = backend.get_customer(staged["customer_record_id"])
        customer = _mapping(customer, "customer") if customer is not None else None
        if customer is None or _hash(_snapshot(customer)) != staged["snapshot_hash"]:
            return _finish(
                ledger,
                change_id,
                "replan_required",
                _replan(change_id, "customer_changed", "Customer data changed after preview."),
            )
        existing = backend.find_followup_by_change(change_id)
        existing = _mapping(existing, "followup") if existing is not None else None
    except Exception:
        result = _failed("prewrite_read_failed", "Pre-write checks failed; Feishu was not written.")
        result["change_id"] = change_id
        return _finish(ledger, change_id, "failed", result)

    if existing is not None:
        return _finish_existing(backend, ledger, staged, existing, moment)

    payload = _followup_payload(staged)
    verification_payload = _followup_verification_payload(staged)
    try:
        created = backend.create_followup(payload)
        followup_id = _created_record_id(created)
        actual_followup = _poll_read(
            lambda: backend.get_followup(followup_id), verification_payload
        )
    except Exception:
        actual_followup = _poll_read(
            lambda: backend.find_followup_by_change(change_id)
        )
        if actual_followup is not None:
            return _finish_existing(
                backend, ledger, staged, _mapping(actual_followup, "followup"), moment
            )
        result = _receipt(
            "verification_unknown",
            "followup_write_unconfirmed",
            staged,
            backend,
            customer,
            None,
            moment,
            "The follow-up write was attempted but could not be read back; nothing was retried.",
        )
        return _finish(ledger, change_id, "verification_unknown", result)

    if actual_followup is None or not _fields_match(
        actual_followup, _followup_verification_payload(staged)
    ):
        result = _receipt(
            "verification_unknown",
            "followup_readback_mismatch",
            staged,
            backend,
            customer,
            actual_followup,
            moment,
            "The follow-up write could not be verified; customer summary was not updated.",
        )
        return _finish(ledger, change_id, "verification_unknown", result)

    patch = staged["customer_patch"]
    if not patch:
        result = _receipt(
            "verified",
            "followup_recorded_customer_unchanged",
            staged,
            backend,
            customer,
            actual_followup,
            moment,
            "Follow-up recorded and verified; the customer summary was already newer.",
        )
        return _finish(ledger, change_id, "verified", result)

    try:
        before_update = backend.get_customer(staged["customer_record_id"])
        before_update = (
            _mapping(before_update, "customer") if before_update is not None else None
        )
    except Exception:
        before_update = None
    if before_update is None or _hash(_snapshot(before_update)) != staged["snapshot_hash"]:
        result = _receipt(
            "partial",
            "customer_changed_after_followup",
            staged,
            backend,
            before_update,
            actual_followup,
            moment,
            "Follow-up was verified, but customer data changed before its summary update.",
        )
        return _finish(ledger, change_id, "partial", result)

    return _update_and_verify_customer(
        backend, ledger, staged, actual_followup, moment
    )


def _finish_existing(
    backend: Backend,
    ledger: Ledger,
    staged: Mapping[str, Any],
    followup: Mapping[str, Any],
    moment: datetime,
) -> dict[str, Any]:
    change_id = staged["change_id"]
    payload = _followup_verification_payload(staged)
    try:
        customer = backend.get_customer(staged["customer_record_id"])
        customer = _mapping(customer, "customer") if customer is not None else None
    except Exception:
        customer = None
    if not _fields_match(followup, payload):
        result = _receipt(
            "verification_unknown",
            "idempotency_conflict",
            staged,
            backend,
            customer,
            followup,
            moment,
            "A follow-up uses this change id but its fields do not match; no write was made.",
        )
        return _finish(ledger, change_id, "verification_unknown", result)
    if not staged["customer_patch"] or (
        customer is not None and _fields_match(customer, staged["customer_patch"])
    ):
        result = _receipt(
            "verified",
            "already_applied",
            staged,
            backend,
            customer,
            followup,
            moment,
            "The existing write matches this change; no duplicate was created.",
        )
        return _finish(ledger, change_id, "verified", result)
    if customer is None or _hash(_snapshot(customer)) != staged["snapshot_hash"]:
        result = _receipt(
            "partial",
            "customer_changed_after_followup",
            staged,
            backend,
            customer,
            followup,
            moment,
            "Follow-up exists, but customer data changed; stage a repair plan.",
        )
        return _finish(ledger, change_id, "partial", result)

    return _update_and_verify_customer(backend, ledger, staged, followup, moment)


def _update_and_verify_customer(
    backend: Backend,
    ledger: Ledger,
    staged: Mapping[str, Any],
    followup: Mapping[str, Any],
    moment: datetime,
) -> dict[str, Any]:
    try:
        backend.update_customer(staged["customer_record_id"], staged["customer_patch"])
    except Exception as exc:
        uncertain = getattr(exc, "kind", None) in {
            "timeout",
            "protocol_error",
            "unavailable",
        }
    else:
        uncertain = False
    current = _poll_read(
        lambda: backend.get_customer(staged["customer_record_id"]),
        staged["customer_patch"],
    )
    return _finish_after_customer_write(
        backend, ledger, staged, followup, current, moment, uncertain=uncertain
    )


def _finish_after_customer_write(
    backend: Backend,
    ledger: Ledger,
    staged: Mapping[str, Any],
    followup: Mapping[str, Any],
    customer: Mapping[str, Any] | None,
    moment: datetime,
    *,
    uncertain: bool,
) -> dict[str, Any]:
    change_id = staged["change_id"]
    if customer is not None and _fields_match(customer, staged["customer_patch"]):
        result = _receipt(
            "verified",
            "followup_and_customer_verified",
            staged,
            backend,
            customer,
            followup,
            moment,
            "Follow-up and current customer summary were read back and verified.",
        )
        return _finish(ledger, change_id, "verified", result)

    unchanged = (
        customer is not None
        and _hash(_snapshot(customer)) == staged["snapshot_hash"]
    )
    status = "verification_unknown" if not unchanged or uncertain else "partial"
    code = (
        "customer_write_unconfirmed"
        if status == "verification_unknown"
        else "customer_update_failed"
    )
    message = (
        "Customer summary write could not be verified; no retry or rollback was attempted."
        if status == "verification_unknown"
        else "Follow-up was verified, but the customer summary remained unchanged."
    )
    result = _receipt(
        status, code, staged, backend, customer, followup, moment, message
    )
    return _finish(ledger, change_id, status, result)


def _resolve_customer(query: str, backend: Backend) -> tuple[list[Mapping[str, Any]], str]:
    number_query = re.fullmatch(r"[a-z][a-z0-9_]*-[0-9]+", _normal(query)) is not None
    exact_lookup = getattr(backend, "find_customers_by_number", None)
    if callable(exact_lookup):
        exact = list(exact_lookup(query))
        for row in exact:
            _validate_customer(row)
            if _normal(row.get("customer_number")) != _normal(query):
                raise ValueError("Exact customer-number lookup returned a different customer.")
        if exact or number_query:
            return exact, "customer_number"
    rows = list(backend.find_customers(query))
    for row in rows:
        _validate_customer(row)
    needle = _normal(query)
    numbered = [row for row in rows if _normal(row.get("customer_number")) == needle]
    if numbered or number_query:
        return numbered, "customer_number"
    named = [row for row in rows if _normal(row.get("name")) == needle]
    return named, "name"


def _followup(value: Any) -> dict[str, Any]:
    item = _mapping(value, "followup")
    _only_keys(
        item,
        {"occurred_at", "content", "channel", "next_action", "next_followup_at", "remind", "backfill"},
    )
    occurred = _parse_time(item.get("occurred_at"), "followup.occurred_at")
    result: dict[str, Any] = {
        "occurred_at": occurred.isoformat(),
        "content": _required_text(item.get("content"), "followup.content", 5000),
    }
    if item.get("channel") is not None:
        channel = _required_text(item["channel"], "followup.channel", 64)
        if channel not in _CHANNELS:
            raise ValueError("followup.channel is not a configured communication method")
        result["channel"] = channel
    if item.get("next_action") is not None:
        result["next_action"] = _required_text(
            item["next_action"], "followup.next_action", 1000
        )
    if item.get("next_followup_at") is not None:
        from . import plans
        result["next_followup_at"] = plans.normalize_time(item["next_followup_at"])
    for flag in ("remind", "backfill"):
        if flag in item:
            if not isinstance(item[flag], bool):
                raise ValueError(f"{flag} must be a boolean.")
            result[flag] = item[flag]
    return result


def _customer_patch(customer: Mapping[str, Any], followup: Mapping[str, Any]) -> dict[str, Any]:
    patch: dict[str, Any] = {}
    previous = customer.get("last_followup_at")
    previous_time = _optional_time(previous)
    current_time = _parse_time(followup["occurred_at"], "followup.occurred_at")
    if previous_time is not None and current_time < previous_time:
        return patch
    patch["last_followup_at"] = followup["occurred_at"]
    patch["last_followup_content"] = followup["content"]
    if followup.get("backfill"):
        return patch
    for field in ("next_action", "next_followup_at"):
        if field in followup:
            patch[field] = followup[field]
    return patch


def _followup_payload(staged: Mapping[str, Any]) -> dict[str, Any]:
    result = {
        "change_id": staged["change_id"],
        "customer_record_id": staged["customer_record_id"],
        "customer_number": staged.get("customer_number"),
        **staged["followup"],
        "created_by": staged["actor"]["feishu_user_id"],
    }
    result.pop("remind", None)
    result.pop("backfill", None)
    return result


def _followup_verification_payload(staged: Mapping[str, Any]) -> dict[str, Any]:
    """Fields that the follow-up table persists and can therefore read back."""

    payload = _followup_payload(staged)
    payload.pop("customer_number", None)
    return payload


def _receipt(
    status: str,
    code: str,
    staged: Mapping[str, Any],
    backend: Backend,
    customer: Mapping[str, Any] | None,
    followup: Mapping[str, Any] | None,
    moment: datetime,
    message: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": status,
        "code": code,
        "change_id": staged["change_id"],
        "message": message,
        "verified_at": _iso(moment),
        "customer_changes": _field_changes(
            staged["before"], staged["customer_patch"], customer
        ),
    }
    if customer is not None:
        result["customer"] = _display_customer(customer, backend)
    if followup is not None:
        result["followup"] = _display_followup(followup, backend)
    return result


def _field_changes(
    before: Mapping[str, Any],
    patch: Mapping[str, Any],
    actual: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    changes = []
    for field, expected in patch.items():
        item = {
            "field": field,
            "before": _fence_value(before.get(field)),
            "after": expected,
        }
        if actual is not None:
            observed = actual.get(field)
            item["actual"] = _fence_value(observed)
            item["verified"] = _equal(observed, expected)
        changes.append(item)
    return changes


def _display_customer(customer: Mapping[str, Any], backend: Backend) -> dict[str, Any]:
    view = _fence_value(_snapshot(customer))
    record_id = _record_id(customer)
    url = _safe_url(getattr(backend, "customer_url", None), record_id)
    if url:
        view["url"] = url
    return view


def _display_followup(followup: Mapping[str, Any], backend: Backend) -> dict[str, Any]:
    fields = {
        key: value
        for key, value in followup.items()
        if key
        in {"occurred_at", "content", "channel", "next_action", "next_followup_at"}
    }
    view = _fence_value(fields)
    record_id = followup.get("record_id")
    if isinstance(record_id, str) and record_id:
        url = _safe_url(getattr(backend, "followup_url", None), record_id)
        if url:
            view["url"] = url
    return view


def _snapshot(customer: Mapping[str, Any]) -> dict[str, Any]:
    return {field: _jsonable(customer.get(field)) for field in _DISPLAY_FIELDS if field in customer}


def _principal(value: Any) -> dict[str, str]:
    context = _mapping(value, "principal")
    _only_keys(context, _PRINCIPAL_KEYS)
    return {
        key: _required_text(context.get(key), f"principal.{key}", 1024)
        for key in _PRINCIPAL_KEYS
    }


def _same_principal(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    return all(
        hmac.compare_digest(str(left.get(key, "")), str(right.get(key, "")))
        for key in _PRINCIPAL_BINDING_KEYS
    )


def _actor_for_principal(
    principal: Mapping[str, str], config: Mapping[str, Any]
) -> dict[str, str]:
    allowed = config.get("allowed_actors")
    user_id = principal["user_id"]
    if not isinstance(allowed, Mapping) or user_id not in allowed:
        raise ValueError("principal is not configured")
    actor = _mapping(allowed[user_id], "allowed actor")
    display_name = _required_text(actor.get("display_name"), "actor display_name")
    feishu_user_id = _required_text(actor.get("feishu_user_id"), "actor feishu_user_id")
    return {
        "display_name": display_name,
        "feishu_user_id": feishu_user_id,
    }


def _action_token_hash(value: Any) -> str:
    token = _required_text(value, "MYANC_CRM_ACTION_TOKEN", 4096)
    if len(token) < 32:
        raise ValueError("MYANC_CRM_ACTION_TOKEN is too short")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _approval_material(staged: Mapping[str, Any]) -> dict[str, Any]:
    material = {
        key: staged.get(key)
        for key in (
            "change_id",
            "customer_query",
            "matched_by",
            "customer_record_id",
            "customer_number",
            "customer_snapshot",
            "schema_hash",
            "snapshot_hash",
            "before",
            "followup",
            "customer_patch",
            "created_at",
            "expires_at",
            "principal",
            "actor",
        )
    }
    if "operation_type" in staged:
        # Do not add null fields to legacy follow-up fingerprints.
        for key in ("operation_type", "customer_fields", "customer_patch", "assignee",
                    "duplicate_snapshot", "duplicate_hash", "request"):
            material[key] = staged.get(key)
    if "parent_change_id" in staged:
        material["parent_change_id"] = staged["parent_change_id"]
    for key in ("plan", "plan_reminder_binding", "banquet_before", "banquet_patch",
                "handoff_before", "handoff_patch", "handoff_source", "connection_binding"):
        if key in staged:
            material[key] = staged[key]
    return material


def _approval_preview(
    staged: Mapping[str, Any], backend: Backend
) -> dict[str, Any]:
    if staged.get("operation_type", "").startswith("banquet_"):
        from .banquet import approval_preview
        return approval_preview(staged, backend)
    if staged.get("operation_type") in {"customer_create", "customer_update"}:
        from .customers import approval_preview
        return approval_preview(staged, backend)
    customer = _mapping(staged.get("customer_snapshot"), "customer_snapshot")
    patch = _mapping(staged.get("customer_patch"), "customer_patch")
    repairing = staged.get("state") == "partial"
    from . import plans
    return {
        "actor": _mapping(staged.get("actor"), "actor")["display_name"],
        "matched_by": staged.get("matched_by"),
        "customer": _display_customer(customer, backend),
        "effects": {
            "followup": {
                "action": "already_verified" if repairing else "create",
                "after": _display_followup(staged["followup"], backend),
            },
            "customer": {
                "action": "update" if patch else "no_change",
                "changes": _field_changes(staged["before"], patch),
            },
        },
        "untouched_fields": list(_UNTOUCHED_FIELDS),
        "created_at": staged["created_at"],
        "expires_at": staged["expires_at"],
        "execution_order": (
            ["read_followup", "read_customer", "update_customer_summary", "read_customer"]
            if repairing
            else [
                "create_followup",
                "read_followup",
                "update_customer_summary",
                "read_customer",
            ]
        ),
        "failure_policy": (
            "A verified follow-up is retained if the customer-summary write fails."
        ),
        **plans.preview(staged),
        **({"parent_change_id": staged["parent_change_id"],
            "parent_message": "客户建档／资料修改已成功；本卡只批准跟进，取消不会撤销客户操作。"}
           if staged.get("parent_change_id") else {}),
    }


def _approval_begin_result(
    approval: Mapping[str, Any],
    staged: Mapping[str, Any],
    backend: Backend,
    superseded: Sequence[str],
    replayed: bool,
) -> dict[str, Any]:
    return {
        "status": approval["state"],
        "approval_id": approval["approval_id"],
        "change_id": approval["change_id"],
        "expires_at": approval["expires_at"],
        "preview": _approval_preview(staged, backend),
        "superseded_approval_ids": list(superseded),
        "replayed": replayed,
    }


def _validate_customer(customer: Mapping[str, Any]) -> None:
    _record_id(customer)
    _required_text(customer.get("customer_number"), "customer.customer_number")
    _required_text(customer.get("name"), "customer.name")


def _record_id(customer: Mapping[str, Any]) -> str:
    return _required_text(customer.get("record_id"), "customer.record_id")


def _created_record_id(value: str | Mapping[str, Any]) -> str:
    if isinstance(value, str):
        return _required_text(value, "created record id")
    return _record_id(_mapping(value, "created followup"))


def _fields_match(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return all(_equal(actual.get(key), value) for key, value in expected.items())


def _poll_read(
    read: Callable[[], Mapping[str, Any] | None],
    expected: Mapping[str, Any] | None = None,
) -> Mapping[str, Any] | None:
    """Poll a read after one write; never retries or performs a write itself."""

    deadline = time.monotonic() + max(0.0, READBACK_TIMEOUT_SECONDS)
    last: Mapping[str, Any] | None = None
    while True:
        try:
            value = read()
            if value is not None:
                last = _mapping(value, "readback")
                if expected is None or _fields_match(last, expected):
                    return last
        except Exception:
            pass

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return last
        time.sleep(min(max(0.0, READBACK_INTERVAL_SECONDS), remaining))


def _equal(left: Any, right: Any) -> bool:
    left_time = _optional_time(left)
    right_time = _optional_time(right)
    if left_time is not None and right_time is not None:
        return left_time == right_time
    return _jsonable(left) == _jsonable(right)


def _normal(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(unicodedata.normalize("NFKC", str(value)).split()).casefold()


def _filter_forged_tags(value: str) -> str:
    # Normalize only candidate markup for detection, including combining marks.
    # Preserve other spelling: the preview must not silently rename a business.
    return _TAG_LIKE.sub(
        lambda match: "[filtered-tag]"
        if _FORGED_TAG.search(unicodedata.normalize("NFKC", match.group()))
        else match.group(),
        value,
    )


def _fence_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _fence_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_fence_value(item) for item in value]
    if not isinstance(value, str):
        return value
    text = _filter_forged_tags(value)
    text = "".join(
        character if not unicodedata.category(character).startswith("C") else " "
        for character in text
    )
    text = " ".join(text.split())[:2000]
    return f"{_FENCE_OPEN}{text}{_FENCE_CLOSE}"


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _json(value: Any) -> str:
    return json.dumps(
        _jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be an object")
    return value


def _only_keys(value: Mapping[str, Any], allowed: set[str]) -> None:
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise ValueError(f"unsupported fields: {', '.join(unexpected)}")


def _required_text(value: Any, name: str, max_length: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    text = value.strip()
    if max_length is not None and len(text) > max_length:
        raise ValueError(f"{name} exceeds {max_length} characters")
    return text


def _opaque_id(value: Any, name: str, prefix: str) -> str:
    text = _required_text(value, name, 132)
    if re.fullmatch(re.escape(prefix) + r"[A-Za-z0-9_-]{1,128}", text) is None:
        raise ValueError(f"{name} is invalid")
    return text


def _parse_time(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an RFC 3339 timestamp with an offset")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise ValueError(f"{name} must be an RFC 3339 timestamp with an offset") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name} must include a timezone offset")
    return parsed


def _optional_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return _parse_time(value, "timestamp")
    except ValueError:
        return None


def _now(value: datetime | None) -> datetime:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must include a timezone")
    return current


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_url(function: Any, record_id: str) -> str | None:
    try:
        value = function(record_id)
    except Exception:
        return None
    return value if isinstance(value, str) and value.startswith("https://") else None


def _blocked(code: str, message: str) -> dict[str, Any]:
    return {"status": "blocked", "code": code, "message": message}


def _failed(code: str, message: str) -> dict[str, Any]:
    return {"status": "failed", "code": code, "message": message}


def _replan(change_id: str, code: str, message: str) -> dict[str, Any]:
    return {
        "status": "replan_required",
        "code": code,
        "change_id": change_id,
        "message": message,
    }


def _finish(
    ledger: Ledger, change_id: str, state: str, result: Mapping[str, Any]
) -> dict[str, Any]:
    output = dict(result)
    ledger.finish(change_id, state, output)
    return output


def _approval_terminal_state(state: str) -> str:
    return state if state in {"verified", "partial", "verification_unknown"} else "failed"


def _write_scopes(staged: Mapping[str, Any]) -> tuple[str, ...]:
    snapshot = staged["customer_snapshot"]
    names = [snapshot.get("name"), staged.get("customer_fields", {}).get("name")]
    scopes = {_hash(["name", _normal(name)]) for name in names if isinstance(name, str) and name.strip()}
    identifier = staged.get("customer_record_id")
    if identifier:
        scopes.add(_hash(["record", identifier]))
    if not scopes:
        raise ValueError("No frozen CRM write target")
    return tuple(sorted(scopes))


def _run_customer_write(staged, ledger, moment, execute, started):
    # Include approval reads and claim time, not just time spent waiting for locks.
    try:
        with ledger.customer_write(staged):
            effective = moment + timedelta(seconds=time.monotonic() - started)
            if effective > _parse_time(staged["expires_at"], "expires_at"):
                return _finish(ledger, staged["change_id"], "expired",
                               _replan(staged["change_id"], "expired", "The preview expired while waiting; preview again."))
            return execute(effective)
    except write_locks.WriteBlocked as exc:
        return _finish(ledger, staged["change_id"], "replan_required",
                       _replan(staged["change_id"], exc.code, str(exc)))
