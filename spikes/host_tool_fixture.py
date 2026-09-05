"""OFFLINE ONLY: real authenticated CLI/core/SQLite, persisted synthetic Feishu.

Invoke with one host command and JSON stdin. MYANC_SPIKE_DIR must name an
existing absolute scratch directory. Never reads real CRM config or uses Lark.
This JSON fake is for serial integration journeys, not concurrent-writer tests.
"""

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from myanc_crm import cli, core
from test_host_tools import CONFIG, HistoryBackend


class PersistentFakeFeishu(HistoryBackend):
    def __init__(self, directory):
        super().__init__()
        self.path = directory / "fake-feishu.json"
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.customers = data["customers"]
            self.followups = data["followups"]
            self.actions = data["actions"]
            self.update_mode = data.get("update_mode", "normal")
            self.create_mode = data.get("create_mode", "normal")
            self.hide_followup_readback = data.get("hide_followup_readback", False)
        else:
            # Eval-only paired fixtures: do not add these claims to demo/live data.
            seed = os.environ.get("MYANC_SPIKE_SEED", "")
            if seed not in {"", "term-ambiguous", "term-defined"}:
                raise ValueError("Unknown offline fixture seed")
            if seed:
                context = "客户提出 Canary 测试需求；客户认可方案，希望安排演示。"
                if seed == "term-defined":
                    context = ("客户明确说明 Canary 在本次需求中指先向 5% 用户灰度发布新版本、"
                               "观察错误率，异常时回滚；客户认可方案，希望安排演示。")
                self.customers["rec-1"]["last_followup_content"] = context
                self.followups["seed-history"] = {
                    "record_id": "seed-history", "customer_record_id": "rec-1",
                    "occurred_at": "2026-09-03T09:00:00+08:00", "content": context,
                }
                self.save()

    def save(self):
        data = {name: copy.deepcopy(getattr(self, name)) for name in (
            "customers", "followups", "actions", "update_mode", "create_mode",
            "hide_followup_readback",
        )}
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                         prefix="fake-", suffix=".json", delete=False) as stream:
            json.dump(data, stream, ensure_ascii=False)
            temporary = stream.name
        os.replace(temporary, self.path)

    def create_followup(self, fields):
        try:
            return super().create_followup(fields)
        finally:
            self.save()

    def update_customer(self, record_id, fields):
        try:
            return super().update_customer(record_id, fields)
        finally:
            self.save()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {
        "host-tool", "host-bind-card", "host-claim", "host-execute",
    }:
        raise SystemExit("Offline fixture accepts only the four documented host commands.")
    directory = Path(os.environ.get("MYANC_SPIKE_DIR", ""))
    if not directory.is_absolute() or not directory.is_dir():
        raise SystemExit("MYANC_SPIKE_DIR must be an existing absolute scratch directory.")
    directory = directory.resolve()
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    # Configuration and external Feishu are the injected system boundaries.
    # Host authentication, envelope checks, SQLite, claim and apply stay real.
    with (
        mock.patch.object(cli, "_config_path", return_value=directory / "fixture-config-unused"),
        mock.patch.object(cli, "_load_config", return_value=CONFIG),
        mock.patch.object(cli, "_runtime", side_effect=lambda *_: (
            PersistentFakeFeishu(directory), core.Ledger(directory / "ledger.sqlite3"))),
        mock.patch.object(cli, "LarkCliBackend", side_effect=AssertionError("No live Lark in fixture")),
        mock.patch.object(core, "READBACK_TIMEOUT_SECONDS", 0),
    ):
        return cli.main()


if __name__ == "__main__":
    raise SystemExit(main())
