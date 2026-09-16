"""Host-owned customer-plan revisions and a transactional reminder outbox.

These helpers are not model tools. The CRM receipt is the sole authority that
advances a plan; the reminder host owns recipient routing and notification state.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, time, timedelta, timezone
from typing import Mapping

from . import core


FIELDS = frozenset({"next_action", "next_followup_at"})
BEIJING = timezone(timedelta(hours=8))


def initialize(db):
    db.execute("CREATE TABLE IF NOT EXISTS customer_plans ("
               "namespace TEXT NOT NULL, customer_id TEXT NOT NULL, revision INTEGER NOT NULL, "
               "body_json TEXT NOT NULL, PRIMARY KEY(namespace, customer_id))")
    db.execute("CREATE TABLE IF NOT EXISTS plan_outbox ("
               "event_id TEXT PRIMARY KEY, namespace TEXT NOT NULL, customer_id TEXT NOT NULL, "
               "revision INTEGER NOT NULL, body_json TEXT NOT NULL, acknowledged INTEGER NOT NULL DEFAULT 0, "
               "UNIQUE(namespace, customer_id, revision))")


def namespace(config):
    if config.get("base_token") and config.get("customer_table_id"):
        return core._hash([config["base_token"], config["customer_table_id"]])
    # Synthetic/in-process backends do not have Feishu tokens. Never infer a
    # namespace from a model request or a conversation/project identity.
    if config.get("crm_plan_namespace"):
        return core._required_text(config["crm_plan_namespace"], "CRM plan namespace", 256)
    if config.get("crm_plan_reminders_enabled", False):
        raise ValueError("CRM plan namespace is not configured.")
    return "unconfigured-disabled"


def enabled(config):
    value = config.get("crm_plan_reminders_enabled", False)
    if not isinstance(value, bool):
        raise ValueError("crm_plan_reminders_enabled must be a boolean.")
    return value


def normalize_time(value, previous=None):
    if value is None:
        return None
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        day = datetime.strptime(value, "%Y-%m-%d").date()
        prior = core._optional_time(previous)
        clock = prior.astimezone(BEIJING).time().replace(tzinfo=None) if prior else time(9)
        return datetime.combine(day, clock, BEIJING).isoformat()
    return core._parse_time(value, "next_followup_at").isoformat()


def current(ledger, scope, customer_id):
    row = ledger._db.execute("SELECT body_json FROM customer_plans WHERE namespace=? AND customer_id=?",
                             (scope, customer_id)).fetchone()
    return json.loads(row["body_json"]) if row else None


def freeze(customer, patch, request, ledger, config, moment, *, binding=None,
           expected_revision=None, historical=False):
    """Return a frozen effect, or None for unrelated/no-op/historical writes."""
    if "remind" in request and not isinstance(request["remind"], bool):
        raise ValueError("remind must be a boolean.")
    if historical:
        return None
    changed = any(key in patch and not core._equal(customer.get(key), patch[key]) for key in FIELDS)
    if not changed and "remind" not in request:
        return None
    fields = {key: patch.get(key, customer.get(key)) for key in FIELDS}
    at = fields["next_followup_at"]
    check_time = changed or request.get("remind") is not False
    if check_time and at is not None and core._parse_time(at, "next_followup_at") <= moment:
        raise ValueError("The current plan time has passed; specify a future time or explicitly clear it.")
    if request.get("remind") is True and at is None:
        raise ValueError("A reminder needs a future next_followup_at.")
    scope = namespace(config)
    previous = current(ledger, scope, core._record_id(customer))
    revision = previous["revision"] if previous else 0
    if expected_revision is not None and (type(expected_revision) is not int or expected_revision != revision):
        raise ValueError("The associated customer plan changed; read and preview again.")
    notify = enabled(config) and at is not None and request.get("remind", True)
    if notify and (not isinstance(binding, Mapping) or not binding):
        raise ValueError("The host must verify and bind the sender's private reminder route before staging.")
    return {"namespace": scope, "customer_id": core._record_id(customer),
            "expected_revision": revision, "fields": fields, "enabled": bool(notify),
            "queue_enabled": enabled(config), "reminder_binding": dict(binding or {}),
            "check_time": check_time,
            "replaces_previous": bool(previous and previous.get("enabled")),
            "explicit_remind": request.get("remind")}


def preview(staged):
    plan = staged.get("plan")
    if plan is None:
        return {}
    return {"plan_reminder": {
        "enabled": plan["enabled"], "at": plan["fields"]["next_followup_at"],
        "recipient": staged.get("actor", {}).get("display_name"),
        "delivery": "本人私聊" if plan["enabled"] else "不发送提醒",
        "replaces_previous": plan["replaces_previous"],
        "message": "本客户旧计划的关联通知会被替换；其他个人提醒不受影响。"}}


def verify_binding(plan, principal):
    if plan is None or not plan["enabled"]:
        return
    binding = core._mapping(plan["reminder_binding"], "reminder binding")
    core._only_keys(binding, {"user_id", "source_chat_id", "project", "private_chat_id"})
    core._required_text(binding.get("private_chat_id"), "private reminder route", 256)
    if any(binding.get(key) != principal.get(source) for key, source in
           (("user_id", "user_id"), ("source_chat_id", "chat_id"), ("project", "project"))):
        raise ValueError("The host reminder route does not match the requesting principal.")


def check(staged, ledger, moment):
    plan = staged.get("plan")
    if plan is None:
        return None
    actual = current(ledger, plan["namespace"], plan["customer_id"])
    revision = actual["revision"] if actual else 0
    if revision != plan["expected_revision"]:
        return core._replan(staged["change_id"], "plan_changed", "The customer plan changed after preview.")
    at = plan["fields"]["next_followup_at"]
    if plan.get("check_time", True) and at is not None and core._parse_time(at, "next_followup_at") <= moment:
        return core._replan(staged["change_id"], "plan_time_passed", "The plan time passed before execution; preview again.")
    return None


def finish(ledger, staged, receipt):
    """Called inside Ledger.finish's receipt transaction, never commit here."""
    plan = staged.get("plan")
    if plan is None:
        return
    previous = current(ledger, plan["namespace"], plan["customer_id"])
    # A second parent receipt update or an idempotent execution cannot requeue.
    if previous and previous["change_id"] == staged["change_id"]:
        receipt["plan_revision"] = previous["revision"]
        receipt["plan_reminder_status"] = "pending_sync" if plan["queue_enabled"] else "disabled"
        return
    if (previous["revision"] if previous else 0) != plan["expected_revision"]:
        raise ValueError("The verified write cannot overwrite a newer customer plan revision.")
    revision = plan["expected_revision"] + 1
    fields = plan["fields"]
    snapshot = staged["customer_snapshot"]
    event = {"event_id": "plan_" + staged["change_id"], "namespace": plan["namespace"],
             "customer_id": plan["customer_id"], "revision": revision, "change_id": staged["change_id"],
             "principal": staged["principal"], "actor": staged["actor"],
             "at": fields["next_followup_at"], "content": fields["next_action"] or "跟进客户",
             "fields": fields, "enabled": plan["enabled"],
             "customer_query": snapshot["customer_number"], "customer_name": snapshot["name"],
             "reminder_binding": plan["reminder_binding"]}
    ledger._db.execute("INSERT INTO customer_plans(namespace,customer_id,revision,body_json) VALUES(?,?,?,?) "
                       "ON CONFLICT(namespace,customer_id) DO UPDATE SET revision=excluded.revision,body_json=excluded.body_json",
                       (event["namespace"], event["customer_id"], revision, core._json(event)))
    if plan["queue_enabled"]:
        ledger._db.execute("INSERT INTO plan_outbox(event_id,namespace,customer_id,revision,body_json) VALUES(?,?,?,?,?)",
                           (event["event_id"], event["namespace"], event["customer_id"], revision, core._json(event)))
    receipt["plan_revision"] = revision
    receipt["plan_reminder_status"] = "pending_sync" if plan["queue_enabled"] else "disabled"
    receipt["plan_reminder_message"] = ("CRM 计划已核验；关联提醒正在同步，尚未确认设置完成。"
                                        if event["enabled"] else
                                        "CRM 计划已核验；旧关联通知正在关闭，在途消息可能无法撤回。"
                                        if plan["queue_enabled"] else "CRM 计划已核验；关联提醒功能未启用。")


def events(request, ledger, config):
    try:
        core._only_keys(core._mapping(request, "request"), {"limit"})
        if not enabled(config):
            return {"status": "disabled", "events": [], "has_more": False}
        limit = request.get("limit", 100)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100.")
        rows = ledger._db.execute("SELECT body_json FROM plan_outbox WHERE namespace=? AND acknowledged=0 "
                                  "ORDER BY rowid LIMIT ?", (namespace(config), limit + 1)).fetchall()
        return {"status": "ok", "events": [json.loads(row["body_json"]) for row in rows[:limit]],
                "has_more": len(rows) > limit}
    except Exception:
        return core._blocked("plan_queue_unavailable", "The customer-plan queue could not be read.")


def read(request, backend, ledger, config):
    try:
        core._only_keys(core._mapping(request, "request"), {"namespace", "customer_id", "revision"})
        if not enabled(config) or request.get("namespace") != namespace(config):
            return core._blocked("plan_namespace_disabled", "Customer-plan reminders are disabled or the CRM namespace differs.")
        customer_id = core._required_text(request.get("customer_id"), "customer_id", 256)
        revision = request.get("revision")
        if type(revision) is not int or revision < 1:
            raise ValueError("revision is invalid.")
        plan = current(ledger, namespace(config), customer_id)
        if plan is None or plan["revision"] != revision:
            return core._blocked("plan_superseded", "The customer plan has been replaced.")
        # An uncertain write can leave the old CRM fields looking identical
        # (including a recipient-only re-confirmation). Never send the old plan
        # while its customer's write is in flight or awaits reconciliation.
        if ledger._db.execute("SELECT 1 FROM write_fences WHERE scope_key=?",
                              (core._hash(["record", customer_id]),)).fetchone():
            return core._blocked("plan_write_unresolved", "A customer write is in progress or requires verification.")
        if core._actor_for_principal(plan["principal"], config) != plan["actor"]:
            return core._blocked("plan_authorization_changed", "The original CRM actor binding changed.")
        actual = backend.get_customer(customer_id)
        if actual is None or not core._fields_match(actual, plan["fields"]):
            return core._blocked("plan_customer_changed", "The CRM plan differs; confirm a new plan before sending.")
        core._validate_customer(actual)
        return {"status": "current", "plan": plan}
    except Exception:
        return core._blocked("plan_read_unavailable", "The current CRM plan could not be verified; do not send.")


def ack(request, ledger, config):
    try:
        core._only_keys(core._mapping(request, "request"), {"event_id"})
        event_id = core._required_text(request.get("event_id"), "event_id", 256)
        with ledger._immediate():
            row = ledger._db.execute("SELECT 1 FROM plan_outbox WHERE event_id=? AND namespace=?",
                                     (event_id, namespace(config))).fetchone()
            if row is None:
                return core._blocked("unknown_plan_event", "The customer-plan event is unknown.")
            ledger._db.execute("UPDATE plan_outbox SET acknowledged=1 WHERE event_id=?", (event_id,))
        return {"status": "acknowledged", "event_id": event_id}
    except Exception:
        return core._blocked("plan_ack_failed", "The customer-plan event was not acknowledged.")


def synchronization(staged, ledger):
    """Current host synchronization, separate from the immutable CRM receipt."""
    plan = staged.get("plan")
    if plan is None or staged.get("state") != "verified":
        return None
    if not plan["queue_enabled"]:
        return {"status": "disabled", "message": "关联提醒功能未启用。"}
    try:
        actual = current(ledger, plan["namespace"], plan["customer_id"])
        if actual is not None and actual["change_id"] != staged["change_id"]:
            return {"status": "replaced", "message": "这份计划已被后续审批替换。"}
        row = ledger._db.execute("SELECT acknowledged FROM plan_outbox WHERE event_id=?",
                                 ("plan_" + staged["change_id"],)).fetchone()
        if row is None:
            raise ValueError("missing verified plan event")
        if row["acknowledged"]:
            return {"status": "synchronized", "message": "关联通知安排已同步；是否已发送或后来取消，以提醒清单为准。"}
        return {"status": "pending_sync", "message": "CRM 计划已核验，关联通知安排尚待同步。"}
    except Exception:
        return {"status": "unavailable", "message": "CRM 结果不变；暂时无法核实关联通知的同步状态。"}
