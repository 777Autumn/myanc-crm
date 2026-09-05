"""Feishu Base adapter for one fixed host-only bot wrapper."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


READ_TIMEOUT_SECONDS = 30
WRITE_TIMEOUT_SECONDS = 30

_RECORD_ID = re.compile(r"rec[A-Za-z0-9]+\Z")
_OPEN_ID = re.compile(r"ou_[A-Za-z0-9]+\Z")
_CHANGE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
_FIELD_ID = re.compile(r"fld[A-Za-z0-9]+\Z")
_CUSTOMER_STAGES = {"新线索", "已联系", "沟通中", "已成交", "暂缓"}
_PROFILE_FIELDS = {"name", "contact", "phone", "email", "stage", "owner"}

_CUSTOMER_SCHEMA = {
    "客户名称": "text",
    "客户编号": "auto_number",
    "联系人": "text",
    "电话": "text",
    "邮箱": "text",
    "阶段": "select",
    "负责人": "user",
    "最近联系时间": "datetime",
    "最近联系摘要": "text",
    "下一步行动": "text",
    "下次跟进时间": "datetime",
    "更新时间": "updated_at",
}

_FOLLOWUP_SCHEMA = {
    "跟进标题": "text",
    "操作 ID": "text",
    "关联客户": "link",
    "沟通时间": "datetime",
    "沟通方式": "select",
    "沟通内容": "text",
    "下一步行动": "text",
    "下次跟进时间": "datetime",
    "跟进人": "user",
    "创建时间": "created_at",
}

_CUSTOMER_CANONICAL = {
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

_FOLLOWUP_CANONICAL = {
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

_TYPE_ALIASES: dict[Any, str] = {
    1: "text",
    3: "select",
    4: "select",
    5: "datetime",
    11: "user",
    13: "text",
    18: "link",
    21: "link",
    1001: "created_at",
    1002: "updated_at",
    1005: "auto_number",
    "text": "text",
    "phone": "text",
    "email": "text",
    "single_select": "select",
    "multi_select": "select",
    "select": "select",
    "datetime": "datetime",
    "date": "datetime",
    "date_time": "datetime",
    "user": "user",
    "person": "user",
    "link": "link",
    "duplex_link": "link",
    "created_at": "created_at",
    "created_time": "created_at",
    "updated_at": "updated_at",
    "modified_time": "updated_at",
    "auto_number": "auto_number",
    "autonumber": "auto_number",
}


class LarkBackendError(RuntimeError):
    """A structured, redacted adapter failure."""

    def __init__(
        self,
        kind: str,
        operation: str,
        *,
        returncode: int | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.kind = kind
        self.operation = operation
        self.returncode = returncode
        self.details = dict(details or {})
        super().__init__(f"{operation} failed ({kind})")

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "kind": self.kind,
            "operation": self.operation,
        }
        if self.returncode is not None:
            result["returncode"] = self.returncode
        if self.details:
            result["details"] = dict(self.details)
        return result


class LarkCliBackend:
    """Read and write the configured two-table CRM through one fixed wrapper."""

    def __init__(
        self,
        *,
        wrapper_path: str,
        base_token: str,
        customer_table_id: str,
        followup_table_id: str,
        base_url: str,
        fields: Mapping[str, Mapping[str, str]],
    ) -> None:
        self.wrapper_path = _wrapper_path(wrapper_path)
        self.base_token = _config_value("base_token", base_token)
        self.customer_table_id = _table_id("customer_table_id", customer_table_id)
        self.followup_table_id = _table_id("followup_table_id", followup_table_id)
        self.base_url = _base_url(base_url)
        self.customer_canonical = dict(_CUSTOMER_CANONICAL)
        self.customer_schema = dict(_CUSTOMER_SCHEMA)
        if isinstance(fields, Mapping) and isinstance(fields.get("customers"), Mapping):
            if "operation_id" in fields["customers"]:
                self.customer_canonical["operation_id"] = "建档操作ID"
                self.customer_schema["建档操作ID"] = "text"
        self.customer_fields = _field_ids(fields, "customers", self.customer_canonical)
        self.followup_fields = _field_ids(fields, "followups", _FOLLOWUP_CANONICAL)

    def read_schema(self) -> Mapping[str, Any]:
        customers = self._read_table_schema(
            self.customer_table_id, "read customer schema"
        )
        followups = self._read_table_schema(
            self.followup_table_id, "read follow-up schema"
        )
        self._validate_schema(
            customers,
            self.customer_schema,
            self.customer_canonical,
            self.customer_fields,
            "customer",
        )
        self._validate_schema(
            followups,
            _FOLLOWUP_SCHEMA,
            _FOLLOWUP_CANONICAL,
            self.followup_fields,
            "follow-up",
        )

        return {
            "customers": _stable_schema(
                customers, self.customer_schema,
                include_rules="operation_id" in self.customer_fields,
            ),
            "followups": _stable_schema(followups, _FOLLOWUP_SCHEMA),
        }

    def find_customers(self, query: str) -> list[Mapping[str, Any]]:
        query = _query(query)
        args = [
            "base",
            "+record-search",
            "--base-token",
            self.base_token,
            "--table-id",
            self.customer_table_id,
            "--keyword",
            query,
        ]
        for field in ("customer_number", "name"):
            args.extend(("--search-field", self.customer_fields[field]))
        args.extend(("--limit", "200"))
        rows = self._read_records(
            args, tuple(self.customer_fields.values()), "search customers"
        )
        return [_customer(row, self.customer_fields) for row in rows]

    def get_customer(self, record_id: str) -> Mapping[str, Any] | None:
        record_id = _record_id(record_id)
        rows = self._read_records(
            [
                "base",
                "+record-get",
                "--base-token",
                self.base_token,
                "--table-id",
                self.customer_table_id,
                "--record-id",
                record_id,
            ],
            tuple(self.customer_fields.values()),
            "read customer",
        )
        return _customer(rows[0], self.customer_fields) if rows else None

    def find_followup_by_change(self, change_id: str) -> Mapping[str, Any] | None:
        change_id = _change_id(change_id)
        rows = self._read_records(
            [
                "base",
                "+record-search",
                "--base-token",
                self.base_token,
                "--table-id",
                self.followup_table_id,
                "--keyword",
                change_id,
                "--search-field",
                self.followup_fields["change_id"],
                "--limit",
                "10",
            ],
            tuple(self.followup_fields.values()),
            "find follow-up",
        )
        matches = [
            row
            for row in rows
            if _followup(row, self.followup_fields).get("change_id") == change_id
        ]
        if len(matches) > 1:
            raise LarkBackendError(
                "duplicate_change_id",
                "find follow-up",
                details={"match_count": len(matches)},
            )
        return _followup(matches[0], self.followup_fields) if matches else None

    def resolve_assignee(self, query: str) -> list[dict[str, str]]:
        """Resolve one exact user email/mobile with the writer app, never by name."""
        kind, value = _assignee_query(query)
        envelope = self._run_json(
            ["api", "POST", "/open-apis/contact/v3/users/batch_get_id",
             "--params", '{"user_id_type":"open_id"}',
             "--data", json.dumps({kind: [value], "include_resigned": False})],
            "resolve assignee", READ_TIMEOUT_SECONDS,
        )
        rows = _contact_data(envelope, "resolve assignee").get("user_list")
        if not isinstance(rows, list) or len(rows) > 1:
            raise LarkBackendError("protocol_error", "resolve assignee")
        found: list[dict[str, str]] = []
        for row in rows:
            if not isinstance(row, Mapping):
                raise LarkBackendError("protocol_error", "resolve assignee")
            echoed = row.get("email" if kind == "emails" else "mobile")
            if not isinstance(echoed, str) or _assignee_query(echoed) != (kind, value):
                raise LarkBackendError("protocol_error", "resolve assignee")
            if not row.get("user_id"):
                continue  # Absent and outside app visibility are deliberately indistinguishable.
            person = self.get_assignee(_open_id(row["user_id"]))
            if person is not None:
                found.append(person)
        return found

    def get_assignee(self, user_id: str) -> dict[str, str] | None:
        user_id = _open_id(user_id)
        envelope = self._run_json(
            ["contact", "+get-user", "--user-id", user_id,
             "--user-id-type", "open_id", "--format", "json"],
            "read assignee", READ_TIMEOUT_SECONDS,
        )
        data = _contact_data(envelope, "read assignee")
        person = data.get("user", data)
        if person is None:
            return None
        if not isinstance(person, Mapping) or person.get("open_id") != user_id:
            raise LarkBackendError("protocol_error", "read assignee")
        status = person.get("status")
        if not isinstance(status, Mapping) or any(
            type(status.get(key)) is not bool
            for key in ("is_activated", "is_frozen", "is_resigned")
        ):
            raise LarkBackendError("assignee_status_unknown", "read assignee")
        if not status["is_activated"] or status["is_frozen"] or status["is_resigned"]:
            return None
        return {"id": user_id, "name": _text(person.get("name"), "assignee name", 256)}

    def find_customer_by_change(self, change_id: str) -> Mapping[str, Any] | None:
        change_id = _change_id(change_id)
        field_id = self._customer_operation_field()
        rows = self._read_records(
            ["base", "+record-search", "--base-token", self.base_token,
             "--table-id", self.customer_table_id, "--keyword", change_id,
             "--search-field", field_id, "--limit", "10"],
            tuple(self.customer_fields.values()), "find customer creation",
        )
        matches = [_customer(row, self.customer_fields) for row in rows]
        matches = [row for row in matches if row.get("operation_id") == change_id]
        if len(matches) > 1:
            raise LarkBackendError("duplicate_change_id", "find customer creation")
        return matches[0] if matches else None

    def create_customer(self, fields: Mapping[str, Any]) -> str:
        operation_field = self._customer_operation_field()
        values = _write_fields(fields, _PROFILE_FIELDS | {"operation_id"},
                               {"name", "stage", "owner", "operation_id"}, "create customer")
        operation_id = _change_id(values.pop("operation_id"))
        if not any(isinstance(values.get(key), str) and values[key].strip()
                   for key in ("contact", "phone", "email")):
            raise LarkBackendError("invalid_input", "validate customer contact")
        record = self._profile_cells(values)
        record[operation_field] = operation_id
        envelope = self._write_records(self.customer_table_id, "+record-batch-create",
                                       {"create_records": [record]}, "create customer")
        record_ids = _record_ids(envelope)
        if len(record_ids) != 1:
            raise LarkBackendError("protocol_error", "create customer")
        return _record_id(record_ids[0])

    def update_customer_profile(
        self, record_id: str, fields: Mapping[str, Any]
    ) -> Mapping[str, Any] | None:
        record_id = _record_id(record_id)
        values = _write_fields(fields, _PROFILE_FIELDS, set(), "update customer profile")
        patch = self._profile_cells(values)
        if not patch:
            return None
        envelope = self._write_records(self.customer_table_id, "+record-batch-update",
                                       {"update_records": {record_id: patch}}, "update customer profile")
        return envelope.get("data") if isinstance(envelope.get("data"), Mapping) else None

    def _customer_operation_field(self) -> str:
        if "operation_id" not in self.customer_fields:
            raise LarkBackendError("invalid_configuration", "customer creation is not configured")
        return self.customer_fields["operation_id"]

    def _profile_cells(self, values: Mapping[str, Any]) -> dict[str, Any]:
        record: dict[str, Any] = {}
        limits = {"name": 256, "contact": 256, "phone": 64, "email": 254}
        for key, value in values.items():
            if key == "owner":
                if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], Mapping):
                    raise LarkBackendError("invalid_input", "validate customer owner")
                if set(value[0]) != {"id", "name"}:
                    raise LarkBackendError("invalid_input", "validate customer owner")
                _text(value[0]["name"], "owner name", 256)
                cell: Any = [{"id": _open_id(value[0]["id"])}]
            elif key == "stage":
                if not isinstance(value, str) or value not in _CUSTOMER_STAGES:
                    raise LarkBackendError("invalid_input", "validate customer stage")
                cell = [value]
            else:
                cell = None if value is None and key != "name" else _text(value, key, limits[key])
            record[self.customer_fields[key]] = cell
        return record

    def read_customer_history(self, record_id: str, limit: int = 11) -> list[Mapping[str, Any]]:
        """Newest bounded history for one resolved customer, never a full-table scan."""
        record_id = _record_id(record_id)
        if type(limit) is not int or not 1 <= limit <= 11:
            raise LarkBackendError("invalid_input", "validate history limit")
        # CLI 1.0.90 help + official filter SOP document field-name tuples.
        # Validate those names against pinned IDs before using them as selectors.
        schema = self._read_table_schema(self.followup_table_id, "read history schema")
        self._validate_schema(schema, _FOLLOWUP_SCHEMA, _FOLLOWUP_CANONICAL,
                              self.followup_fields, "follow-up")
        rows = self._read_records(
            ["base", "+record-list", "--base-token", self.base_token,
             "--table-id", self.followup_table_id,
             "--filter-json", json.dumps({"logic": "and", "conditions": [
                 ["关联客户", "intersects", [{"id": record_id}]]]}, ensure_ascii=False),
             "--sort-json", json.dumps([{"field": "沟通时间", "desc": True}], ensure_ascii=False),
             "--limit", str(limit)],
            tuple(self.followup_fields.values()), "read customer history",
        )
        history = [_followup(row, self.followup_fields) for row in rows]
        if len(history) > limit or any(row.get("customer_record_id") != record_id for row in history):
            raise LarkBackendError("protocol_error", "read customer history")
        return history

    def create_followup(self, fields: Mapping[str, Any]) -> str:
        allowed = {
            "change_id",
            "customer_record_id",
            "customer_number",
            "occurred_at",
            "content",
            "channel",
            "next_action",
            "next_followup_at",
            "created_by",
        }
        required = {
            "change_id",
            "customer_record_id",
            "customer_number",
            "occurred_at",
            "content",
            "created_by",
        }
        values = _write_fields(fields, allowed, required, "create follow-up")
        change_id = _change_id(values["change_id"])
        customer_record_id = _record_id(values["customer_record_id"])
        created_by = _open_id(values["created_by"])
        title = " · ".join(
            (
                _text(values["customer_number"], "customer_number", 128),
                _text(values["occurred_at"], "occurred_at", 64),
            )
        )
        record: dict[str, Any] = {
            self.followup_fields["title"]: title,
            self.followup_fields["change_id"]: change_id,
            self.followup_fields["customer_record_id"]: [{"id": customer_record_id}],
            self.followup_fields["occurred_at"]: _text(
                values["occurred_at"], "occurred_at", 64
            ),
            self.followup_fields["content"]: _text(
                values["content"], "content", 5000
            ),
            self.followup_fields["created_by"]: [{"id": created_by}],
        }
        if values.get("channel") is not None:
            record[self.followup_fields["channel"]] = [
                _text(values["channel"], "channel", 64)
            ]
        _optional_text(
            record,
            self.followup_fields["next_action"],
            values.get("next_action"),
            1000,
        )
        _optional_text(
            record,
            self.followup_fields["next_followup_at"],
            values.get("next_followup_at"),
            64,
        )
        envelope = self._write_records(
            self.followup_table_id,
            "+record-batch-create",
            {"create_records": [record]},
            "create follow-up",
        )
        record_ids = _record_ids(envelope)
        if len(record_ids) != 1:
            raise LarkBackendError("protocol_error", "create follow-up")
        return _record_id(record_ids[0])

    def update_customer(
        self, record_id: str, fields: Mapping[str, Any]
    ) -> Mapping[str, Any] | None:
        record_id = _record_id(record_id)
        allowed = {
            "last_followup_at",
            "last_followup_content",
            "next_action",
            "next_followup_at",
        }
        values = _write_fields(fields, allowed, set(), "update customer")
        patch: dict[str, Any] = {}
        mapping = {
            "last_followup_at": (self.customer_fields["last_followup_at"], 64),
            "last_followup_content": (
                self.customer_fields["last_followup_content"],
                5000,
            ),
            "next_action": (self.customer_fields["next_action"], 1000),
            "next_followup_at": (self.customer_fields["next_followup_at"], 64),
        }
        for key, value in values.items():
            field_name, limit = mapping[key]
            patch[field_name] = (
                None if value is None else _text(value, key, limit)
            )
        if not patch:
            return None
        envelope = self._write_records(
            self.customer_table_id,
            "+record-batch-update",
            {"update_records": {record_id: patch}},
            "update customer",
        )
        return envelope.get("data") if isinstance(envelope.get("data"), Mapping) else None

    def get_followup(self, record_id: str) -> Mapping[str, Any] | None:
        record_id = _record_id(record_id)
        rows = self._read_records(
            [
                "base",
                "+record-get",
                "--base-token",
                self.base_token,
                "--table-id",
                self.followup_table_id,
                "--record-id",
                record_id,
            ],
            tuple(self.followup_fields.values()),
            "read follow-up",
        )
        return _followup(rows[0], self.followup_fields) if rows else None

    def customer_url(self, record_id: str) -> str:
        return self._record_url(self.customer_table_id, _record_id(record_id))

    def followup_url(self, record_id: str) -> str:
        return self._record_url(self.followup_table_id, _record_id(record_id))

    def _record_url(self, table_id: str, record_id: str) -> str:
        parts = urlsplit(self.base_url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.update({"table": table_id, "record": record_id})
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
        )

    def _read_table_schema(
        self, table_id: str, operation: str
    ) -> dict[str, Mapping[str, Any]]:
        envelope = self._run_json(
            [
                "base",
                "+field-list",
                "--base-token",
                self.base_token,
                "--table-id",
                table_id,
                "--format",
                "json",
                "--limit",
                "200",
            ],
            operation,
            READ_TIMEOUT_SECONDS,
        )
        fields: dict[str, Mapping[str, Any]] = {}
        for item in _items(envelope):
            name = item.get("name") or item.get("field_name")
            if isinstance(name, str):
                fields[name] = item
        return fields

    def _validate_schema(
        self,
        actual: Mapping[str, Mapping[str, Any]],
        expected: Mapping[str, str],
        canonical: Mapping[str, str],
        configured: Mapping[str, str],
        label: str,
    ) -> None:
        missing = sorted(set(expected) - set(actual))
        mismatched: list[dict[str, str]] = []
        for name, wanted in expected.items():
            if name not in actual:
                continue
            got = _field_type(actual[name])
            if got != wanted:
                mismatched.append({"field": name, "expected": wanted, "actual": got})

        for key, name in canonical.items():
            if name not in actual:
                continue
            actual_id = actual[name].get("field_id", actual[name].get("id"))
            if actual_id != configured[key]:
                mismatched.append(
                    {
                        "field": name,
                        "expected": "configured-field-id",
                        "actual": "other-field-id",
                    }
                )

        for primary in ("客户名称", "跟进标题"):
            if primary not in actual:
                continue
            item = actual[primary]
            marker = item.get("is_primary", item.get("primary"))
            if marker is not None and marker is not True:
                mismatched.append(
                    {"field": primary, "expected": "primary", "actual": "non-primary"}
                )

        if label == "follow-up" and "关联客户" in actual:
            target = _link_target(actual["关联客户"])
            if target is not None and target != self.customer_table_id:
                mismatched.append(
                    {
                        "field": "关联客户",
                        "expected": "customer-table-link",
                        "actual": "other-table-link",
                    }
                )

        if missing or mismatched:
            details: dict[str, Any] = {}
            if missing:
                details["missing_fields"] = missing
            if mismatched:
                details["mismatched_fields"] = mismatched
            raise LarkBackendError("schema_mismatch", f"validate {label} schema", details=details)

    def _read_records(
        self,
        args: list[str],
        fields: tuple[str, ...],
        operation: str,
    ) -> list[Mapping[str, Any]]:
        with tempfile.TemporaryDirectory(prefix="myanc-crm-read-") as raw_dir:
            directory = Path(raw_dir)
            output_name = "records.ndjson"
            projected = list(args)
            for field in fields:
                projected.extend(("--field-id", field))
            projected.extend(
                (
                    "--format",
                    "ndjson",
                    "--output",
                    output_name,
                    "--overwrite",
                )
            )
            self._run_json(
                projected,
                operation,
                READ_TIMEOUT_SECONDS,
                cwd=directory,
                artifact_manifest=True,
            )
            path = directory / output_name
            if not path.is_file():
                raise LarkBackendError("protocol_error", operation)
            rows: list[Mapping[str, Any]] = []
            try:
                with path.open(encoding="utf-8") as stream:
                    for line in stream:
                        if not line.strip():
                            continue
                        row = json.loads(line)
                        if not isinstance(row, Mapping):
                            raise ValueError
                        rows.append(row)
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
                raise LarkBackendError("protocol_error", operation) from None
            return rows

    def _write_records(
        self,
        table_id: str,
        command: str,
        payload: Mapping[str, Any],
        operation: str,
    ) -> Mapping[str, Any]:
        with tempfile.TemporaryDirectory(prefix="myanc-crm-write-") as raw_dir:
            directory = Path(raw_dir)
            path = directory / "payload.json"
            try:
                path.write_text(
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    encoding="utf-8",
                )
            except (OSError, TypeError, ValueError):
                raise LarkBackendError("protocol_error", operation) from None
            envelope = self._run_json(
                [
                    "base",
                    command,
                    "--base-token",
                    self.base_token,
                    "--table-id",
                    table_id,
                    "--json",
                    "@payload.json",
                ],
                operation,
                WRITE_TIMEOUT_SECONDS,
                cwd=directory,
            )
            ignored = _find_nested(envelope, "ignored_fields")
            if ignored:
                raise LarkBackendError(
                    "ignored_fields",
                    operation,
                    details={
                        "count": len(ignored) if isinstance(ignored, list) else 1
                    },
                )
            return envelope

    def _run_json(
        self,
        args: list[str],
        operation: str,
        timeout: int,
        *,
        cwd: Path | None = None,
        artifact_manifest: bool = False,
    ) -> Mapping[str, Any]:
        try:
            completed = subprocess.run(
                [self.wrapper_path, *args],
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            raise LarkBackendError("timeout", operation) from None
        except OSError:
            raise LarkBackendError("unavailable", operation) from None

        if completed.returncode != 0:
            raise _cli_error(operation, completed.returncode, completed.stderr)
        try:
            envelope = json.loads(completed.stdout)
        except (json.JSONDecodeError, TypeError):
            raise LarkBackendError("protocol_error", operation) from None
        if not isinstance(envelope, Mapping):
            raise LarkBackendError("protocol_error", operation)
        if artifact_manifest:
            if (
                envelope.get("format") != "ndjson"
                or not isinstance(envelope.get("record_file"), str)
                or not isinstance(envelope.get("records_count"), int)
            ):
                raise LarkBackendError("protocol_error", operation)
            return envelope
        if envelope.get("ok") is not True:
            raise LarkBackendError("protocol_error", operation)
        if envelope.get("identity") != "bot":
            raise LarkBackendError("identity_mismatch", operation)
        return envelope


def _cli_error(operation: str, returncode: int, stderr: str) -> LarkBackendError:
    details: dict[str, Any] = {}
    try:
        envelope = json.loads(stderr)
    except (json.JSONDecodeError, TypeError):
        envelope = None
    error = envelope.get("error") if isinstance(envelope, Mapping) else None
    if isinstance(error, Mapping):
        for source, target in (
            ("type", "error_type"),
            ("subtype", "error_subtype"),
            ("code", "code"),
            ("risk", "risk"),
        ):
            value = error.get(source)
            if isinstance(value, (int, bool)) or (
                isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", value)
            ):
                details[target] = value
    confirmation = (
        returncode == 10
        and details.get("error_type") == "confirmation"
        and details.get("error_subtype") == "confirmation_required"
    )
    kind = "confirmation_required" if confirmation else "cli_error"
    return LarkBackendError(kind, operation, returncode=returncode, details=details)


def _config_value(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or value.startswith("-"):
        raise LarkBackendError("invalid_configuration", f"validate {name}")
    return value


def _wrapper_path(value: Any) -> str:
    value = _config_value("wrapper_path", value)
    if not (
        PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()
    ):
        raise LarkBackendError("invalid_configuration", "validate wrapper_path")
    return value


def _table_id(name: str, value: Any) -> str:
    value = _config_value(name, value)
    if not re.fullmatch(r"tbl[A-Za-z0-9]+", value):
        raise LarkBackendError("invalid_configuration", f"validate {name}")
    return value


def _field_ids(
    fields: Any, group: str, expected: Mapping[str, str]
) -> dict[str, str]:
    if not isinstance(fields, Mapping) or set(fields) != {"customers", "followups"}:
        raise LarkBackendError("invalid_configuration", "validate fields")
    values = fields.get(group)
    if not isinstance(values, Mapping) or set(values) != set(expected):
        raise LarkBackendError("invalid_configuration", f"validate fields.{group}")
    result: dict[str, str] = {}
    for key in expected:
        value = values.get(key)
        if not isinstance(value, str) or not _FIELD_ID.fullmatch(value):
            raise LarkBackendError(
                "invalid_configuration", f"validate fields.{group}.{key}"
            )
        result[key] = value
    if len(set(result.values())) != len(result):
        raise LarkBackendError("invalid_configuration", f"validate fields.{group}")
    return result


def _base_url(value: Any) -> str:
    value = _config_value("base_url", value)
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.netloc:
        raise LarkBackendError("invalid_configuration", "validate base_url")
    return value


def _record_id(value: Any) -> str:
    if not isinstance(value, str) or not _RECORD_ID.fullmatch(value):
        raise LarkBackendError("invalid_input", "validate record ID")
    return value


def _open_id(value: Any) -> str:
    if not isinstance(value, str) or not _OPEN_ID.fullmatch(value):
        raise LarkBackendError("invalid_input", "validate actor ID")
    return value


def _assignee_query(value: Any) -> tuple[str, str]:
    value = _text(value, "assignee query", 254)
    if re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", value):
        # This is the contact API's user email, not the separate enterprise_email field.
        return "emails", value.casefold()
    if re.fullmatch(r"1[0-9]{10}", value):
        return "mobiles", value
    if re.fullmatch(r"\+[1-9][0-9]{5,14}", value):
        return "mobiles", value[3:] if value.startswith("+86") and len(value) == 14 else value
    raise LarkBackendError("invalid_input", "assignee requires exact user email or mobile")


def _contact_data(envelope: Mapping[str, Any], operation: str) -> Mapping[str, Any]:
    data = envelope.get("data")
    if isinstance(data, Mapping) and "code" in data:
        if type(data.get("code")) is not int or data["code"] != 0:
            raise LarkBackendError("protocol_error", operation)
        data = data.get("data")
    if not isinstance(data, Mapping):
        raise LarkBackendError("protocol_error", operation)
    return data


def _change_id(value: Any) -> str:
    if not isinstance(value, str) or not _CHANGE_ID.fullmatch(value):
        raise LarkBackendError("invalid_input", "validate change ID")
    return value


def _query(value: Any) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 200
        or "\x00" in value
        or value.lstrip().startswith("-")
    ):
        raise LarkBackendError("invalid_input", "validate customer query")
    return value.strip()


def _text(value: Any, name: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit or "\x00" in value:
        raise LarkBackendError("invalid_input", f"validate {name}")
    return value.strip()


def _write_fields(
    fields: Mapping[str, Any],
    allowed: set[str],
    required: set[str],
    operation: str,
) -> dict[str, Any]:
    if not isinstance(fields, Mapping):
        raise LarkBackendError("invalid_input", operation)
    unknown = sorted(str(key) for key in set(fields) - allowed)
    missing = sorted(required - set(fields))
    if unknown or missing:
        details: dict[str, Any] = {}
        if unknown:
            details["unknown_fields"] = unknown
        if missing:
            details["missing_fields"] = missing
        raise LarkBackendError("invalid_input", operation, details=details)
    return dict(fields)


def _optional_text(
    target: dict[str, Any], field: str, value: Any, limit: int
) -> None:
    if value is not None:
        target[field] = _text(value, field, limit)


def _items(envelope: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    data: Any = envelope.get("data")
    if isinstance(data, list):
        candidates = data
    elif isinstance(data, Mapping):
        candidates = data.get("items", data.get("fields", []))
    else:
        candidates = []
    if not isinstance(candidates, list) or not all(
        isinstance(item, Mapping) for item in candidates
    ):
        raise LarkBackendError("protocol_error", "parse field schema")
    return candidates


def _field_type(field: Mapping[str, Any]) -> str:
    raw: Any = field.get("type", field.get("field_type"))
    if isinstance(raw, Mapping):
        raw = raw.get("name", raw.get("type"))
    if isinstance(raw, str):
        raw = raw.strip().lower().replace("-", "_").replace(" ", "_")
        if raw.isdigit():
            raw = int(raw)
    return _TYPE_ALIASES.get(raw, f"unknown:{raw}")


def _link_target(field: Mapping[str, Any]) -> str | None:
    properties = field.get("property", field.get("properties"))
    if not isinstance(properties, Mapping):
        return None
    value = properties.get("table_id", properties.get("target_table_id"))
    return value if isinstance(value, str) else None


def _stable_schema(
    actual: Mapping[str, Mapping[str, Any]],
    expected: Mapping[str, str],
    *, include_rules: bool = False,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for name in sorted(expected):
        item = actual[name]
        field_id = item.get("field_id", item.get("id"))
        result.append(
            {
                "name": name,
                "field_id": field_id if isinstance(field_id, str) else None,
                "type": _field_type(item),
            }
        )
        if include_rules:
            # New profile writes also bind select/person constraints; legacy hashes stay unchanged.
            for key in ("multiple", "options", "style", "property", "properties"):
                if key in item:
                    result[-1][key] = item[key]
    return result


def _fields(row: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = row.get("fields")
    return nested if isinstance(nested, Mapping) else row


def _first(value: Any) -> Any:
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _cell(
    fields: Mapping[str, Any], name: str, field_id: str
) -> Any:
    return fields[name] if name in fields else fields.get(field_id)


def _linked_id(value: Any) -> str | None:
    first = _first(value)
    if isinstance(first, Mapping):
        identifier = first.get("id")
        return identifier if isinstance(identifier, str) else None
    return None


def _customer(
    row: Mapping[str, Any], configured: Mapping[str, str]
) -> dict[str, Any]:
    fields = _fields(row)
    result = {
        "record_id": row.get("record_id", fields.get("record_id")),
        "customer_number": _cell(fields, "客户编号", configured["customer_number"]),
        "name": _cell(fields, "客户名称", configured["name"]),
        "contact": _cell(fields, "联系人", configured["contact"]),
        "phone": _cell(fields, "电话", configured["phone"]),
        "email": _cell(fields, "邮箱", configured["email"]),
        "stage": _first(_cell(fields, "阶段", configured["stage"])),
        "owner": _cell(fields, "负责人", configured["owner"]),
        "last_followup_at": _cell(
            fields, "最近联系时间", configured["last_followup_at"]
        ),
        "last_followup_content": _cell(
            fields, "最近联系摘要", configured["last_followup_content"]
        ),
        "next_action": _cell(fields, "下一步行动", configured["next_action"]),
        "next_followup_at": _cell(
            fields, "下次跟进时间", configured["next_followup_at"]
        ),
        "updated_at": _cell(fields, "更新时间", configured["updated_at"]),
    }
    if not isinstance(result["record_id"], str):
        raise LarkBackendError("protocol_error", "parse customer")
    if "operation_id" in configured:
        result["operation_id"] = _cell(fields, "建档操作ID", configured["operation_id"])
        result["owner"] = _customer_owner(result["owner"])
    return result


def _customer_owner(value: Any) -> list[dict[str, str]]:
    """Ignore presentation metadata, but never hide a broken single-person cell."""
    if value is None or value == []:
        return []
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], Mapping):
        raise LarkBackendError("protocol_error", "parse customer owner")
    try:
        return [{"id": _open_id(value[0].get("id")),
                 "name": _text(value[0].get("name"), "owner name", 256)}]
    except LarkBackendError:
        raise LarkBackendError("protocol_error", "parse customer owner") from None


def _followup(
    row: Mapping[str, Any], configured: Mapping[str, str]
) -> dict[str, Any]:
    fields = _fields(row)
    result = {
        "record_id": row.get("record_id", fields.get("record_id")),
        "title": _cell(fields, "跟进标题", configured["title"]),
        "change_id": _cell(fields, "操作 ID", configured["change_id"]),
        "customer_record_id": _linked_id(
            _cell(fields, "关联客户", configured["customer_record_id"])
        ),
        "occurred_at": _cell(fields, "沟通时间", configured["occurred_at"]),
        "channel": _first(_cell(fields, "沟通方式", configured["channel"])),
        "content": _cell(fields, "沟通内容", configured["content"]),
        "next_action": _cell(fields, "下一步行动", configured["next_action"]),
        "next_followup_at": _cell(
            fields, "下次跟进时间", configured["next_followup_at"]
        ),
        "created_by": _linked_id(
            _cell(fields, "跟进人", configured["created_by"])
        ),
        "created_at": _cell(fields, "创建时间", configured["created_at"]),
    }
    if not isinstance(result["record_id"], str):
        raise LarkBackendError("protocol_error", "parse follow-up")
    return result


def _record_ids(envelope: Mapping[str, Any]) -> list[str]:
    data = envelope.get("data")
    if not isinstance(data, Mapping):
        return []
    candidates = data.get("record_id_list", data.get("record_ids"))
    if isinstance(candidates, list):
        return [value for value in candidates if isinstance(value, str)]
    records = data.get("records")
    if isinstance(records, list):
        return [
            item["record_id"]
            for item in records
            if isinstance(item, Mapping) and isinstance(item.get("record_id"), str)
        ]
    return []


def _find_nested(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        if key in value:
            return value[key]
        for nested in value.values():
            found = _find_nested(nested, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_nested(nested, key)
            if found is not None:
                return found
    return None
