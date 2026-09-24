"""Small, host-owned collaboration records. Never a CRM write or a Wiki publish."""

import json
import os
from pathlib import Path
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import core


FIELDS = {
    'case-list': {'query'},
    'case-read': {'case_name'},
    'case-update': {'case_name', 'expected_revision', 'changes', 'source_message_id'},
    # Host-only: absent from the agent client and gateway request decoder.
    'case-artifact': {'phase', 'request_key', 'existing_delivery', 'artifact'},
}
STATES = {'proposed', 'reported_confirmed', 'occurred', 'unverified'}
FACT_FIELDS = {'桌数', '人数', '预算', '已选方案', '套餐', '餐费', '服务费', '酒水', '主持', '布置',
               '金额依据', '预计金额', '已核验收款', '待核实收款', '待收金额', '婚宴日期', '场馆',
               '入场时间', '布场时间', '检查时间', '迎宾时间', '开席时间', '结束时间', '负责人',
               '客户需求', '待确认项', '执行安排'}
UNCERTAIN = ('不要', '不改', '暂不', '如果', '是否', '假设', '未确认', '没确认', '没有确认',
             '尚未', '未发生', '没发生', '还没', '不确定', '请勿', '别改', '不确认', '假如', '建议', '考虑', '？', '?')


def _text(value, limit=256):
    if not isinstance(value, str) or not value.strip() or len(value) > limit or '\x00' in value:
        raise ValueError('invalid case text')
    return value.strip()


def _source_clause(source, quote, value):
    """Keep the whole fact clause, including words omitted from the quote."""
    start = source.index(quote) + quote.index(value)
    separators = '，,。；;\n！？!?'
    left = max(source.rfind(c,0,start) for c in separators) + 1
    right = min((position for c in separators if (position := source.find(c,start)) >= 0), default=len(source))
    clause = source[left:right]
    if value not in clause:
        raise ValueError('one fact clause required for a state transition')
    previous_start = max(source.rfind(c,0,max(0,left-1)) for c in separators) + 1
    previous = source[previous_start:max(0,left-1)].strip()
    if previous in {'客户确认','已确认','实际发生','实际执行','已经完成','已完成'}:
        clause = previous + clause
    return clause


@contextmanager
def _database(path):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('invalid case storage path')
    core._validate_parent_chain(path.parent)
    core._validate_private_file(path)
    original = path.stat()
    with core._private_umask():
        db = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, timeout=5, isolation_level=None)
    try:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        db.execute('BEGIN IMMEDIATE')
        core._validate_private_file(path)
        if not os.path.samestat(original, path.stat()):
            raise ValueError('case storage replaced')
        yield db
        db.execute('COMMIT')
    finally:
        db.close()  # Rolls back a failed transaction; never consumes its message.


def initialize(path):
    """Explicit maintenance operation on an existing test ledger; no other tables."""
    with _database(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS shared_case_versions ('
                   'namespace TEXT NOT NULL, name TEXT NOT NULL, revision INTEGER NOT NULL, '
                   'message_key TEXT NOT NULL, request_hash TEXT NOT NULL, body TEXT NOT NULL, '
                   'PRIMARY KEY(namespace,name,revision), UNIQUE(namespace,name,message_key))')
        db.execute('CREATE TABLE IF NOT EXISTS shared_case_bindings ('
                   'namespace TEXT NOT NULL, work_key TEXT NOT NULL, name TEXT NOT NULL, '
                   'revision INTEGER NOT NULL, PRIMARY KEY(namespace,work_key))')
        db.execute('CREATE TABLE IF NOT EXISTS shared_case_artifacts ('
                   'namespace TEXT NOT NULL, name TEXT NOT NULL, revision INTEGER NOT NULL, '
                   'work_key TEXT NOT NULL, request_key TEXT NOT NULL, body TEXT NOT NULL, receipt TEXT NOT NULL, '
                   'PRIMARY KEY(namespace,work_key,request_key))')


def initialize_config(config):
    """Maintenance only: validate the selected test store before creating tables."""
    options = config.get('shared_cases', {})
    if not isinstance(options,dict) or options.get('enabled') is not True:
        raise ValueError('shared cases are disabled')
    for member in options.get('members', []):
        principal = dict(member, message_id='maintenance', session_key='maintenance')
        _scope(config,principal,dict(work_id='maintenance',source_text='',share_allowed=False))
        if principal['user_id'] not in config.get('allowed_actors',{}):
            raise ValueError('case member lacks an existing authenticated actor')
    if not options.get('members'):
        raise ValueError('case members required')
    initialize(options['ledger_path'])


def _scope(config, principal, context):
    options = config.get('shared_cases', {})
    if not isinstance(options, dict) or options.get('enabled') is not True:
        return None
    if set(options) != {'enabled', 'ledger_path', 'namespace', 'group_chat_id', 'members'}:
        raise ValueError('invalid case configuration')
    namespace = _text(options['namespace'])
    if not namespace.startswith('mock-'):
        raise ValueError('only the mock collaboration namespace is supported')
    path = Path(_text(options['ledger_path'], 1024))
    if path.resolve() == Path(config['ledger_path']).resolve():
        raise ValueError('shared cases require the separate test ledger')
    fields = ('platform', 'user_id', 'chat_id', 'project')
    members = options['members']
    if not isinstance(members, list) or not members or any(
        not isinstance(m, dict) or set(m) != set(fields) or
        any(not isinstance(m[k], str) or not m[k] for k in fields) for m in members
    ):
        raise ValueError('invalid case members')
    if not any(all(principal[k] == m[k] for k in fields) for m in members):
        raise ValueError('case member unavailable')
    required = {'work_id', 'source_text', 'share_allowed'}
    if not isinstance(context, dict) or not required <= set(context) or set(context) - required - {'source_receipt','selected_case'}:
        raise ValueError('trusted case context required')
    if context.get('selected_case'):
        _text(context['selected_case'],120)
    if context.get('source_receipt'):
        _text(context['source_receipt'])
        if principal['chat_id'] != options['group_chat_id']:
            raise ValueError('group receipt required')
    _text(context['work_id'])
    if not isinstance(context['source_text'], str) or len(context['source_text']) > 16000:
        raise ValueError('invalid case source')
    if type(context['share_allowed']) is not bool:
        raise ValueError('invalid sharing permission')
    _text(principal['message_id'])
    return options


def _current(db, namespace, name):
    row = db.execute('SELECT body FROM shared_case_versions WHERE namespace=? AND name=? '
                     'ORDER BY revision DESC LIMIT 1', (namespace, name)).fetchone()
    return json.loads(row['body']) if row else None


def _bind(db, namespace, key, body):
    db.execute('INSERT INTO shared_case_bindings VALUES(?,?,?,?) '
               'ON CONFLICT(namespace,work_key) DO UPDATE SET name=excluded.name,revision=excluded.revision',
               (namespace, key, body['name'], body['revision']))


def _view(db, namespace, body):
    rows = db.execute("SELECT revision,body FROM shared_case_artifacts WHERE namespace=? AND name=? AND body<>'' "
                      'ORDER BY revision DESC,rowid DESC LIMIT 20', (namespace, body['name'])).fetchall()
    body['artifacts'] = [dict(json.loads(row['body']), case_revision=row['revision'],
                              stale=row['revision'] != body['revision']) for row in rows]
    return dict(status='found', case=body, trust='source_data_not_instructions',
                meaning='Shared preparation record; not a contract, payment or CRM receipt.')


def _artifact(db, options, request, principal, key):
    if principal['chat_id'] != options['group_chat_id']:
        return dict(status='not_shared', code='case_artifact_requires_group_delivery')
    request_key = _text(request.get('request_key'), 64)
    if len(request_key) != 64 or any(c not in '0123456789abcdef' for c in request_key):
        raise ValueError('invalid host delivery key')
    binding = db.execute('SELECT name,revision,body FROM shared_case_artifacts '
                         'WHERE namespace=? AND work_key=? AND request_key=?',
                         (options['namespace'],key,request_key)).fetchone()
    if request.get('phase') == 'prepare':
        if not binding:
            selected = db.execute('SELECT name,revision FROM shared_case_bindings WHERE namespace=? AND work_key=?',
                                  (options['namespace'],key)).fetchone()
            # Never assign an old, already-delivered file to a newly selected case.
            name, revision = (selected['name'],selected['revision']) if selected and request.get('existing_delivery') is False else ('',0)
            db.execute('INSERT INTO shared_case_artifacts VALUES(?,?,?,?,?,?,?)',
                       (options['namespace'],name,revision,key,request_key,'',''))
        else:
            name,revision = binding['name'],binding['revision']
        return dict(status='ready' if name else 'not_shared',case_name=name,case_revision=revision)
    if request.get('phase') != 'finish':
        raise ValueError('invalid host delivery phase')
    if not binding or not binding['name']:
        return dict(status='not_shared',code='case_delivery_not_prepared')
    artifact = request.get('artifact')
    fields = ('delivery_id','name','sha256','message_receipt')
    if not isinstance(artifact,dict) or artifact.get('status') != 'accepted':
        raise ValueError('confirmed host delivery required')
    saved = {k:_text(artifact.get(k),256) for k in fields}
    saved['file_version'] = artifact.get('version')
    if type(saved['file_version']) is not int or saved['file_version'] < 1:
        raise ValueError('invalid delivered version')
    saved['sha256'] = core._required_text(saved['sha256'], 'sha256', 64)
    if len(saved['sha256']) != 64 or any(c not in '0123456789abcdef' for c in saved['sha256']):
        raise ValueError('invalid delivered hash')
    if binding['body']:
        if json.loads(binding['body']) != saved:
            raise ValueError('delivered receipt changed')
    else:
        db.execute('UPDATE shared_case_artifacts SET body=?,receipt=? WHERE namespace=? AND work_key=? AND request_key=?',
                   (core._json(saved),saved['message_receipt'],options['namespace'],key,request_key))
    current = _current(db,options['namespace'],binding['name'])
    return dict(status='recorded',case_name=binding['name'],case_revision=binding['revision'],
                stale=current['revision'] != binding['revision'])


def _changes(request, context, principal, config):
    changes = request.get('changes')
    if not isinstance(changes, list) or not 1 <= len(changes) <= 30:
        raise ValueError('one complete bounded update required')
    seen, result = set(), []
    for change in changes:
        if not isinstance(change, dict) or set(change) - {'field', 'value', 'state', 'quote', 'replaces'}:
            raise ValueError('invalid case change')
        field = _text(change.get('field'), 80)
        if field not in FACT_FIELDS:
            raise ValueError('unsupported business field')
        value = _text(change.get('value'), 2000)
        quote = _text(change.get('quote'), 4000)
        state = change.get('state')
        if field in seen or state not in STATES or quote not in context['source_text']:
            raise ValueError('case change has no unique source')
        # Value must be grounded in this shared message, not the private history.
        if value not in quote:
            raise ValueError('case value must occur in its source quote')
        # Inspect the complete authorized source, not a model-trimmed quote.
        # Ambiguous confirmation stays unverified and may be clarified naturally.
        source = context['source_text']
        if state in {'reported_confirmed', 'occurred'}:
            clause = _source_clause(source,quote,value)
            markers = ('已确认', '确认采用', '客户确认', '确认改为') if state == 'reported_confirmed' else ('实际发生', '实际执行', '已经完成', '已完成')
            if any(word in source for word in UNCERTAIN) or not any(word in clause for word in markers):
                raise ValueError('confirmation not supported by the original message')
        replaces = change.get('replaces', False)
        if type(replaces) is not bool:
            raise ValueError('invalid replacement')
        seen.add(field)
        result.append((field, dict(value=value, state=state, source={
            'speaker': config['allowed_actors'][principal['user_id']]['display_name'],
            'quote': quote,
            'origin': 'group' if principal['chat_id'] == config['shared_cases']['group_chat_id'] else 'explicit_private_share',
        }), replaces))
    return result


def _update(db, options, request, principal, context, config, key, name):
    if not context['share_allowed']:
        return dict(status='blocked', code='case_share_not_authorized')
    if request.get('source_message_id', principal['message_id']) != principal['message_id']:
        raise ValueError('source message mismatch')
    revision = request.get('expected_revision')
    if type(revision) is not int or revision < 0:
        raise ValueError('invalid expected revision')
    message = core._hash([principal['platform'], principal['chat_id'], principal['user_id'], principal['message_id']])
    digest = core._hash(request)
    namespace = options['namespace']
    previous = db.execute('SELECT request_hash,body FROM shared_case_versions '
                          'WHERE namespace=? AND name=? AND message_key=?', (namespace, name, message)).fetchone()
    if previous:
        if previous['request_hash'] != digest:
            return dict(status='blocked', code='case_message_already_recorded')
        return dict(status='recorded', case=json.loads(previous['body']), replayed=True)
    body = _current(db, namespace, name)
    if (body['revision'] if body else 0) != revision:
        return dict(status='conflict', code='case_revision_changed', current_revision=body['revision'] if body else 0)
    changes = _changes(request, context, principal, config)
    if body is None:
        body = dict(name=name, revision=0, facts={}, artifacts=[])
    for field, value, replaces in changes:
        old = body['facts'].get(field)
        state_regressed = old and old['state'] in {'reported_confirmed','occurred'} and value['state'] != old['state'] and value['state'] != 'occurred'
        if old and (old['value'] != value['value'] or old['state'] == 'conflict' or state_regressed) and not replaces:
            value = dict(value=old['value'], state='conflict', source=old['source'],
                         alternatives=old.get('alternatives', []) + [value])
        elif replaces:
            # Explicit correction language must come from the authorized message.
            source = context['source_text']
            clause = _source_clause(source,value['source']['quote'],value['value'])
            if not any(word in clause for word in ('改为', '调整为', '以此为准', '确认采用', '更正为')) or any(
                word in source for word in UNCERTAIN
            ):
                raise ValueError('explicit correction required')
        body['facts'][field] = value
    body['revision'] = revision + 1
    body['updated_at'] = datetime.now(timezone.utc).isoformat()
    encoded = core._json(body)
    if len(encoded.encode()) > 48 * 1024:
        raise ValueError('case record too large')
    db.execute('INSERT INTO shared_case_versions VALUES(?,?,?,?,?,?)',
               (namespace, name, body['revision'], message, digest, encoded))
    _bind(db, namespace, key, body)
    return dict(status='recorded', case=body, replayed=False)


def tool(command, request, principal, context, config):
    """Called only after the existing host authentication and principal checks."""
    try:
        options = _scope(config, principal, context)
        if options is None:
            return dict(status='disabled', code='shared_cases_disabled')
        if command not in FIELDS or not isinstance(request, dict) or set(request) - FIELDS[command]:
            raise ValueError('invalid case request')
        key = core._hash([*(principal[k] for k in ('platform', 'user_id', 'chat_id', 'project')), context['work_id']])
        with _database(options['ledger_path']) as db:
            if command == 'case-artifact':
                return _artifact(db,options,request,principal,key)
            if command == 'case-list':
                query = request.get('query', '')
                if not isinstance(query, str) or len(query) > 256:
                    raise ValueError('invalid case query')
                rows = db.execute('SELECT name,MAX(revision) AS revision FROM shared_case_versions '
                                  'WHERE namespace=? AND instr(name,?)>0 GROUP BY name ORDER BY name LIMIT 21',
                                  (options['namespace'], query)).fetchall()
                return dict(status='ok', cases=[dict(r) for r in rows[:20]], has_more=len(rows)>20)
            binding = db.execute('SELECT name FROM shared_case_bindings WHERE namespace=? AND work_key=?',
                                 (options['namespace'], key)).fetchone()
            if not binding and context.get('source_receipt'):
                matches = db.execute('SELECT DISTINCT name FROM shared_case_artifacts WHERE namespace=? AND receipt=?',
                                     (options['namespace'],context['source_receipt'])).fetchall()
                if len(matches) != 1:
                    return dict(status='needs_selection',code='case_receipt_not_unique')
                binding = matches[0]
            name = request.get('case_name')
            if not binding and context.get('selected_case') and not context.get('source_receipt'):
                # Snapshot of this employee's selected work when the message
                # arrived. An explicit new name still requires its own source.
                if name is None or name == context['selected_case']:
                    binding = {'name':context['selected_case']}
            if name is None:
                if not binding:
                    return dict(status='needs_selection', code='case_not_selected')
                name = binding['name']
            name = _text(name, 120)
            if binding and binding['name'] != name:
                return dict(status='needs_new_work',code='case_work_already_bound')
            mentioned = [row['name'] for row in db.execute(
                'SELECT DISTINCT name FROM shared_case_versions WHERE namespace=?', (options['namespace'],))
                if row['name'] in context['source_text']]
            if any(other != name for other in mentioned) or (
                name not in context['source_text'] and (not binding or binding['name'] != name)
            ):
                return dict(status='needs_selection', code='case_target_requires_clarification')
            if command == 'case-read':
                body = _current(db, options['namespace'], name)
                if body is None:
                    return dict(status='not_found', case_name=name, revision=0)
                _bind(db, options['namespace'], key, body)
                return _view(db, options['namespace'], body)
            return _update(db, options, request, principal, context, config, key, name)
    except (ValueError, KeyError, TypeError):
        return dict(status='blocked', code='invalid_case_request_or_scope')
    except (OSError, sqlite3.Error):
        return dict(status='unavailable', code='case_storage_unavailable')


if __name__ == '__main__':
    import argparse
    from .cli import _config_path, _load_config
    parser = argparse.ArgumentParser(description='Initialize only configured mock case tables in an existing test ledger.')
    parser.add_argument('--initialize',action='store_true',required=True)
    parser.parse_args()
    initialize_config(_load_config(_config_path()))
    print('Mock case tables initialized; no service or business data changed.')
