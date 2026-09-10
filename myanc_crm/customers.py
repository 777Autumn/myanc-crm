"""Two narrow customer-profile operations; authenticated approval stays in core."""

from __future__ import annotations

import re
import secrets
from datetime import timedelta
from typing import Any, Mapping

from . import core


STAGES = frozenset({"新线索", "已联系", "沟通中", "已成交", "暂缓"})
PROFILE_FIELDS = {"name", "contact", "phone", "email", "stage", "owner"}
INPUT_FIELDS = PROFILE_FIELDS - {"owner"} | {"owner_ref"}
_LIMITS = {**core.CUSTOMER_TEXT_LIMITS, "stage": 64, "owner_ref": 132}


def _needs(fields, code="customer_input_required"):
    return {"status": "needs_input", "code": code, "missing_fields": fields,
            "message": "Complete the listed fields before staging; CRM is unchanged."}


def _person(value):
    item = core._mapping(value, "verified assignee")
    return {"id": core._required_text(item.get("id"), "assignee.id", 128),
            "name": core._required_text(item.get("name"), "assignee.name", 256)}


def resolve_assignee(request, backend, ledger, config, principal):
    """Resolve trusted roster names, scoped cache, or exact phone/user-email."""
    try:
        principal = core._principal(principal)
        core._actor_for_principal(principal, config)
        core._only_keys(core._mapping(request, "request"), {"query"})
        query = core._required_text(request.get("query"), "query", 256)
        # The administrator's roster wins over any same-name historical cache.
        # Roster membership grants no new assistant access or approval authority.
        roster = [actor for actor in config.get("allowed_actors", {}).values()
                  if actor.get("display_name") == query]
        if roster:
            if len(roster) != 1:
                return _needs(["exact_phone_or_user_email"], "assignee_ambiguous")
            identifier = core._required_text(roster[0].get("feishu_user_id"), "assignee.id", 128)
            person = _person(backend.get_assignee(identifier))
            if person["id"] != identifier or person["name"] != query:
                return _needs(["exact_phone_or_user_email"], "assignee_changed")
            ref = ledger.remember_assignee(principal, person)
            return {"status": "resolved", "owner_ref": ref, "name": core._fence_value(person["name"])}
        cached = ledger.find_assignees(query, principal)
        if cached:
            choices = [{"owner_ref": row["ref"], "name": core._fence_value(row["name"])} for row in cached]
        else:
            if not (re.fullmatch(r"\+?\d{6,20}", query) or re.fullmatch(r"[^@\s]+@[^@\s]+", query)):
                return _needs(["exact_phone_or_user_email"], "assignee_lookup_required")
            choices = []
            seen = set()
            for candidate in backend.resolve_assignee(query):
                person = _person(candidate)
                if person["id"] in seen:
                    continue
                seen.add(person["id"])
                # The fixed backend resolves and verifies this person's name/status.
                # Stage and apply each recheck it again before authorizing a write.
                ref = ledger.remember_assignee(principal, person)
                choices.append({"owner_ref": ref, "name": core._fence_value(person["name"])})
        if not choices:
            return _needs(["exact_phone_or_user_email"], "assignee_not_found")
        if len(choices) != 1:
            return {"status": "needs_selection", "code": "assignee_ambiguous", "candidates": choices}
        return {"status": "resolved", **choices[0]}
    except (ValueError, TypeError) as exc:
        return core._blocked("invalid_assignee_request", str(exc))
    except Exception:
        return core._blocked("assignee_lookup_failed", "The configured CRM identity could not verify this assignee.")


def _owner_ids(value):
    if isinstance(value, Mapping):
        value = [value]
    if not isinstance(value, (list, tuple)):
        return []
    if any(not isinstance(item, Mapping) or not isinstance(item.get("id"), str) or not item["id"] for item in value):
        return []
    return [item["id"] for item in value]


def _missing(fields):
    missing = []
    if not fields.get("name"):
        missing.append("name")
    if not any(fields.get(key) for key in ("contact", "phone", "email")):
        missing.append("contact_or_phone_or_email")
    if not fields.get("stage"):
        missing.append("stage")
    if not fields.get("owner_ref") and not _owner_ids(fields.get("owner")):
        missing.append("owner_ref")
    return missing


def _duplicates(name, backend, excluded=None):
    """Fingerprint every displayed field, not only candidate names or counts."""
    rows = {}
    for candidate in backend.find_customers(name):
        if core._normal(candidate.get("name")) != core._normal(name):
            continue
        identifier = core._record_id(candidate)
        if identifier == excluded:
            continue
        actual = backend.get_customer(identifier)
        if actual is None:
            raise ValueError("A duplicate candidate disappeared.")
        core._validate_customer(actual)
        rows[identifier] = {"record_id": identifier, **core._snapshot(actual)}
    return [rows[key] for key in sorted(rows)]


def stage_customer(command, operation_type, backend, ledger, config, action_token, principal, now=None):
    """Freeze an exact profile plan and optional later follow-up; write no CRM."""
    try:
        principal = core._principal(principal)
        actor = core._actor_for_principal(principal, config)
        token_hash = core._action_token_hash(action_token)
        intent = ledger.note_write_intent(principal)
        moment = core._now(now)
        if operation_type not in {"customer_create", "customer_update"}:
            raise ValueError("Unsupported customer operation.")
        create = operation_type == "customer_create"
        command = core._mapping(command, "request")
        allowed = INPUT_FIELDS if create else {"customer_query", "changes"}
        core._only_keys(command, allowed | {"allow_same_name", "followup"})
        allow_same = command.get("allow_same_name", False)
        if not isinstance(allow_same, bool):
            raise ValueError("allow_same_name must be a boolean.")
        raw = ({key: command[key] for key in INPUT_FIELDS if key in command} if create
               else core._mapping(command.get("changes"), "changes"))
        core._only_keys(raw, INPUT_FIELDS)
        if not raw and not create:
            raise ValueError("At least one customer field must be changed.")
        values = {key: None if value is None else core._required_text(value, key, _LIMITS[key])
                  for key, value in raw.items()}
        if values.get("stage") is not None and values["stage"] not in STAGES:
            raise ValueError("stage must be one of the five configured choices.")
        missing = _missing(values) if create else []
        followup = command.get("followup")
        followup_missing = []
        if followup is not None:
            followup = core._mapping(followup, "followup")
            core._only_keys(followup, {"occurred_at", "content", "channel", "next_action", "next_followup_at"})
            followup_missing = ["followup." + key for key in ("occurred_at", "content") if not followup.get(key)]
        if create and (missing or followup_missing):
            return _needs(missing + followup_missing)
        if followup is not None and not followup_missing:
            followup = core._followup(followup)
        ttl = int(config.get("ttl_seconds", 600))
        if ttl <= 0:
            raise ValueError("ttl_seconds must be positive.")
        query = None if create else core._required_text(command.get("customer_query"), "customer_query", 256)
    except (ValueError, TypeError) as exc:
        return core._blocked("invalid_customer_request", str(exc))
    except Exception:
        return core._blocked("ledger_unavailable", "The write intent could not be recorded.")

    try:
        schema = core._mapping(backend.read_schema(), "schema")
        customer, matched_by = {}, "new_customer"
        if not create:
            matches, matched_by = core._resolve_customer(query, backend)
            if len(matches) != 1:
                return {"status": "needs_selection", "code": "customer_ambiguous" if matches else "customer_not_found",
                        "candidates": [core._display_customer(row, backend) for row in matches]}
            customer = backend.get_customer(core._record_id(matches[0]))
            if customer is None:
                raise ValueError("The selected customer disappeared.")
            core._validate_customer(customer)
        fields = {key: customer.get(key) for key in PROFILE_FIELDS}
        fields.update(values)
        missing = _missing(fields) + followup_missing
        if missing:
            return _needs(missing)
        if fields["stage"] not in STAGES:
            raise ValueError("Current stage is not a configured choice.")
        if "owner_ref" in values:
            stored = ledger.get_assignee(values["owner_ref"], principal)
            if stored is None:
                return _needs(["owner_ref"], "assignee_not_verified")
            assignee = _person(stored)
        else:
            identifiers = _owner_ids(fields.get("owner"))
            if len(identifiers) != 1:
                return _needs(["owner_ref"], "single_assignee_required")
            existing_person = backend.get_assignee(identifiers[0])
            if existing_person is None:
                return _needs(["owner_ref"], "assignee_changed")
            assignee = _person(existing_person)
        current_assignee = backend.get_assignee(assignee["id"])
        if current_assignee is None or _person(current_assignee) != assignee:
            return _needs(["owner_ref"], "assignee_changed")
        fields.pop("owner_ref", None)
        fields["owner"] = [assignee]
        patch = dict(fields) if create else {("owner" if key == "owner_ref" else key):
                                             fields["owner" if key == "owner_ref" else key] for key in values}
        identifier = None if create else core._record_id(customer)
        duplicates = _duplicates(fields["name"], backend, identifier)
        renamed = not create and core._normal(fields["name"]) != core._normal(customer["name"])
        if duplicates and (create or renamed) and not allow_same:
            return {"status": "needs_selection", "code": "same_name_customer", "candidates":
                    [core._display_customer(row, backend) for row in duplicates],
                    "message": "Select an existing customer number, or explicitly confirm a distinct same-name company."}
        change_id = "chg_" + secrets.token_urlsafe(18)
        snapshot = core._snapshot(customer)
        body = {"change_id": change_id, "operation_type": operation_type, "customer_query": query,
                "matched_by": matched_by, "customer_record_id": identifier,
                "customer_number": customer.get("customer_number"),
                "customer_snapshot": {"record_id": identifier, **snapshot},
                "schema_hash": core._hash(schema), "snapshot_hash": core._hash(snapshot),
                "before": {key: snapshot.get(key) for key in patch}, "customer_fields": fields,
                "customer_patch": patch, "assignee": assignee, "duplicate_snapshot": duplicates,
                "duplicate_hash": core._hash(duplicates), "followup": followup,
                "request": {**dict(command), "followup": followup}, "principal": principal, "actor": actor,
                "created_at": core._iso(moment), "expires_at": core._iso(moment + timedelta(seconds=ttl))}
        ledger.stage(body, token_hash, intent_version=intent)
        return {"status": "staged", "change_id": change_id, "expires_at": body["expires_at"],
                "preview": approval_preview(body, backend)}
    except (ValueError, TypeError) as exc:
        return core._blocked("invalid_customer_data", str(exc))
    except Exception:
        return core._blocked("customer_stage_failed", "The customer proposal could not be staged; CRM is unchanged.")


def approval_preview(staged, backend):
    create = staged["operation_type"] == "customer_create"
    customer = (core._fence_value({**staged["customer_fields"], "customer_number": "创建后由飞书生成"})
                if create else core._display_customer(staged["customer_snapshot"], backend))
    changes = core._field_changes(staged["before"], staged["customer_patch"])
    for change in changes:
        change["after"] = core._fence_value(change["after"])
    return {"operation_type": staged["operation_type"], "actor": staged["actor"]["display_name"],
            "matched_by": staged["matched_by"], "customer": customer,
            "effects": {"customer_profile": {"operation_type": staged["operation_type"],
                         "fields": core._fence_value(staged["customer_fields"]),
                         "changes": changes}},
            "followup_draft": core._fence_value(staged.get("followup")),
            "same_name_customers": [core._display_customer(row, backend) for row in staged["duplicate_snapshot"]],
            "allow_same_name": staged["request"].get("allow_same_name", False),
            "created_at": staged["created_at"], "expires_at": staged["expires_at"],
            "execution_order": ["create_customer" if create else "update_customer_profile", "read_customer"],
            "failure_policy": "结果未知时停止，不盲目重试。首次跟进是独立待审批方案，取消它不撤销已核验的客户变更。"}


def _matches_customer(actual, staged):
    try:
        actual = core._mapping(actual, "customer readback")
        core._validate_customer(actual)
        expected = staged["customer_fields"]
        if not all(core._equal(actual.get(key), value) for key, value in expected.items() if key != "owner"):
            return False
        if _owner_ids(actual.get("owner")) != [staged["assignee"]["id"]]:
            return False
        if staged["operation_type"] == "customer_create":
            return actual.get("operation_id") == staged["change_id"]
        return (core._record_id(actual) == staged["customer_record_id"] and
                actual.get("customer_number") == staged["customer_number"])
    except (ValueError, TypeError):
        return False


def _read_verified(read, staged):
    last = None
    def accepted():
        nonlocal last
        actual = read()
        if actual is not None:
            actual = core._mapping(actual, "customer readback")
            core._record_id(actual)
            last = actual
            if _matches_customer(actual, staged):
                return actual
        return None
    return core._poll_read(accepted) or last


def _observed_profile(staged, actual, backend):
    view = core._display_customer(actual, backend)
    changes = core._field_changes(staged["before"], staged["customer_patch"], actual)
    for change in changes:
        change["after"] = core._fence_value(change["after"])
        if change["field"] == "owner":
            change["verified"] = _owner_ids(actual.get("owner")) == [staged["assignee"]["id"]]
    return {"customer": view, "customer_after": view,
            "customer_profile": {"operation_type": staged["operation_type"], "fields": view, "changes": changes}}


def _observed_result(staged, actual, backend, ledger, moment):
    create = staged["operation_type"] == "customer_create"
    if create and actual is not None and actual.get("operation_id") == staged["change_id"]:
        # Observed identity supports later result lookup, not a verified outcome
        # or permission to prepare a child. Never change the approved proposal.
        ledger.set_resolved_customer(staged["change_id"], core._record_id(actual))
    if actual is None or not _matches_customer(actual, staged):
        result = {
            "status": "verification_unknown", "code": "customer_write_unconfirmed",
            "operation_type": staged["operation_type"], "change_id": staged["change_id"],
            "message": "The customer write could not be verified. Inspect the original operation; do not repeat it."}
        if actual is not None:
            try:
                core._record_id(core._mapping(actual, "customer readback"))
                result.update(_observed_profile(staged, actual, backend))
            except (ValueError, TypeError):
                pass
        return core._finish(ledger, staged["change_id"], "verification_unknown", result)
    ledger.set_resolved_customer(staged["change_id"], core._record_id(actual))
    result = {"status": "verified", "code": "customer_created_verified" if create else "customer_updated_verified",
              "operation_type": staged["operation_type"], "change_id": staged["change_id"],
              "verified_at": core._iso(moment), **_observed_profile(staged, actual, backend),
              "message": "Customer profile was written and read back."}
    if staged.get("followup") is not None:
        result["message"] += " The supplied follow-up still requires its own approval."
    return core._finish(ledger, staged["change_id"], "verified", result)


def apply_customer(staged, backend, ledger, moment):
    """Called only after core checks a claimed host approval; never retries writes."""
    change_id = staged["change_id"]
    state = staged["state"]
    if staged.get("receipt") and state not in {"staged", "applying"}:
        return {**staged["receipt"], "replayed": True}
    if state == "applying":
        return {"status": "verification_unknown", "code": "apply_in_progress", "change_id": change_id}
    if state != "staged":
        return core._replan(change_id, "change_not_pending", "This customer plan is no longer pending.")
    if moment > core._parse_time(staged["expires_at"], "expires_at"):
        return core._finish(ledger, change_id, "expired", core._replan(change_id, "expired", "The preview expired."))
    if not ledger.claim(change_id):
        return {"status": "verification_unknown", "code": "apply_in_progress", "change_id": change_id}
    return core._run_customer_write(staged, ledger, moment,
                                    lambda effective: _apply_claimed_customer(staged, backend, ledger, effective))


def _apply_claimed_customer(staged, backend, ledger, moment):
    change_id = staged["change_id"]
    create = staged["operation_type"] == "customer_create"
    try:
        if create:
            existing = backend.find_customer_by_change(change_id)
            if existing is not None:
                return _observed_result(staged, existing, backend, ledger, moment)
        if core._hash(backend.read_schema()) != staged["schema_hash"]:
            return core._finish(ledger, change_id, "replan_required", core._replan(change_id, "schema_changed", "CRM schema changed."))
        person = backend.get_assignee(staged["assignee"]["id"])
        if person is None or _person(person) != staged["assignee"]:
            return core._finish(ledger, change_id, "replan_required", core._replan(change_id, "assignee_changed", "The assignee changed; verify and preview again."))
        if not create:
            matches, _ = core._resolve_customer(staged["customer_query"], backend)
            actual = backend.get_customer(staged["customer_record_id"])
            if (len(matches) != 1 or core._record_id(matches[0]) != staged["customer_record_id"] or
                    actual is None or core._hash(core._snapshot(actual)) != staged["snapshot_hash"]):
                return core._finish(ledger, change_id, "replan_required", core._replan(change_id, "customer_changed", "Customer data changed after preview."))
        duplicates = _duplicates(staged["customer_fields"]["name"], backend, staged["customer_record_id"])
        if core._hash(duplicates) != staged["duplicate_hash"]:
            return core._finish(ledger, change_id, "replan_required", core._replan(change_id, "same_name_changed", "Same-name candidates changed after preview."))
    except Exception:
        return core._finish(ledger, change_id, "failed", {"status": "failed", "code": "prewrite_read_failed",
                            "change_id": change_id, "message": "Pre-write checks failed; no new write was started."})
    try:
        if create:
            identifier = core._created_record_id(backend.create_customer({**staged["customer_fields"], "operation_id": change_id}))
            ledger.set_resolved_customer(change_id, identifier)
        else:
            identifier = staged["customer_record_id"]
            backend.update_customer_profile(identifier, staged["customer_patch"])
        actual = _read_verified(lambda: backend.get_customer(identifier), staged)
    except Exception:
        read = (lambda: backend.find_customer_by_change(change_id)) if create else (lambda: backend.get_customer(staged["customer_record_id"]))
        actual = _read_verified(read, staged)
    return _observed_result(staged, actual, backend, ledger, moment)
