import multiprocessing
import os
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from myanc_crm import core, handoffs
from test_core import NOW, PRINCIPAL, TOKEN
import test_banquet as sales


class HandoffJourneyTests(unittest.TestCase):
    approve = sales.BanquetJourneyTests.approve
    create = sales.BanquetJourneyTests.create
    stage = sales.BanquetJourneyTests.stage

    def setUp(self):
        sales.BanquetJourneyTests.setUp(self)
        self.recipient = {**PRINCIPAL, 'user_id': 'employee', 'chat_id': 'employee-chat',
                          'session_key': 'employee-session'}
        self.config['allowed_actors']['employee'] = {'display_name': '示例同事', 'feishu_user_id': 'ou_member'}
        self.binding = {'subject': 'owner', 'profile': 'fixed-profile', 'version': 1}
        self.current_version = 1
        def check(binding):
            if binding['version'] != self.current_version:
                raise ValueError('old connection')
        self.backend.runner = SimpleNamespace(binding=self.binding, connections=SimpleNamespace(check_version=check))
        self.business = self.approve(self.create())['banquet']['record_id']
        self.store.rows[('banquets', self.business)]['stage'] = '已签单'
        self.files = [{'delivery_id': 'delivery1', 'name': '虚构交接.docx', 'sha256': 'a' * 64,
                       'version': 1, 'message_receipt': 'file-receipt'}]

    def proposal(self, command='stage-handoff-submit', principal=PRINCIPAL, now=NOW, **fields):
        request = {'banquet_id': self.business, **fields}
        if command == 'stage-handoff-submit':
            request = {'recipient_ref': self.owner, 'delivery_ids': ['delivery1'], 'missing': '菜单待确认', **request}
        return handoffs.stage(command, request, self.backend, self.ledger, self.config, TOKEN + principal['user_id'],
            principal, context={'work_id': 'work1', 'files': self.files}, personal_backend=self.backend, now=now)

    def decide(self, staged, principal=PRINCIPAL, files_verified=True, now=NOW):
        self.assertEqual('staged', staged['status'], staged)
        result = core.begin_approval({'change_id': staged['change_id'], 'principal': principal},
            self.backend, self.ledger, self.config, TOKEN + principal['user_id'], NOW)
        self.assertEqual('pending', result['status'], result)
        p = {**principal, 'message_id': 'handoff-card-' + staged['change_id']}
        bound = core.bind_approval_card({'approval_id': result['approval_id'], 'principal': p}, self.ledger, self.config)
        self.assertEqual('bound', bound['status'], bound)
        claim = core.claim_approval_decision({'approval_id': result['approval_id'], 'decision': 'approve', 'principal': p},
            self.ledger, self.config, now, backend=self.backend)
        self.assertTrue(claim['execute'], claim)
        self.assertIn('file_check', claim)
        return core.execute_claimed_approval({'approval_id': result['approval_id'], 'principal': p},
            self.backend, self.ledger, self.config, now, personal_backend=self.backend,
            handoff_files_verified=files_verified)

    def test_delayed_approval_records_execution_time_and_preserves_publication(self):
        steps = [('stage-handoff-submit', PRINCIPAL, {}),
                 ('stage-handoff-return', self.recipient, {'version': 1, 'reason': '补菜单'}),
                 ('stage-handoff-submit', PRINCIPAL, {'missing': '菜单待确认'}),
                 ('stage-handoff-accept', self.recipient, {'version': 2})]
        for index, (command, principal, fields) in enumerate(steps):
            staged_at = NOW + timedelta(minutes=index * 2)
            executed_at = staged_at + timedelta(minutes=1)
            staged = self.proposal(command, principal, now=staged_at, **fields)
            receipt = self.decide(staged, principal, now=executed_at)
            self.assertEqual('verified', receipt['status'])
            row = handoffs.latest(self.store, self.business)
            key = 'submitted_at' if command == 'stage-handoff-submit' else 'acknowledged_at'
            self.assertEqual(core._iso(executed_at), row[key])
            handoffs.publication(self.ledger, row)
            writes = len(self.store.writes)
            replay = handoffs.apply(self.ledger.get(staged['change_id']), self.backend, self.ledger,
                                    executed_at + timedelta(seconds=30), personal_backend=self.backend,
                                    files_verified=True)
            self.assertTrue(replay['replayed'])
            self.assertEqual(writes, len(self.store.writes))
            changed = {**row, key: core._iso(staged_at)}
            with self.assertRaises(ValueError):
                handoffs.publication(self.ledger, changed)

    def test_legacy_publications_keep_their_original_timestamp_evidence(self):
        submitted = self.proposal()
        self.decide(submitted)
        accepted = self.proposal('stage-handoff-accept', self.recipient, version=1)
        self.decide(accepted, self.recipient)
        row = handoffs.latest(self.store, self.business)
        legacy = {}
        for staged, key in ((submitted, 'submitted_at'), (accepted, 'acknowledged_at')):
            record = self.ledger.get(staged['change_id'])
            record['handoff_patch'][key] = row[key]
            record['receipt'].pop('executed_at')
            legacy[record['change_id']] = record
        with mock.patch.object(self.ledger, 'get', side_effect=legacy.get):
            self.assertEqual(submitted['change_id'], handoffs.publication(self.ledger, row)['change_id'])
            with self.assertRaises(ValueError):
                handoffs.publication(self.ledger, {**row, 'acknowledged_at': core._iso(NOW + timedelta(minutes=1))})

    def test_submit_return_revise_and_named_recipient_accepts_current_version(self):
        first = self.proposal()
        self.assertEqual('verified', self.decide(first)['status'])
        original = handoffs.latest(self.store, self.business)
        self.assertEqual('待接手', original['status'])
        wrong = self.proposal('stage-handoff-accept', version=1)
        self.assertEqual('blocked', wrong['status'])
        returned = self.proposal('stage-handoff-return', self.recipient, version=1, reason='请补菜单')
        self.assertEqual('verified', self.decide(returned, self.recipient)['status'])
        second = self.proposal(missing='菜单已补充，场地细节待确认')
        self.assertEqual('verified', self.decide(second)['status'])
        self.assertEqual('已退回', self.store.rows[('handoffs', original['record_id'])]['status'])
        self.assertEqual('blocked', self.proposal('stage-handoff-accept', self.recipient, version=1)['status'])
        accepted = self.proposal('stage-handoff-accept', self.recipient, version=2)
        self.assertEqual('verified', self.decide(accepted, self.recipient)['status'])
        self.assertEqual('已接手', handoffs.latest(self.store, self.business)['status'])
        self.assertEqual('blocked', self.proposal('stage-handoff-accept', self.recipient, version=2)['status'])

    def test_changed_material_does_not_authorize_another_file(self):
        first = self.proposal()
        self.assertEqual('verified', self.decide(first)['status'])
        row = handoffs.latest(self.store, self.business)
        pub = f"bh_{first['change_id']}_0"
        authorized = handoffs.authorize_file(pub, self.backend, self.ledger, self.config, self.recipient)
        self.assertEqual('a' * 64, authorized['source']['sha256'])
        self.store.rows[('handoffs', row['record_id'])]['materials'] = 'forged material'
        with self.assertRaises(ValueError):
            handoffs.authorize_file(pub, self.backend, self.ledger, self.config, self.recipient)
        self.assertEqual('blocked', self.proposal('stage-handoff-accept', self.recipient, version=1)['status'])

    def test_reader_role_uses_host_mapping_not_source_app_id_or_display_name(self):
        self.decide(self.proposal())
        request = {'banquet_id': self.business}
        self.assertNotEqual(self.recipient['user_id'], 'ou_member')
        for principal, expected in ((self.recipient, True), (PRINCIPAL, False)):
            value = handoffs.read(request, self.backend, self.ledger, self.config, principal)
            self.assertIs(value['is_recipient'], expected)
        other = {**self.recipient, 'user_id': 'same-name-other'}
        self.config['allowed_actors']['same-name-other'] = {
            'display_name': '示例同事', 'feishu_user_id': 'ou_other'}
        denied = handoffs.read(request, self.backend, self.ledger, self.config, other)
        self.assertEqual('blocked', denied['status'])
        self.assertNotIn('is_recipient', denied)

    def test_file_failure_and_revocation_do_not_publish_or_acknowledge(self):
        staged = self.proposal()
        self.assertEqual('failed', self.decide(staged, files_verified=False)['status'])
        self.assertIsNone(handoffs.latest(self.store, self.business))
        staged = self.proposal()
        self.current_version = 2
        self.assertEqual('failed', self.decide(staged)['status'])
        self.assertIsNone(handoffs.latest(self.store, self.business))

    def test_lost_write_response_recovers_submit_and_accept_without_rewriting(self):
        write = self.store.write
        def lose_response(*args):
            write(*args)
            raise TimeoutError('fixture: response lost after committing')
        for command, principal, fields in (
                ('stage-handoff-submit', PRINCIPAL, {}),
                ('stage-handoff-accept', self.recipient, {'version': 1})):
            with self.subTest(command=command):
                staged = self.proposal(command, principal, **fields)
                before = len(self.store.writes)
                with mock.patch.object(self.store, 'write', side_effect=lose_response) as attempted:
                    receipt = self.decide(staged, principal)
                self.assertEqual('verified', receipt['status'], receipt)
                attempted.assert_called_once()
                self.assertEqual(before + 1, len(self.store.writes))
                replay = handoffs.apply(self.ledger.get(staged['change_id']), self.backend,
                    self.ledger, NOW, personal_backend=self.backend, files_verified=True)
                self.assertTrue(replay['replayed'])
                self.assertEqual(before + 1, len(self.store.writes))
                handoffs.publication(self.ledger, handoffs.latest(self.store, self.business))

    def persistent_ledger(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'handoff.sqlite3'
        ledger = core.Ledger(path)
        self.ledger._db.backup(ledger._db)
        self.ledger = ledger
        self.addCleanup(ledger.close)
        return path

    def test_unobservable_write_keeps_fence_after_reopen_and_never_replays(self):
        for committed in (False, True):
            with self.subTest(committed=committed):
                self.setUp()
                path = self.persistent_ledger()
                staged = self.proposal()
                write, read = self.store.write, self.store.list
                writing = False
                def lose_response(*args):
                    nonlocal writing
                    writing = True
                    if committed:
                        write(*args)
                    raise TimeoutError('fixture: write outcome unknown')
                def unavailable(kind):
                    if writing:
                        raise TimeoutError('fixture: readback unavailable')
                    return read(kind)
                with mock.patch.object(self.store, 'write', side_effect=lose_response) as attempted, \
                     mock.patch.object(self.store, 'list', side_effect=unavailable), \
                     mock.patch.object(core, 'READBACK_TIMEOUT_SECONDS', 0):
                    receipt = self.decide(staged)
                self.assertEqual('verification_unknown', receipt['status'], receipt)
                attempted.assert_called_once()
                writes = len(self.store.writes)
                reopened = core.Ledger(path)
                self.addCleanup(reopened.close)
                self.ledger = reopened
                replay = handoffs.apply(reopened.get(staged['change_id']), self.backend,
                    reopened, NOW, personal_backend=self.backend, files_verified=True)
                self.assertTrue(replay['replayed'])
                self.assertEqual('verification_unknown', replay['status'])
                self.assertGreater(reopened._db.execute('SELECT count(*) FROM write_fences').fetchone()[0], 0)
                with self.assertRaises(ValueError):
                    handoffs.authorize_file('bh_' + staged['change_id'] + '_0', self.backend,
                                            reopened, self.config, self.recipient)
                blocked = self.decide(self.proposal(missing='故障后另一次提交'))
                self.assertEqual('crm_write_unresolved', blocked['code'], blocked)
                self.assertEqual(writes, len(self.store.writes))

    def test_receipt_commit_failure_preserves_handoff_fence_and_no_publication(self):
        path = self.persistent_ledger()
        staged = self.proposal()
        self.ledger._db.execute("CREATE TRIGGER receipt_failure BEFORE DELETE ON write_fences "
                               "BEGIN SELECT RAISE(ABORT, 'fixture receipt commit failure'); END")
        before = len(self.store.writes)
        with self.assertRaises(sqlite3.IntegrityError):
            self.decide(staged)
        self.assertEqual(before + 1, len(self.store.writes))
        reopened = core.Ledger(path)
        self.addCleanup(reopened.close)
        approval = reopened.get_approval_for_change(staged['change_id'])
        self.assertEqual('executing', approval['state'])
        self.assertIsNone(approval['receipt'])
        self.assertEqual('applying', reopened.get(staged['change_id'])['state'])
        decision = core.claim_approval_decision({'approval_id': approval['approval_id'],
            'decision': 'approve', 'principal': {**PRINCIPAL, 'message_id': approval['card_message_id']}},
            reopened, self.config, NOW + timedelta(seconds=core.APPROVAL_EXECUTION_UNCERTAIN_SECONDS + 1),
            backend=self.backend)
        self.assertFalse(decision['execute'])
        self.assertEqual('execution_result_unknown', decision['code'])
        with self.assertRaises(ValueError):
            handoffs.authorize_file('bh_' + staged['change_id'] + '_0', self.backend,
                                    reopened, self.config, self.recipient)
        self.assertGreater(reopened._db.execute('SELECT count(*) FROM write_fences').fetchone()[0], 0)
        self.assertEqual(before + 1, len(self.store.writes))

    @unittest.skipUnless(hasattr(os, 'fork'), 'real worker exit requires POSIX')
    def test_worker_exit_after_write_blocks_replay_and_following_handoff(self):
        path = self.persistent_ledger()
        staged = self.proposal()
        write = self.store.write
        def exit_after_write(*args):
            write(*args)
            os._exit(77)
        def execute():
            try:
                self.ledger = core.Ledger(path)
                with mock.patch.object(self.store, 'write', side_effect=exit_after_write):
                    self.decide(staged)
            finally:
                os._exit(78)
        worker = multiprocessing.get_context('fork').Process(target=execute)
        worker.start()
        try:
            worker.join(5)
            self.assertEqual(77, worker.exitcode)
        finally:
            if worker.is_alive():
                worker.kill()
                worker.join(5)
            worker.close()
        reopened = core.Ledger(path)
        self.addCleanup(reopened.close)
        self.ledger = reopened
        approval = reopened.get_approval_for_change(staged['change_id'])
        self.assertEqual('executing', approval['state'])
        self.assertIsNone(approval['receipt'])
        self.assertEqual('applying', reopened.get(staged['change_id'])['state'])
        writes = len(self.store.writes)
        replay = core.claim_approval_decision({'approval_id': approval['approval_id'],
            'decision': 'approve', 'principal': {**PRINCIPAL, 'message_id': approval['card_message_id']}},
            reopened, self.config, NOW + timedelta(seconds=core.APPROVAL_EXECUTION_UNCERTAIN_SECONDS + 1),
            backend=self.backend)
        self.assertFalse(replay['execute'])
        self.assertEqual('execution_result_unknown', replay['code'])
        blocked = self.decide(self.proposal(missing='进程退出后新预览'))
        self.assertEqual('crm_write_unresolved', blocked['code'], blocked)
        self.assertEqual(writes, len(self.store.writes))
        with self.assertRaises(ValueError):
            handoffs.authorize_file('bh_' + staged['change_id'] + '_0', self.backend,
                                    reopened, self.config, self.recipient)

    def test_manual_status_edit_cannot_forge_recipient_confirmation(self):
        first = self.proposal()
        self.decide(first)
        row = handoffs.latest(self.store, self.business)
        self.store.rows[('handoffs', row['record_id'])]['status'] = '已接手'
        with self.assertRaises(ValueError):
            handoffs.authorize_file(f"bh_{first['change_id']}_0", self.backend, self.ledger, self.config, self.recipient)

    def test_new_version_invalidates_pending_acceptance_and_old_publication(self):
        first = self.proposal()
        self.decide(first)
        old_accept = self.proposal('stage-handoff-accept', self.recipient, version=1)
        # Different real sessions do not supersede one another's approvals.
        new = self.proposal(missing='更新后的待补项')
        self.decide(new)
        with self.assertRaises(ValueError):
            handoffs.authorize_file(f"bh_{first['change_id']}_0", self.backend, self.ledger, self.config, self.recipient)
        result = self.decide(old_accept, self.recipient)
        self.assertEqual('replan_required', result['status'], result)
