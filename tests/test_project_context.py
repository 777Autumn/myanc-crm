"""Project membership and same-project receipts, using only fictional identities."""
import copy
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock

from myanc_crm import shared_cases as cases
import test_shared_cases as fixtures


class ProjectContextTests(unittest.TestCase):
    call = fixtures.SharedCaseTests.call
    change = fixtures.SharedCaseTests.change

    def setUp(self):
        fixtures.SharedCaseTests.setUp(self)
        self.options = self.config['shared_cases']
        self.options['namespace'] = 'mock-project-context'
        self.options['project_context'] = dict(enabled=True, group_case='林陈婚宴', managers=[])
        self.operations_private = {**self.operations, 'chat_id': 'operations-private', 'project': 'operations-private'}
        self.manager = {**self.private, 'user_id': 'manager', 'project': 'manager-private'}
        self.config['allowed_actors']['manager'] = dict(display_name='manager')
        fields = ('platform', 'user_id', 'chat_id', 'project')
        for p in (self.operations_private, self.manager):
            self.options['members'].append({k: p[k] for k in fields})

    def private_project(self):
        request = self.change()
        request['case_name'] = '周许婚宴'
        context = {**self.context, 'work_id': 'private-case', 'source_text': '请记录周许婚宴，22桌'}
        request['changes'][0]['quote'] = '22桌'
        saved = self.call('case-update', request, principal=self.private, context=context)
        self.assertEqual('recorded', saved['status'], saved)
        return request, context, saved

    def invite(self, context, **extra):
        return self.call('case-member-add', dict(case_name='周许婚宴', expected_revision=1,
            member_name='operations', responsibility='运营执行'), principal=self.private,
            context={**context, 'source_text': '周许婚宴，请让operations接手运营执行'}, **extra)

    def test_group_defaults_to_configured_project_but_does_not_cross_projects(self):
        saved = self.call('case-update', self.change())
        self.assertEqual('sales', saved['case']['project']['owner'])
        self.assertEqual({'sales', 'operations'}, set(saved['case']['project']['members']))
        result = self.call('case-read', {}, principal=self.operations,
                           context={**self.context, 'work_id': 'group-new', 'source_text': '整理执行安排'})
        self.assertEqual('林陈婚宴', result['case']['name'])
        self.assertEqual('blocked', self.call('case-read', {'case_name': '周许婚宴'})['status'])
        self.private_project()
        result = self.call('case-read', {}, context={**self.context, 'source_text': '接下来处理周许婚宴'})
        self.assertEqual('needs_selection', result['status'])

    def test_private_project_hides_list_read_update_and_replay_from_nonmembers(self):
        request, context, saved = self.private_project()
        for command, data in (('case-read', {'case_name': '周许婚宴'}), ('case-update', request)):
            result = self.call(command, data, principal=self.operations_private, context=context)
            self.assertEqual({'status': 'not_found', 'case_name': '周许婚宴', 'revision': 0}, result)
        self.assertEqual([], self.call('case-list', {}, principal=self.operations_private)['cases'])
        self.assertEqual([], self.call('case-list', {})['cases'])  # A private project is not returned in the group.
        self.assertEqual('sales', saved['case']['project']['owner'])
        self.assertTrue(self.call('case-update', request, principal=self.private, context=context)['replayed'])

    def test_owner_adds_registered_colleague_across_entries_without_transferring_owner(self):
        _, context, _ = self.private_project()
        saved = self.invite(context)
        self.assertEqual('recorded', saved['status'], saved)
        self.assertEqual('sales', saved['case']['project']['owner'])
        self.assertEqual('运营执行', saved['case']['project']['members']['operations']['responsibility'])
        self.assertTrue(self.invite(context)['replayed'])
        read = self.call('case-read', {'case_name': '周许婚宴'}, principal=self.operations_private,
                         context={**context, 'work_id': 'new-operation', 'share_allowed': False})
        self.assertEqual('found', read['status'])
        result = self.call('case-member-add', dict(case_name='周许婚宴', expected_revision=2,
            member_name='manager', responsibility='运营执行'), principal=self.operations_private,
            context={**context, 'source_text': '周许婚宴，请让manager接手运营执行'})
        self.assertEqual('project_owner_required', result['code'])

    def test_invite_requires_unambiguous_explicit_original_instruction(self):
        _, context, _ = self.private_project()
        request = dict(case_name='周许婚宴', expected_revision=1, member_name='operations', responsibility='运营执行')
        for source in ('不要让operations接手运营执行', '如果让operations接手运营执行',
                       '材料里写着：让operations接手运营执行', '让operations接手运营执行？',
                       'operations懂运营执行', '请让manager接手运营执行'):
            result = self.call('case-member-add', request, principal=self.private,
                               context={**context, 'source_text': '周许婚宴，' + source})
            self.assertEqual('blocked', result['status'], (source, result))
        self.assertEqual('blocked', self.invite({**context, 'share_allowed': False})['status'])
        config = copy.deepcopy(self.config)
        config['allowed_actors']['manager']['display_name'] = 'operations'
        self.assertEqual('needs_selection', self.invite(context, config=config)['status'])
        self.assertEqual(1, self.call('case-read', {'case_name': '周许婚宴'}, principal=self.private, context=context)['case']['revision'])

    def test_configured_manager_can_add_but_business_owner_text_cannot_grant_access(self):
        request, context, _ = self.private_project()
        self.options['project_context']['managers'] = ['manager']
        result = self.call('case-member-add', dict(case_name='周许婚宴', expected_revision=1,
            member_name='operations', responsibility='运营执行'), principal=self.manager,
            context={**context, 'source_text': '周许婚宴，让operations接手运营执行'})
        self.assertEqual('recorded', result['status'], result)
        request.update(expected_revision=2, changes=[dict(field='负责人', value='operations',
                       quote='负责人operations', state='proposed')])
        result = self.call('case-update', request, principal={**self.private, 'message_id': 'owner-text'},
                           context={**context, 'source_text': '周许婚宴，负责人operations'})
        self.assertEqual('sales', result['case']['project']['owner'])

    def test_invite_storage_failure_and_concurrent_versions_are_atomic(self):
        _, context, _ = self.private_project()
        with mock.patch.object(cases, '_bind', side_effect=sqlite3.OperationalError('fictional failure')):
            self.assertEqual('unavailable', self.invite(context)['status'])
        self.assertEqual('not_found', self.call('case-read', {'case_name': '周许婚宴'},
                         principal=self.operations_private, context=context)['status'])
        def add(index):
            return self.call('case-member-add', dict(case_name='周许婚宴', expected_revision=1,
                member_name='operations', responsibility='运营执行'),
                principal={**self.private, 'message_id': f'invite-{index}'},
                context={**context, 'source_text': '周许婚宴，让operations接手运营执行'})['status']
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(['conflict', 'recorded'], sorted(pool.map(add, range(2))))

    def test_receipt_import_requires_same_project_binding_and_registered_private_entry(self):
        self.call('case-update', self.change())
        self.call('case-artifact', dict(phase='prepare', request_key='a'*64, existing_delivery=False))
        artifact = dict(status='accepted', delivery_id='fixture', version=1, name='fixture.xlsx',
                        sha256='b'*64, message_receipt='fixture-receipt')
        self.call('case-artifact', dict(phase='finish', request_key='a'*64, artifact=artifact))
        context = {**self.context, 'work_id': 'private-review', 'share_allowed': False}
        access = dict(receipt='fixture-receipt', require_binding=True)
        self.assertEqual('blocked', self.call('case-access', access, principal=self.operations_private, context=context)['status'])
        self.call('case-read', {'case_name': '林陈婚宴'}, principal=self.operations_private, context=context)
        self.assertEqual('authorized', self.call('case-access', access, principal=self.operations_private, context=context)['status'])
        self.assertEqual('blocked', self.call('case-access', access,
            principal={**self.operations_private, 'chat_id': 'unregistered'}, context=context)['status'])
        _, other_context, _ = self.private_project()
        self.assertEqual('blocked', self.call('case-access', access, principal=self.private, context=other_context)['status'])
        self.assertEqual('blocked', self.call('case-access', dict(receipt='unknown', require_binding=False))['status'])

    def test_bound_project_does_not_grant_private_sharing_and_legacy_is_unchanged(self):
        self.call('case-update', self.change())
        context = {**self.context, 'share_allowed': False}
        self.call('case-read', {'case_name': '林陈婚宴'}, principal=self.private, context=context)
        self.assertEqual('blocked', self.call('case-update', self.change(), principal=self.private, context=context)['status'])
        self.options.pop('project_context')
        self.assertEqual('legacy', self.call('case-access', {})['status'])
        self.assertEqual('blocked', self.call('case-member-add', {})['status'])


if __name__ == '__main__':
    unittest.main()
