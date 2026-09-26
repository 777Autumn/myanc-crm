"""Fictional six-entry replay. No host, credentials, model or network access."""
import json
import unittest

from ops.maintenance_activity import log_fields
from ops.maintenance_health import ADMIN_WARNING, journal_command, shutdown_health, startup_health


def journal(messages):
    return '\n'.join(json.dumps(dict(__REALTIME_TIMESTAMP=str((n + 1) * 1000000), MESSAGE=m))
                     for n, m in enumerate(messages))


def fixture():
    projects = {f'example-{i}': f'worker-{i}' for i in range(6)}
    messages = ['2026/01/01 00:00:01 INFO acquired instance lock path=/example/.lock',
                '2026/01/01 00:00:02 INFO config loaded path=/example/config.toml']

    def add(event, **fields):
        messages.append(json.dumps(dict(level='INFO', msg=event) | fields))

    add('run_as_user: running startup safety checks', project_count=6)
    for project, user in projects.items():
        add('run_as_user: preflight warning', level='WARN', project=project, message='fictional reviewed warning')
        add('run_as_user: isolation audit completed', project=project, whoami=user,
            workdir_writable=True, target_paths=3, cross_user_results=5)
        add('session: loaded from disk', path=f'/example/{project}/sessions.json', sessions=2)
        add(ADMIN_WARNING, level='WARN', project=project)
    for count in range(2, 7):
        add('feishu: sharing WebSocket connection', app_id='fictional-application', platforms=count)
    add('feishu: interactive card mode enabled, ensure card.action.trigger event is subscribed in Feishu console')
    for project in projects:
        add('platform ready', project=project, platform='feishu')
        add('engine started', project=project, agent='claude', platforms=1)
    add('cron: scheduler started', jobs=0)
    add('timer: scheduler started', scheduled=0, missed_fired=0, skipped_stale=0, total=0)
    add('api server started', socket='/example/run/api.sock')
    add('cc-connect is running', projects=6)
    expected = [log_fields(m) for m in messages]
    messages.append('2026/01/01 00:00:50 [Info] [connected to wss://example.invalid/ws [conn_id=fictional]')
    return projects, messages, expected


class MaintenanceHealthTests(unittest.TestCase):
    def setUp(self):
        self.projects, self.messages, self.expected = fixture()

    def health(self, messages=None):
        return startup_health(journal(self.messages if messages is None else messages), 200,
                              self.projects, self.expected)

    def index(self, message):
        return next(i for i, m in enumerate(self.messages) if log_fields(m)['msg'] == message)

    def changed(self, index, **fields):
        messages = self.messages.copy()
        messages[index] = json.dumps(log_fields(messages[index]) | fields)
        return messages

    def test_reviewed_startup_and_long_complete_messages(self):
        self.assertEqual(50, len(self.messages))
        self.assertTrue(self.health()['ready'])
        index = self.index('session: loaded from disk')
        self.messages[index] = json.dumps(log_fields(self.messages[index]) | {'path': '/example/' + 'a' * 18000})
        self.expected = [log_fields(m) for m in self.messages[:-1]]
        self.assertTrue(self.health()['ready'])
        with self.assertRaisesRegex(ValueError, 'unsupported_journal_record'):
            self.health(self.messages[:index] + [None] + self.messages[index + 1:])

    def test_missing_null_binary_and_malformed_records(self):
        for record in ({'MESSAGE': None}, {}, {'MESSAGE': [1, 2]}, [],
                       {'MESSAGE': 'level=INFO msg="truncated'}, {'MESSAGE': '{}'}):
            with self.subTest(record=record):
                if isinstance(record, dict):
                    record = dict(__REALTIME_TIMESTAMP='1000000', **record)
                with self.assertRaisesRegex(ValueError, '^unsupported_journal_record$'):
                    startup_health(json.dumps(record), 200, self.projects, self.expected)

    def test_changed_warning_unknown_warning_error_business_and_sdk_error(self):
        warning = self.index('run_as_user: preflight warning')
        cases = {
            'changed_warning_detail': self.changed(warning, unexpected=True),
            'unknown_warning': self.messages + ['level=WARN msg=unknown'],
            'error': self.messages + ['level=ERROR msg=bad'],
            'business': self.messages + ['level=INFO msg="message received"'],
            'unsolicited': self.messages + ['level=INFO msg="unsolicited events detected, relaying to platform"'],
            'unknown_info': self.messages + ['level=INFO msg="new undocumented startup event"'],
            'sdk_error': self.messages + ['[Error] websocket failed'],
            'sdk_disconnected': self.messages + ['[Info] [disconnected]'],
            'sdk_unknown_info': self.messages + ['[Info] unexplained'],
        }
        for name, messages in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.health(messages)

    def test_identity_and_audit_details_remain_exact(self):
        index = self.index('run_as_user: isolation audit completed')
        for name, value in (('whoami', 'another-worker'), ('workdir_writable', False),
                            ('cross_user_results', 0), ('target_paths', 0)):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.health(self.changed(index, **{name: value}))

    def test_missing_or_duplicate_events_are_not_ready(self):
        for event in ('run_as_user: isolation audit completed', 'run_as_user: preflight warning',
                      'platform ready', 'engine started', 'feishu: sharing WebSocket connection'):
            index = self.index(event)
            with self.subTest(event=event):
                self.assertFalse(self.health(self.messages[:index] + self.messages[index + 1:])['ready'])
                self.assertFalse(self.health(self.messages + [self.messages[index]])['ready'])
        self.assertFalse(self.health(self.messages[:-1])['ready'])
        self.assertFalse(self.health(self.messages + [self.messages[-1]])['ready'])

    def test_unknown_info_cannot_be_approved_by_learning_from_the_current_log(self):
        message = {'level': 'INFO', 'msg': 'unknown event'}
        self.expected.append(message)
        with self.assertRaisesRegex(ValueError, 'startup_activity_or_error'):
            self.health(self.messages + [json.dumps(message)])

    def test_warning_cannot_masquerade_as_known_startup_event(self):
        index = self.index('platform ready')
        for level in ('WARN', 'ERROR'):
            with self.subTest(level=level):
                with self.assertRaisesRegex(ValueError, 'startup_activity_or_error'):
                    self.health(self.changed(index, level=level))

    def test_complete_reader_command_has_scope_and_all_without_row_limit(self):
        command = journal_command('123', 'a' * 32)
        self.assertIn('--all', command)
        self.assertIn('_PID=123', command)
        self.assertIn('_SYSTEMD_INVOCATION_ID=' + 'a' * 32, command)
        self.assertNotIn('-n', command)
        for pid, invocation in (('0', 'a' * 32), ('-1', 'a' * 32), ('123', 'bad')):
            with self.assertRaises(ValueError):
                journal_command(pid, invocation)

    def test_normal_bye_needs_independent_clean_exit_evidence(self):
        exit_status = dict(Result='success', ExecMainCode='1', ExecMainStatus='0',
                           ActiveState='inactive', MainPID='0', NRestarts='0', receivers=[])
        messages = ['level=INFO msg="shutting down..."',
                    'level=INFO msg="claudeSession: exited cleanly after stdin close"',
                    'level=WARN msg="feishu: primary shutting down, secondary platforms will lose event source" remaining=5',
                    'level=INFO msg=bye']
        self.assertTrue(shutdown_health(journal(messages), 200, 6, exit_status)['clean_exit'])
        for key, value in (('Result', 'failed'), ('ExecMainStatus', '1'), ('ExecMainCode', '2'),
                           ('ActiveState', 'active'), ('MainPID', '123'), ('NRestarts', '1'),
                           ('receivers', ['123'])):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, 'main_exit_not_normal'):
                    shutdown_health(journal(messages), 200, 6, exit_status | {key: value})
        for case in ([messages[-1]], messages[:-1], messages + [messages[-1]],
                     messages[:1] + ['level=INFO msg="unknown shutdown event"'] + messages[1:]):
            with self.assertRaises(ValueError):
                shutdown_health(journal(case), 200, 6, exit_status)


if __name__ == '__main__':
    unittest.main()
