"""Host-only handoff notices and start claims, separate from business receipts."""
import json
import secrets

from . import banquet, core, customers, handoffs, publication_basis
from .connections import ROUTE_FIELDS, resolve_member_id


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS handoff_events ('
               'event_id TEXT PRIMARY KEY, kind TEXT NOT NULL, publication_id TEXT NOT NULL, '
               'banquet_id TEXT NOT NULL, version INTEGER NOT NULL, recipient_id TEXT NOT NULL, '
               'target_id TEXT NOT NULL, notification_status TEXT NOT NULL DEFAULT \'pending\', '
               'dispatch_id TEXT, target_json TEXT, message_id TEXT, start_json TEXT, '
               'work_id TEXT UNIQUE, session_id TEXT UNIQUE)')


def finish(ledger, staged):
    """Part of Ledger.finish's verified business receipt transaction."""
    operation = staged.get('operation_type', '')
    if operation not in {'banquet_handoff_submit', 'banquet_handoff_accept', 'banquet_handoff_return'}:
        return
    kind = operation.removeprefix('banquet_handoff_')
    row = staged['handoff_patch'] if kind == 'submit' else staged['handoff_before']
    recipient = customers._owner_ids(row['recipient'])
    submitter = customers._owner_ids(row['submitted_by'])
    if len(recipient) != 1 or len(submitter) != 1:
        raise ValueError('A handoff notice requires exactly two named parties.')
    ledger._db.execute('INSERT OR IGNORE INTO handoff_events '
                       '(event_id,kind,publication_id,banquet_id,version,recipient_id,target_id) VALUES(?,?,?,?,?,?,?)',
                       (staged['change_id'], kind, row['publication_id'], row['banquet_id'], int(row['version']),
                        recipient[0], recipient[0] if kind == 'submit' else submitter[0]))


def _target(config, event):
    members = [key for key, actor in config['allowed_actors'].items() if actor['feishu_user_id'] == event['target_id']]
    if len(members) != 1:
        raise ValueError('Handoff recipient is not uniquely configured.')
    options = config['personal_connections']
    routes = [route for route in options['routes'] if route['audience'] == 'private' and
              route.get('member_id', route['user_id']) == members[0]]
    if len(routes) != 1:
        raise ValueError('Handoff recipient needs one private entrance.')
    route = routes[0]
    return {**{key: route[key] for key in ROUTE_FIELDS}, 'member_id': members[0],
            **{key: route.get(key, options[key]) for key in ('source_app_id', 'source_tenant_key')}}


def _event(ledger, event_id):
    row = ledger._db.execute('SELECT * FROM handoff_events WHERE event_id=?', (event_id,)).fetchone()
    if row is None:
        raise ValueError('Unknown handoff event.')
    return row


def _view(event, config):
    return {**{key: event[key] for key in ('event_id', 'kind', 'banquet_id', 'publication_id', 'version')},
            'target': _target(config, event)}


def summary(ledger, row):
    """Called only after the reader verifies the publication and its parties."""
    messages = {'pending': '助手通知待发送', 'dispatching': '助手通知发送已开始，结果待核实',
                'sent': '助手通知已获得发送回执', 'unknown': '助手通知发送结果未知，需核实'}
    events = ledger._db.execute(
        'SELECT e.kind,e.version,e.notification_status,e.start_json FROM handoff_events e '
        'JOIN staged_changes s ON s.change_id=e.event_id WHERE s.state=\'verified\' '
        'AND e.event_id IN (?,?) AND e.publication_id=? AND e.version=? '
        'ORDER BY CASE e.kind WHEN \'submit\' THEN 0 ELSE 1 END',
        (row['publication_id'], row['operation_id'], row['publication_id'], int(row['version'])))
    result = []
    for event in events:
        status = event['notification_status']
        item = dict(kind=event['kind'], version=event['version'], notification_status=status,
                    notification_message=messages[status])
        if event['kind'] == 'submit':
            item['start'] = dict(status='recorded' if event['start_json'] else 'not_recorded',
                                 message='已记录开始请求' if event['start_json'] else '尚未记录开始请求')
        result.append(item)
    return result


def _current(event, backend, ledger):
    change = ledger.get(event['event_id'])
    if not change or change.get('state') != 'verified':
        raise ValueError('Handoff event is not verified.')
    scopes = core._write_scopes(change)
    slots = ','.join('?' for _ in scopes)
    if ledger._db.execute(f'SELECT 1 FROM write_fences WHERE scope_key IN ({slots}) LIMIT 1', scopes).fetchone():
        raise ValueError('Handoff has an unresolved business write.')
    store = banquet.Store(backend)
    store.read_schema()
    business = store.get('banquets', event['banquet_id'])
    if not business:
        raise ValueError('Handoff banquet is unavailable.')
    current = handoffs.latest(store, event['banquet_id'])
    if (not current or handoffs.publication(ledger, current)['change_id'] != event['publication_id'] or
            int(current['version']) != event['version'] or current.get('operation_id') != event['event_id'] or
            customers._owner_ids(current['recipient']) != [event['recipient_id']]):
        raise ValueError('Handoff publication or version changed.')
    if event['kind'] == 'submit':
        publication_basis.require_current(publication_basis.read(ledger.get(event['publication_id']), business, backend))
    return current


def _entry(request, connections):
    connections.validate_source(request['source_app_id'], request['project'], request['source_tenant_key'])


def events(request, backend, ledger, config, connections):
    core._only_keys(request, {'project', 'source_app_id', 'source_tenant_key', 'event_id'})
    _entry(request, connections)
    if 'event_id' in request:
        event = _event(ledger, request['event_id'])
        view = _view(event, config)
        if any(view['target'][key] != request[key] for key in ('project', 'source_app_id', 'source_tenant_key')):
            raise ValueError('Handoff notice belongs to another entrance.')
        return dict(status='found', event=view, notification_status=event['notification_status'],
                    message_id=event['message_id'], start=json.loads(event['start_json']) if event['start_json'] else None)
    result = []
    for event in ledger._db.execute("SELECT * FROM handoff_events WHERE notification_status='pending' ORDER BY rowid"):
        try:
            view = _view(event, config)
            if any(view['target'][key] != request[key] for key in ('project', 'source_app_id', 'source_tenant_key')):
                continue
            _current(event, backend, ledger)
        except ValueError:
            continue
        result.append(view)
        if len(result) == 100:
            break
    return {'status': 'ok', 'events': result}


def claim(request, backend, ledger, config, connections):
    core._only_keys(request, {'event_id', 'project', 'source_app_id', 'source_tenant_key'})
    _entry(request, connections)
    event = _event(ledger, request['event_id'])
    view = _view(event, config)
    if any(view['target'][key] != request[key] for key in ('project', 'source_app_id', 'source_tenant_key')):
        raise ValueError('Handoff notice belongs to another entrance.')
    _current(event, backend, ledger)
    with ledger._immediate():
        _current(event, backend, ledger)
        dispatch_id = secrets.token_urlsafe(24)
        changed = ledger._db.execute("UPDATE handoff_events SET notification_status='dispatching',dispatch_id=?,target_json=? "
                                     "WHERE event_id=? AND notification_status='pending'",
                                     (dispatch_id, core._json(view['target']), event['event_id'])).rowcount
        event = _event(ledger, event['event_id'])
        return dict(status='claimed' if changed else 'already_claimed', event=view,
                    dispatch_id=event['dispatch_id'], notification_status=event['notification_status'],
                    message_id=event['message_id'], start=json.loads(event['start_json']) if event['start_json'] else None)


def acknowledge(request, ledger):
    core._only_keys(request, {'event_id', 'dispatch_id', 'status', 'message_id'})
    if request.get('status') not in {'sent', 'unknown'}:
        raise ValueError('Invalid notification receipt.')
    message_id = request.get('message_id', '')
    if request['status'] == 'sent':
        core._required_text(message_id, 'message_id', 1024)
    elif message_id != '':
        raise ValueError('An unknown send cannot claim a message receipt.')
    with ledger._immediate():
        event = _event(ledger, request['event_id'])
        if not event['dispatch_id'] or event['dispatch_id'] != request.get('dispatch_id'):
            raise ValueError('Notification dispatch does not match.')
        if event['notification_status'] != 'dispatching':
            if event['notification_status'] != request['status'] or (event['message_id'] or '') != message_id:
                raise ValueError('Notification outcome is already recorded.')
            return {'status': 'recorded', 'replayed': True}
        ledger._db.execute('UPDATE handoff_events SET notification_status=?,message_id=? WHERE event_id=?',
                           (request['status'], message_id, event['event_id']))
        return {'status': 'recorded', 'replayed': False}


def _busy(ledger, principal):
    for approval in ledger._db.execute("SELECT principal_json,state,expires_at FROM approvals WHERE state IN ('pending','executing')"):
        owner = json.loads(approval['principal_json'])
        if (all(owner.get(key) == principal[key] for key in ROUTE_FIELDS) and
                (approval['state'] == 'executing' or core._parse_time(approval['expires_at'], 'expires_at') > core._now(None))):
            return True
    return False


def start(request, backend, ledger, config, connections, binding):
    core._only_keys(request, {'event_id', 'principal', 'work_id', 'session_id', 'handoff_files_verified'})
    principal = core._principal(request['principal'])
    event = _event(ledger, request['event_id'])
    target = _target(config, event)
    if (event['kind'] != 'submit' or event['notification_status'] != 'sent' or
            event['message_id'] != principal['message_id'] or not event['target_json'] or
            json.loads(event['target_json']) != target or
            any(target[key] != principal[key] for key in ROUTE_FIELDS) or
            resolve_member_id(config, principal) != target['member_id'] or connections.route(principal) != 'private'):
        raise ValueError('This notice cannot start work for this principal.')
    current = _current(event, backend, ledger)
    if current['status'] != '待接手':
        raise ValueError('This handoff is no longer pending.')
    connections.check_version(binding)
    result = {key: event[key] for key in ('event_id', 'banquet_id', 'publication_id', 'version')}
    result['binding'] = binding
    origin = ledger.get(event['publication_id'])
    result['file_check'] = {**handoffs.file_check(origin), 'published': True}
    if event['start_json'] and json.loads(event['start_json'])['binding'] != binding:
        raise ValueError('Handoff start belongs to an earlier connection.')
    if _busy(ledger, principal):
        return dict(result, status='busy', start=None)
    if 'work_id' not in request and 'session_id' not in request:
        return dict(result, status='replayed' if event['start_json'] else 'ready',
                    start=json.loads(event['start_json']) if event['start_json'] else None)
    work = core._required_text(request.get('work_id'), 'work_id', 256)
    session = core._required_text(request.get('session_id'), 'session_id', 1024)
    if request.get('handoff_files_verified') is not True:
        raise ValueError('Handoff start requires verified published files.')
    saved = dict(work_id=work, session_id=session, principal=principal, binding=binding)
    with ledger._immediate():
        _current(event, backend, ledger)
        connections.check_version(binding)
        if _busy(ledger, principal):
            return dict(result, status='busy', start=None)
        changed = ledger._db.execute('UPDATE handoff_events SET start_json=?,work_id=?,session_id=? WHERE event_id=? AND start_json IS NULL',
                                     (core._json(saved), work, session, event['event_id'])).rowcount
        event = _event(ledger, event['event_id'])
        existing = json.loads(event['start_json'])
        if existing['binding'] != binding:
            raise ValueError('Handoff start belongs to an earlier connection.')
        if changed:
            connections._bind_work(principal, work, private=connections.options['resource_mode'] == 'restricted',
                                   requires_connection=True, binding=binding)
        return dict(result, status='started' if changed else 'replayed', start=existing)
