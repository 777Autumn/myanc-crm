"""JSON-only command-line boundary for the CRM follow-up flow."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, TextIO

from .core import (
    Ledger,
    begin_approval,
    bind_approval_card,
    claim_approval_decision,
    decide_approval,
    execute_claimed_approval,
    stage_followup,
)
from .lark import LarkCliBackend
from . import core


MAX_INPUT_BYTES = 256 * 1024
ACTION_TOKEN_ENV = "MYANC_CRM_ACTION_TOKEN"
HOST_SECRET_ENV = "MYANC_CRM_HOST_SECRET"
BUSINESS_FIELDS = frozenset(
    {
        "customer_query",
        "occurred_at",
        "channel",
        "content",
        "next_action",
        "next_followup_at",
    }
)
PRINCIPAL_FIELDS = frozenset(
    {"platform", "user_id", "chat_id", "session_key", "project", "message_id"}
)
NON_PENDING_STAGE_STATUSES = frozenset(
    {"needs_time", "needs_input", "needs_selection", "not_found", "blocked"}
)
CREATE_FIELDS = frozenset({"name", "contact", "phone", "email", "stage", "owner_ref",
                           "allow_same_name", "followup"})
UPDATE_FIELDS = frozenset({"customer_query", "changes", "allow_same_name", "followup"})


class CliConfigurationError(ValueError):
    """A safe-to-report local configuration error."""


def _config_path() -> Path:
    development = Path(__file__).resolve().parents[1] / "config.local.json"
    if development.is_file():
        return development
    return Path("/etc/myanc-crm/config.json")


def _load_config(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CliConfigurationError("CRM configuration is unavailable or invalid.") from exc
    if not isinstance(value, dict):
        raise CliConfigurationError("CRM configuration must be a JSON object.")
    return value


def _required_mapping(config: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = config.get(name)
    if not isinstance(value, Mapping):
        raise CliConfigurationError(f"CRM configuration is missing {name}.")
    return value


def _required_text(config: Mapping[str, Any], name: str) -> str:
    value = config.get(name)
    if not isinstance(value, str) or not value.strip():
        raise CliConfigurationError(f"CRM configuration is missing {name}.")
    return value.strip()


def _runtime(config: Mapping[str, Any], config_path: Path) -> tuple[LarkCliBackend, Ledger]:
    raw_ledger = _required_text(config, "ledger_path")
    ledger_path = Path(raw_ledger)
    if not ledger_path.is_absolute():
        raise CliConfigurationError("CRM ledger_path must be absolute.")
    ledger_path = ledger_path.resolve(strict=False)
    working_directory = Path.cwd().resolve(strict=False)
    if ledger_path == working_directory or working_directory in ledger_path.parents:
        raise CliConfigurationError(
            "CRM ledger_path must be outside the Claude working directory."
        )
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    backend = LarkCliBackend(
        wrapper_path=_required_text(config, "wrapper_path"),
        base_token=_required_text(config, "base_token"),
        customer_table_id=_required_text(config, "customer_table_id"),
        followup_table_id=_required_text(config, "followup_table_id"),
        base_url=_required_text(config, "base_url"),
        fields=_required_mapping(config, "fields"),
    )
    return backend, Ledger(ledger_path)


def _read_command(stream: TextIO) -> Mapping[str, Any]:
    raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw.encode("utf-8")) > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds the 256 KiB limit.")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Input must be one valid JSON object.") from exc
    if not isinstance(value, Mapping):
        raise ValueError("Input must be one valid JSON object.")
    return value


def _safe_failure(command: str, code: str, message: str) -> dict[str, Any]:
    if command == "stage":
        return {"status": "blocked", "code": code, "message": message}
    return {"status": "failed", "code": code, "message": message}


def _environment_secret(name: str) -> str:
    value = os.environ.get(name, "")
    if len(value) < 32 or len(value) > 4096:
        raise CliConfigurationError(f"{name} is unavailable.")
    return value


def _require_host(config: Mapping[str, Any]) -> None:
    expected = _required_text(config, "host_secret_sha256")
    if len(expected) != 64 or any(
        character not in "0123456789abcdef" for character in expected
    ):
        raise CliConfigurationError("CRM host authentication is invalid.")
    actual = hashlib.sha256(
        _environment_secret(HOST_SECRET_ENV).encode("utf-8")
    ).hexdigest()
    if not hmac.compare_digest(actual, expected):
        raise CliConfigurationError("CRM host authentication failed.")


def _host_prepare_payload(
    value: Mapping[str, Any], config: Mapping[str, Any],
    request_fields: frozenset[str] = BUSINESS_FIELDS,
) -> tuple[Mapping[str, Any], dict[str, str]]:
    """Validate the complete host-to-CRM handoff before any CRM read."""

    if set(value) != {"request", "principal"}:
        raise ValueError("host-prepare requires exactly request and principal.")

    request = value.get("request")
    if not isinstance(request, Mapping):
        raise ValueError("request must be one JSON object.")
    unexpected = sorted(set(request) - request_fields)
    if unexpected:
        raise ValueError("request contains unsupported business fields.")

    raw_principal = value.get("principal")
    if not isinstance(raw_principal, Mapping) or set(raw_principal) != PRINCIPAL_FIELDS:
        raise ValueError("principal must contain exactly the trusted transport fields.")
    principal: dict[str, str] = {}
    for name in PRINCIPAL_FIELDS:
        item = raw_principal.get(name)
        if not isinstance(item, str) or not item.strip() or len(item.strip()) > 1024:
            raise ValueError("principal contains an invalid transport field.")
        principal[name] = item.strip()

    allowed = _required_mapping(config, "allowed_actors")
    actor = allowed.get(principal["user_id"])
    if not isinstance(actor, Mapping):
        raise ValueError("principal is not configured.")
    _required_text(actor, "display_name")
    _required_text(actor, "feishu_user_id")
    return request, principal


def _host_tool_payload(value, config):
    if set(value) != {"command", "request", "principal"}:
        raise ValueError("host-tool requires exactly command, request and principal.")
    fields = {"customer": frozenset({"customer_query"}),
              "stage": BUSINESS_FIELDS, "result": frozenset({"change_id"}),
              "assignee": frozenset({"query"}),
              "stage-customer-create": CREATE_FIELDS,
              "stage-customer-update": UPDATE_FIELDS}
    command = value.get("command")
    if not isinstance(command, str) or command not in fields:
        raise ValueError("Unsupported controlled tool.")
    request, principal = _host_prepare_payload(
        {"request": value["request"], "principal": value["principal"]}, config, fields[command]
    )
    if command == "customer":
        core._required_text(request.get("customer_query"), "customer_query", 256)
    elif command == "result":
        core._opaque_id(request.get("change_id"), "change_id", "chg_")
    return command, request, principal


def _customer_result(request, backend, principal, ledger):
    matches, matched_by = core._resolve_customer(request["customer_query"], backend)
    if len(matches) != 1:
        return {"status": "needs_selection" if matches else "not_found",
                "matched_by": matched_by,
                "candidates": [core._display_customer(row, backend) for row in matches]}
    row = backend.get_customer(matches[0]["record_id"])
    if row is None:
        return {"status": "unavailable", "code": "customer_disappeared"}
    result = {"status": "found", "customer": core._display_customer(row, backend),
              "read_at": datetime.now(timezone.utc).isoformat(),
              "latest_operation_status": "none", "latest_operation": None}
    try:
        change_id = ledger.latest_change_for_customer(principal, row["record_id"])
        if change_id is not None:
            operation = _change_result({"change_id": change_id}, principal, ledger)
            if operation["status"] == "blocked":
                raise ValueError("The selected operation could not be read.")
            result.update(latest_operation_status="available", latest_operation=operation)
    except Exception:
        # A missing outcome is not evidence that the old approval is still pending.
        result.update(latest_operation_status="unavailable", latest_operation=None)
    try:
        # Request one sentinel row to distinguish an empty history from a truncated one.
        history = list(backend.read_customer_history(row["record_id"], 11))
        if len(history) > 11 or any(
            item.get("customer_record_id") != row["record_id"] for item in history
        ):
            raise ValueError("Invalid bounded history response.")
        history.sort(key=lambda item: datetime.fromisoformat(item["occurred_at"]), reverse=True)
    except Exception:
        # Never represent an unavailable history as an empty customer history.
        return {**result, "history": None, "history_status": "unavailable"}
    return {**result, "history_status": "available", "truncated": len(history) > 10,
            "history": [core._display_followup(item, backend) for item in history[:10]]}


def _change_result(request, principal, ledger, *, include_related=True):
    approval = ledger.get_approval_for_change(request["change_id"])
    if approval is None or not core._same_principal(approval["principal"], principal):
        return {"status": "blocked", "code": "result_not_accessible"}
    staged = ledger.get(request["change_id"])
    if staged is None:
        return {"status": "blocked", "code": "result_not_accessible"}
    now = datetime.now(timezone.utc)
    state = approval["state"]
    if state == "pending" and now > datetime.fromisoformat(approval["expires_at"]):
        state = "expired"
    result = {"status": state, "change_id": request["change_id"],
              "queried_at": now.isoformat(), "receipt": approval["receipt"],
              "card_bound": bool(approval["card_message_id"]),
              # Cancelling repair approval does not undo a previously verified follow-up.
              "durable_change_state": staged["state"],
              "durable_change_receipt": staged["receipt"]}
    if state == "executing" and approval["receipt"] is None:
        uncertain = now >= core._parse_time(approval["decided_at"], "decided_at") + timedelta(
            seconds=core.APPROVAL_EXECUTION_UNCERTAIN_SECONDS
        )
        result.update(
            code="execution_result_unknown" if uncertain else "apply_in_progress",
            message=(
                "The original worker has not produced a receipt; reconcile the CRM before any retry."
                if uncertain else "The approved write is still executing; no receipt is available yet."
            ),
        )
    if include_related:
        parent_id = staged.get("parent_change_id")
        child_id = ledger.child_change_id(parent_id or staged["change_id"])
        expects_child = staged.get("operation_type") in {"customer_create", "customer_update"} and bool(staged.get("followup"))
        if parent_id or child_id or expects_child:
            parent_id = parent_id or staged["change_id"]
            result["related_operations"] = {
                "parent": _change_result({"change_id": parent_id}, principal, ledger,
                                         include_related=False),
                "child": (_change_result({"change_id": child_id}, principal, ledger,
                                         include_related=False) if child_id else None),
            }
            if child_id is None:
                result["followup_status"] = "not_prepared"
                result["followup_message"] = (
                    "客户操作已成功；尚无跟进子方案，请人工重新发起跟进，不要重复客户操作。"
                    if staged["state"] == "verified" else
                    "跟进尚未暂存；须先完成并核验客户操作，之后仍需单独批准跟进。"
                )
    return result


def _write(target: TextIO, result: Mapping[str, Any]) -> None:
    target.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    """Run one public or host request without configuration overrides."""

    args = list(sys.argv[1:] if argv is None else argv)
    source = sys.stdin if stdin is None else stdin
    target = sys.stdout if stdout is None else stdout

    if args == ["request-approval"]:
        _write(
            target,
            {
                "status": "handoff_only",
                "message": "The authenticated gateway host must handle this approval.",
            },
        )
        return 0

    command = args[0] if len(args) == 1 else ""
    if command == "apply":
        _write(
            target,
            {
                "status": "blocked",
                "code": "host_approval_required",
                "message": "Only the authenticated gateway host can apply CRM changes.",
            },
        )
        return 0
    if command == "stage":
        _write(
            target,
            {
                "status": "blocked",
                "code": "host_prepare_required",
                "message": "Only the authenticated gateway host can read and stage CRM data.",
            },
        )
        return 0
    if command not in {
        "host-tool",
        "host-prepare",
        "host-begin",
        "host-bind-card",
        "host-claim",
        "host-execute",
        "host-decide",
    }:
        result = {
            "status": "failed",
            "code": "usage",
            "message": (
                "Usage: crm-followup host-tool|host-prepare|host-begin|host-bind-card|host-claim|"
                "host-execute|host-decide, or "
                "the exact request-approval marker."
            ),
        }
        _write(target, result)
        return 2

    try:
        request = _read_command(source)
        path = _config_path()
        config = _load_config(path)
        action_token = None
        if command in {"host-tool", "host-prepare", "host-begin"}:
            action_token = _environment_secret(ACTION_TOKEN_ENV)
        if command.startswith("host-"):
            _required_mapping(config, "allowed_actors")
            _require_host(config)
        prepare_request = None
        prepare_principal = None
        tool_command = None
        if command == "host-prepare":
            prepare_request, prepare_principal = _host_prepare_payload(request, config)
        elif command == "host-tool":
            tool_command, prepare_request, prepare_principal = _host_tool_payload(request, config)
        backend, ledger = _runtime(config, path)
    except (CliConfigurationError, OSError, TypeError, ValueError):
        result = _safe_failure(
            command,
            "invalid_local_input",
            "The request or protected CRM configuration is invalid; Feishu is unchanged.",
        )
        _write(target, result)
        return 2

    try:
        if tool_command == "customer":
            result = _customer_result(prepare_request, backend, prepare_principal, ledger)
        elif tool_command == "result":
            result = _change_result(prepare_request, prepare_principal, ledger)
        elif tool_command == "assignee":
            from .customers import resolve_assignee
            result = resolve_assignee(prepare_request, backend, ledger, config, prepare_principal)
        elif command == "host-prepare" or tool_command in {
            "stage", "stage-customer-create", "stage-customer-update",
        }:
            if tool_command in {"stage-customer-create", "stage-customer-update"}:
                from .customers import stage_customer
                operation = "customer_create" if tool_command.endswith("create") else "customer_update"
                staged = stage_customer(prepare_request, operation, backend, ledger, config,
                                        action_token, prepare_principal)
            else:
                staged = stage_followup(
                    prepare_request, backend, ledger, config, action_token,
                    trusted_principal=prepare_principal,
                )
            if staged.get("status") == "staged":
                result = begin_approval(
                    {
                        "change_id": staged.get("change_id"),
                        "principal": prepare_principal,
                    },
                    backend,
                    ledger,
                    config,
                    action_token,
                )
            elif staged.get("status") in NON_PENDING_STAGE_STATUSES:
                result = staged
            else:
                result = {
                    "status": "failed",
                    "code": "invalid_stage_result",
                    "message": (
                        "CRM staging returned an unsupported result; Feishu is unchanged."
                    ),
                }
        elif command == "host-begin":
            result = begin_approval(
                request,
                backend,
                ledger,
                config,
                action_token,
            )
        elif command == "host-bind-card":
            result = bind_approval_card(request, ledger, config)
        elif command == "host-claim":
            result = claim_approval_decision(request, ledger, config)
        elif command == "host-execute":
            result = execute_claimed_approval(request, backend, ledger, config)
        else:
            result = decide_approval(request, backend, ledger, config)
    except Exception:
        result = _safe_failure(
            command,
            "unexpected_failure",
            "The CRM operation could not be completed safely; inspect protected service logs.",
        )
        exit_code = 1
    else:
        exit_code = 0
    finally:
        ledger.close()

    _write(target, result)
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
