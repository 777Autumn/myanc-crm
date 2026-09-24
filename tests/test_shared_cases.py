"""Fictional cross-employee records, persisted in the existing test-ledger pattern."""
import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
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
        change = self.change()
        change['changes'][0]['field'] = '不属于这条消息的私人信息'
        self.assertEqual('blocked', self.call('case-update',change)['status'])

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

    def test_invalid_batch_explains_verbatim_value_and_retries_whole_message(self):
        self.context['source_text'] = '林陈婚宴，22桌，选择A套餐和基础布置，尚未签约。'
        update = self.change()
        update['changes'].append(dict(field='已选方案', value='A套餐+基础布置',
                                      state='proposed', quote='选择A套餐和基础布置'))
        rejected = self.call('case-update', update)
        self.assertEqual('case_changes_invalid', rejected['code'])
        self.assertIn('已选方案', rejected['reason'])
        self.assertIn('verbatim', rejected['reason'])
        self.assertFalse(rejected['recorded'])
        self.assertIn('whole batch', rejected['retry'])
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM shared_case_versions').fetchone()[0])
            self.assertEqual(0, db.execute('SELECT COUNT(*) FROM shared_case_bindings').fetchone()[0])
        update['changes'][1]['value'] = 'A套餐和基础布置'
        update['changes'].append(dict(field='待确认项', value='尚未签约',
                                      state='reported_confirmed', quote='尚未签约'))
        rejected = self.call('case-update', update)
        self.assertEqual('case_changes_invalid', rejected['code'])
        self.assertIn('待确认项', rejected['reason'])
        self.assertFalse(rejected['recorded'])
        update['changes'][2]['state'] = 'unverified'
        saved = self.call('case-update', update)
        self.assertEqual('recorded', saved['status'])
        self.assertEqual({'桌数','已选方案','待确认项'}, set(saved['case']['facts']))
        self.assertEqual(1, saved['case']['revision'])
        self.assertTrue(self.call('case-update', update)['replayed'])
        update['expected_revision'] = 1
        self.assertEqual('case_message_already_recorded', self.call('case-update', update)['code'])

    def test_conflicting_claim_preserves_both_sources_then_explicit_correction(self):
        self.call('case-update', self.change())
        context = {**self.context, 'source_text': '林陈婚宴，我记得是23桌。'}
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
                             context={**self.context,'source_text':'林陈婚宴，'+text})['status'])

    def test_storage_failure_does_not_consume_message_or_modify_record(self):
        with mock.patch.object(cases,'_bind',side_effect=sqlite3.OperationalError('fictional disk failure')):
            self.assertEqual('unavailable',self.call('case-update',self.change())['status'])
        self.assertEqual('not_found',self.call('case-read',{'case_name':'林陈婚宴'})['status'])
        self.assertEqual('recorded',self.call('case-update',self.change())['status'])

    def test_second_case_keeps_separate_history_and_binding(self):
        self.call('case-update',self.change())
        second = self.change()
        second['case_name']='周许婚宴'
        context = {**self.context, 'source_text': '周许婚宴，客户要求22桌，A套餐。'}
        second['changes'][0]['quote'] = context['source_text']
        self.assertEqual('needs_new_work',self.call('case-update',second,context=context)['status'])
        context['work_id'] = 'another-work'
        self.call('case-update',second,principal={**self.principal,'message_id':'second-case'},context=context)
        self.assertEqual('周许婚宴',self.call('case-read',{},context=context)['case']['name'])
        self.assertEqual('林陈婚宴',self.call('case-read',{'case_name':'林陈婚宴'})['case']['name'])
        self.assertEqual(2,len(self.call('case-list',{})['cases']))

    def test_trimmed_quote_cannot_remove_denial_or_invent_confirmation(self):
        self.call('case-update', self.change())
        for source, quote, state, replaces in (
            ('林陈婚宴不要改为23桌', '改为23桌', 'proposed', True),
            ('林陈婚宴22桌还没有确认', '22桌', 'reported_confirmed', False),
            ('林陈婚宴22桌', '22桌', 'occurred', False),
        ):
            update = dict(case_name='林陈婚宴', expected_revision=1, changes=[dict(
                field='桌数', value='23桌' if replaces else '22桌', state=state, quote=quote, replaces=replaces)])
            result = self.call('case-update', update, principal=self.operations,
                               context={**self.context, 'source_text':source})
            self.assertEqual('blocked',result['status'],result)
        self.assertEqual(1,self.call('case-read',{'case_name':'林陈婚宴'})['case']['revision'])

    def test_unmentioned_or_ambiguous_target_is_not_selected_by_model(self):
        update = self.change()
        update['case_name'] = '王李婚宴'
        self.assertEqual('needs_selection',self.call('case-update',update)['status'])
        self.call('case-update',self.change())
        self.assertEqual('needs_new_work',self.call('case-read',{'case_name':'王李婚宴'})['status'])
        context = {**self.context,'work_id':'another','source_text':'王李婚宴22桌'}
        update['changes'][0]['quote'] = context['source_text']
        self.call('case-update',update,principal={**self.principal,'message_id':'another'},context=context)
        context['source_text'] = '林陈婚宴和王李婚宴，修改预算'
        context['work_id'] = 'ambiguous-new-work'
        self.assertEqual('needs_selection',self.call('case-read',{'case_name':'林陈婚宴'},context=context)['status'])

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

    def test_replaceable_parent_is_rejected_before_sqlite(self):
        with mock.patch.object(cases.core, '_validate_parent_chain', side_effect=ValueError('untrusted parent')):
            with mock.patch.object(cases.sqlite3, 'connect') as connect:
                self.assertEqual('blocked',self.call('case-list',{})['status'])
                connect.assert_not_called()

    def test_delivery_basis_is_pinned_before_send_and_late_file_stays_stale(self):
        self.call('case-update',self.change())
        prepare = dict(phase='prepare',request_key='a'*64,existing_delivery=False)
        self.assertEqual(1,self.call('case-artifact',prepare)['case_revision'])
        update = self.change()
        update['expected_revision'] = 1
        self.call('case-update',update,principal=self.operations)
        self.call('case-read',{'case_name':'林陈婚宴'})  # Refresh does not relabel the in-flight delivery.
        artifact = dict(status='accepted',delivery_id='fictional-delivery',version=1,
                        name='fictional.xlsx',sha256='b'*64,message_receipt='fictional-receipt')
        finish = dict(phase='finish',request_key='a'*64,artifact=artifact)
        self.assertTrue(self.call('case-artifact',finish)['stale'])
        self.assertTrue(self.call('case-artifact',finish)['stale'])
        files=self.call('case-read',{'case_name':'林陈婚宴'})['case']['artifacts']
        self.assertEqual(1,len(files))
        self.assertEqual((1,True),(files[0]['case_revision'],files[0]['stale']))
        self.assertNotIn('path',files[0])
        self.assertEqual('not_shared',self.call('case-artifact',prepare,principal=self.private)['status'])

    def test_unknown_and_old_unbound_deliveries_are_never_registered(self):
        self.call('case-update',self.change())
        request = dict(phase='prepare',request_key='c'*64,existing_delivery=True)
        self.assertEqual('not_shared',self.call('case-artifact',request)['status'])
        request['request_key']='d'*64
        request['existing_delivery']=False
        self.assertEqual('ready',self.call('case-artifact',request)['status'])
        request=dict(phase='finish',request_key='d'*64,artifact={'status':'unknown'})
        self.assertEqual('blocked',self.call('case-artifact',request)['status'])
        self.assertEqual([],self.call('case-read',{'case_name':'林陈婚宴'})['case']['artifacts'])

    def test_trusted_selection_and_delivered_reference_bind_a_new_work(self):
        self.call('case-update',self.change())
        context={**self.context,'work_id':'next-sales-work','source_text':'继续准备方案','selected_case':'林陈婚宴'}
        self.assertEqual('林陈婚宴',self.call('case-read',{},context=context)['case']['name'])
        self.call('case-artifact',dict(phase='prepare',request_key='f'*64,existing_delivery=False))
        artifact=dict(status='accepted',delivery_id='handoff',version=1,name='fixture.xlsx',sha256='a'*64,message_receipt='handoff-receipt')
        self.call('case-artifact',dict(phase='finish',request_key='f'*64,artifact=artifact))
        context={**self.context,'work_id':'new-operations','source_text':'请接手这个文件','source_receipt':'handoff-receipt'}
        self.assertEqual('林陈婚宴',self.call('case-read',{},principal=self.operations,context=context)['case']['name'])
        context['work_id']='unknown-work'
        context['source_receipt']='unknown-receipt'
        self.assertEqual('needs_selection',self.call('case-read',{},principal=self.operations,context=context)['status'])

    def test_confirmation_or_correction_cannot_be_borrowed_from_another_fact(self):
        self.call('case-update',self.change())
        for source, field, value, state, replaces in (
            ('林陈婚宴客户确认A套餐；布置2500元只是建议','布置','2500元','reported_confirmed',False),
            ('林陈婚宴客户确认A套餐，布置2500元','布置','2500元','reported_confirmed',False),
            ('林陈婚宴开席改为12点；桌数23桌','桌数','23桌','proposed',True),
        ):
            update=dict(case_name='林陈婚宴',expected_revision=1,changes=[dict(
                field=field,value=value,state=state,replaces=replaces,quote=source)])
            self.assertEqual('blocked',self.call('case-update',update,principal=self.operations,
                             context={**self.context,'source_text':source})['status'])

    def test_concurrent_updates_only_one_revision_commits(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.call,'case-update',self.change(),principal=p)
                       for p in (self.principal,self.operations)]
            self.assertEqual(['conflict','recorded'],sorted(f.result()['status'] for f in futures))
        self.assertEqual(1,self.call('case-read',{'case_name':'林陈婚宴'})['case']['revision'])

    def test_confirmed_fact_and_pending_fact_can_be_saved_together(self):
        for separator in ('；', '，'):
            with self.subTest(separator=separator):
                source = '林陈婚宴，客户已确认22桌' + separator + 'LED尚未确认'
                update = dict(case_name='林陈婚宴',expected_revision=0,changes=[
                    dict(field='桌数',value='22桌',state='reported_confirmed',quote='已确认22桌'),
                    dict(field='待确认项',value='LED',state='unverified',quote='LED尚未确认')])
                result = self.call('case-update',update,context={**self.context,'source_text':source})
                self.assertEqual('recorded',result['status'],result)
                self.assertEqual('reported_confirmed',result['case']['facts']['桌数']['state'])
                self.assertEqual('unverified',result['case']['facts']['待确认项']['state'])
                source = '林陈婚宴，客户已确认桌数改为23桌' + separator + 'LED尚未确认'
                update.update(expected_revision=1)
                update['changes'][0].update(value='23桌',quote='已确认桌数改为23桌',replaces=True)
                result = self.call('case-update',update,principal=self.operations,
                                   context={**self.context,'source_text':source})
                self.assertEqual('recorded',result['status'],result)
                self.assertEqual('23桌',result['case']['facts']['桌数']['value'])
                # Each separator exercises the same initially empty store.
                with closing(sqlite3.connect(self.path)) as db:
                    db.execute('DELETE FROM shared_case_versions')
                    db.execute('DELETE FROM shared_case_bindings')
                    db.commit()

    def test_clause_checks_keep_question_and_conditional_scope(self):
        for source in ('林陈婚宴，客户已确认22桌？',
                       '如果客户明天同意，林陈婚宴客户已确认22桌',
                       '林陈婚宴，不要，桌数改为22桌'):
            update = self.change()
            update['changes'][0].update(quote='22桌',state='reported_confirmed',replaces=True)
            self.assertEqual('blocked',self.call('case-update',update,
                             context={**self.context,'source_text':source})['status'])

    def test_maintenance_initializes_only_existing_separate_test_store(self):
        cases.initialize_config(self.config)
        with self.assertRaises(ValueError):
            cases.initialize_config({})
        config=copy.deepcopy(self.config)
        config['shared_cases']['ledger_path']=config['ledger_path']
        with self.assertRaises(ValueError):
            cases.initialize_config(config)
        self.assertFalse(Path(config['ledger_path']).exists())


if __name__ == '__main__':
    unittest.main()
