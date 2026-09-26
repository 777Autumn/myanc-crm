"""Pure checks for reviewed startup/shutdown journals, never service operations.

The caller freezes expected startup fields from source/configuration and reviewed
evidence before maintenance. Never learn an allowlist from the journal being
checked. Process identity, control hashes and business-state checks remain with
the existing maintenance caller.
"""
from collections import Counter
import hashlib
import json
import re

from ops.maintenance_activity import log_key, parse_journal


ADMIN_WARNING = ('admin_from is not set — privileged commands (/shell, /show, /dir, /restart, /upgrade) '
                 'are blocked. Set admin_from in config to enable them, or use disabled_commands to hide them.')
STARTUP_INFO = {
    'acquired instance lock', 'config loaded', 'run_as_user: running startup safety checks',
    'run_as_user: isolation audit completed', 'session: loaded from disk',
    'feishu: sharing WebSocket connection',
    'feishu: interactive card mode enabled, ensure card.action.trigger event is subscribed in Feishu console',
    'platform ready', 'engine started', 'cron: scheduler started',
    'timer: scheduler started', 'api server started', 'cc-connect is running',
}
STARTUP_WARN = {'run_as_user: preflight warning', ADMIN_WARNING}


def journal_command(pid, invocation):
    """No row/size truncation: callers must fail if collection itself fails."""
    if not isinstance(pid, str) or not re.fullmatch(r'[1-9][0-9]*', pid):
        raise ValueError('invalid_journal_pid')
    if not isinstance(invocation, str) or not re.fullmatch(r'[a-f0-9]{32}', invocation):
        raise ValueError('invalid_journal_invocation')
    return ['journalctl', '-b', '0', '-u', 'cc-connect.service', '_PID=' + pid,
            '_SYSTEMD_INVOCATION_ID=' + invocation, '-o', 'json', '--all', '--no-pager']


def _fingerprint(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()


def _startup_fields(fields, projects):
    level, message = fields.get('level'), fields.get('msg')
    if level == 'WARN' and message in STARTUP_WARN:
        if fields.get('project') not in projects:
            raise ValueError('startup_warning_project_changed')
    elif level != 'INFO' or message not in STARTUP_INFO:
        raise ValueError('startup_activity_or_error')
    if message == 'run_as_user: isolation audit completed':
        if (fields.get('project') not in projects
                or fields.get('whoami') != projects[fields['project']]
                or not (fields.get('workdir_writable') is True or fields.get('workdir_writable') == 'true')):
            raise ValueError('isolation_audit_changed')


def startup_health(journal, now, projects, expected_messages):
    """Match exact frozen startup fields; incomplete readiness returns false.

    The sole variable SDK connection line has a fixed shape. All other fields,
    including warning details and isolation audit counts, must match the reviewed
    expectation. Missing or duplicate events cannot satisfy readiness.
    """
    if not projects or any(not isinstance(k, str) or not k or not isinstance(v, str) or not v
                           for k, v in projects.items()):
        raise ValueError('invalid_expected_projects')
    expected_messages = tuple(expected_messages)
    for fields in expected_messages:
        _startup_fields(fields, projects)
    expected = Counter(log_key(fields) for fields in expected_messages)
    rows = parse_journal(journal, now)
    actual, connections = Counter(), 0
    fields_list = []
    for _, fields in rows:
        if fields.get('format') == 'sdk':
            if fields.get('level') != 'INFO' or not re.fullmatch(
                    r'\[connected to wss://[^\s\]]+ \[conn_id=[^\]\s]+\]', fields['msg']):
                raise ValueError('sdk_connection_failure')
            connections += 1
            continue
        _startup_fields(fields, projects)
        key = log_key(fields)
        if key not in expected:
            raise ValueError('startup_fields_changed')
        actual[key] += 1
        fields_list.append(fields)
    project_counts = Counter(projects.keys())
    matched_projects = all(Counter(f.get('project') for f in fields_list if f['msg'] == event)
                           == project_counts for event in
                           ('run_as_user: isolation audit completed', 'platform ready', 'engine started'))
    sharing = sum(f['msg'] == 'feishu: sharing WebSocket connection' for f in fields_list)
    return dict(ready=actual == expected and matched_projects and connections == 1
                and sharing == len(projects) - 1,
                records=len(rows), sdk_connections=connections, fingerprint=_fingerprint(rows))


def shutdown_health(journal, now, project_count, exit_status):
    """Classify the shutdown suffix only, with independently sampled clean exit.

    The caller must also verify its unchanged invocation and retained journal
    prefix. A `bye` line alone is never proof the process has exited normally.
    """
    expected_exit = dict(Result='success', ExecMainCode='1', ExecMainStatus='0',
                         ActiveState='inactive', MainPID='0', NRestarts='0', receivers=[])
    if (not isinstance(project_count, int) or isinstance(project_count, bool) or project_count < 1
            or any(exit_status.get(k) != v for k, v in expected_exit.items())):
        raise ValueError('main_exit_not_normal')
    rows = parse_journal(journal, now)
    events = []
    for _, fields in rows:
        message, level = fields['msg'], fields.get('level')
        if level == 'INFO' and message in {'shutting down...', 'bye', 'claudeSession: exited cleanly after stdin close'}:
            if set(fields) - {'time', 'level', 'msg'}:
                raise ValueError('shutdown_fields_changed')
        elif level == 'WARN' and message == 'feishu: primary shutting down, secondary platforms will lose event source':
            if (set(fields) - {'time', 'level', 'msg', 'remaining'} or
                    str(fields.get('remaining')) not in {str(n) for n in range(1, project_count)}):
                raise ValueError('unexpected_shutdown_platform_count')
        else:
            raise ValueError('unclassified_or_business_event_during_shutdown')
        events.append(message)
    counts = Counter(events)
    if (not events or events[0] != 'shutting down...' or events[-1] != 'bye'
            or counts['shutting down...'] != 1 or counts['bye'] != 1
            or counts['claudeSession: exited cleanly after stdin close'] > project_count
            or counts['feishu: primary shutting down, secondary platforms will lose event source'] > 1):
        raise ValueError('unexpected_shutdown_sequence')
    return dict(clean_exit=True, records=len(rows), fingerprint=_fingerprint(rows))
