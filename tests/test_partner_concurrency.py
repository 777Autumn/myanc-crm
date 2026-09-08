"""Two operators through the real host protocol; only Feishu is a fixture."""

import copy
import multiprocessing
import os
import sqlite3
import time
import unittest
from contextlib import closing
from datetime import datetime, timedelta
import threading

from myanc_crm import cli, core, write_locks

from test_customer_journey import CustomerBackend
import test_host_tools as host_tools
from test_host_tools import CONFIG, PRINCIPAL, SECRET, TOKEN


class SharedBackend(CustomerBackend):
    def __init__(self, rows, actions, entered, release):
        super().__init__()
        self.customers, self.actions = rows, actions
        self.entered, self.release = entered, release

    def update_customer_profile(self, record_id, fields):
        self.entered.set()
        if not self.release.wait(5):
            raise RuntimeError("fixture write timed out")
        row = dict(self.customers[record_id])
        row.update(copy.deepcopy(fields))
        self.customers[record_id] = row
        self.actions.append(record_id)

    def create_customer(self, fields):
        self.entered.set()
        if not self.release.wait(5):
            raise RuntimeError("fixture create timed out")
        return super().create_customer(fields)


def execute_worker(path, approval, rows, actions, entered, release, results):
    backend = SharedBackend(rows, actions, entered, release)
    core.READBACK_TIMEOUT_SECONDS = 0
    with closing(core.Ledger(path)) as ledger:
        results.put(core.execute_claimed_approval(approval, backend, ledger, CONFIG))


def hold_targets(path, change_id, entered, release):
    with closing(core.Ledger(path)) as ledger:
        with ledger.customer_write(ledger.get(change_id)):
            entered.set()
            release.wait(20)


def hold_locks(directory, scopes, entered, release):
    with write_locks.acquire(directory, scopes):
        entered.set()
        release.wait(5)


class PartnerConcurrencyTests(unittest.TestCase):
    def call(self, command, request, **kwargs):
        principal = kwargs.get("principal") or request.get("principal") or PRINCIPAL
        kwargs["env"] = {cli.HOST_SECRET_ENV: SECRET,
                         cli.ACTION_TOKEN_ENV: TOKEN + ":" + principal["session_key"]}
        return host_tools.HostToolTests.call(self, command, request, **kwargs)

    def setUp(self):
        host_tools.HostToolTests.setUp(self)
        self.backend = CustomerBackend()

    def approve_update(self, stage, sender="sender-1"):
        return self.approve_request("stage-customer-update", {
            "customer_query": "C-001", "changes": {"stage": stage},
        }, sender)

    def approve_request(self, command, request, sender="sender-1"):
        approval = self.prepare_request(command, request, sender)
        _, result = self.call("", approval, host_command="host-execute")
        return result

    def prepare_request(self, command, request, sender="sender-1"):
        principal = {**PRINCIPAL, "user_id": sender,
                     "session_key": f"mock:group-1:{sender}"}
        _, preview = self.call(command, request, principal=principal)
        self.assertEqual("pending", preview["status"], preview)
        approval = {"approval_id": preview["approval_id"], "principal": {
            **principal, "message_id": f"card-{preview['approval_id']}",
        }}
        _, bound = self.call("", approval, host_command="host-bind-card")
        self.assertEqual("bound", bound["status"], bound)
        _, claimed = self.call("", {**approval, "decision": "approve"},
                               host_command="host-claim")
        self.assertTrue(claimed.get("execute"), claimed)
        return approval

    def test_unknown_write_blocks_another_operator_on_same_customer_after_cli_exit(self):
        self.backend.profile_mode = "raise"
        first = self.approve_update("已联系")
        self.assertEqual("verification_unknown", first["status"], first)
        self.backend.profile_mode = "normal"
        second = self.approve_update("暂缓", "sender-2")
        self.assertEqual("crm_write_unresolved", second["code"], second)
        self.assertEqual("新线索", self.backend.customers["rec-1"]["stage"])
        self.assertEqual(["update_customer_profile"], self.backend.actions)

    def test_unknown_followup_also_blocks_new_profile_without_repeating_history(self):
        self.backend.hide_followup_readback = True
        first = self.approve_request("stage", {
            "customer_query": "C-001", "occurred_at": "2026-09-08T10:00:00+08:00",
            "content": "虚构并发验收",
        })
        self.assertEqual("verification_unknown", first["status"], first)
        second = self.approve_update("已联系", "sender-2")
        self.assertEqual("crm_write_unresolved", second["code"], second)
        self.assertEqual(["create_followup"], self.backend.actions)
        self.assertEqual(1, len(self.backend.followups))

    def test_second_preapproved_same_name_create_rechecks_candidates(self):
        approvals = []
        for sender in ("sender-1", "sender-2"):
            principal = {**PRINCIPAL, "user_id": sender, "session_key": f"mock:group-1:{sender}"}
            _, person = self.call("assignee", {"query": "member@example.com"}, principal=principal)
            approvals.append(self.prepare_request("stage-customer-create", {
                "name": "同名虚构客户", "contact": "示例甲", "stage": "新线索", "owner_ref": person["owner_ref"],
            }, sender))
        _, first = self.call("", approvals[0], host_command="host-execute")
        _, second = self.call("", approvals[1], host_command="host-execute")
        self.assertEqual("verified", first["status"], first)
        self.assertEqual("replan_required", second["status"], second)
        self.assertEqual(["create_customer"], self.backend.actions)

    @unittest.skipUnless(os.name == "posix", "production cross-process locks tested on Linux")
    def test_same_name_creation_waits_for_other_process_then_rechecks(self):
        approvals = []
        for sender in ("sender-1", "sender-2"):
            principal = {**PRINCIPAL, "user_id": sender, "session_key": f"mock:group-1:{sender}"}
            _, person = self.call("assignee", {"query": "member@example.com"}, principal=principal)
            approvals.append(self.prepare_request("stage-customer-create", {
                "name": "并发同名虚构客户", "contact": "示例甲", "stage": "新线索", "owner_ref": person["owner_ref"],
            }, sender))
        ctx = multiprocessing.get_context("spawn")
        with ctx.Manager() as manager:
            rows, actions = manager.dict(self.backend.customers), manager.list()
            entered, release, results = ctx.Event(), ctx.Event(), ctx.Queue()
            worker = ctx.Process(target=execute_worker, args=(str(self.path), approvals[0],
                rows, actions, entered, release, results))
            worker.start()
            try:
                self.assertTrue(entered.wait(3))
                timer = threading.Timer(0.3, release.set)
                timer.start()
                self.addCleanup(timer.join)
                started = time.monotonic()
                with closing(core.Ledger(self.path)) as ledger:
                    second = core.execute_claimed_approval(approvals[1],
                        SharedBackend(rows, actions, ctx.Event(), release), ledger, CONFIG)
                self.assertGreaterEqual(time.monotonic() - started, 0.2)
                self.assertEqual("verified", results.get(timeout=5)["status"])
                self.assertEqual("replan_required", second["status"], second)
                self.assertEqual(["create_customer"], list(actions))
                self.assertEqual(1, sum(row["name"] == "并发同名虚构客户" for row in rows.values()))
            finally:
                release.set()
                worker.join(5)
                if worker.is_alive():
                    worker.terminate()
                    worker.join()
                results.close()

    @unittest.skipUnless(os.name == "posix", "production lock expiry tested on Linux")
    def test_expired_while_waiting_does_not_write_or_leave_own_fence(self):
        approval = self.prepare_request("stage-customer-update", {
            "customer_query": "C-001", "changes": {"stage": "已联系"},
        })
        with closing(core.Ledger(self.path)) as ledger:
            staged = ledger.get(ledger.get_approval(approval["approval_id"])["change_id"])
        directory = self.path.with_name(self.path.name + ".locks")
        directory.mkdir(mode=0o700)
        ctx = multiprocessing.get_context("spawn")
        entered, release = ctx.Event(), ctx.Event()
        worker = ctx.Process(target=hold_locks, args=(directory, core._write_scopes(staged), entered, release))
        worker.start()
        try:
            self.assertTrue(entered.wait(3))
            timer = threading.Timer(0.3, release.set)
            timer.start()
            self.addCleanup(timer.join)
            before_expiry = datetime.fromisoformat(staged["expires_at"].replace("Z", "+00:00")) - timedelta(seconds=0.15)
            with closing(core.Ledger(self.path)) as ledger:
                result = core.execute_claimed_approval(approval, self.backend, ledger, CONFIG, now=before_expiry)
                self.assertEqual("expired", result["code"], result)
                self.assertEqual("expired", ledger.get(staged["change_id"])["state"])
                self.assertEqual(0, ledger._db.execute("SELECT count(*) FROM write_fences").fetchone()[0])
            self.assertEqual([], self.backend.actions)
        finally:
            release.set()
            worker.join(5)
            if worker.is_alive():
                worker.terminate()
                worker.join()

    @unittest.skipUnless(os.name == "posix", "Linux lock file boundary")
    def test_unsafe_lock_entries_fail_closed_without_writes(self):
        approval = self.prepare_request("stage-customer-update", {
            "customer_query": "C-001", "changes": {"stage": "已联系"},
        })
        with closing(core.Ledger(self.path)) as ledger:
            staged = ledger.get(ledger.get_approval(approval["approval_id"])["change_id"])
            directory = self.path.with_name(self.path.name + ".locks")
            directory.mkdir(mode=0o700)
            entry = directory / (core._write_scopes(staged)[0] + ".lock")
            target = directory / "fixture-target"
            target.touch(mode=0o600)
            for kind in ("symlink", "hardlink", "permissions"):
                with self.subTest(kind=kind):
                    if kind == "symlink":
                        entry.symlink_to(target)
                    elif kind == "hardlink":
                        os.link(target, entry)
                    else:
                        entry.touch(mode=0o644)
                        entry.chmod(0o644)
                    try:
                        with self.assertRaises(write_locks.WriteBlocked) as caught:
                            with ledger.customer_write(staged):
                                self.fail("unsafe lock was accepted")
                        self.assertEqual("crm_write_lock_unavailable", caught.exception.code)
                        self.assertEqual(0, ledger._db.execute("SELECT count(*) FROM write_fences").fetchone()[0])
                    finally:
                        entry.unlink()
            self.assertEqual([], self.backend.actions)

    @unittest.skipUnless(os.name == "posix", "production lock deadline tested on Linux")
    def test_ten_second_busy_deadline_makes_no_write_and_keeps_other_fence(self):
        approvals = [self.prepare_request("stage-customer-update", {
            "customer_query": "C-001", "changes": {"stage": "已联系"},
        }, sender) for sender in ("sender-1", "sender-2")]
        with closing(core.Ledger(self.path)) as ledger:
            change_id = ledger.get_approval(approvals[0]["approval_id"])["change_id"]
        ctx = multiprocessing.get_context("spawn")
        entered, release = ctx.Event(), ctx.Event()
        worker = ctx.Process(target=hold_targets, args=(str(self.path), change_id, entered, release))
        worker.start()
        try:
            self.assertTrue(entered.wait(3))
            started = time.monotonic()
            _, result = self.call("", approvals[1], host_command="host-execute")
            elapsed = time.monotonic() - started
            self.assertEqual("crm_write_busy", result["code"], result)
            self.assertGreaterEqual(elapsed, 9.8)
            self.assertLess(elapsed, 13)
            self.assertEqual([], self.backend.actions)
            with closing(core.Ledger(self.path)) as ledger:
                self.assertGreater(ledger._db.execute("SELECT count(*) FROM write_fences WHERE change_id=?", (change_id,)).fetchone()[0], 0)
        finally:
            release.set()
            worker.join(5)
            if worker.is_alive():
                worker.terminate()
                worker.join()

    def test_receipt_commit_failure_keeps_fences_and_no_terminal_receipt(self):
        approval = self.prepare_request("stage-customer-update", {
            "customer_query": "C-001", "changes": {"stage": "已联系"},
        })
        with closing(core.Ledger(self.path)) as ledger:
            ledger._db.execute("CREATE TRIGGER receipt_failure BEFORE DELETE ON write_fences "
                               "BEGIN SELECT RAISE(ABORT, 'fixture commit failure'); END")
            with self.assertRaises(sqlite3.IntegrityError):
                core.execute_claimed_approval(approval, self.backend, ledger, CONFIG)
            saved = ledger.get_approval(approval["approval_id"])
            self.assertEqual("executing", saved["state"])
            self.assertIsNone(saved["receipt"])
            self.assertEqual("applying", ledger.get(saved["change_id"])["state"])
            self.assertGreater(ledger._db.execute("SELECT count(*) FROM write_fences").fetchone()[0], 0)
        blocked = self.approve_update("暂缓", "sender-2")
        self.assertEqual("crm_write_unresolved", blocked["code"], blocked)
        self.assertEqual(["update_customer_profile"], self.backend.actions)

    def test_rename_unknown_protects_both_names_but_not_unrelated_customer(self):
        for identifier, number, name in [("rec-2", "C-002", "新名称"), ("rec-3", "C-003", "独立客户")]:
            self.backend.customers[identifier] = {**self.backend.customers["rec-1"],
                "record_id": identifier, "customer_number": number, "name": name}
        self.backend.profile_mode = "raise"
        first = self.approve_request("stage-customer-update", {
            "customer_query": "C-001", "changes": {"name": "新名称"}, "allow_same_name": True,
        })
        self.assertEqual("verification_unknown", first["status"])
        self.backend.profile_mode = "normal"
        second = self.approve_request("stage-customer-update", {
            "customer_query": "C-002", "changes": {"stage": "已联系"},
        }, "sender-2")
        self.assertEqual("crm_write_unresolved", second["code"], second)
        third = self.approve_request("stage-customer-update", {
            "customer_query": "C-003", "changes": {"stage": "已联系"},
        }, "sender-2")
        self.assertEqual("verified", third["status"], third)
        self.assertEqual(2, len(self.backend.actions))

    @unittest.skipUnless(os.name == "posix", "production locks are tested on Linux")
    def test_same_customer_waits_then_rechecks_and_crash_stays_blocked(self):
        for crash in (False, True):
            with self.subTest(crash=crash):
                self.setUp()
                approvals = [self.prepare_request("stage-customer-update", {
                    "customer_query": "C-001", "changes": {"stage": "已联系"},
                }, sender) for sender in ("sender-1", "sender-2")]
                ctx = multiprocessing.get_context("spawn")
                with ctx.Manager() as manager:
                    rows, actions = manager.dict(self.backend.customers), manager.list()
                    entered, release, results = ctx.Event(), ctx.Event(), ctx.Queue()
                    worker = ctx.Process(target=execute_worker, args=(str(self.path), approvals[0],
                        rows, actions, entered, release, results))
                    worker.start()
                    try:
                        self.assertTrue(entered.wait(3))
                        if crash:
                            worker.terminate()
                            worker.join(3)
                        else:
                            # The second process can claim approval, but cannot write while this lock is held.
                            timer = threading.Timer(0.3, release.set)
                            timer.start()
                            self.addCleanup(timer.join)
                        backend = SharedBackend(rows, actions, ctx.Event(), release)
                        started = time.monotonic()
                        with closing(core.Ledger(self.path)) as ledger:
                            second = core.execute_claimed_approval(approvals[1], backend, ledger, CONFIG)
                        self.assertEqual("crm_write_unresolved" if crash else "customer_changed", second["code"], second)
                        self.assertEqual(0 if crash else 1, len(actions))
                        if not crash:
                            self.assertGreaterEqual(time.monotonic() - started, 0.2)
                    finally:
                        if not crash:
                            release.set()
                        worker.join(5)
                        if worker.is_alive():
                            worker.terminate()
                            worker.join()
                        results.close()

    @unittest.skipUnless(os.name == "posix", "production cross-process lock is tested on Linux")
    def test_different_customers_write_in_parallel_and_keep_both_verified_results(self):
        other = copy.deepcopy(self.backend.customers["rec-1"])
        other.update(record_id="rec-2", customer_number="C-002", name="另一家虚构公司")
        self.backend.customers["rec-2"] = other
        approvals = [self.prepare_request("stage-customer-update", {
            "customer_query": number, "changes": {"stage": "已联系"},
        }, sender) for number, sender in [("C-001", "sender-1"), ("C-002", "sender-2")]]
        ctx = multiprocessing.get_context("spawn")
        with ctx.Manager() as manager:
            rows = manager.dict(self.backend.customers)
            actions = manager.list()
            release = ctx.Event()
            entered = [ctx.Event(), ctx.Event()]
            results = ctx.Queue()
            workers = [ctx.Process(target=execute_worker, args=(
                str(self.path), approval, rows, actions, entered[index], release, results,
            )) for index, approval in enumerate(approvals)]
            try:
                workers[0].start()
                self.assertTrue(entered[0].wait(3), "first customer never reached Feishu")
                workers[1].start()
                self.assertTrue(entered[1].wait(3), "independent customer was unnecessarily serialized")
                release.set()
                outputs = [results.get(timeout=5), results.get(timeout=5)]
                self.assertEqual(["verified", "verified"], [out["status"] for out in outputs], outputs)
                self.assertCountEqual(["rec-1", "rec-2"], list(actions))
                for row in rows.values():
                    self.assertEqual("已联系", row["stage"])
            finally:
                release.set()
                for worker in workers:
                    if worker.pid is not None:
                        worker.join(5)
                        if worker.is_alive():
                            worker.terminate()
                            worker.join()
                results.close()


if __name__ == "__main__":
    unittest.main()
