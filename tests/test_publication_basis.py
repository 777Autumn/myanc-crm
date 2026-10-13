import copy
import unittest

from myanc_crm import publication_basis as basis


class PublicationBasisTests(unittest.TestCase):
    def setUp(self):
        self.business = {key: None for key in basis.BANQUET_FIELDS}
        self.business.update(record_id='recB', name='虚构婚宴', number='YAN-0001', customer_record_id='recC',
                             estimated_tables=20, banquet_date='2026-10-20T00:00:00+08:00')
        self.customer = {key: None for key in basis.CUSTOMER_FIELDS}
        self.customer.update(record_id='recC', customer_number='C-001', name='虚构客户', contact='测试联系人')
        self.origin = dict(change_id='chg_test', banquet_before=copy.deepcopy(self.business),
                           customer_snapshot=copy.deepcopy(self.customer))

    def compare(self):
        return basis.compare(self.origin, self.business, self.customer)

    def test_current_normalizes_existing_dates_and_numbers_but_ignores_followup(self):
        self.business.update(estimated_tables=20.0, banquet_date='2026-10-19T16:00:00Z', next_followup_at='new')
        self.customer.update(last_followup_at='new', next_action='new', updated_at='new')
        self.assertEqual('current', self.compare()['status'])

    def test_each_checked_field_changes_the_basis(self):
        for name, fields in (('business', basis.BANQUET_FIELDS), ('customer', basis.CUSTOMER_FIELDS)):
            for field in fields:
                with self.subTest(source=name, field=field):
                    self.setUp()
                    target = getattr(self, name)
                    target[field] = 23 if field in {'budget', 'estimated_tables'} else (
                        '2026-10-21T00:00:00+08:00' if field == 'banquet_date' else 'changed')
                    if field == 'customer_record_id':
                        self.customer['record_id'] = 'changed'
                    result = self.compare()
                    self.assertEqual('stale', result['status'], result)
                    self.assertIn(field, [d['field'] for d in result['differences']])

    def test_missing_null_empty_and_zero_are_not_conflated(self):
        self.business['budget'] = 0
        self.assertEqual('stale', self.compare()['status'])
        self.business['budget'] = None
        self.customer['email'] = ''
        self.assertEqual('stale', self.compare()['status'])
        del self.origin['customer_snapshot']['email']
        self.assertEqual('unknown', self.compare()['status'])
        self.assertNotIn('email', self.origin['customer_snapshot'])

    def test_missing_or_invalid_current_source_is_unavailable(self):
        del self.customer['phone']
        self.assertEqual('unavailable', self.compare()['status'])
        self.setUp()
        self.business['estimated_tables'] = True
        self.assertEqual('unavailable', self.compare()['status'])
        self.assertEqual('unavailable', basis.compare(self.origin, self.business, None)['status'])

    def test_invalid_or_missing_historical_evidence_is_unknown(self):
        for field, value in (('banquet_before', {}), ('customer_snapshot', None)):
            with self.subTest(field=field):
                self.setUp()
                self.origin[field] = value
                self.assertEqual('unknown', self.compare()['status'])

    def test_legacy_comparison_does_not_mutate_approval_evidence(self):
        original = copy.deepcopy(self.origin)
        self.assertEqual('current', self.compare()['status'])
        self.assertEqual(original, self.origin)
