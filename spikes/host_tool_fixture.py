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
from test_customer_journey import CustomerBackend
from test_core import customer


class PersistentFakeFeishu(HistoryBackend):
    def __init__(self, directory):
        super().__init__()
        self.people = {"ou_member": {"id": "ou_member", "name": "示例同事"}}
        self.profile_mode = "normal"
        self.path = directory / "fake-feishu.json"
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.customers = data["customers"]
            self.followups = data["followups"]
            self.actions = data["actions"]
            self.update_mode = data.get("update_mode", "normal")
            self.create_mode = data.get("create_mode", "normal")
            self.hide_followup_readback = data.get("hide_followup_readback", False)
            self.people = data.get("people", self.people)
            self.profile_mode = data.get("profile_mode", "normal")
            self.schema = data.get("schema", self.schema)
        else:
            # Eval-only paired fixtures: do not add these claims to demo/live data.
            seed = os.environ.get("MYANC_SPIKE_SEED", "")
            if seed not in {"", "term-ambiguous", "term-defined", "customer-trial",
                            "customer-roster", "customer-roster-ambiguous", "daily-followup"}:
                raise ValueError("Unknown offline fixture seed")
            if seed == "daily-followup":
                self.schema["customers"].append("operation_id")
                self.people.update({f"ou_fixture_sender-{n}": {
                    "id": f"ou_fixture_sender-{n}", "name": f"Fixture sender-{n}"}
                    for n in (1, 2)})
                self.customers = {}
                for n in range(1, 23):
                    row = customer(f"rec-{n}", f"C-{n:03d}", f"虚构日常客户{n:03d}")
                    row.update(stage="新线索", owner=[self.people[
                        "ou_fixture_sender-1" if n <= 21 else "ou_fixture_sender-2"]],
                        next_action="准备虚构材料", next_followup_at="2099-01-03T09:00:00+08:00")
                    self.customers[row["record_id"]] = row
                self.followups = {f"history-{n:02d}": {
                    "record_id": f"history-{n:02d}", "customer_record_id": "rec-2",
                    "occurred_at": f"2026-09-{n:02d}T09:00:00+08:00",
                    "content": f"虚构历史沟通{n:02d}",
                } for n in range(1, 13)}
                self.save()
            elif seed.startswith("customer-"):
                self.schema["customers"].append("operation_id")
                self.customers["rec-1"].update(stage="新线索", owner=[self.people["ou_member"]])
                self.save()
            elif seed:
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
            "people", "profile_mode", "schema",
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

    resolve_assignee = CustomerBackend.resolve_assignee
    get_assignee = CustomerBackend.get_assignee
    find_customer_by_change = CustomerBackend.find_customer_by_change

    def create_customer(self, fields):
        try:
            return CustomerBackend.create_customer(self, fields)
        finally:
            self.save()

    def update_customer_profile(self, record_id, fields):
        try:
            return CustomerBackend.update_customer_profile(self, record_id, fields)
        finally:
            self.save()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {
        "host-tool", "host-bind-card", "host-claim", "host-execute",
        "host-plan-events", "host-plan-read", "host-plan-ack",
    }:
        raise SystemExit("Offline fixture accepts only the documented host commands.")
    directory = Path(os.environ.get("MYANC_SPIKE_DIR", ""))
    if not directory.is_absolute() or not directory.is_dir():
        raise SystemExit("MYANC_SPIKE_DIR must be an existing absolute scratch directory.")
    directory = directory.resolve()
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    # Configuration and external Feishu are the injected system boundaries.
    # Host authentication, envelope checks, SQLite, claim and apply stay real.
    config = copy.deepcopy(CONFIG)
    if os.environ.get("MYANC_SPIKE_SEED") == "daily-followup":
        config.update(crm_plan_reminders_enabled=True, crm_plan_namespace="offline-daily-plan")
    if os.environ.get("MYANC_SPIKE_SEED", "").startswith("customer-roster"):
        config["allowed_actors"]["sender-2"] = {
            "display_name": "示例同事", "feishu_user_id": "ou_member"}
        if os.environ["MYANC_SPIKE_SEED"] == "customer-roster-ambiguous":
            config["allowed_actors"]["sender-1"]["display_name"] = "示例同事"
    with (
        mock.patch.object(cli, "_config_path", return_value=directory / "fixture-config-unused"),
        mock.patch.object(cli, "_load_config", return_value=config),
        mock.patch.object(cli, "_runtime", side_effect=lambda *_: (
            PersistentFakeFeishu(directory), core.Ledger(directory / "ledger.sqlite3"))),
        mock.patch.object(cli, "LarkCliBackend", side_effect=AssertionError("No live Lark in fixture")),
        mock.patch.object(core, "READBACK_TIMEOUT_SECONDS", 0),
    ):
        return cli.main()


if __name__ == "__main__":
    raise SystemExit(main())
