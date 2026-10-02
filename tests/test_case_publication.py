"""Selected accepted files: explicit confirmation, atomic publication and access."""
import copy
import json
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from unittest import mock

from myanc_crm import shared_cases as cases
import test_case_confirmation as fixtures


class CasePublicationTests(unittest.TestCase):
    setUp = fixtures.CaseConfirmationTests.setUp
    call = fixtures.CaseConfirmationTests.call
    change = fixtures.CaseConfirmationTests.change
    private_project = fixtures.CaseConfirmationTests.private_project
    confirmed = fixtures.CaseConfirmationTests.confirmed

    def selection(self):
        _, context, original = self.private_project()
        request = dict(case_name='周许婚宴', expected_revision=1, delivery_ids=['budget', 'plan'])
        context = dict(context, source_text='请发布周许婚宴的选定成果',
                       original_text='请发布周许婚宴的选定成果', share_allowed=False,
                       offer_confirmation=True, publication_files=[
                           dict(delivery_id='budget', name='预算.xlsx', sha256='a' * 64,
                                version=3, message_receipt='private-budget-receipt'),
                           dict(delivery_id='plan', name='建议.docx', sha256='b' * 64,
                                version=1, message_receipt='private-plan-receipt')])
        principal = dict(self.private, message_id='publish-selected-files')
        return request, context, principal, original

    def publish(self, request, context, principal):
        return self.call('case-publish', request, principal=principal,
                         context=self.confirmed('case-publish', request, context, request['expected_revision']))

    def snapshot(self):
        with closing(sqlite3.connect(self.path)) as db:
            return {name: db.execute('SELECT * FROM ' + name + ' ORDER BY rowid').fetchall()
                    for name in ('shared_case_versions', 'shared_case_bindings', 'shared_case_artifacts')}

    def test_selected_files_require_confirmation_then_members_can_read_exact_publication(self):
        request, context, principal, original = self.selection()
        before = self.snapshot()
        pending = self.call('case-publish', request, principal=principal, context=context)
        self.assertEqual('needs_confirmation', pending['status'], pending)
        for text in ('预算.xlsx', '建议.docx', '已交付版本 3', '项目成员', '其他私聊内容保持私有'):
            self.assertIn(text, pending['question'])
        self.assertNotIn('private-budget-receipt', pending['question'])
        self.assertEqual(before, self.snapshot())
        self.assertEqual('needs_confirmation', self.call('case-publish', request, principal=principal,
            context=dict(context, share_allowed=True))['status'])
        denied = self.call('case-publish', request, principal=principal,
            context=dict(context, original_text='不要共享文件'))
        self.assertIn(denied['status'], ('blocked', 'needs_selection'))
        self.assertEqual(before, self.snapshot())
        saved = self.publish(request, context, principal)
        self.assertEqual('recorded', saved['status'], saved)
        self.assertEqual(2, saved['case']['revision'])
        self.assertEqual(original['case']['facts'], saved['case']['facts'])
        self.assertEqual(original['case']['project'], saved['case']['project'])
        publications = saved['publications']
        self.assertEqual(2, len(publications))
        self.assertEqual({'kind', 'publication_id', 'name', 'sha256', 'file_version', 'case_revision'},
                         set(publications[0]))
        publication = publications[0]['publication_id']
        self.assertTrue(publication.startswith('casepub_'))
        recipient = dict(work_id='recipient-work', source_text='接手周许婚宴', share_allowed=False)
        access = dict(publication_id=publication, require_binding=True)
        self.assertEqual('blocked', self.call('case-access', access,
            principal=self.operations_private, context=recipient)['status'])
        invite = dict(case_name='周许婚宴', expected_revision=2,
                      member_name='operations', responsibility='运营执行')
        invitation_context = dict(context, source_text='周许婚宴，请让operations接手运营执行',
                                  original_text='周许婚宴，请让operations接手运营执行')
        invited = self.call('case-member-add', invite, principal=dict(principal, message_id='invite'),
                            context=invitation_context)
        self.assertEqual('recorded', invited['status'], invited)
        self.assertEqual('blocked', self.call('case-access', access,
            principal=self.operations_private, context=recipient)['status'])
        viewed = self.call('case-read', {'case_name': '周许婚宴'},
                           principal=self.operations_private, context=recipient)
        self.assertEqual('found', viewed['status'], viewed)
        self.assertEqual(2, len(viewed['case']['artifacts']))
        self.assertNotIn('private-budget-receipt', json.dumps(viewed))
        self.assertNotIn('source', viewed['case']['artifacts'][0])
        authorized = self.call('case-access', access, principal=self.operations_private, context=recipient)
        self.assertEqual('authorized', authorized['status'], authorized)
        self.assertNotIn('source_chat_id', authorized)
        expected = dict(context['publication_files'][0], work_id=context['work_id'],
                        **{key: principal[key] for key in ('platform', 'user_id', 'chat_id', 'project', 'session_key')})
        self.assertEqual(expected, authorized['source'])
        for denied in [dict(publication_id=publication, require_binding=False),
                       dict(receipt=publication, require_binding=True),
                       dict(receipt='private-budget-receipt', require_binding=True),
                       dict(access, receipt='private-budget-receipt')]:
            self.assertEqual('blocked', self.call('case-access', denied,
                principal=self.operations_private, context=recipient)['status'])
        self.assertEqual('blocked', self.call('case-access', access,
            principal=dict(self.operations_private, chat_id='unregistered'), context=recipient)['status'])
        # Later private files/notes do not change the frozen public version or grants.
        after = self.snapshot()
        context['publication_files'].append(dict(delivery_id='private-note', name='私下备注.txt',
            sha256='c' * 64, version=1, message_receipt='private-note-receipt'))
        self.assertEqual('blocked', self.call('case-access',
            dict(receipt='private-note-receipt', require_binding=True),
            principal=self.operations_private, context=recipient)['status'])
        self.assertEqual(after, self.snapshot())
        with closing(sqlite3.connect(self.path)) as db:
            self.assertEqual({'shared_case_versions', 'shared_case_bindings', 'shared_case_artifacts'},
                             {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")})

    def test_replay_and_result_are_exact_read_only_and_work_scoped(self):
        request, context, principal, _ = self.selection()
        query = dict(command='case-publish', input=request)
        before = self.snapshot()
        self.assertEqual('not_executed', self.call('case-result', query,
            principal=principal, context=context)['status'])
        self.assertEqual(before, self.snapshot())
        saved = self.publish(request, context, principal)
        after = self.snapshot()
        replay = self.publish(request, context, principal)
        recovered = self.call('case-result', query, principal=principal, context=context)
        for result in (replay, recovered):
            self.assertTrue(result['replayed'], result)
            self.assertEqual(saved['publications'], result['publications'])
        self.assertEqual(after, self.snapshot())
        changed = copy.deepcopy(context)
        changed['publication_files'][0]['sha256'] = 'c' * 64
        for altered in (changed, dict(context, work_id='another-work')):
            self.assertEqual('blocked', self.call('case-result', query,
                principal=principal, context=altered)['status'])
        self.assertEqual('blocked', self.call('case-result', query,
            principal=dict(principal, session_key='another-session'), context=context)['status'])
        self.assertEqual(after, self.snapshot())

    def test_revision_conflict_or_storage_failure_never_partially_publishes(self):
        request, context, principal, _ = self.selection()
        before = self.snapshot()
        with mock.patch.object(cases, '_save_version', side_effect=sqlite3.OperationalError('fixture')):
            self.assertEqual('unavailable', self.publish(request, context, principal)['status'])
        self.assertEqual(before, self.snapshot())
        self.assertEqual('not_executed', self.call('case-result', dict(command='case-publish', input=request),
            principal=principal, context=context)['status'])
        self.assertEqual('recorded', self.publish(request, context, principal)['status'])
        after = self.snapshot()
        conflict = self.publish(request, context, dict(principal, message_id='competing-publication'))
        self.assertEqual('conflict', conflict['status'], conflict)
        self.assertEqual(after, self.snapshot())

    def test_concurrent_publications_consume_one_revision(self):
        request, context, principal, _ = self.selection()
        def publish(index):
            return self.publish(request, context, dict(principal, message_id=f'publication-{index}'))['status']
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(['conflict', 'recorded'], sorted(pool.map(publish, range(2))))
        saved = self.snapshot()
        self.assertEqual(2, len(saved['shared_case_artifacts']))
        self.assertEqual(2, len(saved['shared_case_versions']))

    def test_model_fields_cannot_supply_source_or_override_host_selection(self):
        request, context, principal, _ = self.selection()
        before = self.snapshot()
        for extra in ('publication_files', 'source', 'message_receipt', 'confirmation', 'publication_id'):
            self.assertEqual('blocked', self.call('case-publish', dict(request, **{extra: 'forged'}),
                principal=principal, context=context)['status'])
        for missing in request:
            changed = {key: value for key, value in request.items() if key != missing}
            self.assertEqual('blocked', self.call('case-publish', changed,
                principal=principal, context=context)['status'])
        for ids in ([], ['budget', 'budget'], ['unknown'], ['budget', 'plan', 'x', 'y', 'z']):
            self.assertEqual('blocked', self.call('case-publish', dict(request, delivery_ids=ids),
                principal=principal, context=context)['status'])
        for changed in (dict(context, publication_files=[]), dict(context, publication_files='forged')):
            self.assertEqual('blocked', self.call('case-publish', request,
                principal=principal, context=changed)['status'])
        for field, value in [('version', True), ('version', 0), ('sha256', 'invalid'), ('status', 'unknown')]:
            changed = copy.deepcopy(context)
            changed['publication_files'][0][field] = value
            self.assertEqual('blocked', self.publish(request, changed, principal)['status'])
        self.assertEqual(before, self.snapshot())

    def test_other_project_or_borrowed_answer_and_legacy_artifact_do_not_publish(self):
        request, context, principal, _ = self.selection()
        before = self.snapshot()
        self.assertEqual('blocked', self.call('case-publish', request, principal=principal,
            context=self.confirmed('case-read', {'case_name': request['case_name']}, context, 1))['status'])
        self.assertNotEqual('recorded', self.publish(dict(request, case_name='别的婚宴'), context, principal)['status'])
        self.assertEqual('not_found', self.publish(request, context, self.operations_private)['status'])
        self.assertEqual('not_shared', self.call('case-artifact',
            dict(phase='prepare', request_key='f' * 64, existing_delivery=False),
            principal=principal, context=context)['status'])
        self.assertEqual(before, self.snapshot())


if __name__ == '__main__':
    unittest.main()
