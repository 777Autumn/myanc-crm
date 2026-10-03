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

    def test_bound_case_accepts_name_separator_and_mock_marker(self):
        self.call('case-update', self.change())
        for source in ('林、陈婚宴追加消息', '仍是模拟婚宴。',
                       '林、陈婚宴追加消息\n仍是模拟婚宴。桌数改为23桌'):
            with self.subTest(source=source):
                context = {**self.context, 'source_text': source, 'offer_confirmation': True}
                read = self.call('case-read', {'case_name': '林陈婚宴'}, context=context)
                self.assertEqual('found', read['status'], read)
        request = dict(case_name='林陈婚宴', expected_revision=1, changes=[
            dict(field='桌数', value='23桌', quote=context['source_text'], state='proposed', replaces=True)])
        principal = {**self.principal, 'message_id': 'punctuated-update'}
        pending = self.call('case-update', request, context=context, principal=principal)
        self.assertEqual('needs_confirmation', pending['status'], pending)
        self.assertEqual('not_executed', self.call('case-result',
            dict(command='case-update', input=request), context=context, principal=principal)['status'])
        saved = self.call('case-update', request, principal=principal,
                          context=self.confirmed('case-update', request, context, 1))
        self.assertEqual('recorded', saved['status'], saved)
        self.assertEqual('23桌', saved['case']['facts']['桌数']['value'])
        self.assertEqual('confirmed_interpretation', saved['case']['facts']['桌数']['source']['origin'])
        self.assertEqual('林、陈婚宴追加消息\n仍是模拟婚宴。桌数改为23桌', context['source_text'])
        self.assertEqual(context['source_text'], request['changes'][0]['quote'])

    def assert_source_does_not_write(self, source):
        saved = self.call('case-update', self.change())
        context = {**self.context, 'source_text': source, 'original_text': source,
                   'share_allowed': True, 'offer_confirmation': True}
        request = dict(case_name='林陈婚宴', expected_revision=1, changes=[
            dict(field='桌数', value='23桌', quote='23桌', state='proposed')])
        result = self.call('case-update', request, context=context,
                           principal={**self.principal, 'message_id': 'non-authorizing-source'})
        self.assertNotEqual('recorded', result['status'], result)
        self.assertEqual(saved['case'], self.call('case-read', {'case_name': '林陈婚宴'})['case'])

    def test_bound_store_phrase_does_not_swallow_denial(self):
        self.assert_source_does_not_write('不要把23桌存进林陈婚宴。')

    def test_bound_record_phrase_does_not_swallow_denial(self):
        self.assert_source_does_not_write('不要记入林陈婚宴，23桌。')

    def test_bound_generic_question_does_not_swallow_denial(self):
        self.assert_source_does_not_write('我没说是哪场婚宴，先记23桌。')

    def test_bound_generic_question_does_not_swallow_condition(self):
        self.assert_source_does_not_write('如果知道是哪场婚宴就记23桌。')

    def test_bound_generic_question_does_not_swallow_quoted_material(self):
        self.assert_source_does_not_write('材料写着“是哪场婚宴”，23桌仅是样例。')

    def test_bound_mock_marker_does_not_relax_write_authorization(self):
        self.assert_source_does_not_write('不要改，仍是模拟婚宴，23桌。')

    def test_bound_long_prefaces_still_require_project_clarification(self):
        self.call('case-update', self.change())
        for source in ('我这边只看到确认是哪场婚宴的卡，已经点了。',
                       '请接着把刚才的追加消息存进林陈婚宴，给运营看。'):
            with self.subTest(source=source):
                result = self.call('case-read', {'case_name': '林陈婚宴'}, context={
                    **self.context, 'source_text': source, 'offer_confirmation': True})
                self.assertEqual('needs_confirmation', result['status'], result)

    def test_bound_full_name_and_exact_quotes_do_not_repeat_selection(self):
        name = '林陈婚宴讨论'
        context = {**self.context, 'source_text': name + '，22桌', 'offer_confirmation': True}
        request = {**self.change(), 'case_name': name}
        request['changes'][0]['quote'] = '22桌'
        saved = self.call('case-update', request, principal=self.private,
                         context=self.confirmed('case-update', request, context, 0))
        self.assertEqual('recorded', saved['status'], saved)
        for source in (name, '请查看' + name,
                       '请把这轮文件作为“' + name + '”的共享版本，其他内容保留私人。',
                       '我刚才已确认，请读取 "' + name + '" 当前的结果。'):
            with self.subTest(source=source):
                read_context = {**context, 'source_text': source, 'share_allowed': False}
                result = self.call('case-read', {'case_name': name},
                                   principal=self.private, context=read_context)
                self.assertEqual('found', result['status'], result)
                self.assertEqual(saved['case'], result['case'])
                self.assertEqual(source, read_context['source_text'])
                self.assertFalse(read_context['share_allowed'])
        for source in ('请看“' + name + '”，另看赵钱婚宴讨论。',
                       '周' + name, '请看“周' + name + '”', name + '二', '请查看' + name + '二'):
            with self.subTest(source=source):
                result = self.call('case-read', {'case_name': name}, principal=self.private,
                                   context={**context, 'source_text': source})
                self.assertEqual('needs_confirmation', result['status'], result)
        source = '请把23桌记入“' + name + '”'
        change = {**request, 'expected_revision': 1, 'changes': [dict(
            field='桌数', value='23桌', state='proposed', quote='23桌')]}
        pending = self.call('case-update', change, principal={**self.private, 'message_id': 'quoted-write'},
                            context={**context, 'source_text': source})
        self.assertEqual('needs_confirmation', pending['status'], pending)
        unbound = self.call('case-read', {'case_name': name}, principal=self.private,
                            context={**context, 'work_id': 'unbound-long-name', 'source_text': name})
        self.assertEqual('needs_confirmation', unbound['status'], unbound)

    def test_name_separator_does_not_select_an_unbound_work(self):
        self.call('case-update', self.change())
        for principal in (self.principal, self.private):
            context = {**self.context, 'work_id': 'unbound-alias', 'share_allowed': False,
                       'source_text': '林、陈婚宴追加消息\n仍是模拟婚宴。', 'offer_confirmation': True}
            request = {'case_name': '林陈婚宴'}
            self.assertEqual('needs_confirmation', self.call('case-read', request,
                principal=principal, context=context)['status'])
            result = self.call('case-result', dict(command='case-read', input=request),
                               principal=principal, context=context)
            self.assertEqual('not_executed', result['status'])

    def test_bound_name_separator_does_not_hide_other_projects_or_grant_membership(self):
        saved = self.call('case-update', self.change())
        invitation = dict(case_name='林陈婚宴', expected_revision=1,
                          member_name='manager', responsibility='运营执行')
        update = {**self.change(), 'expected_revision': 1}
        for source in ('林、陈婚宴和赵钱婚宴', '周林、陈婚宴', '赵、钱婚宴',
                       '仍是另一场赵钱婚宴', '赵钱婚宴是哪场婚宴',
                       '赵钱婚宴，仍是模拟婚宴', '请把赵钱婚宴存进林陈婚宴'):
            context = {**self.context, 'source_text': source, 'offer_confirmation': True}
            for command, request in (('case-read', {'case_name': '林陈婚宴'}),
                                     ('case-update', update), ('case-member-add', invitation)):
                with self.subTest(source=source, command=command):
                    result = self.call(command, request, context=context)
                    self.assertEqual('needs_confirmation', result['status'], result)
        context = {**self.context, 'source_text': '林、陈婚宴追加消息\n仍是模拟婚宴。',
                   'offer_confirmation': True}
        result = self.call('case-member-add', invitation, context=context)
        self.assertEqual('needs_confirmation', result['status'], result)
        self.call('case-read', {'case_name': '林陈婚宴'}, principal=self.operations)
        refused = self.call('case-member-add', invitation,
            context={**context, 'source_text': '林陈婚宴'}, principal=self.operations)
        self.assertEqual('project_owner_required', refused['code'], refused)
        current = self.call('case-read', {'case_name': '林陈婚宴'})['case']
        self.assertEqual(saved['case'], current)

    def test_bound_private_alias_read_keeps_original_sharing_permission(self):
        self.call('case-update', self.change())
        context = {**self.context, 'share_allowed': False, 'source_text': '林陈婚宴'}
        self.assertEqual('found', self.call('case-read', {'case_name': '林陈婚宴'},
            principal=self.private, context=context)['status'])
        context['source_text'] = '林、陈婚宴追加消息\n仍是模拟婚宴。不要同步。'
        self.assertEqual('found', self.call('case-read', {'case_name': '林陈婚宴'},
            principal=self.private, context=context)['status'])
        refused = self.call('case-update', {**self.change(), 'expected_revision': 1},
                            principal=self.private, context=context)
        self.assertEqual('case_share_not_authorized', refused['code'])
        self.assertFalse(context['share_allowed'])

    def test_bound_stored_name_with_separator_keeps_identity_and_source(self):
        name = '林、陈婚宴'
        self.options['project_context']['group_case'] = name
        self.context['source_text'] = name + '，客户要求22桌，A套餐。'
        request = {**self.change(), 'case_name': name}
        saved = self.call('case-update', request)
        self.assertEqual('recorded', saved['status'], saved)
        read = self.call('case-read', {'case_name': name})
        self.assertEqual('found', read['status'], read)
        self.assertEqual(name, read['case']['name'])
        self.assertEqual(self.context['source_text'], read['case']['facts']['桌数']['source']['quote'])

    def test_distinct_registered_names_are_not_collapsed_by_mention_comparison(self):
        self.call('case-update', self.change())
        other_name = '林、陈婚宴'
        other_context = {**self.context, 'work_id': 'private-punctuated-case',
                         'source_text': other_name + '，客户要求22桌，A套餐。'}
        request = {**self.change(), 'case_name': other_name}
        request['changes'][0]['quote'] = other_context['source_text']
        saved = self.call('case-update', request, principal=self.private, context=other_context)
        self.assertEqual('recorded', saved['status'], saved)
        for principal, context, target, mentioned in (
            (self.principal, self.context, '林陈婚宴', other_name),
            (self.private, other_context, other_name, '林陈婚宴'),
        ):
            result = self.call('case-read', {'case_name': target}, principal=principal,
                              context={**context, 'source_text': mentioned, 'offer_confirmation': True})
            self.assertEqual('needs_confirmation', result['status'], result)
            current = self.call('case-read', {'case_name': target}, principal=principal, context=context)
            self.assertEqual('found', current['status'], current)
            self.assertEqual(target, current['case']['name'])
        listed = self.call('case-list', {}, principal=self.private, context=other_context)
        self.assertEqual({'林陈婚宴', other_name}, {row['name'] for row in listed['cases']})

    def test_other_conditions_unchanged_does_not_veto_specific_share_confirmation(self):
        _, context, original = self.private_project()
        source = '先换个事，周许婚宴是澄禾婚宴团队的虚构练习，套餐价格按公司最新版。这条同步给运营，其余条件先不改。'
        context = {**context, 'source_text': source, 'original_text': source,
                   'share_allowed': False, 'offer_confirmation': True}
        principal = {**self.private, 'message_id': 'share-price-basis'}
        request = dict(case_name='周许婚宴', expected_revision=1, changes=[dict(
            field='金额依据', value='澄禾婚宴团队的虚构练习，套餐价格按公司最新版',
            state='proposed', quote='周许婚宴是澄禾婚宴团队的虚构练习，套餐价格按公司最新版')])
        pending = self.call('case-update', request, principal=principal, context=context)
        self.assertEqual('needs_confirmation', pending['status'], pending)
        for value in ('金额依据', '公司最新版', '供该项目成员读取'):
            self.assertIn(value, pending['question'])
        self.assertEqual('not_executed', self.call('case-result',
            dict(command='case-update', input=request), principal=principal, context=context)['status'])
        for denied in ('不要同步给运营，其余条件先不改。', '这条不改，其余条件先不改。',
                       '别共享，其他条件不改。', '其余条件先不改。',
                       '材料写着“其余条件先不改”，请先看看。', '其他条件不改价格。'):
            with self.subTest(denied=denied):
                # The model cannot hide the denial by retaining only its selected source.
                result = self.call('case-update', request, principal=principal,
                    context={**context, 'original_text': denied})
                self.assertEqual('case_share_not_authorized', result['code'], result)
        self.assertEqual('case_share_not_authorized', self.call('case-update', request,
            principal=principal, context={**context, 'offer_confirmation': False})['code'])
        saved = self.call('case-update', request, principal=principal,
            context=self.confirmed('case-update', request, context, 1))
        self.assertEqual('recorded', saved['status'], saved)
        self.assertEqual(original['case']['project'], saved['case']['project'])
        self.assertEqual(original['case']['facts'],
            {k: v for k, v in saved['case']['facts'].items() if k != '金额依据'})
        self.assertFalse(context['share_allowed'])

    def test_batch_preview_keeps_original_values_when_later_change_needs_confirmation(self):
        _, context, _ = self.private_project()
        context = {**context, 'source_text': '桌数改为23桌；迎宾11:30', 'share_allowed': True,
                   'offer_confirmation': True}
        request = dict(case_name='周许婚宴', expected_revision=1, changes=[
            dict(field='桌数', value='23桌', quote='桌数改为23桌', state='proposed', replaces=True),
            dict(field='迎宾时间', value='11:30', quote='迎宾11:30', state='proposed', replaces=True)])
        pending = self.call('case-update', request,
            principal={**self.private, 'message_id': 'batch-preview'}, context=context)
        self.assertEqual('needs_confirmation', pending['status'], pending)
        self.assertIn('原记录：22桌', pending['question'])
        self.assertNotIn('原记录：23桌', pending['question'])

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
