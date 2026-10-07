"""Banquet sales use the real approval ledger; only Feishu IO is simulated."""
import copy
import unittest
from unittest import mock

from myanc_crm import core, banquet
from test_core import CONFIG, NOW, PRINCIPAL, TOKEN
from test_customers import CustomerBackend


class SalesStore:
    def __init__(self):
        self.rows = {}
        self.writes = []
        self.schema = {"banquets": "fixed-schema"}

    def read_schema(self):
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


if __name__ == '__main__':
    unittest.main()
