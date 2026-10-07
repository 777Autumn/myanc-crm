"""Fixed schema/CLI boundary: no user-selected table, strict links, no silent truncation."""
import copy
import unittest
from unittest import mock

from myanc_crm import banquet, lark
from test_lark import CUSTOMER_FIELD_IDS, FOLLOWUP_FIELD_IDS
from test_core import CONFIG, PRINCIPAL


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

    def test_schema_checks_fixed_field_ids_and_both_relationships(self):
        with mock.patch.object(self.backend,'_read_table_schema',side_effect=lambda table,_:copy.deepcopy(self.schema[table])):
            self.assertEqual(3,len(self.store.read_schema()['schema']))
            self.schema['tblHandoffs']['关联婚宴']['property']['table_id']='tblOther'
            with self.assertRaises(ValueError):self.store.read_schema()
            self.schema['tblHandoffs']['关联婚宴']['property']['table_id']='tblBanquets'
            self.schema['tblBanquets']['销售负责人']['field_id']='fldWrong'
            with self.assertRaises(lark.LarkBackendError):self.store.read_schema()

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


if __name__=='__main__':unittest.main()
