"""Deterministic staged follow-up workflow.

Claude sees two operations: stage a factual preview, then apply that exact staged
change after the existing cc-connect approval flow.  Feishu identifiers and command
construction stay behind ``Backend``.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence


READBACK_TIMEOUT_SECONDS = 30.0
READBACK_INTERVAL_SECONDS = 1.0


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
        if value != ":memory:":
            Path(value).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(value, timeout=10)
        self._db.row_factory = sqlite3.Row
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS staged_changes (
                change_id TEXT PRIMARY KEY,
                sender_id TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                state TEXT NOT NULL,
                body_json TEXT NOT NULL,
                receipt_json TEXT
            )
            """
        )

    def stage(self, body: Mapping[str, Any]) -> None:
        encoded = _json(body)
        with self._db:
            self._db.execute(
                """
                UPDATE staged_changes
                   SET state = 'superseded'
                 WHERE sender_id = ? AND chat_id = ? AND state = 'staged'
                """,
                (body["sender_id"], body["chat_id"]),
            )
            self._db.execute(
                """
                INSERT INTO staged_changes
                    (change_id, sender_id, chat_id, state, body_json)
                VALUES (?, ?, ?, 'staged', ?)
                """,
                (body["change_id"], body["sender_id"], body["chat_id"], encoded),
            )

    def get(self, change_id: str) -> dict[str, Any] | None:
        row = self._db.execute(
            "SELECT state, body_json, receipt_json FROM staged_changes WHERE change_id = ?",
            (change_id,),
        ).fetchone()
        if row is None:
            return None
        body = json.loads(row["body_json"])
        body["state"] = row["state"]
        body["receipt"] = json.loads(row["receipt_json"]) if row["receipt_json"] else None
        return body

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

    def reclaim_partial(self, change_id: str) -> bool:
        """Claim only the unfinished customer half of an already recorded follow-up."""

        with self._db:
            cursor = self._db.execute(
                """
                UPDATE staged_changes SET state = 'applying'
                 WHERE change_id = ? AND state = 'partial'
                """,
                (change_id,),
            )
        return cursor.rowcount == 1

    def finish(self, change_id: str, state: str, receipt: Mapping[str, Any]) -> None:
        with self._db:
            self._db.execute(
                """
                UPDATE staged_changes SET state = ?, receipt_json = ?
                 WHERE change_id = ?
                """,
                (state, _json(receipt), change_id),
            )

    def close(self) -> None:
        self._db.close()


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


def stage_followup(
    command: Mapping[str, Any],
    backend: Backend,
    ledger: Ledger,
    config: Mapping[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Read and stage one follow-up.  This function never writes to Feishu."""

    try:
        moment = _now(now)
        _only_keys(command, {"actor", "customer_query", "followup"})
        context, actor = _actor(command.get("actor"), config)
        query = _required_text(command.get("customer_query"), "customer_query", 256)
        raw_followup = _mapping(command.get("followup"), "followup")
        if not raw_followup.get("occurred_at"):
            return {
                "status": "needs_time",
                "code": "followup_time_required",
                "message": "Ask for the follow-up time before staging; Feishu is unchanged.",
            }
        followup = _followup(raw_followup)
        ttl = int(config.get("ttl_seconds", 600))
        if ttl <= 0:
            raise ValueError("ttl_seconds must be positive")
    except (TypeError, ValueError) as exc:
        return _blocked("invalid_request", str(exc))

    try:
        schema = _mapping(backend.read_schema(), "schema")
        matches, matched_by = _resolve_customer(query, backend)
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
        change_id = "chg_" + secrets.token_urlsafe(18)
        created_at = _iso(moment)
        expires_at = _iso(moment + timedelta(seconds=ttl))
        body = {
            "change_id": change_id,
            "sender_id": context["sender_id"],
            "chat_id": context["chat_id"],
            "actor": actor,
            "customer_query": query,
            "customer_record_id": record_id,
            "customer_number": customer.get("customer_number"),
            "schema_hash": _hash(schema),
            "snapshot_hash": _hash(canonical_snapshot),
            "before": {field: canonical_snapshot.get(field) for field in patch},
            "followup": followup,
            "customer_patch": patch,
            "created_at": created_at,
            "expires_at": expires_at,
        }
        ledger.stage(body)
    except (TypeError, ValueError) as exc:
        return _blocked("invalid_backend_data", str(exc))
    except Exception:
        return _blocked("staging_failed", "The preview could not be staged; Feishu is unchanged.")

    return {
        "status": "staged",
        "change_id": change_id,
        "expires_at": expires_at,
        "actor": actor["display_name"],
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
    }


def apply_followup(
    command: Mapping[str, Any],
    backend: Backend,
    ledger: Ledger,
    config: Mapping[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Apply one unchanged staged follow-up and verify the observable CRM state."""

    try:
        moment = _now(now)
        _only_keys(command, {"actor", "change_id"})
        context, actor = _actor(command.get("actor"), config)
        change_id = _required_text(command.get("change_id"), "change_id")
    except (TypeError, ValueError) as exc:
        supplied = command.get("change_id") if isinstance(command, Mapping) else None
        if isinstance(supplied, str) and supplied.strip():
            return _replan(supplied.strip(), "invalid_request", str(exc))
        return _failed("invalid_request", str(exc))

    try:
        staged = ledger.get(change_id)
    except Exception:
        return _failed("ledger_unavailable", "The staged change could not be read.")
    if staged is None:
        return _replan(change_id, "unknown_change", "Stage this follow-up again.")
    if (
        staged["sender_id"] != context["sender_id"]
        or staged["chat_id"] != context["chat_id"]
        or staged["actor"] != actor
    ):
        return _replan(
            change_id,
            "actor_or_chat_mismatch",
            "Only the same sender in the same chat may apply this staged change.",
        )

    state = staged["state"]
    if state == "partial":
        try:
            claimed = ledger.reclaim_partial(change_id)
        except Exception:
            return _failed("ledger_unavailable", "The partial change could not be claimed.")
        if not claimed:
            return {
                "status": "verification_unknown",
                "code": "apply_in_progress",
                "change_id": change_id,
                "message": "Another repair attempt owns this change; no second write was started.",
            }
        return _resume_partial(backend, ledger, staged, moment)
    if staged.get("receipt") and state not in {"staged", "applying"}:
        return {**staged["receipt"], "replayed": True}
    if state == "superseded":
        return _replan(change_id, "superseded", "A newer plan replaced this change.")
    if state == "applying":
        try:
            existing = backend.find_followup_by_change(change_id)
        except Exception:
            existing = None
        if existing is not None:
            return _resume_partial(backend, ledger, staged, moment)
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

    try:
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


def _resume_partial(
    backend: Backend,
    ledger: Ledger,
    staged: Mapping[str, Any],
    moment: datetime,
) -> dict[str, Any]:
    """Retry only the customer summary after the truthful follow-up is verified."""

    change_id = staged["change_id"]
    try:
        schema = _mapping(backend.read_schema(), "schema")
        followup = backend.find_followup_by_change(change_id)
        followup = _mapping(followup, "followup") if followup is not None else None
        customer = backend.get_customer(staged["customer_record_id"])
        customer = _mapping(customer, "customer") if customer is not None else None
    except Exception:
        result = _receipt(
            "partial",
            "partial_recheck_failed",
            staged,
            backend,
            None,
            None,
            moment,
            "The follow-up was previously recorded, but repair checks failed; no write was made.",
        )
        return _finish(ledger, change_id, "partial", result)

    if _hash(schema) != staged["schema_hash"]:
        result = _receipt(
            "partial",
            "schema_changed_after_partial",
            staged,
            backend,
            customer,
            followup,
            moment,
            "The follow-up remains recorded, but the schema changed; stage a repair plan.",
        )
        return _finish(ledger, change_id, "partial", result)
    if followup is None or not _fields_match(
        followup, _followup_verification_payload(staged)
    ):
        result = _receipt(
            "verification_unknown",
            "partial_followup_unverified",
            staged,
            backend,
            customer,
            followup,
            moment,
            "The prior follow-up can no longer be verified; no customer write was made.",
        )
        return _finish(ledger, change_id, "verification_unknown", result)
    if customer is not None and _fields_match(customer, staged["customer_patch"]):
        result = _receipt(
            "verified",
            "partial_already_completed",
            staged,
            backend,
            customer,
            followup,
            moment,
            "Both records now match the staged change; no duplicate write was made.",
        )
        return _finish(ledger, change_id, "verified", result)
    if customer is None or _hash(_snapshot(customer)) != staged["snapshot_hash"]:
        result = _receipt(
            "partial",
            "customer_changed_after_partial",
            staged,
            backend,
            customer,
            followup,
            moment,
            "The follow-up remains recorded, but customer data changed; stage a repair plan.",
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
    rows = list(backend.find_customers(query))
    for row in rows:
        _validate_customer(row)
    needle = _normal(query)
    numbered = [row for row in rows if _normal(row.get("customer_number")) == needle]
    if numbered:
        return numbered, "customer_number"
    named = [row for row in rows if _normal(row.get("name")) == needle]
    return named, "name"


def _followup(value: Any) -> dict[str, Any]:
    item = _mapping(value, "followup")
    _only_keys(
        item,
        {"occurred_at", "content", "channel", "next_action", "next_followup_at"},
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
        result["next_followup_at"] = _parse_time(
            item["next_followup_at"], "followup.next_followup_at"
        ).isoformat()
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
    for field in ("next_action", "next_followup_at"):
        if field in followup:
            patch[field] = followup[field]
    return patch


def _followup_payload(staged: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "change_id": staged["change_id"],
        "customer_record_id": staged["customer_record_id"],
        "customer_number": staged.get("customer_number"),
        **staged["followup"],
        "created_by": staged["actor"]["feishu_user_id"],
    }


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
    url = _safe_url(backend.customer_url, record_id)
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
        url = _safe_url(backend.followup_url, record_id)
        if url:
            view["url"] = url
    return view


def _snapshot(customer: Mapping[str, Any]) -> dict[str, Any]:
    return {field: _jsonable(customer.get(field)) for field in _DISPLAY_FIELDS if field in customer}


def _actor(value: Any, config: Mapping[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    context = _mapping(value, "actor")
    _only_keys(context, {"sender_id", "chat_id"})
    sender_id = _required_text(context.get("sender_id"), "actor.sender_id")
    chat_id = _required_text(context.get("chat_id"), "actor.chat_id")
    allowed = config.get("allowed_actors")
    if not isinstance(allowed, Mapping) or sender_id not in allowed:
        raise ValueError("actor is not configured")
    actor = _mapping(allowed[sender_id], "allowed actor")
    display_name = _required_text(actor.get("display_name"), "actor display_name")
    feishu_user_id = _required_text(actor.get("feishu_user_id"), "actor feishu_user_id")
    return {"sender_id": sender_id, "chat_id": chat_id}, {
        "display_name": display_name,
        "feishu_user_id": feishu_user_id,
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


def _fence_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _fence_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_fence_value(item) for item in value]
    if not isinstance(value, str):
        return value
    text = unicodedata.normalize("NFKC", value)
    text = _FORGED_TAG.sub("[filtered-tag]", text)
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
