#!/usr/bin/env python3
"""Create the disposable two-table Feishu Base used by the CRM sandbox."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import subprocess
import sys
import re
import tempfile
from typing import Any, Iterable


BASE_NAME = "ANC CRM Sandbox"
REAL_BASE_NAME = "ANC CRM"
CUSTOMER_TABLE = "客户"
FOLLOWUP_TABLE = "跟进记录"
TIMEZONE = "Asia/Shanghai"
CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.local.json"
LEDGER_PATH = (Path.home() / ".myanc-crm" / "ledger.sqlite3").resolve()

CUSTOMER_FIELDS = [
    {"name": "客户名称", "type": "text"},
    {
        "name": "客户编号",
        "type": "auto_number",
        "style": {
            "rules": [
                {"type": "text", "text": "ANC-"},
                {"type": "incremental_number", "length": 4},
            ]
        },
    },
    {"name": "联系人", "type": "text"},
    {"name": "电话", "type": "text"},
    {"name": "邮箱", "type": "text", "style": {"type": "email"}},
    {
        "name": "阶段",
        "type": "select",
        "multiple": False,
        "options": [
            {"name": "新线索"},
            {"name": "已联系"},
            {"name": "沟通中"},
            {"name": "已成交"},
            {"name": "暂缓"},
        ],
    },
    {"name": "负责人", "type": "user", "multiple": False},
    {
        "name": "最近联系时间",
        "type": "datetime",
        "style": {"format": "yyyy-MM-dd HH:mm"},
    },
    {"name": "最近联系摘要", "type": "text"},
    {"name": "下一步行动", "type": "text"},
    {
        "name": "下次跟进时间",
        "type": "datetime",
        "style": {"format": "yyyy-MM-dd HH:mm"},
    },
    {
        "name": "更新时间",
        "type": "updated_at",
        "style": {"format": "yyyy-MM-dd HH:mm"},
    },
]

CUSTOMER_CANONICAL = {
    "name": "客户名称",
    "customer_number": "客户编号",
    "contact": "联系人",
    "phone": "电话",
    "email": "邮箱",
    "stage": "阶段",
    "owner": "负责人",
    "last_followup_at": "最近联系时间",
    "last_followup_content": "最近联系摘要",
    "next_action": "下一步行动",
    "next_followup_at": "下次跟进时间",
    "updated_at": "更新时间",
}

FOLLOWUP_CANONICAL = {
    "title": "跟进标题",
    "change_id": "操作 ID",
    "customer_record_id": "关联客户",
    "occurred_at": "沟通时间",
    "channel": "沟通方式",
    "content": "沟通内容",
    "next_action": "下一步行动",
    "next_followup_at": "下次跟进时间",
    "created_by": "跟进人",
    "created_at": "创建时间",
}

FIELD_TYPE_ALIASES = {
    1: "text",
    3: "select",
    4: "select",
    5: "datetime",
    11: "user",
    18: "link",
    21: "link",
    1001: "created_at",
    1002: "updated_at",
    1005: "auto_number",
    "single_select": "select",
    "multi_select": "select",
    "date": "datetime",
    "date_time": "datetime",
    "person": "user",
    "duplex_link": "link",
    "created_time": "created_at",
    "modified_time": "updated_at",
    "autonumber": "auto_number",
}

SEED_CUSTOMERS = [
    {
        "客户名称": "演示客户·青岚科技（唯一）",
        "联系人": "虚构联系人·青一",
        "电话": "TEST-PHONE-001",
        "邮箱": "qinglan@example.com",
        "阶段": ["新线索"],
    },
    {
        "客户名称": "演示客户·星河商贸",
        "联系人": "虚构联系人·星甲",
        "电话": "TEST-PHONE-002",
        "邮箱": "xinghe-a@example.com",
        "阶段": ["新线索"],
    },
    {
        "客户名称": "演示客户·星河商贸",
        "联系人": "虚构联系人·星乙",
        "电话": "TEST-PHONE-003",
        "邮箱": "xinghe-b@example.com",
        "阶段": ["新线索"],
    },
]


class BootstrapError(RuntimeError):
    """Safe-to-print bootstrap failure without command output or identifiers."""


def _walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _find_string(value: Any, keys: tuple[str, ...]) -> str | None:
    for item in _walk(value):
        for key in keys:
            found = item.get(key)
            if isinstance(found, str) and found:
                return found
    return None


def _named_id(value: Any, name: str, id_keys: tuple[str, ...]) -> str | None:
    for item in _walk(value):
        if item.get("name") != name and item.get("title") != name:
            continue
        for key in id_keys:
            found = item.get(key)
            if isinstance(found, str) and found:
                return found

    # Some CLI versions return a matrix instead of record-shaped objects.
    for item in _walk(value):
        fields, rows = item.get("fields"), item.get("rows")
        if not isinstance(fields, list) or not isinstance(rows, list):
            continue
        name_index = next(
            (index for index, field in enumerate(fields) if field in ("name", "title")),
            None,
        )
        id_index = next(
            (index for index, field in enumerate(fields) if field in id_keys), None
        )
        if name_index is None or id_index is None:
            continue
        for row in rows:
            if (
                isinstance(row, list)
                and len(row) > max(name_index, id_index)
                and row[name_index] == name
                and isinstance(row[id_index], str)
            ):
                return row[id_index]
    return None


def _has_named_item(value: Any, name: str) -> bool:
    return _named_id(
        value,
        name,
        ("base_token", "app_token", "token", "table_id", "id", "url"),
    ) is not None


def _record_ids(value: Any) -> list[str]:
    found: list[str] = []
    for item in _walk(value):
        many = item.get("record_id_list")
        if isinstance(many, list):
            found.extend(entry for entry in many if isinstance(entry, str) and entry)
        one = item.get("record_id")
        if isinstance(one, str) and one:
            found.append(one)
    return list(dict.fromkeys(found))


def _run(
    cli: Path,
    profile: str,
    command: list[str],
    label: str,
    *,
    json_output: bool = True,
    format_flag: bool = True,
    identity: str | None = "bot",
    cwd: Path | None = None,
) -> Any:
    argv = [str(cli), "--profile", profile, *command]
    if json_output and format_flag:
        argv += ["--format", "json"]
    if identity is not None:
        argv += ["--as", identity]
    try:
        result = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=120,
            cwd=cwd,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BootstrapError(f"{label} failed before a verified response") from exc
    if result.returncode != 0:
        raise BootstrapError(f"{label} failed (exit {result.returncode})")
    if not json_output:
        return result.stdout
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise BootstrapError(f"{label} returned an unreadable response") from exc
    if isinstance(parsed, dict) and parsed.get("ok") is False:
        raise BootstrapError(f"{label} returned a failed response")
    return parsed


def _identity_context(
    cli: Path, profile: str
) -> tuple[dict[str, str], dict[str, Any]]:
    status = _run(
        cli,
        profile,
        ["auth", "status", "--json", "--verify"],
        "enterprise user authentication check",
        format_flag=False,
        identity=None,
    )
    user_auth: dict[str, Any] | None = None
    for item in _walk(status):
        identities = item.get("identities")
        if isinstance(identities, dict) and isinstance(identities.get("user"), dict):
            user_auth = identities["user"]
            break
    if user_auth is None:
        raise BootstrapError("enterprise user authentication details are unavailable")
    if not isinstance(status, dict) or status.get("verified") is not True:
        raise BootstrapError("enterprise user authentication could not be verified")

    user = _run(
        cli,
        profile,
        ["whoami"],
        "enterprise user identity check",
        format_flag=False,
        identity="user",
    )
    bot = _run(
        cli,
        profile,
        ["whoami"],
        "enterprise bot identity check",
        format_flag=False,
        identity="bot",
    )
    if not isinstance(user, dict) or not isinstance(bot, dict):
        raise BootstrapError("enterprise identity check returned an unreadable response")
    # `--profile` accepts either an immutable app ID or a local profile name, while
    # `whoami` reports the local name.  The argv already pins the requested selector;
    # verify that both identities resolved to the same non-empty profile instead of
    # comparing unlike representations.
    resolved_profile = user.get("profile")
    if (
        not isinstance(resolved_profile, str)
        or not resolved_profile
        or bot.get("profile") != resolved_profile
    ):
        raise BootstrapError("enterprise identities resolved to different profiles")
    if user.get("identity") != "user" or bot.get("identity") != "bot":
        raise BootstrapError("enterprise identity selection failed")
    if user.get("available") is not True or bot.get("available") is not True:
        raise BootstrapError("both enterprise user and bot identities must be available")
    app_id = user.get("appId")
    if not isinstance(app_id, str) or not app_id or app_id != bot.get("appId"):
        raise BootstrapError("enterprise user and bot identities do not share one application")

    user_name = user_auth.get("userName")
    open_id = user_auth.get("openId")
    if not isinstance(user_name, str) or not user_name:
        raise BootstrapError("enterprise user authentication omitted its display name")
    if not isinstance(open_id, str) or not open_id:
        raise BootstrapError("enterprise user authentication omitted its open ID")
    owner = {"display_name": user_name, "feishu_user_id": open_id}
    summary = {
        "application_id": app_id,
        "brand": bot.get("brand"),
        "bot": {"identity": "bot", "available": True},
        "user": {
            "identity": "user",
            "available": True,
            "display_name": user_name,
            "open_id": open_id,
        },
    }
    return owner, summary


def _field_map(value: Any) -> dict[str, dict[str, Any]]:
    fields: dict[str, dict[str, Any]] = {}
    for item in _walk(value):
        name = item.get("name")
        field_id = item.get("field_id") or item.get("id")
        if isinstance(name, str) and isinstance(field_id, str):
            fields[name] = item
    return fields


def _verify_fields(value: Any, expected: list[dict[str, Any]], label: str) -> None:
    actual = _field_map(value)
    missing = [field["name"] for field in expected if field["name"] not in actual]
    if missing:
        raise BootstrapError(f"{label} schema verification failed")
    for field in expected:
        actual_type = actual[field["name"]].get("type")
        if isinstance(actual_type, dict):
            actual_type = actual_type.get("name") or actual_type.get("type")
        if isinstance(actual_type, str):
            actual_type = actual_type.strip().lower().replace("-", "_")
            if actual_type.isdigit():
                actual_type = int(actual_type)
        actual_type = FIELD_TYPE_ALIASES.get(actual_type, actual_type)
        if actual_type != field["type"]:
            raise BootstrapError(f"{label} schema verification failed")


def _canonical_field_ids(
    value: Any, canonical: dict[str, str], label: str
) -> dict[str, str]:
    actual = _field_map(value)
    result: dict[str, str] = {}
    for key, name in canonical.items():
        field = actual.get(name, {})
        field_id = field.get("field_id") or field.get("id")
        if not isinstance(field_id, str) or not field_id:
            raise BootstrapError(f"{label} schema omitted a field identifier")
        result[key] = field_id
    return result


def _write_config(config: dict[str, Any], path: Path | None = None, *, exclusive: bool = False) -> None:
    path = CONFIG_PATH if path is None else path
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _read_checkpoint() -> dict[str, Any]:
    try:
        value = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BootstrapError("config.local.json is unreadable; no changes were made") from exc
    if not isinstance(value, dict):
        raise BootstrapError("config.local.json is invalid; no changes were made")
    return value


def _checkpoint_text(config: dict[str, Any], name: str) -> str:
    value = config.get(name)
    if not isinstance(value, str) or not value:
        raise BootstrapError(f"checkpoint omitted {name}; no changes were made")
    return value


def _checkpoint(
    wrapper_path: str,
    owner_sender_id: str,
    owner: dict[str, str],
    identity_summary: dict[str, Any],
    *,
    status: str,
    base_token: str = "",
    customer_table_id: str = "",
    followup_table_id: str = "",
    base_url: str = "",
    customer_field_ids: dict[str, str] | None = None,
    followup_field_ids: dict[str, str] | None = None,
) -> None:
    config: dict[str, Any] = {
        "wrapper_path": wrapper_path,
        "base_token": base_token,
        "customer_table_id": customer_table_id,
        "followup_table_id": followup_table_id,
        "base_url": base_url,
        "fields": {
            "customers": customer_field_ids or {},
            "followups": followup_field_ids or {},
        },
        "allowed_actors": {owner_sender_id: owner},
        "ttl_seconds": 600,
        "ledger_path": str(LEDGER_PATH),
        "host_secret_sha256": _host_secret_hash(),
        "identity_summary": identity_summary,
    }
    if status != "verified":
        config["_bootstrap_status"] = status
    _write_config(config)


def _host_secret_hash() -> str:
    secret = os.environ.get("MYANC_CRM_HOST_SECRET", "")
    if len(secret) < 32 or len(secret) > 4096:
        raise BootstrapError("MYANC_CRM_HOST_SECRET must contain 32-4096 characters")
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _followup_fields(customer_table_id: str) -> list[dict[str, Any]]:
    return [
        {"name": "跟进标题", "type": "text"},
        {"name": "操作 ID", "type": "text"},
        {
            "name": "关联客户",
            "type": "link",
            "link_table": customer_table_id,
            "bidirectional": False,
        },
        {
            "name": "沟通时间",
            "type": "datetime",
            "style": {"format": "yyyy-MM-dd HH:mm"},
        },
        {
            "name": "沟通方式",
            "type": "select",
            "multiple": False,
            "options": [
                {"name": "电话"},
                {"name": "微信"},
                {"name": "飞书"},
                {"name": "邮件"},
                {"name": "面谈"},
                {"name": "其他"},
            ],
        },
        {"name": "沟通内容", "type": "text"},
        {"name": "下一步行动", "type": "text"},
        {
            "name": "下次跟进时间",
            "type": "datetime",
            "style": {"format": "yyyy-MM-dd HH:mm"},
        },
        {"name": "跟进人", "type": "user", "multiple": False},
        {
            "name": "创建时间",
            "type": "created_at",
            "style": {"format": "yyyy-MM-dd HH:mm"},
        },
    ]


def _batch_payload(cli: Path, profile: str) -> dict[str, Any]:
    help_text = _run(
        cli,
        profile,
        ["base", "+record-batch-create", "--help"],
        "record-create capability check",
        json_output=False,
    )
    if "create_records" in help_text:
        return {"create_records": SEED_CUSTOMERS}
    if '"fields"' in help_text and '"rows"' in help_text:
        fields = list(SEED_CUSTOMERS[0])
        rows = []
        for record in SEED_CUSTOMERS:
            row = [record.get(field) for field in fields]
            row[fields.index("阶段")] = record["阶段"][0]
            rows.append(row)
        return {"fields": fields, "rows": rows}
    raise BootstrapError("the selected lark-cli has an unsupported record-create shape")


def _verify_seed_records(
    cli: Path,
    profile: str,
    base_token: str,
    customer_table_id: str,
    customer_field_ids: dict[str, str],
) -> None:
    records = _run(
        cli,
        profile,
        [
            "base",
            "+record-list",
            "--base-token",
            base_token,
            "--table-id",
            customer_table_id,
            "--field-id",
            customer_field_ids["name"],
            "--field-id",
            customer_field_ids["contact"],
            "--limit",
            "20",
        ],
        "fictional customer verification",
    )
    serialized = json.dumps(records, ensure_ascii=False)
    expected_values = [
        "演示客户·青岚科技（唯一）",
        "演示客户·星河商贸",
        "虚构联系人·星甲",
        "虚构联系人·星乙",
    ]
    if any(value not in serialized for value in expected_values):
        raise BootstrapError("fictional customer verification failed")


def _resume_verified_checkpoint(
    cli: Path,
    profile: str,
    wrapper_path: str,
    owner_sender_id: str,
) -> bool:
    """Finish only the readback after a successful batch create was retained."""

    if not CONFIG_PATH.exists():
        return False
    config = _read_checkpoint()
    if config.get("_bootstrap_status") != "tables_verified":
        raise BootstrapError("config.local.json already exists; no changes were made")
    if config.get("wrapper_path") != wrapper_path:
        raise BootstrapError("checkpoint wrapper does not match; no changes were made")
    actors = config.get("allowed_actors")
    if not isinstance(actors, dict) or set(actors) != {owner_sender_id}:
        raise BootstrapError("checkpoint owner does not match; no changes were made")

    print("Resuming retained sandbox verification without creating new resources...")
    owner, identity_summary = _identity_context(cli, profile)
    if actors[owner_sender_id] != owner:
        raise BootstrapError("checkpoint enterprise user does not match; no changes were made")

    base_token = _checkpoint_text(config, "base_token")
    customer_table_id = _checkpoint_text(config, "customer_table_id")
    followup_table_id = _checkpoint_text(config, "followup_table_id")
    base_url = _checkpoint_text(config, "base_url")
    fields = config.get("fields")
    if not isinstance(fields, dict):
        raise BootstrapError("checkpoint omitted immutable field IDs; no changes were made")
    customer_field_ids = fields.get("customers")
    followup_field_ids = fields.get("followups")
    if not isinstance(customer_field_ids, dict) or not isinstance(followup_field_ids, dict):
        raise BootstrapError("checkpoint omitted immutable field IDs; no changes were made")

    customer_schema = _run(
        cli,
        profile,
        [
            "base",
            "+field-list",
            "--base-token",
            base_token,
            "--table-id",
            customer_table_id,
            "--limit",
            "100",
        ],
        "customer schema re-verification",
    )
    followup_fields = _followup_fields(customer_table_id)
    followup_schema = _run(
        cli,
        profile,
        [
            "base",
            "+field-list",
            "--base-token",
            base_token,
            "--table-id",
            followup_table_id,
            "--limit",
            "100",
        ],
        "follow-up schema re-verification",
    )
    _verify_fields(customer_schema, CUSTOMER_FIELDS, "customer")
    _verify_fields(followup_schema, followup_fields, "follow-up")
    if _canonical_field_ids(customer_schema, CUSTOMER_CANONICAL, "customer") != customer_field_ids:
        raise BootstrapError("customer field identifiers changed; no changes were made")
    if _canonical_field_ids(followup_schema, FOLLOWUP_CANONICAL, "follow-up") != followup_field_ids:
        raise BootstrapError("follow-up field identifiers changed; no changes were made")
    _verify_seed_records(
        cli, profile, base_token, customer_table_id, customer_field_ids
    )
    _checkpoint(
        wrapper_path,
        owner_sender_id,
        owner,
        identity_summary,
        status="verified",
        base_token=base_token,
        customer_table_id=customer_table_id,
        followup_table_id=followup_table_id,
        base_url=base_url,
        customer_field_ids=customer_field_ids,
        followup_field_ids=followup_field_ids,
    )
    print("Retained sandbox schema and three fictional customer records were verified.")
    return True


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lark-cli", required=True, help="absolute administrator CLI path")
    parser.add_argument("--profile", required=True, help="fixed enterprise bot profile")
    parser.add_argument("--mode", choices=("sandbox", "empty-real"), default="sandbox")
    parser.add_argument("--source-config", help="existing protected, verified CRM config; read-only")
    parser.add_argument("--config-output", help="new absolute config path (empty-real only)")
    parser.add_argument("--ledger-path", help="new absolute ledger path (empty-real only; never copied)")
    parser.add_argument("--expected-app-id", help="expected CRM app when absent from source config")
    parser.add_argument("--confirm-empty-real", action="store_true", help="explicitly confirm creating an empty real Base")
    parser.add_argument(
        "--wrapper-path",
        required=False,
        help="absolute runtime lark-enterprise wrapper path written to config.local.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show the safe plan without calling Feishu or writing config.local.json",
    )
    return parser.parse_args()


def _is_absolute_any(value: str) -> bool:
    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()


def _real_customer_fields() -> list[dict[str, Any]]:
    fields = copy.deepcopy(CUSTOMER_FIELDS)
    number = next(field for field in fields if field["name"] == "客户编号")
    number["style"]["rules"][0]["text"] = "CRM-"
    fields.append({"name": "建档操作ID", "type": "text"})
    return fields


def _real_context(args: argparse.Namespace) -> tuple[dict[str, Any], Path, str]:
    """Read only a supplied deployment context; no default credential discovery."""
    paths: dict[str, Path] = {}
    for name in ("source_config", "config_output", "ledger_path"):
        value = getattr(args, name)
        if not value or not Path(value).is_absolute():
            raise BootstrapError(f"--{name.replace('_', '-')} must be an explicit absolute path")
        paths[name] = Path(value).resolve()
    source_path, output, ledger = (paths[key] for key in ("source_config", "config_output", "ledger_path"))
    if len({source_path, output, ledger}) != 3 or output == CONFIG_PATH.resolve():
        raise BootstrapError("real targets must be independent of the source and old default config")
    if output.exists() or ledger.exists() or Path(str(ledger) + "-wal").exists() or Path(str(ledger) + "-shm").exists():
        raise BootstrapError("real config and ledger targets must not already exist")
    if not output.parent.is_dir() or not ledger.parent.is_dir():
        raise BootstrapError("provision the separate config and ledger parent directories first")
    try:
        source = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise BootstrapError("source config is unreadable") from None
    if not isinstance(source, dict) or source.get("_bootstrap_status") is not None:
        raise BootstrapError("source config is not a verified CRM configuration")
    source_ledger = source.get("ledger_path")
    if not isinstance(source_ledger, str) or not _is_absolute_any(source_ledger):
        raise BootstrapError("source config omitted its protected ledger path")
    if ledger == Path(source_ledger).resolve():
        raise BootstrapError("the old ledger cannot be reused")
    wrapper = source.get("wrapper_path")
    if not isinstance(wrapper, str) or not _is_absolute_any(wrapper):
        raise BootstrapError("source config omitted the fixed writer wrapper")
    if args.wrapper_path is not None and args.wrapper_path != wrapper:
        raise BootstrapError("the real bootstrap cannot change the writer identity wrapper")
    actors = source.get("allowed_actors")
    if not isinstance(actors, dict) or len(actors) != 1:
        raise BootstrapError("empty-real requires the existing single Owner mapping")
    actor = next(iter(actors.values()))
    if not isinstance(actor, dict) or not isinstance(actor.get("display_name"), str) or not re.fullmatch(
        r"ou_[A-Za-z0-9]+", str(actor.get("feishu_user_id", ""))
    ):
        raise BootstrapError("source Owner mapping is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", str(source.get("host_secret_sha256", ""))):
        raise BootstrapError("source config omitted its host authentication digest")
    summary = source.get("identity_summary", {})
    configured_app = source.get("expected_app_id") or (
        summary.get("application_id") if isinstance(summary, dict) else None)
    if configured_app and args.expected_app_id and configured_app != args.expected_app_id:
        raise BootstrapError("explicit app identity conflicts with the verified source")
    expected_app = configured_app or args.expected_app_id
    if not isinstance(expected_app, str) or not expected_app:
        raise BootstrapError("an expected CRM app ID is required; a profile name is insufficient")
    if source.get("profile") is not None and source["profile"] != args.profile:
        raise BootstrapError("profile conflicts with the verified source")
    config = copy.deepcopy(source)
    config.update(base_token="", base_url="", customer_table_id="", followup_table_id="",
                  fields={"customers": {}, "followups": {}}, ledger_path=str(ledger),
                  _bootstrap_status="prepared")
    return config, output, expected_app


def _verify_real_identity(cli: Path, profile: str, config: dict[str, Any], expected_app: str) -> None:
    version = _run(cli, profile, ["--version"], "fixed CLI version check",
                   json_output=False, format_flag=False, identity=None)
    if version.strip() != "lark-cli version 1.0.90":
        raise BootstrapError("real bootstrap requires the reviewed CLI 1.0.90")
    bot = _run(cli, profile, ["whoami"], "CRM bot identity check", format_flag=False)
    if not isinstance(bot, dict) or bot.get("identity") != "bot" or bot.get("available") is not True or bot.get("appId") != expected_app:
        raise BootstrapError("the selected bot is not the verified CRM application")
    owner = next(iter(config["allowed_actors"].values()))
    result = _run(cli, profile, ["contact", "+get-user", "--user-id", owner["feishu_user_id"],
                                "--user-id-type", "open_id"], "same-app Owner verification")
    if not isinstance(result, dict) or result.get("ok") is not True or result.get("identity") != "bot":
        raise BootstrapError("Owner verification did not prove bot identity")
    data = result.get("data", {})
    person = data.get("user", data) if isinstance(data, dict) else {}
    status = person.get("status", {}) if isinstance(person, dict) else {}
    if (not isinstance(person, dict) or person.get("open_id") != owner["feishu_user_id"]
            or not person.get("name") or not isinstance(status, dict)
            or status.get("is_activated") is not True or status.get("is_frozen") is not False
            or status.get("is_resigned") is not False):
        raise BootstrapError("Owner identity/status is not verifiable with the current CRM app permissions")


def _verify_empty_table(cli: Path, profile: str, token: str, table: str, field_id: str) -> None:
    # CLI 1.0.90 +record-list help and the official Base Record SOP define this
    # manifest contract. No view/filter: this probes the whole table, not a subset.
    with tempfile.TemporaryDirectory(prefix="crm-empty-check-") as directory:
        artifact = Path(directory) / "empty.ndjson"
        result = _run(cli, profile, ["base", "+record-list", "--base-token", token,
            "--table-id", table, "--field-id", field_id, "--limit", "1", "--format", "ndjson",
            "--output", "./empty.ndjson"], "verify real table is empty", format_flag=False,
            cwd=Path(directory))
        manifests = [item for item in _walk(result) if "records_count" in item]
        if (len(manifests) != 1 or type(manifests[0]["records_count"]) is not int
                or manifests[0]["records_count"] != 0 or manifests[0].get("has_more") is not False
                or not artifact.is_file() or artifact.stat().st_size != 0):
            raise BootstrapError("empty table state is unverified; retain checkpoint for manual review")


def _create_empty_real(args: argparse.Namespace, cli: Path) -> int:
    config, output, expected_app = _real_context(args)
    if args.dry_run:
        print("DRY RUN: reuse the verified source bot and single Owner; never log in as user")
        print("DRY RUN: verify fixed CLI/app and same-app Owner ID/status before any create")
        print("DRY RUN: create 'ANC CRM': empty customers + follow-ups; native CRM- numbering + 建档操作ID")
        print("DRY RUN: use a new config and new ledger; retain old Base/config/ledger unchanged")
        print("DRY RUN: no customer seeds, Feishu calls, files, or ledger copies")
        return 0
    if not args.confirm_empty_real:
        raise BootstrapError("empty-real creation requires --confirm-empty-real after reviewing its dry run")
    if not cli.is_file():
        raise BootstrapError("--lark-cli does not name an existing file")
    _verify_real_identity(cli, args.profile, config, expected_app)
    # Reserve only the new checkpoint. On uncertainty keep it and every resource;
    # an operator reconciles manually rather than retrying Base creation.
    try:
        _write_config(config, output, exclusive=True)
        fields = _real_customer_fields()
        created = _run(cli, args.profile, ["base", "+base-create", "--name", REAL_BASE_NAME,
            "--time-zone", TIMEZONE, "--table-name", CUSTOMER_TABLE, "--fields",
            json.dumps(fields, ensure_ascii=False)], "empty real Base creation")
        token = _find_string(created, ("base_token", "app_token"))
        if not token:
            raise BootstrapError("Base creation result is uncertain; retain checkpoint and reconcile manually")
        config.update(base_token=token, base_url=_find_string(created, ("base_url", "url")) or "",
                      _bootstrap_status="base_created")
        _write_config(config, output)
        base = _run(cli, args.profile, ["base", "+base-get", "--base-token", token], "real Base verification")
        if not _has_named_item(base, REAL_BASE_NAME):
            raise BootstrapError("real Base name verification failed")
        config["base_url"] = config["base_url"] or _find_string(base, ("base_url", "url")) or ""
        tables = _run(cli, args.profile, ["base", "+table-list", "--base-token", token], "real customer table lookup")
        customer_table = _named_id(tables, CUSTOMER_TABLE, ("table_id", "id"))
        if not customer_table or not config["base_url"]:
            raise BootstrapError("real customer table/URL verification failed")
        config["customer_table_id"] = customer_table
        canonical = {**CUSTOMER_CANONICAL, "operation_id": "建档操作ID"}
        schema = _run(cli, args.profile, ["base", "+field-list", "--base-token", token,
            "--table-id", customer_table, "--limit", "100"], "real customer schema verification")
        _verify_fields(schema, fields, "real customer")
        config["fields"]["customers"] = _canonical_field_ids(schema, canonical, "real customer")
        config["_bootstrap_status"] = "customer_verified"
        _write_config(config, output)
        followup_fields = _followup_fields(customer_table)
        created = _run(cli, args.profile, ["base", "+table-create", "--base-token", token,
            "--name", FOLLOWUP_TABLE, "--fields", json.dumps(followup_fields, ensure_ascii=False)],
            "real follow-up table creation")
        followup_table = _find_string(created, ("table_id",))
        if not followup_table:
            raise BootstrapError("follow-up table creation is uncertain; reconcile the retained Base")
        config.update(followup_table_id=followup_table, _bootstrap_status="followup_created")
        _write_config(config, output)
        schema = _run(cli, args.profile, ["base", "+field-list", "--base-token", token,
            "--table-id", followup_table, "--limit", "100"], "real follow-up schema verification")
        _verify_fields(schema, followup_fields, "real follow-up")
        config["fields"]["followups"] = _canonical_field_ids(schema, FOLLOWUP_CANONICAL, "real follow-up")
        config["_bootstrap_status"] = "tables_verified_empty_pending"
        _write_config(config, output)
        for table, field in ((customer_table, config["fields"]["customers"]["name"]),
                             (followup_table, config["fields"]["followups"]["title"])):
            _verify_empty_table(cli, args.profile, token, table, field)
        config.pop("_bootstrap_status")
        _write_config(config, output)
    except OSError:
        raise BootstrapError("real checkpoint could not be persisted; retain any created resources") from None
    print("Created and verified an empty ANC CRM. Old configuration and ledger are unchanged.")
    print("Only the new config contains identifiers; no ledger was created or copied.")
    return 0


def main() -> int:
    args = _parse_args()
    cli = Path(args.lark_cli)
    if not cli.is_absolute():
        raise BootstrapError("--lark-cli must be an absolute path")
    if args.mode == "empty-real":
        if not args.profile.strip():
            raise BootstrapError("--profile must not be empty")
        return _create_empty_real(args, cli)
    if any((args.source_config, args.config_output, args.ledger_path, args.expected_app_id, args.confirm_empty_real)):
        raise BootstrapError("real deployment options require --mode empty-real")
    if not args.wrapper_path or not _is_absolute_any(args.wrapper_path):
        raise BootstrapError("--wrapper-path must be absolute")
    if not args.profile.strip():
        raise BootstrapError("--profile must not be empty")

    if args.dry_run:
        print(f"DRY RUN: check for an existing {BASE_NAME!r} Base")
        print(f"DRY RUN: create {CUSTOMER_TABLE!r} and {FOLLOWUP_TABLE!r}")
        print("DRY RUN: seed three fictional customers, including one duplicate name")
        print("DRY RUN: no Feishu calls or files were written")
        return 0

    if not cli.is_file():
        raise BootstrapError("--lark-cli does not name an existing file")
    owner_sender_id = os.environ.get("MYANC_CRM_OWNER_SENDER_ID", "").strip()
    if not owner_sender_id:
        raise BootstrapError("MYANC_CRM_OWNER_SENDER_ID must be set")
    if _resume_verified_checkpoint(
        cli, args.profile, args.wrapper_path, owner_sender_id
    ):
        return 0

    print("Verifying the pinned enterprise user and bot identities...")
    owner, identity_summary = _identity_context(cli, args.profile)

    print("Checking that the sandbox Base name is unused...")
    search = _run(
        cli,
        args.profile,
        [
            "drive",
            "+search",
            "--query",
            BASE_NAME,
            "--doc-types",
            "bitable",
            "--only-title",
            "--page-size",
            "20",
        ],
        "duplicate Base check",
        identity="user",
    )
    if _has_named_item(search, BASE_NAME):
        raise BootstrapError(f"a Base named {BASE_NAME!r} already exists; no changes were made")

    print("Creating and verifying the customer table...")
    created = _run(
        cli,
        args.profile,
        [
            "base",
            "+base-create",
            "--name",
            BASE_NAME,
            "--time-zone",
            TIMEZONE,
            "--table-name",
            CUSTOMER_TABLE,
            "--fields",
            json.dumps(CUSTOMER_FIELDS, ensure_ascii=False, separators=(",", ":")),
        ],
        "Base creation",
    )
    base_token = _find_string(created, ("base_token", "app_token"))
    base_url = _find_string(created, ("base_url", "url")) or ""
    if not base_token:
        raise BootstrapError("Base creation response omitted its identifier")
    _checkpoint(
        args.wrapper_path,
        owner_sender_id,
        owner,
        identity_summary,
        status="base_created",
        base_token=base_token,
        base_url=base_url,
    )

    base_state = _run(
        cli,
        args.profile,
        ["base", "+base-get", "--base-token", base_token],
        "Base verification",
    )
    if not _has_named_item(base_state, BASE_NAME):
        raise BootstrapError("Base name verification failed")
    base_url = base_url or _find_string(base_state, ("base_url", "url")) or ""
    if not base_url:
        raise BootstrapError("Base verification response omitted its URL")

    tables = _run(
        cli,
        args.profile,
        ["base", "+table-list", "--base-token", base_token],
        "customer table lookup",
    )
    customer_table_id = _named_id(tables, CUSTOMER_TABLE, ("table_id", "id"))
    if not customer_table_id:
        raise BootstrapError("customer table verification failed")
    customer_schema = _run(
        cli,
        args.profile,
        [
            "base",
            "+field-list",
            "--base-token",
            base_token,
            "--table-id",
            customer_table_id,
            "--limit",
            "100",
        ],
        "customer schema verification",
    )
    _verify_fields(customer_schema, CUSTOMER_FIELDS, "customer")
    customer_field_ids = _canonical_field_ids(
        customer_schema, CUSTOMER_CANONICAL, "customer"
    )
    _checkpoint(
        args.wrapper_path,
        owner_sender_id,
        owner,
        identity_summary,
        status="customer_verified",
        base_token=base_token,
        customer_table_id=customer_table_id,
        base_url=base_url,
        customer_field_ids=customer_field_ids,
    )

    print("Creating and verifying the follow-up table...")
    followup_fields = _followup_fields(customer_table_id)
    followup_created = _run(
        cli,
        args.profile,
        [
            "base",
            "+table-create",
            "--base-token",
            base_token,
            "--name",
            FOLLOWUP_TABLE,
            "--fields",
            json.dumps(followup_fields, ensure_ascii=False, separators=(",", ":")),
        ],
        "follow-up table creation",
    )
    followup_table_id = _find_string(followup_created, ("table_id",))
    if not followup_table_id:
        tables = _run(
            cli,
            args.profile,
            ["base", "+table-list", "--base-token", base_token],
            "follow-up table lookup",
        )
        followup_table_id = _named_id(tables, FOLLOWUP_TABLE, ("table_id", "id"))
    if not followup_table_id:
        raise BootstrapError("follow-up table verification failed")
    followup_schema = _run(
        cli,
        args.profile,
        [
            "base",
            "+field-list",
            "--base-token",
            base_token,
            "--table-id",
            followup_table_id,
            "--limit",
            "100",
        ],
        "follow-up schema verification",
    )
    _verify_fields(followup_schema, followup_fields, "follow-up")
    followup_field_ids = _canonical_field_ids(
        followup_schema, FOLLOWUP_CANONICAL, "follow-up"
    )
    _checkpoint(
        args.wrapper_path,
        owner_sender_id,
        owner,
        identity_summary,
        status="tables_verified",
        base_token=base_token,
        customer_table_id=customer_table_id,
        followup_table_id=followup_table_id,
        base_url=base_url,
        customer_field_ids=customer_field_ids,
        followup_field_ids=followup_field_ids,
    )

    print("Creating and verifying fictional customer fixtures...")
    seed_result = _run(
        cli,
        args.profile,
        [
            "base",
            "+record-batch-create",
            "--base-token",
            base_token,
            "--table-id",
            customer_table_id,
            "--json",
            json.dumps(
                _batch_payload(cli, args.profile),
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        ],
        "fictional customer creation",
    )
    record_ids = _record_ids(seed_result)
    if len(record_ids) != len(SEED_CUSTOMERS):
        raise BootstrapError("fictional customer creation did not return every record")
    _verify_seed_records(
        cli, args.profile, base_token, customer_table_id, customer_field_ids
    )

    _checkpoint(
        args.wrapper_path,
        owner_sender_id,
        owner,
        identity_summary,
        status="verified",
        base_token=base_token,
        customer_table_id=customer_table_id,
        followup_table_id=followup_table_id,
        base_url=base_url,
        customer_field_ids=customer_field_ids,
        followup_field_ids=followup_field_ids,
    )
    print("Created and verified two tables and three fictional customer records.")
    print(
        "Sensitive identifiers were written only to config.local.json; "
        "the Base was retained."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootstrapError as error:
        print(f"Bootstrap stopped: {error}", file=sys.stderr)
        print("Any created resources and checkpoints were retained; reconcile them before retrying.",
              file=sys.stderr)
        raise SystemExit(1)
