"""Fictional cross-employee records, persisted in the existing test-ledger pattern."""
import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock

from myanc_crm import shared_cases as cases


class SharedCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve() / 'test.sqlite3'
        self.path.touch(mode=0o600)
        cases.initialize(self.path)
        self.principal = dict(platform='mock', user_id='sales', chat_id='test-group',
                              project='sales-group', session_key='mock:test-group:sales', message_id='first')
        self.operations = {**self.principal, 'user_id': 'operations', 'project': 'operations-group',
                           'session_key': 'mock:test-group:operations', 'message_id': 'second'}
        self.private = {**self.principal, 'chat_id': 'private', 'project': 'maintenance',
                        'session_key': 'mock:private:sales'}
        self.context = dict(work_id='fictional-work', source_text='林陈婚宴，客户要求22桌，A套餐。', share_allowed=True)
        fields = ('platform', 'user_id', 'chat_id', 'project')
        self.config = dict(ledger_path=str(self.path.parent / 'production-unused.sqlite3'),
                           allowed_actors={u: dict(display_name=u) for u in ('sales', 'operations')},
                           shared_cases=dict(enabled=True, ledger_path=str(self.path), namespace='mock-banquet',
                                             group_chat_id='test-group', members=[{k: p[k] for k in fields}
                                             for p in (self.principal, self.operations, self.private)]))

    def call(self, command, request, *, principal=None, context=None, config=None):
        return cases.tool(command, request, principal or self.principal,
                          self.context if context is None else context, self.config if config is None else config)

    def change(self, **extra):
        return dict(case_name='林陈婚宴', expected_revision=0, changes=[dict(
            field='桌数', value='22桌', state='proposed', quote=self.context['source_text'])], **extra)

    def test_new_employee_new_work_reads_same_record_without_other_history(self):
        self.assertEqual('recorded', self.call('case-update', self.change())['status'])
        context = {**self.context, 'work_id': 'operations-new-work', 'source_text': '准备林陈婚宴执行清单'}
        read = self.call('case-read', {'case_name': '林陈婚宴'}, principal=self.operations, context=context)
        self.assertEqual('22桌', read['case']['facts']['桌数']['value'])
        self.assertEqual(1, read['case']['revision'])
        self.assertEqual('found', self.call('case-read', {}, principal=self.operations, context=context)['status'])
        self.assertEqual('needs_selection', self.call('case-read', {}, context={**context, 'work_id': 'another'})['status'])

    def test_private_read_does_not_grant_private_sharing(self):
        self.call('case-update', self.change())
        context = {**self.context, 'share_allowed': False}
        self.assertEqual('found', self.call('case-read', {'case_name': '林陈婚宴'}, principal=self.private, context=context)['status'])
        self.assertEqual('case_share_not_authorized', self.call('case-update', self.change(), principal=self.private, context=context)['code'])
        self.assertEqual('recorded', self.call('case-update', self.change())['status'])

    def test_exact_source_and_host_scope_required(self):
        for field, value in (('user_id','stranger'), ('chat_id','another-group'), ('project','another-project')):
            with self.subTest(field=field):
                self.assertEqual('blocked', self.call('case-read', {'case_name':'林陈婚宴'},
                                 principal={**self.principal,field:value})['status'])
        change = self.change()
        change['changes'][0]['value'] = '30桌'
        self.assertEqual('blocked', self.call('case-update', change)['status'])
        change = self.change()
        change['share_allowed'] = True
        self.assertEqual('blocked', self.call('case-update', change)['status'])
        self.assertEqual('blocked', self.call('case-update', self.change(), context={})['status'])

    def test_successful_message_is_deduplicated_but_failed_revision_can_retry(self):
        update = self.change()
        first = self.call('case-update', update)
        self.assertEqual(first['case'], self.call('case-update', update)['case'])
        self.assertTrue(self.call('case-update', update)['replayed'])
        update['expected_revision'] = 1
        self.assertEqual('case_message_already_recorded', self.call('case-update', update)['code'])
        update['expected_revision'] = 0
        self.assertEqual('conflict', self.call('case-update', update, principal=self.operations)['status'])
        update['expected_revision'] = 1
        self.assertEqual('recorded', self.call('case-update', update, principal=self.operations)['status'])

    def test_conflicting_claim_preserves_both_sources_then_explicit_correction(self):
        self.call('case-update', self.change())
        context = {**self.context, 'source_text': '我记得是23桌。'}
        update = dict(case_name='林陈婚宴', expected_revision=1, changes=[dict(
            field='桌数', value='23桌', state='unverified', quote=context['source_text'])])
        result = self.call('case-update', update, principal=self.operations, context=context)
        fact = result['case']['facts']['桌数']
        self.assertEqual(('conflict','22桌','23桌'), (fact['state'], fact['value'],fact['alternatives'][0]['value']))
        context['source_text'] = '客户确认，桌数改为23桌。'
        update['changes'][0].update(quote=context['source_text'], state='reported_confirmed', replaces=True)
        update['expected_revision'] = 2
        result = self.call('case-update', update, principal={**self.principal,'message_id':'correction'}, context=context)
        self.assertEqual('23桌',result['case']['facts']['桌数']['value'])
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(3,db.execute('SELECT COUNT(*) FROM shared_case_versions').fetchone()[0])
            original = json.loads(db.execute('SELECT body FROM shared_case_versions WHERE revision=1').fetchone()[0])
        self.assertEqual('22桌', original['facts']['桌数']['value'])

    def test_denial_and_hypothesis_cannot_resolve_conflicts(self):
        self.call('case-update',self.change())
        for text in ('不要改为23桌', '如果改为23桌', '是否改为23桌？'):
            update = dict(case_name='林陈婚宴',expected_revision=1,changes=[dict(
                field='桌数',value='23桌',state='reported_confirmed',quote=text,replaces=True)])
            self.assertEqual('blocked',self.call('case-update',update,principal=self.operations,
                             context={**self.context,'source_text':text})['status'])

    def test_storage_failure_does_not_consume_message_or_modify_record(self):
        with mock.patch.object(cases,'_bind',side_effect=sqlite3.OperationalError('fictional disk failure')):
            self.assertEqual('unavailable',self.call('case-update',self.change())['status'])
        self.assertEqual('not_found',self.call('case-read',{'case_name':'林陈婚宴'})['status'])
        self.assertEqual('recorded',self.call('case-update',self.change())['status'])

    def test_second_case_keeps_separate_history_and_binding(self):
        self.call('case-update',self.change())
        second = self.change()
        second['case_name']='周许婚宴'
        self.call('case-update',second,principal={**self.principal,'message_id':'second-case'})
        self.assertEqual('周许婚宴',self.call('case-read',{})['case']['name'])
        self.assertEqual('林陈婚宴',self.call('case-read',{'case_name':'林陈婚宴'})['case']['name'])
        self.assertEqual(2,len(self.call('case-list',{})['cases']))

    def test_disabled_and_uninitialized_do_not_create_storage_or_tables(self):
        self.assertEqual('disabled',self.call('case-list',{},config={})['status'])
        self.path.unlink()
        self.assertEqual('unavailable',self.call('case-list',{})['status'])
        self.assertFalse(self.path.exists())
        self.path.touch(mode=0o600)
        self.assertEqual('unavailable',self.call('case-list',{})['status'])
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual([],db.execute('SELECT name FROM sqlite_master').fetchall())

    def test_production_store_cannot_be_used(self):
        config=copy.deepcopy(self.config)
        config['ledger_path']=str(self.path)
        self.assertEqual('blocked',self.call('case-list',{},config=config)['status'])


if __name__ == '__main__':
    unittest.main()
