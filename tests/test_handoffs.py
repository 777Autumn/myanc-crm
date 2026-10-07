import unittest
from types import SimpleNamespace

from myanc_crm import core, handoffs
from test_core import NOW, PRINCIPAL, TOKEN
import test_banquet as sales


class HandoffJourneyTests(unittest.TestCase):
    approve = sales.BanquetJourneyTests.approve
    create = sales.BanquetJourneyTests.create
    stage = sales.BanquetJourneyTests.stage

    def setUp(self):
        sales.BanquetJourneyTests.setUp(self)
        self.recipient = {**PRINCIPAL, 'user_id': 'employee', 'chat_id': 'employee-chat',
                          'session_key': 'employee-session'}
        self.config['allowed_actors']['employee'] = {'display_name': '示例同事', 'feishu_user_id': 'ou_member'}
        self.binding = {'subject': 'owner', 'profile': 'fixed-profile', 'version': 1}
        self.current_version = 1
        def check(binding):
            if binding['version'] != self.current_version:
                raise ValueError('old connection')
        self.backend.runner = SimpleNamespace(binding=self.binding, connections=SimpleNamespace(check_version=check))
        self.business = self.approve(self.create())['banquet']['record_id']
        self.store.rows[('banquets', self.business)]['stage'] = '已签单'
        self.files = [{'delivery_id': 'delivery1', 'name': '虚构交接.docx', 'sha256': 'a' * 64,
                       'version': 1, 'message_receipt': 'file-receipt'}]

    def proposal(self, command='stage-handoff-submit', principal=PRINCIPAL, **fields):
        request = {'banquet_id': self.business, **fields}
        if command == 'stage-handoff-submit':
            request = {'recipient_ref': self.owner, 'delivery_ids': ['delivery1'], 'missing': '菜单待确认', **request}
        return handoffs.stage(command, request, self.backend, self.ledger, self.config, TOKEN + principal['user_id'],
            principal, context={'work_id': 'work1', 'files': self.files}, personal_backend=self.backend, now=NOW)

    def decide(self, staged, principal=PRINCIPAL, files_verified=True):
        self.assertEqual('staged', staged['status'], staged)
        result = core.begin_approval({'change_id': staged['change_id'], 'principal': principal},
            self.backend, self.ledger, self.config, TOKEN + principal['user_id'], NOW)
        self.assertEqual('pending', result['status'], result)
        p = {**principal, 'message_id': 'handoff-card-' + staged['change_id']}
        bound = core.bind_approval_card({'approval_id': result['approval_id'], 'principal': p}, self.ledger, self.config)
        self.assertEqual('bound', bound['status'], bound)
        claim = core.claim_approval_decision({'approval_id': result['approval_id'], 'decision': 'approve', 'principal': p},
            self.ledger, self.config, NOW, backend=self.backend)
        self.assertTrue(claim['execute'], claim)
        self.assertIn('file_check', claim)
        return core.execute_claimed_approval({'approval_id': result['approval_id'], 'principal': p},
            self.backend, self.ledger, self.config, NOW, personal_backend=self.backend,
            handoff_files_verified=files_verified)

    def test_submit_return_revise_and_named_recipient_accepts_current_version(self):
        first = self.proposal()
        self.assertEqual('verified', self.decide(first)['status'])
        original = handoffs.latest(self.store, self.business)
        self.assertEqual('待接手', original['status'])
        wrong = self.proposal('stage-handoff-accept', version=1)
        self.assertEqual('blocked', wrong['status'])
        returned = self.proposal('stage-handoff-return', self.recipient, version=1, reason='请补菜单')
        self.assertEqual('verified', self.decide(returned, self.recipient)['status'])
        second = self.proposal(missing='菜单已补充，场地细节待确认')
        self.assertEqual('verified', self.decide(second)['status'])
        self.assertEqual('已退回', self.store.rows[('handoffs', original['record_id'])]['status'])
        self.assertEqual('blocked', self.proposal('stage-handoff-accept', self.recipient, version=1)['status'])
        accepted = self.proposal('stage-handoff-accept', self.recipient, version=2)
        self.assertEqual('verified', self.decide(accepted, self.recipient)['status'])
        self.assertEqual('已接手', handoffs.latest(self.store, self.business)['status'])
        self.assertEqual('blocked', self.proposal('stage-handoff-accept', self.recipient, version=2)['status'])

    def test_changed_material_does_not_authorize_another_file(self):
        first = self.proposal()
        self.assertEqual('verified', self.decide(first)['status'])
        row = handoffs.latest(self.store, self.business)
        pub = f"bh_{first['change_id']}_0"
        authorized = handoffs.authorize_file(pub, self.backend, self.ledger, self.config, self.recipient)
        self.assertEqual('a' * 64, authorized['source']['sha256'])
        self.store.rows[('handoffs', row['record_id'])]['materials'] = 'forged material'
        with self.assertRaises(ValueError):
            handoffs.authorize_file(pub, self.backend, self.ledger, self.config, self.recipient)
        self.assertEqual('blocked', self.proposal('stage-handoff-accept', self.recipient, version=1)['status'])

    def test_reader_role_uses_host_mapping_not_source_app_id_or_display_name(self):
        self.decide(self.proposal())
        request = {'banquet_id': self.business}
        self.assertNotEqual(self.recipient['user_id'], 'ou_member')
        for principal, expected in ((self.recipient, True), (PRINCIPAL, False)):
            value = handoffs.read(request, self.backend, self.ledger, self.config, principal)
            self.assertIs(value['is_recipient'], expected)
        other = {**self.recipient, 'user_id': 'same-name-other'}
        self.config['allowed_actors']['same-name-other'] = {
            'display_name': '示例同事', 'feishu_user_id': 'ou_other'}
        denied = handoffs.read(request, self.backend, self.ledger, self.config, other)
        self.assertEqual('blocked', denied['status'])
        self.assertNotIn('is_recipient', denied)

    def test_file_failure_and_revocation_do_not_publish_or_acknowledge(self):
        staged = self.proposal()
        self.assertEqual('failed', self.decide(staged, files_verified=False)['status'])
        self.assertIsNone(handoffs.latest(self.store, self.business))
        staged = self.proposal()
        self.current_version = 2
        self.assertEqual('failed', self.decide(staged)['status'])
        self.assertIsNone(handoffs.latest(self.store, self.business))

    def test_manual_status_edit_cannot_forge_recipient_confirmation(self):
        first = self.proposal()
        self.decide(first)
        row = handoffs.latest(self.store, self.business)
        self.store.rows[('handoffs', row['record_id'])]['status'] = '已接手'
        with self.assertRaises(ValueError):
            handoffs.authorize_file(f"bh_{first['change_id']}_0", self.backend, self.ledger, self.config, self.recipient)

    def test_new_version_invalidates_pending_acceptance_and_old_publication(self):
        first = self.proposal()
        self.decide(first)
        old_accept = self.proposal('stage-handoff-accept', self.recipient, version=1)
        # Different real sessions do not supersede one another's approvals.
        new = self.proposal(missing='更新后的待补项')
        self.decide(new)
        with self.assertRaises(ValueError):
            handoffs.authorize_file(f"bh_{first['change_id']}_0", self.backend, self.ledger, self.config, self.recipient)
        result = self.decide(old_accept, self.recipient)
        self.assertEqual('replan_required', result['status'], result)
