import unittest
from unittest import mock

from myanc_crm import banquet_context, handoff_notifications
import test_handoffs as fixture


class BanquetContextTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture.HandoffJourneyTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        self.f.decide(self.f.proposal())

    def read(self, principal=fixture.PRINCIPAL, private=True):
        return banquet_context.read({'banquet_id': self.f.business}, self.f.backend, self.f.ledger,
                                    self.f.config, principal, private=private)

    def test_context_is_read_only_and_bounded_with_per_source_evidence(self):
        for i in range(12):
            row = dict(record_id='followup' + str(i), banquet_id=self.f.business,
                       occurred_at=f'2026-10-01T{i:02d}:00:00+08:00', content='虚构跟进')
            self.f.store.rows[('followups', row['record_id'])] = row
        writes = len(self.f.store.writes)
        for principal in (fixture.PRINCIPAL, self.f.recipient):
            value = self.read(principal)
            self.assertEqual('found', value['status'], value)
            self.assertEqual('private', value['conversation_scope'])
            self.assertEqual(10, len(value['history']))
            self.assertTrue(value['history_has_more'])
            self.assertFalse(value['materials_read'])
            self.assertNotIn('files', value['handoff'])
            self.assertEqual('current', value['publication_basis']['status'])
            self.assertEqual({'banquet', 'customer', 'followups', 'handoff', 'notifications'}, set(value['sources']))
            self.assertTrue(all(s['read_at'] for s in value['sources'].values()))
        self.assertEqual(writes, len(self.f.store.writes))

    def test_group_and_nonparty_do_not_disclose_handoff_metadata(self):
        value = self.read(private=False)
        self.assertEqual('shared', value['conversation_scope'])
        self.assertEqual('private_required', value['sources']['handoff']['status'])
        for key in ('handoff', 'notifications', 'publication_basis', 'is_recipient'):
            self.assertNotIn(key, value)
        other = {**fixture.PRINCIPAL, 'user_id': 'other'}
        self.f.config['allowed_actors']['other'] = {'feishu_user_id': 'ou_other', 'display_name': '虚构其他人'}
        value = self.read(other)
        self.assertEqual('private', value['conversation_scope'])
        self.assertEqual('denied', value['sources']['handoff']['status'])
        self.assertNotIn('handoff', value)

    def test_request_cannot_claim_a_private_conversation(self):
        with self.assertRaises(ValueError):
            banquet_context.read({'banquet_id': self.f.business, 'conversation_scope': 'private'},
                                 self.f.backend, self.f.ledger, self.f.config, fixture.PRINCIPAL,
                                 private=False)

    def test_optional_source_failure_is_partial_not_empty(self):
        original = self.f.store.list
        def read(kind):
            if kind == 'followups':
                raise TimeoutError('fixture unavailable')
            return original(kind)
        with mock.patch.object(self.f.store, 'list', side_effect=read):
            value = self.read()
        self.assertEqual('partial', value['status'])
        self.assertEqual('unavailable', value['sources']['followups']['status'])
        self.assertIsNone(value['history_has_more'])
        self.assertNotIn('history', value)
        with mock.patch.object(self.f.backend, 'get_customer', side_effect=TimeoutError):
            value = self.read()
        self.assertEqual('partial', value['status'])
        self.assertEqual('unavailable', value['publication_basis']['status'])
        self.assertNotIn('customer', value)

    def test_banquet_failure_denies_entire_context_and_stale_material_is_explicit(self):
        self.f.store.rows[('banquets', self.f.business)]['estimated_tables'] = 23
        value = self.read()
        self.assertEqual('publication_basis_stale', value['material_block_reason'])
        with mock.patch.object(self.f.store, 'get', return_value=None):
            value = self.read()
        self.assertEqual('blocked', value['status'])
        self.assertNotIn('customer', value)

    def test_notification_failure_preserves_readable_handoff_and_empty_is_explicit(self):
        with mock.patch.object(handoff_notifications, 'summary', side_effect=TimeoutError):
            value = self.read()
        self.assertEqual('partial', value['status'])
        self.assertEqual('read', value['sources']['handoff']['status'])
        self.assertEqual('unavailable', value['sources']['notifications']['status'])
        self.assertIn('notifications', value['missing'])
        self.assertNotIn('notifications', value)
        self.assertIn('handoff', value)
        self.f.store.rows = {k: v for k, v in self.f.store.rows.items() if k[0] != 'handoffs'}
        value = self.read()
        self.assertEqual('empty', value['sources']['handoff']['status'])
        self.assertEqual('not_applicable', value['sources']['notifications']['status'])

    def test_optional_schema_failure_does_not_hide_the_banquet(self):
        def schema(kinds=None):
            if kinds == ('followups',):
                raise ValueError('fixture followup schema changed')
            return self.f.store.schema
        with mock.patch.object(self.f.store, 'read_schema', side_effect=schema):
            value = self.read()
        self.assertEqual('partial', value['status'])
        self.assertEqual('read', value['sources']['banquet']['status'])
        self.assertEqual('unavailable', value['sources']['followups']['status'])
        self.assertEqual('read', value['sources']['handoff']['status'])
