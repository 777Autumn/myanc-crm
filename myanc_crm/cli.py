"""JSON-only command-line boundary for the CRM follow-up flow."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping, TextIO

from .core import Ledger, apply_followup, stage_followup
from .lark import LarkCliBackend


MAX_INPUT_BYTES = 256 * 1024
CONFIG_ENV = "MYANC_CRM_CONFIG"


class CliConfigurationError(ValueError):
    """A safe-to-report local configuration error."""


def _config_path() -> Path:
    override = os.environ.get(CONFIG_ENV)
    if override:
        return Path(override).expanduser().resolve()

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
    backend = LarkCliBackend(
        wrapper_path=_required_text(config, "wrapper_path"),
        base_token=_required_text(config, "base_token"),
        customer_table_id=_required_text(config, "customer_table_id"),
        followup_table_id=_required_text(config, "followup_table_id"),
        base_url=_required_text(config, "base_url"),
        fields=_required_mapping(config, "fields"),
    )
    raw_ledger = _required_text(config, "ledger_path")
    ledger_path = Path(raw_ledger)
    if not ledger_path.is_absolute():
        ledger_path = config_path.parent / ledger_path
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
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


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    """Run one stage or apply request without exposing configuration overrides."""

    args = list(sys.argv[1:] if argv is None else argv)
    source = sys.stdin if stdin is None else stdin
    target = sys.stdout if stdout is None else stdout

    command = args[0] if len(args) == 1 else ""
    if command not in {"stage", "apply"}:
        result = {
            "status": "failed",
            "code": "usage",
            "message": "Usage: crm-followup stage|apply (JSON is read from stdin).",
        }
        target.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
        return 2

    try:
        request = _read_command(source)
        path = _config_path()
        config = _load_config(path)
        _required_mapping(config, "allowed_actors")
        backend, ledger = _runtime(config, path)
    except (CliConfigurationError, OSError, TypeError, ValueError):
        result = _safe_failure(
            command,
            "invalid_local_input",
            "The request or protected CRM configuration is invalid; Feishu is unchanged.",
        )
        target.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
        return 2

    try:
        if command == "stage":
            result = stage_followup(request, backend, ledger, config)
        else:
            result = apply_followup(request, backend, ledger, config)
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

    target.write(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n")
    return exit_code


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
