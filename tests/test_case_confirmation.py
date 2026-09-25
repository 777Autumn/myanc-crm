"""Synthetic host confirmation, exact operation scope and recovery receipts."""
import copy
import unittest

import test_project_context as fixtures


class CaseConfirmationTests(unittest.TestCase):
    setUp = fixtures.ProjectContextTests.setUp
    call = fixtures.ProjectContextTests.call
    change = fixtures.ProjectContextTests.change
    private_project = fixtures.ProjectContextTests.private_project
    invite = fixtures.ProjectContextTests.invite
    def confirmed(self, command, request, context, revision):
        return {**context, 'offer_confirmation': True, 'confirmation': dict(
            command=command, input=copy.deepcopy(request), answer_message_id='answer-fixture', revision=revision)}

    def test_natural_invitation_preview_does_not_grant_access_then_exact_answer_does(self):
        _, context, _ = self.private_project()
        context = {**context, 'source_text': '这场让operations一起帮忙做运营吧', 'offer_confirmation': True}
        request = dict(case_name='周许婚宴', expected_revision=1, member_name='operations', responsibility='运营执行')
        pending = self.call('case-member-add', request, principal=self.private, context=context)
        self.assertEqual('needs_confirmation', pending['status'], pending)
        self.assertIn('负责人不变', pending['question'])
        self.assertEqual('not_found', self.call('case-read', {'case_name': '周许婚宴'},
            principal=self.operations_private, context=context)['status'])
        answered = self.confirmed('case-member-add', request, context, 1)
        saved = self.call('case-member-add', request, principal=self.private, context=answered)
        self.assertEqual('recorded', saved['status'], saved)
        self.assertEqual('sales', saved['case']['project']['owner'])
        self.assertIn('operations', saved['case']['project']['members'])
        self.assertTrue(self.call('case-member-add', request, principal=self.private, context=answered)['replayed'])
        result = self.call('case-result', dict(command='case-member-add', input=request), principal=self.private, context=context)
        self.assertTrue(result['replayed'])

    def test_private_relative_change_freezes_displayed_fields_and_scope(self):
        _, context, _ = self.private_project()
        context = {**context, 'source_text': '再加一桌，同步给运营就这一个变更',
                   'share_allowed': False, 'offer_confirmation': True}
        request = dict(case_name='周许婚宴', expected_revision=1,
            changes=[dict(field='桌数', value='23桌', state='proposed', quote='再加一桌', replaces=True)])
        principal = {**self.private, 'message_id': 'relative-change'}
        pending = self.call('case-update', request, principal=principal, context=context)
        self.assertEqual('needs_confirmation', pending['status'], pending)
        for value in ('23桌', '22桌', '供该项目成员读取', '提出要求'):
            self.assertIn(value, pending['question'])
        before = self.call('case-result', dict(command='case-update', input=request), principal=principal, context=context)
        self.assertEqual('not_executed', before['status'])
        answered = self.confirmed('case-update', request, context, 1)
        changed = self.call('case-update', request, principal=principal, context=answered)
        self.assertEqual('recorded', changed['status'], changed)
        self.assertEqual('23桌', changed['case']['facts']['桌数']['value'])
        self.assertEqual('confirmed_interpretation', changed['case']['facts']['桌数']['source']['origin'])
        self.assertFalse(context['share_allowed'])
        forged = {**request, 'expected_revision': 2}
        self.assertEqual('blocked', self.call('case-update', forged, principal=principal, context=answered)['status'])
        self.assertEqual('blocked', self.call('case-update', {**request, 'confirmation': True}, principal=principal, context=context)['status'])
        recovered = self.call('case-result', dict(command='case-update', input=request), principal=principal, context=context)
        self.assertTrue(recovered['replayed'])

    def test_read_clarification_only_selects_project_does_not_share(self):
        self.call('case-update', self.change())
        context = {**self.context, 'work_id': 'ordinary-read', 'source_text': '麻烦看看林陈婚宴',
                   'share_allowed': False, 'offer_confirmation': True}
        request = {'case_name': '林陈婚宴'}
        pending = self.call('case-read', request, principal=self.operations_private, context=context)
        self.assertEqual('needs_confirmation', pending['status'])
        answered = self.confirmed('case-read', request, context, 1)
        read = self.call('case-read', request, principal=self.operations_private, context=answered)
        self.assertEqual('found', read['status'])
        # Reusing a read answer for a write is not a grant.
        self.assertEqual('blocked', self.call('case-update', self.change(), principal=self.operations_private, context=answered)['status'])
        result = self.call('case-read', {}, principal=self.operations_private,
                          context={**context, 'source_text': '继续', 'offer_confirmation': False})
        self.assertEqual('found', result['status'])
        self.assertFalse(context['share_allowed'])

    def test_version_conflict_and_denial_do_not_execute_or_invent_confirmation(self):
        _, context, _ = self.private_project()
        request = dict(case_name='周许婚宴', expected_revision=1, member_name='operations', responsibility='运营执行')
        for source in ('不要让operations参与运营执行', '禁止共享本次项目', '暂不邀请operations'):
            denied = self.call('case-member-add', request, principal=self.private,
                context={**context, 'source_text': source, 'offer_confirmation': True})
            self.assertNotIn(denied['status'], ('recorded', 'needs_confirmation'))
        self.invite(context)
        request['member_name'] = 'manager'
        answered = self.confirmed('case-member-add', request, context, 1)
        conflict = self.call('case-member-add', request,
            principal={**self.private, 'message_id': 'next'}, context=answered)
        self.assertEqual('conflict', conflict['status'], conflict)
        read = self.call('case-read', {'case_name': '周许婚宴'}, principal=self.private, context=context)
        self.assertNotIn('manager', read['case']['project']['members'])


if __name__ == '__main__':
    unittest.main()
