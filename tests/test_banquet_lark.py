"""Fixed schema/CLI boundary: no user-selected table, strict links, no silent truncation."""
import copy
import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock

from myanc_crm import banquet, core, lark
from test_lark import CUSTOMER_FIELD_IDS, FOLLOWUP_FIELD_IDS
from test_core import CONFIG, PRINCIPAL, NOW, TOKEN, customer


class BanquetAdapterTests(unittest.TestCase):
    def setUp(self):
        options = {'table_id': 'tblBanquets', 'fields': {k:'fldBanquet'+str(i) for i,k in enumerate(banquet.SCHEMA)},
                   'handoff_table_id':'tblHandoffs','handoff_fields':{k:'fldHandoff'+str(i) for i,k in enumerate(banquet.HANDOFF_SCHEMA)},
                   'followup_field_id':'fldFollowupBanquet'}
        self.backend=lark.LarkCliBackend(wrapper_path='/opt/host/writer',base_token='baseFixture',
            customer_table_id='tblCustomers',followup_table_id='tblFollowups',base_url='https://example.feishu.cn/base/baseFixture',
            fields={'customers':CUSTOMER_FIELD_IDS,'followups':FOLLOWUP_FIELD_IDS},banquet_config=options)
        self.store=banquet.Store(self.backend)
        self.schema={}
        for kind,fields in self.store.schemas.items():
            values={}
            for key,(name,typ) in fields.items():
                values[name]={'field_id':self.store.fields[kind][key],'type':typ,'name':name}
                if typ=='link':values[name]['property']={'table_id':'tblCustomers' if key=='customer_record_id' else 'tblBanquets'}
            self.schema[self.store.tables[kind]]=values

    def test_simple_reads_do_not_depend_on_unrelated_handoff_service(self):
        for command, request in [('banquet', {'banquet_id': 'YAN-0006'}),
                                 ('banquets', {'owner': 'all'})]:
            calls = []
            def run(argv, **kwargs):
                operation = argv[2]
                table = argv[argv.index('--table-id') + 1]
                calls.append((operation, table))
                if table == 'tblHandoffs':
                    return subprocess.CompletedProcess(argv, 1, stdout='', stderr='unrelated service unavailable')
                if operation == '+field-list':
                    data = {'ok': True, 'identity': 'bot', 'data': {'items': list(self.schema[table].values())}}
                else:
                    self.assertIn(operation, ('+record-get', '+record-list'))
                    rows = [{'record_id': 'recBanquet', 'fields': {'业务编号': 'YAN-0006', '预计桌数': 23}}] if table == 'tblBanquets' else []
                    Path(kwargs['cwd'], 'records.ndjson').write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
                    data = {'format': 'ndjson', 'record_file': 'records.ndjson', 'records_count': len(rows), 'has_more': False}
                return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(data), stderr='')
            with self.subTest(command=command):
                self.backend.runner = run
                result = banquet.read(command, request, self.backend, CONFIG, PRINCIPAL)
                self.assertEqual('found', result['status'])
                row = result['banquet'] if command == 'banquet' else result['items'][0]
                self.assertEqual(23, row['estimated_tables'])
                self.assertNotIn('tblHandoffs', [table for _, table in calls])
                self.assertEqual(4 if command == 'banquet' else 2, len(calls))
                # Required schema validation still precedes any record reads.
                self.schema['tblBanquets']['预计桌数']['field_id'] = 'fldWrong'
                calls.clear()
                with self.assertRaises(lark.LarkBackendError):
                    banquet.read(command, request, self.backend, CONFIG, PRINCIPAL)
                self.assertTrue(all(op == '+field-list' for op, _ in calls))
                self.schema['tblBanquets']['预计桌数']['field_id'] = self.store.fields['banquets']['estimated_tables']

    def test_schema_checks_fixed_field_ids_and_both_relationships(self):
        with mock.patch.object(self.backend,'_read_table_schema',side_effect=lambda table,_:copy.deepcopy(self.schema[table])):
            self.assertEqual(3,len(self.store.read_schema()['schema']))
            self.schema['tblHandoffs']['关联婚宴']['property']['table_id']='tblOther'
            with self.assertRaises(ValueError):self.store.read_schema()
            self.schema['tblHandoffs']['关联婚宴']['property']['table_id']='tblBanquets'
            self.schema['tblBanquets']['销售负责人']['field_id']='fldWrong'
            with self.assertRaises(lark.LarkBackendError):self.store.read_schema()

    def test_read_number_uses_fresh_list_record_without_second_get(self):
        calls = []
        def run(argv, **kwargs):
            operation = argv[2]
            table = argv[argv.index('--table-id') + 1]
            calls.append((operation, table))
            if operation == '+field-list':
                data = {'ok': True, 'identity': 'bot', 'data': {'items': list(self.schema[table].values())}}
            else:
                if operation == '+record-get':
                    raise subprocess.TimeoutExpired(argv, 30)
                rows = [{'record_id': 'recBanquet', 'fields': {'业务编号': 'YAN-0006', '预计桌数': 23}}] if table == 'tblBanquets' else []
                Path(kwargs['cwd'], 'records.ndjson').write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8')
                data = {'format': 'ndjson', 'record_file': 'records.ndjson', 'records_count': len(rows), 'has_more': False}
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(data), stderr='')
        self.backend.runner = run
        result = banquet.read('banquet', {'banquet_id': 'YAN-0006'}, self.backend, CONFIG, PRINCIPAL)
        self.assertEqual('found', result['status'])
        self.assertEqual(23, result['banquet']['estimated_tables'])
        self.assertEqual(4, len(calls))
        self.assertNotIn(('+record-get', 'tblBanquets'), calls)

    def test_native_cli_link_table_is_checked_and_bound_to_preview(self):
        for values in self.schema.values():
            for field in values.values():
                if field['type']=='link':
                    field['link_table']=field.pop('property')['table_id']
                    field['bidirectional']=False
        with mock.patch.object(self.backend,'_read_table_schema',side_effect=lambda table,_:copy.deepcopy(self.schema[table])):
            snapshot=self.store.read_schema()
            links=[f for f in snapshot['schema']['banquets'] if f['type']=='link']
            self.assertEqual('tblCustomers',links[0]['link_table'])
            self.schema['tblBanquets']['关联客户']['link_table']='tblOther'
            with self.assertRaises(ValueError):self.store.read_schema()

    def test_display_formulas_do_not_change_approval_schema(self):
        with mock.patch.object(self.backend,'_read_table_schema',side_effect=lambda table,_:copy.deepcopy(self.schema[table])):
            before=self.store.read_schema()
            for table in ('tblBanquets','tblHandoffs'):
                self.schema[table]['展示·状态']={'field_id':'fldDisplay','type':'formula','name':'展示·状态'}
            self.assertEqual(before,self.store.read_schema())

    def test_workbench_selects_configured_actor_and_rejects_other_resource(self):
        config=copy.deepcopy(CONFIG)
        actor=config['allowed_actors'][PRINCIPAL['user_id']]['feishu_user_id']
        config.update(base_token='baseFixture',base_url='https://example.feishu.cn/base/baseFixture',
                      banquet=self.backend.banquet_config)
        config['banquet_workbench']={'base_token':'baseFixture','table_id':'tblBanquets',
            'handoff_table_id':'tblHandoffs','banquet-mine':{actor:'vewMine','other':'vewOther'}}
        result=banquet.open_workbench({'target':'banquet-mine'},config,PRINCIPAL)
        self.assertIn('view=vewMine',result['url'])
        self.assertEqual('blocked',banquet.open_workbench({'target':'handoff-mine'},config,PRINCIPAL)['status'])
        config['banquet_workbench'].update({'handoff-pending':'vewPending','handoff-mine':{actor:'vewCurrent'}})
        pending=banquet.open_workbench({'target':'handoff-pending'},config,PRINCIPAL)
        mine=banquet.open_workbench({'target':'handoff-mine'},config,PRINCIPAL)
        self.assertIn('table=tblBanquets&view=vewPending',pending['url'])
        self.assertIn('table=tblHandoffs&view=vewCurrent',mine['url'])
        config['banquet_workbench']['base_token']='anotherBase'
        with self.assertRaises(ValueError):banquet.open_workbench({'target':'banquet-mine'},config,PRINCIPAL)

    def test_write_uses_fixed_table_exact_cells_and_reads_project_only_pinned_fields(self):
        with mock.patch.object(self.backend,'_write_records',return_value={'data':{'records':[{'record_id':'recNew'}]}}) as write:
            identifier=self.store.write('banquets',None,{'name':'虚构宴会','owner':[{'id':'ou_Manager','name':'Manager'}],
                'customer_record_id':'recCustomer','stage':'新线索','budget':200000,'operation_id':'chg_fixture'})
            self.assertEqual('recNew',identifier)
            self.assertEqual('tblBanquets',write.call_args.args[0])
            cells=write.call_args.args[2]['create_records'][0]
            self.assertEqual([{'id':'ou_Manager'}],cells[self.store.fields['banquets']['owner']])
            self.assertEqual([{'id':'recCustomer'}],cells[self.store.fields['banquets']['customer_record_id']])
            self.assertEqual(['新线索'],cells[self.store.fields['banquets']['stage']])
        with mock.patch.object(self.backend,'_read_records',return_value=[]) as read:
            self.assertIsNone(self.store.get('banquets','recAbsent'))
            self.assertIn('tblBanquets',read.call_args.args[0])
            self.assertEqual(tuple(self.store.fields['banquets'].values()),read.call_args.args[1])

    def test_overflow_and_mismatched_exact_id_are_not_partial_success(self):
        with mock.patch.object(self.backend,'_read_record_page',return_value={'items':[],'has_more':True}):
            with self.assertRaises(ValueError):self.store.list('banquets')
        with mock.patch.object(self.backend,'_read_records',return_value=[{'record_id':'recWrong'}]):
            with self.assertRaises(ValueError):self.store.get('banquets','recRequested')

    def test_business_number_resolves_in_same_store_and_rechecks_exact_record(self):
        row={'record_id':'recBanquet','fields':{'业务编号':'YAN-0006'}}
        with mock.patch.object(self.backend,'_read_record_page',return_value={'items':[row],'has_more':False}) as listing, \
                mock.patch.object(self.backend,'_read_records',return_value=[row]) as read:
            self.assertEqual('recBanquet',self.store.get('banquets','YAN-0006')['record_id'])
            self.assertIn('tblBanquets',listing.call_args.args[0])
            self.assertIn('recBanquet',read.call_args.args[0])
            listing.reset_mock()
            self.store.get('banquets','recBanquet')
            listing.assert_not_called()
            read.return_value=[{'record_id':'recBanquet','fields':{'业务编号':'YAN-0007'}}]
            with self.assertRaises(ValueError):self.store.get('banquets','YAN-0006')

    def test_business_number_missing_duplicate_denied_and_overflow_fail_closed(self):
        row={'record_id':'recBanquet','fields':{'业务编号':'YAN-0006'}}
        cases=[([],False,None),([row,{**row,'record_id':'recOther'}],False,ValueError),
               ([row],True,ValueError)]
        with mock.patch.object(self.backend,'_read_records') as read:
            for rows,more,error in cases:
                with self.subTest(rows=rows,more=more), mock.patch.object(self.backend,'_read_record_page',
                        return_value={'items':rows,'has_more':more}):
                    if error:
                        with self.assertRaises(error):self.store.get('banquets','YAN-0006')
                    else:self.assertIsNone(self.store.get('banquets','YAN-0006'))
            with mock.patch.object(self.backend,'_read_record_page',side_effect=PermissionError('denied')):
                with self.assertRaises(PermissionError):self.store.get('banquets','YAN-0006')
            read.assert_not_called()
        with mock.patch.object(self.backend,'_read_record_page') as listing:
            for kind,value in [('handoffs','YAN-0006'),('banquets','YAN-0006 extra'),('banquets',None)]:
                with self.assertRaises(lark.LarkBackendError):self.store.get(kind,value)
            listing.assert_not_called()

    def test_number_preview_freezes_record_and_changed_number_cannot_redirect_apply(self):
        row={'record_id':'recBanquet','fields':{'业务编号':'YAN-0006','宴会名称':'虚构宴会',
             '关联客户':[{'id':'recCustomer'}],'销售阶段':['跟进中']}}
        ledger=core.Ledger()
        self.addCleanup(ledger.close)
        with mock.patch.object(self.backend,'_read_table_schema',side_effect=lambda table,_:copy.deepcopy(self.schema[table])), \
                mock.patch.object(self.backend,'_read_record_page',return_value={'items':[row],'has_more':False}) as listing, \
                mock.patch.object(self.backend,'_read_records',side_effect=lambda *args:[copy.deepcopy(row)]) as read, \
                mock.patch.object(self.backend,'get_customer',return_value=customer('recCustomer')), \
                mock.patch.object(self.backend,'_write_records') as write:
            result=banquet.stage('stage-banquet-update',{'banquet_id':'YAN-0006','changes':{'venue':'待确认'}},
                                 self.backend,ledger,CONFIG,TOKEN,PRINCIPAL,NOW)
            self.assertEqual('staged',result['status'],result)
            staged=ledger.get(result['change_id'])
            self.assertEqual('recBanquet',staged['banquet_before']['record_id'])
            row['fields']['业务编号']='YAN-0007'
            listing.reset_mock();read.reset_mock()
            applied=banquet.apply(staged,self.backend,ledger,NOW)
            self.assertEqual('banquet_changed',applied['code'],applied)
            self.assertIn('recBanquet',read.call_args.args[0])
            listing.assert_not_called();write.assert_not_called()


if __name__=='__main__':unittest.main()
