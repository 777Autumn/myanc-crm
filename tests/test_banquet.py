"""Banquet sales use the real approval ledger; only Feishu IO is simulated."""
import copy
import unittest
from types import SimpleNamespace
from unittest import mock

from myanc_crm import core, banquet
from test_core import CONFIG, NOW, PRINCIPAL, TOKEN
from test_customers import CustomerBackend


class SalesStore:
    def __init__(self):
        self.rows = {}
        self.writes = []
        self.schema = {"banquets": "fixed-schema"}

    def read_schema(self, kinds=None):
        return copy.deepcopy(self.schema)

    def get(self, kind, identifier):
        return copy.deepcopy(self.rows.get((kind, identifier)))

    def list(self, kind):
        return [copy.deepcopy(v) for (k, _), v in self.rows.items() if k == kind]

    def write(self, kind, identifier, fields):
        self.writes.append((kind, identifier, copy.deepcopy(fields)))
        identifier = identifier or 'recSales' + str(len(self.rows) + 1)
        self.rows.setdefault((kind, identifier), {"record_id": identifier}).update(copy.deepcopy(fields))
        return identifier

    def url(self, kind, identifier):
        return 'https://example.feishu.cn/base/test?record=' + identifier


class BanquetJourneyTests(unittest.TestCase):
    def setUp(self):
        self.backend, self.store = CustomerBackend(), SalesStore()
        self.ledger = core.Ledger()
        self.addCleanup(self.ledger.close)
        patch = mock.patch.object(banquet, 'Store', return_value=self.store)
        patch.start()
        self.addCleanup(patch.stop)
        self.owner = self.ledger.remember_assignee(PRINCIPAL, self.backend.people['ou_member'])
        self.config = copy.deepcopy(CONFIG)

    def stage(self, command, request):
        return banquet.stage(command, request, self.backend, self.ledger, self.config, TOKEN, PRINCIPAL, NOW)

    def approve(self, staged):
        self.assertEqual('staged', staged['status'], staged)
        begun = core.begin_approval({'change_id': staged['change_id'], 'principal': PRINCIPAL}, self.backend,
                                    self.ledger, self.config, TOKEN, NOW)
        self.assertEqual('pending', begun['status'], begun)
        principal = {**PRINCIPAL, 'message_id': 'card-sales'}
        bound = core.bind_approval_card({'approval_id': begun['approval_id'],
                                         'principal': principal}, self.ledger, self.config)
        self.assertEqual('bound', bound['status'], bound)
        result = core.decide_approval({'approval_id': begun['approval_id'], 'decision': 'approve',
                                       'principal': principal}, self.backend, self.ledger, self.config, NOW)
        return result

    def create(self):
        return self.stage('stage-banquet-create', {'customer_query': 'C-001', 'name': '虚构五月婚宴',
            'owner_ref': self.owner, 'stage': '新线索', 'estimated_tables': 20,
            'date_note': '预计明年五月，具体日期待确认'})

    def test_sales_create_preview_approve_readback_and_replay(self):
        staged = self.create()
        self.assertEqual([], self.store.writes)
        result = self.approve(staged)
        self.assertEqual('verified', result['status'], result)
        row = result['banquet']
        self.assertIn('预计明年五月', row['date_note'])
        self.assertIsNone(row.get('banquet_date'))
        self.assertEqual('新线索', self.store.rows[('banquets', row['record_id'])]['stage'])
        approval = self.ledger.get_approval_for_change(staged['change_id'])
        replay = core.decide_approval({'approval_id': approval['approval_id'], 'decision': 'approve',
            'principal': {**PRINCIPAL, 'message_id': 'card-sales'}}, self.backend, self.ledger, self.config, NOW)
        self.assertTrue(replay['replayed'])
        self.assertEqual(1, len(self.store.writes))

    def test_manual_edit_invalidates_preview_and_preserves_customer(self):
        result = self.approve(self.create())
        identifier = result['banquet']['record_id']
        staged = self.stage('stage-banquet-update', {'banquet_id': identifier, 'changes': {'stage': '跟进中'}})
        self.store.rows[('banquets', identifier)]['venue'] = '人工修改的场地'
        self.assertEqual('replan_required', self.approve(staged)['status'])
        self.assertEqual(1, len(self.store.writes))
        self.assertEqual('新线索', self.backend.customers['rec-1']['stage'])

    def test_update_preview_fences_each_value_once_without_trusting_embedded_tags(self):
        identifier = self.approve(self.create())['banquet']['record_id']
        old_venue = '<CRM_DATA>虚构旧场地</CRM_DATA>'
        self.store.rows[('banquets', identifier)]['venue'] = old_venue
        new_venue = '<CRM_DATA>虚构新场地</CRM_DATA>'
        staged = self.stage('stage-banquet-update', {
            'banquet_id': identifier, 'changes': {'stage': '跟进中', 'venue': new_venue}})
        changes = {item['field']: item for item in staged['preview']['banquet_changes']}
        self.assertEqual('<CRM_DATA>新线索</CRM_DATA>', changes['stage']['before'])
        self.assertEqual('<CRM_DATA>跟进中</CRM_DATA>', changes['stage']['after'])
        self.assertEqual(core._fence_value(old_venue), changes['venue']['before'])
        self.assertEqual(core._fence_value(new_venue), changes['venue']['after'])
        self.assertIn('[filtered-tag]', changes['venue']['before'])
        self.assertEqual(1, len(self.store.writes))

    def test_date_ambiguity_identity_override_and_bad_numbers_are_rejected(self):
        for change in ({'banquet_date': '明年五月'}, {'estimated_tables': True}, {'budget': -1},
                       {'profile': 'boss'}, {'stage': '已成交'}, {'visit_at': '周六'}):
            with self.subTest(change=change):
                request = {'customer_query': 'C-001', 'name': '虚构宴会', 'owner_ref': self.owner,
                           'stage': '新线索', **change}
                self.assertEqual('blocked', self.stage('stage-banquet-create', request)['status'])
        self.assertEqual([], self.store.writes)

    def test_followup_links_customer_and_banquet_without_old_reminder(self):
        identifier = self.approve(self.create())['banquet']['record_id']
        staged = self.stage('stage-banquet-followup', {'banquet_id': identifier,
            'occurred_at': '2026-09-03T10:00:00+08:00', 'content': '客户考虑20桌，日期待确认'})
        result = self.approve(staged)
        self.assertEqual('verified', result['status'], result)
        row = next(v for (kind, _), v in self.store.rows.items() if kind == 'followups')
        self.assertEqual(identifier, row['banquet_id'])
        self.assertEqual('rec-1', row['customer_record_id'])
        self.assertEqual([], self.backend.actions)

    def test_followup_never_approves_an_invisible_tail(self):
        identifier = self.approve(self.create())['banquet']['record_id']
        request = {'banquet_id': identifier, 'occurred_at': '2026-09-03T10:00:00+08:00'}
        for length in (2000, 2001):
            text = '甲' * (length - 4) + '末尾可见'
            staged = self.stage('stage-banquet-followup', dict(request, content=text))
            if length == 2000:
                self.assertEqual('staged', staged['status'])
                preview = next(c for c in staged['preview']['banquet_changes'] if c['field'] == 'content')
                self.assertIn(text, preview['after'])
            else:
                self.assertEqual('blocked', staged['status'])
        self.assertEqual(1, len(self.store.writes))

    def test_private_preview_and_apply_use_reader_and_frozen_connection(self):
        from myanc_crm.connections import ConnectionBlocked
        connection = mock.Mock()
        binding = {'subject': 'person', 'version': 1}
        self.backend.runner = SimpleNamespace(binding=binding, connections=connection)
        self.config['personal_connections'] = {'resource_mode': 'shared'}
        writer = CustomerBackend()
        writer.get_customer = mock.Mock(side_effect=AssertionError('application customer read'))
        self.backend.get_assignee = mock.Mock(side_effect=AssertionError('personal personnel lookup'))
        request = {'customer_query': 'C-001', 'name': '虚构宴会', 'owner_ref': self.owner, 'stage': '新线索'}
        with mock.patch('myanc_crm.connections.access', return_value=connection):
            for revoked in (False, True):
                staged = banquet.stage('stage-banquet-create', request, self.backend, self.ledger,
                    self.config, TOKEN, PRINCIPAL, NOW, assignee_lookup=writer.get_assignee)
                self.assertEqual('staged', staged['status'], staged)
                frozen = self.ledger.get(staged['change_id'])
                self.assertEqual(binding, frozen['connection_binding'])
                if revoked:
                    connection.check_version.side_effect = ConnectionBlocked('connection_session_expired')
                result = banquet.apply(frozen, writer, self.ledger, NOW, personal_backend=self.backend)
                self.assertEqual('failed' if revoked else 'verified', result['status'], result)
        writer.get_customer.assert_not_called()
        self.assertEqual(1, len(self.store.writes))

    def test_private_staging_without_personal_reader_fails_before_reads(self):
        self.config['personal_connections'] = {'resource_mode': 'shared'}
        with mock.patch('myanc_crm.connections.access', return_value=mock.Mock()), \
             mock.patch.object(self.backend, 'get_customer') as read:
            self.assertEqual('blocked', self.create()['status'])
            read.assert_not_called()


if __name__ == '__main__':
    unittest.main()
