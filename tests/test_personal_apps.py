"""Different AppBot open IDs share membership, never transport sessions or tokens."""
import copy
import unittest

from myanc_crm import cli, core, connections as identity
from myanc_crm.connections import Connections, ConnectionBlocked
import test_connections as connection_fixture
import test_project_context as project_fixture


class PersonalAppConnectionsTests(unittest.TestCase):
    def setUp(self):
        self.fixture = connection_fixture.ConnectionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def migrated(self):
        f = self.fixture
        config = copy.deepcopy(f.config)
        original = config['personal_connections']['routes'][0]
        original.update(member_id='bot-manager', source_app_id='personal-app', source_tenant_key='fixture-tenant',
                        user_id='personal-open-id', chat_id='personal-chat', project='personal-bot')
        principal = {**f.principal, **{k: original[k] for k in ('platform', 'user_id', 'chat_id', 'project')},
                     'session_key': 'new-physical-session'}
        return config, principal

    def test_new_app_reuses_native_profile_subject_and_generation(self):
        f = self.fixture
        f.connect()
        old = f.connections.require(f.principal, f.token)
        config, principal = self.migrated()
        new = Connections(config, run=f.fake, now=lambda: f.clock)
        before = len(f.fake.calls)
        binding = new.require(principal, f.token + '-personal')
        self.assertEqual(old, binding)
        self.assertFalse(any(call[1:3] == ['auth', 'login'] for call in f.fake.calls[before:]))
        self.assertEqual('bot-manager', identity.resolve_member_id(config, principal))
        self.assertEqual('crm-manager', core._actor_for_principal(principal, config)['feishu_user_id'])
        self.assertEqual(principal, cli._host_prepare_payload({'request': {}, 'principal': principal}, config)[1])
        with self.assertRaises(ConnectionBlocked):
            new.actor(f.principal)
        with self.assertRaises(ConnectionBlocked):
            new.actor({**principal, 'project': 'manager-group'})
        new.command('disconnect', principal)
        with self.assertRaises(ConnectionBlocked):
            f.connections.check_version(old)

    def test_startup_binds_project_app_tenant_and_maintenance_uses_member(self):
        f = self.fixture
        f.connect()
        config, principal = self.migrated()
        new = Connections(config, run=f.fake, now=lambda: f.clock)
        result = new.validate_source('personal-app', 'personal-bot', 'fixture-tenant')
        self.assertEqual(['bot-manager'], result['users'])
        self.assertEqual('personal-open-id', result['bindings'][0]['user_id'])
        for args in [('personal-app',), ('bot-app', 'personal-bot', 'fixture-tenant'),
                     ('personal-app', 'personal-bot', 'other-tenant')]:
            with self.assertRaises(ConnectionBlocked):
                new.validate_source(*args)
        self.assertEqual('bot-manager', new.maintain('bot-manager', member=True)[0]['member_id'])
        config['allowed_actors']['another'] = dict(config['allowed_actors']['bot-manager'])
        with self.assertRaises(ConnectionBlocked):
            Connections(config)

    def test_reminder_binding_keeps_physical_source_and_checks_member_private_app(self):
        config, personal = self.migrated()
        source = dict(self.fixture.principal, chat_id='shared-group', project='manager-group')
        binding = dict(user_id=source['user_id'], source_chat_id=source['chat_id'], project=source['project'],
                       private_chat_id=personal['chat_id'], member_id='bot-manager', private_project=personal['project'],
                       private_user_id=personal['user_id'], private_app_id='personal-app')
        result = cli._plan_host_options({'plan_reminder_binding': binding}, source, config)
        self.assertEqual(binding, result['trusted_plan_binding'])
        for field in ('member_id', 'private_project', 'private_user_id', 'private_app_id', 'private_chat_id', 'user_id'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                cli._plan_host_options({'plan_reminder_binding': dict(binding, **{field: 'another'})}, source, config)
        with self.assertRaises(ValueError):
            cli._plan_host_options({'plan_reminder_binding': {k: binding[k] for k in
                                    ('user_id', 'source_chat_id', 'project', 'private_chat_id')}}, source, config)


class PersonalAppProjectTests(unittest.TestCase):
    def test_existing_membership_survives_new_bot_without_moving_work_or_principal(self):
        f = project_fixture.ProjectContextTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        request, context, saved = f.private_project()
        original = copy.deepcopy(f.private)
        routes = [dict(m, audience='shared' if m['chat_id'] == f.options['group_chat_id'] else 'private')
                  for m in f.options['members']]
        personal = {**original, 'user_id': 'sales-personal-app-open-id', 'chat_id': 'personal-app-chat',
                    'project': 'personal-app', 'session_key': 'personal-app-session'}
        member = {k: personal[k] for k in ('platform', 'user_id', 'chat_id', 'project')}
        f.options['members'].append(member)
        routes.append(dict(member, audience='private', member_id='sales', source_app_id='sales-app', source_tenant_key='tenant'))
        f.config['personal_connections'] = {'routes': routes}
        result = f.call('case-read', {'case_name': request['case_name']}, principal=personal,
                        context={**context, 'work_id': 'fresh-work'})
        self.assertEqual('found', result['status'], result)
        self.assertEqual('sales', result['case']['project']['owner'])
        self.assertEqual(original, f.private)


if __name__ == '__main__':
    unittest.main()
