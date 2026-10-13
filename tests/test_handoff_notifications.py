"""Durable notices and atomic starts use real SQLite; only Feishu IO is fake."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from myanc_crm import core, handoffs, handoff_notifications as notices
from myanc_crm.connections import Connections
import test_connections as connection_fixture
import test_handoffs as handoff_fixture


class HandoffNotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve() / 'ledger.db'
        self.ledger = core.Ledger(self.path)
        self.f = handoff_fixture.HandoffJourneyTests()
        with mock.patch.object(core, 'Ledger', return_value=self.ledger):
            self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.cf = connection_fixture.ConnectionTests()
        self.cf.setUp()
        self.addCleanup(self.cf.doCleanups)
        self.config = self.f.config
        self.config['allowed_actors']['employee']['connection_profile'] = 'anc-user-employee'
        options = self.cf.config['personal_connections']
        self.config['personal_connections'] = options
        self.recipient = dict(self.f.recipient, user_id='personal-employee', chat_id='personal-employee-chat',
                              project='employee-app', session_key='employee-physical-session')
        fields = ('platform', 'user_id', 'chat_id', 'project')
        options['routes'] = [dict({k: self.recipient[k] for k in fields}, audience='private', member_id='employee',
                                 source_app_id='employee-app', source_tenant_key='fixture-tenant'),
                             dict({k: handoff_fixture.PRINCIPAL[k] for k in fields}, audience='private')]
        options['resource_mode'] = 'shared'
        (Path(options['cli_home_root']) / 'anc-user-employee').mkdir(mode=0o700)
        self.cf.fake.user = 'ou_member'
        self.connections = Connections(self.config, run=self.cf.fake, now=lambda: self.cf.clock)
        self.connections.command('connect', self.recipient)
        self.binding = self.connections.require(self.recipient, self.cf.token)
        self.entry = dict(project='employee-app', source_app_id='employee-app', source_tenant_key='fixture-tenant')

    def publish(self):
        staged = self.f.proposal()
        self.assertEqual('verified', self.f.decide(staged)['status'])
        return staged['change_id']

    def sent(self, event):
        claimed = notices.claim(dict(self.entry, event_id=event), self.f.backend, self.ledger, self.config, self.connections)
        notices.acknowledge(dict(event_id=event, dispatch_id=claimed['dispatch_id'], status='sent', message_id='notice-' + event), self.ledger)
        return dict(event_id=event, principal=dict(self.recipient, message_id='notice-' + event))

    def start(self, request, ledger=None):
        return notices.start(request, self.f.backend, ledger or self.ledger, self.config, self.connections, self.binding)

    def test_verified_receipt_atomically_queues_safe_notice_and_restart_claims_once(self):
        event = self.publish()
        pending = notices.events(self.entry, self.f.backend, self.ledger, self.config, self.connections)['events']
        self.assertEqual(1, len(pending))
        self.assertEqual({'event_id', 'kind', 'banquet_id', 'publication_id', 'version', 'target'}, set(pending[0]))
        self.assertEqual('employee', pending[0]['target']['member_id'])
        self.assertNotIn('files', pending[0])
        self.assertNotIn('materials', pending[0])
        request = self.sent(event)
        ready = self.start(request)
        self.assertEqual('ready', ready['status'])
        self.assertTrue(ready['file_check']['published'])
        self.assertEqual(self.f.files, ready['file_check']['files'])
        started = self.start(dict(request, work_id='work-one', session_id='internal-session-one', handoff_files_verified=True))
        self.assertEqual('started', started['status'])
        reopened = core.Ledger(self.path)
        self.addCleanup(reopened.close)
        replay = self.start(dict(request, work_id='work-two', session_id='internal-session-two', handoff_files_verified=True), reopened)
        self.assertEqual('replayed', replay['status'])
        self.assertEqual(started['start'], replay['start'])
        self.assertEqual('replayed', self.start(request, reopened)['status'])
        self.assertEqual('verified', reopened.get(event)['state'])

    def test_simultaneous_clicks_have_one_start(self):
        request = self.sent(self.publish())
        def click(index):
            ledger = core.Ledger(self.path)
            try:
                return self.start(dict(request, work_id=f'work-{index}', session_id=f'session-{index}', handoff_files_verified=True), ledger)
            finally:
                ledger.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(click, range(2)))
        self.assertEqual(['replayed', 'started'], sorted(r['status'] for r in results))
        self.assertEqual(results[0]['start'], results[1]['start'])

    def test_send_unknown_or_crash_after_claim_is_never_requeued(self):
        event = self.publish()
        request = dict(self.entry, event_id=event)
        claimed = notices.claim(request, self.f.backend, self.ledger, self.config, self.connections)
        reopened = core.Ledger(self.path)
        self.addCleanup(reopened.close)
        self.assertEqual([], notices.events(self.entry, self.f.backend, reopened, self.config, self.connections)['events'])
        self.assertEqual('already_claimed', notices.claim(request, self.f.backend, reopened, self.config, self.connections)['status'])
        receipt = dict(event_id=event, dispatch_id=claimed['dispatch_id'], status='unknown', message_id='')
        self.assertEqual('recorded', notices.acknowledge(receipt, reopened)['status'])
        self.assertTrue(notices.acknowledge(receipt, reopened)['replayed'])
        with self.assertRaises(ValueError):
            notices.acknowledge(dict(receipt, status='sent', message_id='guessed'), reopened)
        with self.assertRaises(ValueError):
            self.start(dict(event_id=event, principal=self.recipient), reopened)
        self.assertEqual('verified', reopened.get(event)['state'])
        outcome = notices.events(dict(self.entry, event_id=event), self.f.backend, reopened, self.config, self.connections)
        self.assertEqual('unknown', outcome['notification_status'])
        self.assertIsNone(outcome['start'])

    def test_unknown_notice_keeps_normal_handoff_recovery_without_resending(self):
        event = self.publish()
        claimed = notices.claim(dict(self.entry, event_id=event), self.f.backend, self.ledger, self.config, self.connections)
        notices.acknowledge(dict(event_id=event, dispatch_id=claimed['dispatch_id'],
                                status='unknown', message_id=''), self.ledger)
        current = self.read()
        self.assertEqual('found', current['status'])
        self.assertEqual('unknown', current['notifications'][0]['notification_status'])
        accepted = self.f.proposal('stage-handoff-accept', self.recipient, version=1)
        self.assertEqual('verified', self.f.decide(accepted, self.recipient)['status'])
        writes = len(self.f.store.writes)
        self.assertEqual('blocked', self.f.proposal('stage-handoff-accept', self.recipient, version=1)['status'])
        self.assertEqual(writes, len(self.f.store.writes))
        outcome = notices.events(dict(self.entry, event_id=event), self.f.backend, self.ledger, self.config, self.connections)
        self.assertEqual('unknown', outcome['notification_status'])
        self.assertIsNone(outcome['start'])
        self.assertEqual([], notices.events(self.entry, self.f.backend, self.ledger, self.config, self.connections)['events'])

    def test_failed_receipt_rolls_back_notification_event(self):
        staged = self.f.proposal()
        self.ledger._db.execute("CREATE TRIGGER notice_failure BEFORE INSERT ON handoff_events "
                               "BEGIN SELECT RAISE(ABORT, 'fixture notification commit failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.f.decide(staged)
        reopened = core.Ledger(self.path)
        self.addCleanup(reopened.close)
        self.assertEqual('applying', reopened.get(staged['change_id'])['state'])
        self.assertEqual(0, reopened._db.execute('SELECT count(*) FROM handoff_events').fetchone()[0])

    def test_claim_requires_file_proof_and_binds_work_generation(self):
        request = self.sent(self.publish())
        with self.assertRaises(ValueError):
            self.start(dict(request, work_id='work', session_id='session'))
        self.assertIsNone(notices._event(self.ledger, request['event_id'])['start_json'])
        self.start(dict(request, work_id='work', session_id='session', handoff_files_verified=True))
        with self.connections.database() as db:
            row = db.execute('SELECT * FROM connection_work WHERE work=?', ('work',)).fetchone()
        self.assertEqual((self.binding['subject'], self.binding['version'], 1),
                         (row['subject'], row['version'], row['requires_connection']))

    def test_wrong_actor_message_version_or_reconnected_generation_cannot_start(self):
        request = self.sent(self.publish())
        for principal in (dict(request['principal'], user_id='other'), dict(request['principal'], message_id='forged')):
            with self.assertRaises(ValueError):
                self.start(dict(request, principal=principal))
        self.connections.command('disconnect', self.recipient)
        with self.assertRaises(ValueError):
            self.start(request)
        self.connections.command('connect', self.recipient)
        self.cf.fake.login_user = 'ou_member'
        self.connections.command('complete', self.recipient)
        self.binding = self.connections.require(self.recipient, self.cf.token + '-new')
        self.publish()
        with self.assertRaises(ValueError):
            self.start(request)

    def test_accept_and_return_events_target_submitter_with_separate_receipts(self):
        event = self.publish()
        self.f.recipient = self.recipient
        returned = self.f.proposal('stage-handoff-return', self.recipient, version=1, reason='请补菜单')
        self.assertEqual('verified', self.f.decide(returned, self.recipient)['status'])
        row = notices._event(self.ledger, returned['change_id'])
        self.assertEqual(('return', event), (row['kind'], row['publication_id']))
        self.assertEqual(handoff_fixture.PRINCIPAL['user_id'], notices._view(row, self.config)['target']['member_id'])
        self.assertEqual('pending', row['notification_status'])
        self.assertIsNone(row['start_json'])
        self.assertEqual('verified', self.ledger.get(event)['state'])

    def test_stale_publication_blocks_notice_claim_start_and_restart_replay(self):
        event = self.publish()
        self.f.store.rows[('banquets', self.f.business)]['estimated_tables'] = 23
        self.assertEqual([], notices.events(self.entry, self.f.backend, self.ledger, self.config, self.connections)['events'])
        with self.assertRaises(ValueError):
            self.sent(event)
        self.f.store.rows[('banquets', self.f.business)]['estimated_tables'] = 20
        request = self.sent(event)
        self.f.store.rows[('banquets', self.f.business)]['estimated_tables'] = 23
        with self.assertRaises(ValueError):
            self.start(request)
        self.f.store.rows[('banquets', self.f.business)]['estimated_tables'] = 20
        self.start(dict(request, work_id='work', session_id='session', handoff_files_verified=True))
        self.f.store.rows[('banquets', self.f.business)]['estimated_tables'] = 23
        reopened = core.Ledger(self.path)
        self.addCleanup(reopened.close)
        with self.assertRaises(ValueError):
            self.start(request, reopened)

    def test_stale_business_does_not_suppress_verified_accept_or_return_result_notice(self):
        self.publish()
        accepted = self.f.proposal('stage-handoff-accept', self.recipient, version=1)
        self.f.decide(accepted, self.recipient)
        self.f.store.rows[('banquets', self.f.business)]['estimated_tables'] = 23
        target = notices._view(notices._event(self.ledger, accepted['change_id']), self.config)['target']
        entry = {key: target[key] for key in ('project', 'source_app_id', 'source_tenant_key')}
        self.assertEqual([accepted['change_id']], [r['event_id'] for r in
            notices.events(entry, self.f.backend, self.ledger, self.config, self.connections)['events']])
        self.assertEqual('claimed', notices.claim(dict(entry, event_id=accepted['change_id']),
            self.f.backend, self.ledger, self.config, self.connections)['status'])
        self.f.files[0].update(sha256='b' * 64, version=2)
        self.publish()
        self.f.store.rows[('banquets', self.f.business)]['estimated_tables'] = 24
        returned = self.f.proposal('stage-handoff-return', self.recipient, version=2, reason='请修订')
        self.f.decide(returned, self.recipient)
        self.assertEqual('claimed', notices.claim(dict(entry, event_id=returned['change_id']),
            self.f.backend, self.ledger, self.config, self.connections)['status'])

    def test_pending_approval_blocks_preflight_and_claim(self):
        request = self.sent(self.publish())
        self.f.recipient = self.recipient
        staged = self.f.proposal('stage-handoff-accept', self.recipient, version=1)
        begun = core.begin_approval(dict(change_id=staged['change_id'], principal=self.recipient), self.f.backend,
                                    self.ledger, self.config, handoff_fixture.TOKEN + self.recipient['user_id'], handoff_fixture.NOW)
        self.assertEqual('pending', begun['status'])
        with self.ledger._db:
            self.ledger._db.execute('UPDATE approvals SET expires_at=? WHERE approval_id=?',
                                    (core._iso(core._now(None) + timedelta(minutes=5)), begun['approval_id']))
        self.assertEqual('busy', self.start(request)['status'])
        self.assertEqual('busy', self.start(dict(request, work_id='new', session_id='new'))['status'])
        self.assertIsNone(notices._event(self.ledger, request['event_id'])['start_json'])

    def read(self, principal=None):
        return handoffs.read({'banquet_id': self.f.business}, self.f.backend, self.ledger,
                             self.config, principal or self.recipient)

    def test_read_keeps_unknown_notice_separate_from_verified_publication(self):
        event = self.publish()
        before = self.read()
        self.assertEqual('pending', before['notifications'][0]['notification_status'])
        claimed = notices.claim(dict(self.entry, event_id=event), self.f.backend, self.ledger, self.config, self.connections)
        self.assertEqual('dispatching', self.read()['notifications'][0]['notification_status'])
        notices.acknowledge(dict(event_id=event, dispatch_id=claimed['dispatch_id'], status='unknown', message_id=''), self.ledger)
        after = self.read(handoff_fixture.PRINCIPAL)
        self.assertEqual(before['handoff'], after['handoff'])
        self.assertEqual('verified', self.ledger.get(event)['state'])
        notification = after['notifications'][0]
        self.assertEqual('unknown', notification['notification_status'])
        self.assertEqual({'status': 'not_recorded', 'message': '尚未记录开始请求'}, notification['start'])
        self.assertIn('未知', notification['notification_message'])
        self.assertNotIn('成功', notification['notification_message'])
        self.assertNotIn('失败', notification['notification_message'])
        self.assertEqual({'kind', 'version', 'notification_status', 'notification_message', 'start'}, set(notification))
        other = dict(self.recipient, user_id='other', chat_id='other', project='other')
        self.config['allowed_actors']['other'] = dict(display_name='同名人员', feishu_user_id='ou_other')
        self.config['personal_connections']['routes'].append(dict({key: other[key] for key in
            ('platform', 'user_id', 'chat_id', 'project')}, audience='private'))
        denied = self.read(other)
        self.assertEqual('blocked', denied['status'])
        self.assertNotIn('notifications', denied)

    def test_read_summarizes_start_and_only_current_verified_decision_events(self):
        for version, command in ((1, 'stage-handoff-return'), (2, 'stage-handoff-accept')):
            event = self.publish()
            request = self.sent(event)
            self.start(dict(request, work_id=f'work-{version}', session_id=f'session-{version}', handoff_files_verified=True))
            summary = self.read()['notifications'][0]
            self.assertEqual('sent', summary['notification_status'])
            self.assertEqual({'status': 'recorded', 'message': '已记录开始请求'}, summary['start'])
            extra = {'reason': '需要补充菜单'} if command.endswith('return') else {}
            staged = self.f.proposal(command, self.recipient, version=version, **extra)
            receipt = self.f.decide(staged, self.recipient)
            self.assertEqual('verified', receipt['status'])
            self.assertIn('通知单独记录', receipt['notification_note'])
            current = self.read()['notifications']
            self.assertEqual(['submit', command.removeprefix('stage-handoff-')], [item['kind'] for item in current])
            self.assertEqual([version, version], [item['version'] for item in current])
            self.assertEqual(['sent', 'pending'], [item['notification_status'] for item in current])
            self.assertEqual({'kind', 'version', 'notification_status', 'notification_message'}, set(current[1]))


if __name__ == '__main__':
    unittest.main()
