import copy
import sqlite3
import unittest

from ops.personal_connection_migration import apply_registry, native_work_session, plan_history
import test_connections


class HistoryMigrationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_connections.ConnectionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.connect()
        self.c = self.fixture.connections
        self.p = self.fixture.principal
        self.c.guard('customer', self.p, self.fixture.token, 'bound')
        with self.c.database() as db:
            self.rows = [dict(r) for r in db.execute('SELECT * FROM connections')]
            self.bindings = [dict(r) for r in db.execute('SELECT * FROM connection_work')]
        self.sessions = {sid: dict(id=sid, created_at='2026-10-05T10:00:00.123456789Z',
                                  agent_session_id='native-'+sid, history=[{'content': 'fixture'}])
                         for sid in ('bound', 'unknown', 'no-work', 'group')}
        self.snapshots = {'fixture': dict(sessions=self.sessions, active_session={'private-session': 'unknown', 'group-key': 'group'},
                                        user_sessions={'private-session': ['bound', 'unknown', 'no-work'], 'group-key': ['group']})}
        self.works = {sid: dict(ID=sid, Principal=self.p, SessionID=native_work_session(self.sessions[sid]))
                      for sid in ('bound', 'unknown')}
        self.entrances = [dict(principal=self.p, snapshot='fixture', session_key='private-session',
                               orphan_native_ids=['orphan-native'])]

    def plan(self):
        return plan_history(self.fixture.config, self.works, self.snapshots, self.entrances, self.rows, self.bindings)

    def test_unknown_history_expires_without_erasing_artifacts_or_shared_work(self):
        before = copy.deepcopy((self.works, self.snapshots))
        plan = self.plan()
        result = plan['snapshots']['fixture']
        self.assertFalse(result['sessions']['bound'].get('connection_expired', False))
        for sid in ('unknown', 'no-work'):
            self.assertTrue(result['sessions'][sid]['connection_expired'])
            self.assertEqual(self.sessions[sid]['history'], result['sessions'][sid]['history'])
            self.assertEqual(self.sessions[sid]['agent_session_id'], result['sessions'][sid]['agent_session_id'])
        self.assertEqual(self.sessions['group'], result['sessions']['group'])
        self.assertNotIn('private-session', result['active_session'])
        self.assertEqual('group', result['active_session']['group-key'])
        orphan = [s for s in result['sessions'].values() if s['agent_session_id'] == 'orphan-native']
        self.assertEqual(1, len(orphan))
        self.assertTrue(orphan[0]['connection_expired'])
        self.assertEqual(before, (self.works, self.snapshots))
        self.assertEqual('bound@1791194400123456789', native_work_session(self.sessions['bound']))
        # Execute twice against the real old four-column schema.
        with sqlite3.connect(self.c.path) as db:
            apply_registry(db, plan)
            apply_registry(db, plan)
            self.assertEqual(-1, db.execute('SELECT version FROM connection_work WHERE work="unknown"').fetchone()[0])
            self.assertEqual(2, db.execute('SELECT COUNT(*) FROM connection_work').fetchone()[0])
        self.fixture.assertBlocked('connection_session_expired',
            lambda: self.c.guard('customers', self.p, self.fixture.token+'fresh', 'unknown'))

    def test_conflicts_stop_before_mutation_and_old_generations_stay_expired(self):
        plan = self.plan()
        with sqlite3.connect(self.c.path) as db:
            db.execute('UPDATE connections SET version=version+1')
            db.commit()
            with self.assertRaisesRegex(ValueError, 'generation changed'):
                apply_registry(db, plan)
            self.assertEqual(1, db.execute('SELECT COUNT(*) FROM connection_work').fetchone()[0])
        self.rows[0]['version'] += 1
        plan = self.plan()
        self.assertTrue(plan['snapshots']['fixture']['sessions']['bound']['connection_expired'])
        self.bindings[0]['subject'] = 'another-user'
        with self.assertRaisesRegex(ValueError, 'subject conflict'):
            self.plan()


if __name__ == '__main__':
    unittest.main()
