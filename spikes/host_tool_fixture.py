"""OFFLINE ONLY: real authenticated CLI/core/SQLite, persisted synthetic Feishu.

Invoke with one host command and JSON stdin. MYANC_SPIKE_DIR must name an
existing absolute scratch directory. Never reads real CRM config or uses Lark
authentication/API commands. Capacity startup checks the installed CLI version.
This JSON fake is for serial integration journeys, not concurrent-writer tests.
"""

import copy
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from myanc_crm import banquet, cli, core
from test_host_tools import CONFIG, HistoryBackend
from test_customer_journey import CustomerBackend
from test_core import customer


class PersistentFakeFeishu(HistoryBackend):
    def __init__(self, directory):
        super().__init__()
        self.people = {"ou_member": {"id": "ou_member", "name": "示例同事"}}
        self.profile_mode = "normal"
        self.banquet_rows = {}
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
            self.banquet_rows = data.get("banquet_rows", {})
        else:
            # Eval-only paired fixtures: do not add these claims to demo/live data.
            seed = os.environ.get("MYANC_SPIKE_SEED", "")
            if seed not in {"", "term-ambiguous", "term-defined", "customer-trial",
                            "customer-roster", "customer-roster-ambiguous", "daily-followup", "capacity"}:
                raise ValueError("Unknown offline fixture seed")
            if seed in {"daily-followup", "capacity"}:
                self.schema["customers"].append("operation_id")
                self.people.update({f"ou_fixture_sender-{n}": {
                    "id": f"ou_fixture_sender-{n}", "name": f"Fixture sender-{n}"}
                    for n in (1, 2)})
                self.customers = {}
                for n in range(1, 6 if seed == "capacity" else 23):
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
            "people", "profile_mode", "schema", "banquet_rows",
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


class PersistentSalesStore:
    """Synthetic Feishu tables only; staged writes/claims/receipts stay real."""
    def __init__(self, backend):
        self.backend = backend

    def read_schema(self, kinds=None):
        return {'banquets': 'synthetic-fixed-schema'}

    def get(self, kind, identifier, *, recheck=True):
        return copy.deepcopy(self.backend.banquet_rows.get(kind, {}).get(identifier))

    def list(self, kind):
        return copy.deepcopy(list(self.backend.banquet_rows.get(kind, {}).values()))

    def write(self, kind, identifier, fields):
        rows = self.backend.banquet_rows.setdefault(kind, {})
        identifier = identifier or 'recSales' + str(len(rows) + 1)
        initial = {key: None for key in (banquet.SCHEMA if kind == 'banquets' else {})}
        if kind == 'banquets':
            initial['number'] = 'YAN-' + str(len(rows) + 1).zfill(4)
        rows.setdefault(identifier, {'record_id': identifier, **initial}).update(copy.deepcopy(fields))
        self.backend.save()
        return identifier

    def url(self, kind, identifier):
        return 'https://example.invalid/base/fixture?record=' + identifier


def capacity_config(directory):
    """Two fictional participants, four fixed routes, real connection checks.

    No personal account is enrolled; startup only reads the installed CLI version. File-only
    private work and shared reads are allowed by the production guard; private
    CRM reads must fail. Each caller supplies a separate cohort scratch root.
    """
    config = copy.deepcopy(CONFIG)
    routes = []
    for n, user in enumerate(("sender-1", "sender-2")):
        config["allowed_actors"][user]["connection_profile"] = f"anc-user-capacity-{n}"
        for offset, audience in enumerate(("private", "shared")):
            routes.append(dict(platform="feishu", user_id=user,
                               chat_id=f"private-{user}" if offset == 0 else "group-1",
                               project=f"capacity-{2*n+offset}", audience=audience))
    config["personal_connections"] = dict(
        app_id="capacity-crm", tenant_key="capacity-tenant", source_app_id="capacity-app",
        source_tenant_key="capacity-tenant", cli_path=str(Path('/usr/local/libexec/lark-cli-1.0.90').absolute()),
        database_path=str(directory / "connections.sqlite3"), cli_home_root=str(directory / "no-credentials"),
        resource_mode="shared", routes=routes)
    return config


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {
        "host-tool", "host-bind-card", "host-claim", "host-execute",
        "host-plan-events", "host-plan-read", "host-plan-ack",
        "host-connection-config", "host-connection-guard",
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
    if os.environ.get("MYANC_SPIKE_SEED") == "capacity":
        config = capacity_config(directory)
        if sys.argv[1] not in {"host-tool", "host-connection-config", "host-connection-guard"}:
            raise SystemExit("Capacity fixture is read-only.")
        # Reject any business write before the real CLI can stage it.
        import io
        payload = json.load(sys.stdin)
        if sys.argv[1] == "host-tool" and payload.get("command") not in {"customer", "customers"}:
            raise SystemExit("Capacity fixture accepts only customer reads.")
        sys.stdin = io.StringIO(json.dumps(payload))
    if os.environ.get('MYANC_SPIKE_SEED') in {'shared-cases', 'project-context'}:
        from myanc_crm import shared_cases
        test_store = directory / 'mock-cases.sqlite3'
        config['ledger_path'] = str(directory / 'formal-never-opened.sqlite3')
        config['shared_cases'] = dict(enabled=True,ledger_path=str(test_store),namespace='mock-banquet',
            group_chat_id='group-1',members=[dict(platform='mock',user_id=user,chat_id=chat,project='test')
            for user,chat in [('sender-1','group-1'),('sender-2','group-1'),('sender-1','private-1'),('sender-2','private-2')]])
        if os.environ['MYANC_SPIKE_SEED'] == 'project-context':
            config['shared_cases'].update(namespace='mock-project-journey',
                project_context=dict(enabled=True, group_case='林陈婚宴', managers=[]))
        if not test_store.exists():
            test_store.touch(mode=0o600)
            shared_cases.initialize_config(config)
    if os.environ.get("MYANC_SPIKE_SEED") == "daily-followup":
        config.update(crm_plan_reminders_enabled=True, crm_plan_namespace="offline-daily-plan")
    if os.environ.get("MYANC_SPIKE_SEED", "").startswith("customer-roster"):
        config["allowed_actors"]["sender-2"] = {
            "display_name": "示例同事", "feishu_user_id": "ou_member"}
        if os.environ["MYANC_SPIKE_SEED"] == "customer-roster-ambiguous":
            config["allowed_actors"]["sender-1"]["display_name"] = "示例同事"
    with (
        mock.patch('myanc_crm.banquet.Store', side_effect=PersistentSalesStore)
        if os.environ.get('MYANC_SPIKE_BANQUET') == '1' else nullcontext(),
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
