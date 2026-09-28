"""Small, host-owned collaboration records. Never a CRM write or a Wiki publish."""

import json
import os
import re
from pathlib import Path
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import core


FIELDS = {
    'case-list': {'query'},
    'case-read': {'case_name'},
    'case-update': {'case_name', 'expected_revision', 'changes', 'source_message_id'},
    'case-member-add': {'case_name', 'expected_revision', 'member_name', 'responsibility', 'source_message_id'},
    # Host-only: absent from the agent client and gateway request decoder.
    'case-artifact': {'phase', 'request_key', 'existing_delivery', 'artifact'},
    'case-access': {'receipt', 'require_binding'},
    'case-result': {'command', 'input'},
}
STATES = {'proposed', 'reported_confirmed', 'occurred', 'unverified'}
INVITE_RESPONSIBILITIES = {'销售', '运营', '销售准备', '销售跟进', '运营执行', '执行准备', '宴后核对', '项目协作'}
FACT_FIELDS = {'桌数', '人数', '预算', '已选方案', '套餐', '餐费', '服务费', '酒水', '主持', '布置',
               '金额依据', '预计金额', '已核验收款', '待核实收款', '待收金额', '婚宴日期', '场馆',
               '入场时间', '布场时间', '检查时间', '迎宾时间', '开席时间', '结束时间', '负责人',
               '客户需求', '待确认项', '执行安排', '项目阶段'}
UNCERTAIN = ('不要', '不用', '不改', '暂不', '如果', '是否', '假设', '未确认', '没确认', '没有确认',
             '尚未', '未发生', '没发生', '还没', '不确定', '请勿', '别改', '不确认', '假如', '建议', '考虑', '吗', '？', '?')


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
    if right < len(source) and source[right] in '？?':
        clause += source[right]
    if value not in clause:
        raise ValueError('one fact clause required for a state transition')
    previous_start = max(source.rfind(c,0,max(0,left-1)) for c in separators) + 1
    previous = source[previous_start:max(0,left-1)].strip()
    if previous in {'客户确认','已确认','实际发生','实际执行','已经完成','已完成', *UNCERTAIN}:
        clause = previous + clause
    # A conditional introduction may span clauses. Keep these conservative;
    # an unrelated pending fact does not invalidate an affirmative fact.
    if any(word in source for word in ('如果', '假设', '假如', '是否')):
        clause = '假设' + clause
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
    if set(options) - {'enabled', 'ledger_path', 'namespace', 'group_chat_id', 'members', 'project_context'} or not {
        'enabled', 'ledger_path', 'namespace', 'group_chat_id', 'members'
    } <= set(options):
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
    _project_policy(options, config)
    required = {'work_id', 'source_text', 'share_allowed'}
    if not isinstance(context, dict) or not required <= set(context) or set(context) - required - {'source_receipt','selected_case','original_text', 'offer_confirmation', 'confirmation'}:
        raise ValueError('trusted case context required')
    if type(context.get('offer_confirmation', False)) is not bool:
        raise ValueError('invalid confirmation policy')
    if context.get('selected_case'):
        _text(context['selected_case'],120)
    if context.get('source_receipt'):
        _text(context['source_receipt'])
        if principal['chat_id'] != options['group_chat_id']:
            raise ValueError('group receipt required')
    _text(context['work_id'])
    if not isinstance(context['source_text'], str) or len(context['source_text']) > 16000:
        raise ValueError('invalid case source')
    if 'original_text' in context and (not isinstance(context['original_text'], str) or len(context['original_text']) > 16000):
        raise ValueError('invalid original case source')
    if type(context['share_allowed']) is not bool:
        raise ValueError('invalid sharing permission')
    _text(principal['message_id'])
    return options


def _project_policy(options, config):
    policy = options.get('project_context')
    if 'project_context' not in options or policy == {'enabled': False}:
        return None
    if not isinstance(policy, dict) or set(policy) != {'enabled', 'group_case', 'managers'} or policy['enabled'] is not True:
        raise ValueError('invalid project context configuration')
    if not options['namespace'].startswith('mock-project-'):
        raise ValueError('project context requires a fresh mock-project namespace')
    _text(policy['group_case'], 120)
    registered = {m['user_id'] for m in options['members']}
    if (len({m['platform'] for m in options['members']}) != 1 or
            not registered <= config['allowed_actors'].keys() or
            not isinstance(policy['managers'], list) or
            any(not isinstance(user, str) or user not in registered for user in policy['managers'])):
        raise ValueError('invalid registered project actors')
    return policy


def _can_read(options, body, principal):
    policy = options.get('project_context', {})
    if not policy.get('enabled'):
        return True
    project = (body or {}).get('project', {})
    return bool(project) and (principal['user_id'] in project['members'] or
                              principal['user_id'] in policy['managers'])


def _new_project(options, principal, config, name):
    users = {principal['user_id']}
    if name == options['project_context']['group_case']:
        # The configured project group is a frozen shared audience, not a
        # claim that an attachment already posted there can be kept secret.
        users.update(m['user_id'] for m in options['members'] if m['chat_id'] == options['group_chat_id'])
    return dict(owner=principal['user_id'], members={user: dict(
        name=config['allowed_actors'][user]['display_name'],
        responsibility='项目负责' if user == principal['user_id'] else '项目协作') for user in sorted(users)})


def _save_version(db, options, key, body, message, digest):
    body['revision'] += 1
    body['updated_at'] = datetime.now(timezone.utc).isoformat()
    encoded = core._json(body)
    if len(encoded.encode()) > 48 * 1024:
        raise ValueError('case record too large')
    db.execute('INSERT INTO shared_case_versions VALUES(?,?,?,?,?,?)',
               (options['namespace'], body['name'], body['revision'], message, digest, encoded))
    _bind(db, options['namespace'], key, body)
    return dict(status='recorded', case=body, replayed=False)


def _confirmed(command, request, context):
    """Only the authenticated gateway supplies this frozen answer, never tools."""
    answer = context.get('confirmation')
    if answer is None:
        return False
    if (not isinstance(answer, dict) or set(answer) != {'command', 'input', 'answer_message_id', 'revision'} or
            answer['command'] != command or answer['input'] != request or
            type(answer['revision']) is not int or answer['revision'] < 0):
        raise ValueError('confirmation does not match this operation')
    _text(answer['answer_message_id'], 1024)
    return True


def _confirmation(command, request, context, options, config, principal, body, name, fallback):
    if not context.get('offer_confirmation'):
        return fallback
    if body is not None and not _can_read(options, body, principal):
        return dict(status='not_found', case_name=name, revision=0)
    # ponytail: recognize only a whole "other conditions unchanged" clause;
    # this permits a scoped question, never direct sharing or general intent inference.
    source = context.get('original_text', context['source_text'])
    source = '，'.join(clause for clause in re.split(r'[，,。；;\n]', source)
        if not re.fullmatch(r'\s*(?:其余|其他)条件(?:先)?不改\s*', clause))
    # Explicit denials must not be converted to another invitation to share.
    if command != 'case-read' and (not source.strip('， \t\r') or any(word in source
            for word in ('不要', '不用', '不许', '不能', '禁止', '请勿', '暂不', '别同步', '别共享', '别改', '不改', '保密', '仅私下'))):
        return fallback
    revision = body['revision'] if body else 0
    if command == 'case-read':
        if body is None:
            return dict(status='not_found', case_name=name, revision=0)
        question = f'这次处理的是「{name}」吗？只确定当前工作的项目，私聊内容仍不共享。'
    else:
        if request.get('source_message_id', principal['message_id']) != principal['message_id']:
            raise ValueError('source message mismatch')
        if type(request.get('expected_revision')) is not int or request['expected_revision'] != revision:
            return dict(status='conflict', code='case_revision_changed', current_revision=revision)
        if command == 'case-member-add':
            if body is None or not options.get('project_context', {}).get('enabled'):
                return fallback
            if principal['user_id'] != body['project']['owner'] and principal['user_id'] not in options['project_context']['managers']:
                return dict(status='blocked', code='project_owner_required')
            member = _text(request.get('member_name'), 100)
            responsibility = _text(request.get('responsibility'), 100)
            registered = {m['user_id'] for m in options['members'] if config['allowed_actors'][m['user_id']]['display_name'] == member}
            if len(registered) != 1 or responsibility not in INVITE_RESPONSIBILITIES:
                return fallback
            question = f'让「{member}」加入「{name}」，负责「{responsibility}」，可以读取该项目的共享记录和成果，项目负责人不变。确认吗？'
        else:
            changes = _changes(request, context, principal, config, interpreted=True)
            states = dict(proposed='提出要求', reported_confirmed='员工报告已确认', occurred='报告实际发生', unverified='待核实')
            lines = []
            for field, value, replaces in changes:
                old = body['facts'].get(field) if body else None
                change = f'{field}：{value["value"]}（{states[value["state"]]}）'
                if old:
                    change += f'；原记录：{old["value"]}；' + ('替换旧值' if replaces else '有差异则并列保留待澄清')
                lines.append(change)
            question = f'将以下内容记入「{name}」，供该项目成员读取（当前版本 {revision}）：\n' + '\n'.join(lines) + '\n确认这些内容和共享范围吗？'
    if len(question) > 3500:
        return dict(status='blocked', code='case_confirmation_too_large')
    return dict(status='needs_confirmation', question=question, revision=revision)


def _operation_result(db, options, request, principal, key):
    """Host-only reconciliation; never executes an operation after a restart."""
    command, data = request.get('command'), request.get('input')
    if command not in {'case-read', 'case-update', 'case-member-add'} or not isinstance(data, dict) or set(data) - FIELDS[command]:
        raise ValueError('invalid operation result query')
    name = _text(data.get('case_name'), 120)
    body = _current(db, options['namespace'], name)
    if body is not None and not _can_read(options, body, principal):
        return dict(status='not_found', case_name=name, revision=0)
    if command == 'case-read':
        row = db.execute('SELECT name FROM shared_case_bindings WHERE namespace=? AND work_key=?', (options['namespace'], key)).fetchone()
        return dict(status='found' if row and row['name'] == name and body else 'not_executed', current_revision=body['revision'] if body else 0)
    parts = [principal[k] for k in ('platform', 'chat_id', 'user_id', 'message_id')]
    if command == 'case-member-add':
        parts.append(command)
    row = db.execute('SELECT request_hash,body FROM shared_case_versions WHERE namespace=? AND name=? AND message_key=?',
                     (options['namespace'], name, core._hash(parts))).fetchone()
    if row:
        if row['request_hash'] != core._hash(data):
            return dict(status='blocked', code='case_message_already_recorded')
        return dict(status='recorded', case=json.loads(row['body']), replayed=True)
    return dict(status='not_executed', current_revision=body['revision'] if body else 0)


def _add_member(db, options, request, principal, context, config, key, body):
    policy = options.get('project_context', {})
    if not policy.get('enabled') or body is None:
        return dict(status='blocked', code='project_context_required')
    if principal['user_id'] != body['project']['owner'] and principal['user_id'] not in policy['managers']:
        return dict(status='blocked', code='project_owner_required')
    if request.get('source_message_id', principal['message_id']) != principal['message_id']:
        return dict(status='blocked', code='case_share_not_authorized')
    name = _text(request.get('member_name'), 100)
    responsibility = _text(request.get('responsibility'), 100)
    if responsibility not in INVITE_RESPONSIBILITIES:
        return dict(status='needs_selection', code='project_responsibility_required')
    candidates = {m['user_id'] for m in options['members']
                  if config['allowed_actors'][m['user_id']]['display_name'] == name}
    if len(candidates) != 1:
        return dict(status='needs_selection', code='project_member_name_not_unique')
    source = context.get('original_text', '')
    # A membership grant must be the complete original request, never a
    # matching line extracted from a quotation, question or mixed message.
    # ponytail: deliberately narrow grammar; unsupported phrasing asks the
    # employee to restate one invitation, rather than guessing permission.
    instruction = (r'(?:' + re.escape(body['name']) + r'[，,:：]\s*)?'
                   r'(?:请)?(?:让|邀请|安排|添加|增加)\s*' + re.escape(name) +
                   r'\s*(?:来)?(?:加入|参与|接手|负责)(?:本项目的)?' +
                   re.escape(responsibility) + r'[。！!]?')
    if not _confirmed('case-member-add', request, context) and (any(word in source for word in (*UNCERTAIN, '禁止', '吗')) or not re.fullmatch(instruction, source.strip())):
        return _confirmation('case-member-add', request, context, options, config, principal, body, body['name'],
                             dict(status='blocked', code='project_member_instruction_required'))
    revision = request.get('expected_revision')
    if type(revision) is not int or revision < 1:
        raise ValueError('invalid expected revision')
    message = core._hash([*(principal[k] for k in ('platform', 'chat_id', 'user_id', 'message_id')), 'case-member-add'])
    digest = core._hash(request)
    previous = db.execute('SELECT request_hash,body FROM shared_case_versions WHERE namespace=? AND name=? AND message_key=?',
                          (options['namespace'], body['name'], message)).fetchone()
    if previous:
        if previous['request_hash'] != digest:
            return dict(status='blocked', code='case_message_already_recorded')
        return dict(status='recorded', case=json.loads(previous['body']), replayed=True)
    if revision != body['revision']:
        return dict(status='conflict', code='case_revision_changed', current_revision=body['revision'])
    user = candidates.pop()
    if context.get('confirmation'):
        source = f'确认邀请{name}负责{responsibility}'
    body['project']['members'][user] = dict(name=name, responsibility=responsibility,
        source=dict(speaker=config['allowed_actors'][principal['user_id']]['display_name'], quote=source))
    return _save_version(db, options, key, body, message, digest)


def _access(db, options, request, principal, key):
    """Host-only receipt check shared by explicit references and snapshot import."""
    if not options.get('project_context', {}).get('enabled'):
        return dict(status='legacy')
    receipt = _text(request.get('receipt'))
    require_binding = request.get('require_binding')
    if type(require_binding) is not bool:
        raise ValueError('binding policy required')
    rows = db.execute("SELECT DISTINCT name FROM shared_case_artifacts WHERE namespace=? AND receipt=? AND body<>''",
                      (options['namespace'], receipt)).fetchall()
    if len(rows) != 1 or not _can_read(options, _current(db, options['namespace'], rows[0]['name']), principal):
        return dict(status='blocked', code='project_artifact_unavailable')
    name = rows[0]['name']
    binding = db.execute('SELECT name FROM shared_case_bindings WHERE namespace=? AND work_key=?',
                         (options['namespace'], key)).fetchone()
    if (require_binding and not binding) or (binding and binding['name'] != name):
        return dict(status='blocked', code='project_artifact_work_mismatch')
    if principal['chat_id'] == options['group_chat_id'] and name != options['project_context']['group_case']:
        return dict(status='blocked', code='project_artifact_group_mismatch')
    return dict(status='authorized', case_name=name, source_chat_id=options['group_chat_id'])


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
    if options.get('project_context', {}).get('enabled'):
        selected = db.execute('SELECT name FROM shared_case_bindings WHERE namespace=? AND work_key=?',
                              (options['namespace'], key)).fetchone()
        name = binding['name'] if binding else (selected['name'] if selected else '')
        if (name != options['project_context']['group_case'] or
                not _can_read(options, _current(db, options['namespace'], name), principal)):
            return dict(status='blocked', code='project_delivery_not_authorized')
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


def _changes(request, context, principal, config, interpreted=False):
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
        if field in seen:
            raise ValueError(f'{field}: duplicate field; use one entry per field, preserving all facts in the complete batch')
        if state not in STATES:
            raise ValueError(f'{field}: state must be proposed, reported_confirmed, occurred or unverified')
        if not interpreted and quote not in context['source_text']:
            raise ValueError(f'{field}: quote must occur verbatim in the authorized source message')
        # Value must be grounded in this shared message, not the private history.
        if not interpreted and value not in quote:
            raise ValueError(f'{field}: value must occur verbatim in its source quote')
        # Inspect the complete authorized source, not a model-trimmed quote.
        # Ambiguous confirmation stays unverified and may be clarified naturally.
        source = context['source_text']
        if not interpreted and state in {'reported_confirmed', 'occurred'}:
            clause = _source_clause(source,quote,value)
            markers = ('已确认', '确认采用', '客户确认', '确认改为') if state == 'reported_confirmed' else ('实际发生', '实际执行', '已经完成', '已完成')
            if any(word in clause for word in UNCERTAIN) or not any(word in clause for word in markers):
                raise ValueError(f'{field}: confirmation not supported by the original message; keep proposed or unverified')
        replaces = change.get('replaces', False)
        if type(replaces) is not bool:
            raise ValueError('invalid replacement')
        if replaces and not interpreted:
            clause = _source_clause(source, quote, value)
            if not any(word in clause for word in ('改为', '改成', '调整为', '以此为准', '确认采用', '更正为')) or any(
                    word in clause for word in UNCERTAIN):
                raise ValueError('explicit_correction_required')
        seen.add(field)
        result.append((field, dict(value=value, state=state, source={
            'speaker': config['allowed_actors'][principal['user_id']]['display_name'],
            'quote': f'{field}：{value}（{state}）' if interpreted else quote,
            'origin': 'confirmed_interpretation' if interpreted else ('group' if principal['chat_id'] == config['shared_cases']['group_chat_id'] else 'explicit_private_share'),
        }), replaces))
    return result


def _update(db, options, request, principal, context, config, key, name):
    confirmed = _confirmed('case-update', request, context)
    if not context['share_allowed'] and not confirmed:
        return _confirmation('case-update', request, context, options, config, principal,
                             _current(db, options['namespace'], name), name,
                             dict(status='blocked', code='case_share_not_authorized'))
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
    try:
        changes = _changes(request, context, principal, config, interpreted=confirmed)
    except ValueError as exc:
        # Validation only: no writes or message consumption have occurred.
        # Reasons contain fixed messages and whitelisted business field names.
        return _confirmation('case-update', request, context, options, config, principal, body, name,
                    dict(status='blocked', code='case_changes_invalid', reason=str(exc), recorded=False,
                    retry='Fix and resubmit the whole batch with the same revision. Do not probe with a subset; '
                          'a successful update consumes this message. Values must be verbatim source text, '
                          'without normalized names, added punctuation or state labels.'))
    if body is None:
        body = dict(name=name, revision=0, facts={}, artifacts=[])
        if options.get('project_context', {}).get('enabled'):
            body['project'] = _new_project(options, principal, config, name)
    for field, value, replaces in changes:
        old = body['facts'].get(field)
        state_regressed = old and old['state'] in {'reported_confirmed','occurred'} and value['state'] != old['state'] and value['state'] != 'occurred'
        if old and (old['value'] != value['value'] or old['state'] == 'conflict' or state_regressed) and not replaces:
            value = dict(value=old['value'], state='conflict', source=old['source'],
                         alternatives=old.get('alternatives', []) + [value])
        body['facts'][field] = value
    return _save_version(db, options, key, body, message, digest)


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
            policy = options.get('project_context', {})
            project_mode = policy.get('enabled') is True
            if command == 'case-access':
                return _access(db, options, request, principal, key)
            if command == 'case-artifact':
                return _artifact(db,options,request,principal,key)
            if command == 'case-result':
                return _operation_result(db, options, request, principal, key)
            if command == 'case-list':
                query = request.get('query', '')
                if not isinstance(query, str) or len(query) > 256:
                    raise ValueError('invalid case query')
                rows = []
                # ponytail: linear scan of this bounded mock namespace;
                # index memberships only when a larger rollout is authorized.
                candidates = db.execute('SELECT name,MAX(revision) AS revision FROM shared_case_versions '
                                        'WHERE namespace=? AND instr(name,?)>0 GROUP BY name ORDER BY name',
                                        (options['namespace'], query))
                for row in candidates:
                    if project_mode and principal['chat_id'] == options['group_chat_id'] and row['name'] != policy['group_case']:
                        continue
                    if _can_read(options, _current(db, options['namespace'], row['name']), principal):
                        rows.append(row)
                    if len(rows) == 21:
                        break
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
            previously_bound = binding['name'] if binding else None
            if project_mode and principal['chat_id'] == options['group_chat_id']:
                if (name is not None and name != policy['group_case']) or (binding and binding['name'] != policy['group_case']):
                    return dict(status='blocked', code='project_group_mismatch')
                binding = {'name': policy['group_case']}
            if name is None:
                if not binding:
                    return dict(status='needs_selection', code='case_not_selected')
                name = binding['name']
            name = _text(name, 120)
            if binding and binding['name'] != name:
                return dict(status='needs_new_work',code='case_work_already_bound')
            confirmed = _confirmed(command, request, context)
            if command == 'case-update' and not context['share_allowed'] and not confirmed:
                return _confirmation(command, request, context, options, config, principal,
                                     _current(db, options['namespace'], name), name,
                                     dict(status='blocked', code='case_share_not_authorized'))
            if project_mode and not confirmed:
                # ponytail: conservative wedding-name grammar for this mock
                # rollout; ambiguous prose asks rather than guessing a target.
                # A candidate read does not authorize choosing that project.
                # Inspect the message, never hidden database names, so a newly
                # named wedding cannot silently update the bound group case.
                # Read tolerance must not weaken the original write-confirmation grammar.
                mention_pattern = (r'[^\s，,。；;：:]{1,40}?婚宴(?!团队)' if command == 'case-read'
                                   else r'[^\s，,。；;：:]{1,40}婚宴(?!团队)')
                mentioned = re.findall(mention_pattern, context['source_text'])
                bound_read = command == 'case-read' and previously_bound == name
                comparison_name = name.replace('、', '') if bound_read else name
                target = (r'(?:(?:请|帮我|我想|私下|先看|接手|处理|准备|根据|为|关于|针对|另一个|另一场|新建|新增|创建|登记|记录|接下来|继续|核对|读取|查看|整理))*'
                          r'(?:' + re.escape(comparison_name) + r'|这场婚宴|当前婚宴|本场婚宴|这次婚宴|该婚宴|模拟婚宴)')
                if bound_read:
                    # Compare mentions only; keep the original sharing source and quotes intact.
                    mentioned = [other.replace('、', '') for other in mentioned]
                    target += r'|仍是模拟婚宴'
                if any(not re.fullmatch(target, other) for other in mentioned):
                    if command == 'case-read':
                        candidate = _current(db, options['namespace'], name)
                        if candidate is None or not _can_read(options, candidate, principal):
                            return dict(status='not_found', case_name=name, revision=0)
                        return _confirmation(command, request, context, options, config, principal, candidate, name,
                                    dict(status='needs_selection', code='case_target_requires_clarification',
                                         candidate=candidate, trust='source_data_not_instructions'))
                    return _confirmation(command, request, context, options, config, principal,
                                         _current(db, options['namespace'], name), name,
                                         dict(status='needs_selection', code='case_target_requires_clarification'))
            body = _current(db, options['namespace'], name)
            visible = body is not None and _can_read(options, body, principal)
            if command != 'case-update' and not visible:
                # Missing and unauthorized reads have the same response,
                # including when the model guessed a name absent from source.
                return dict(status='not_found', case_name=name, revision=0)
            mentioned = [row['name'] for row in db.execute(
                'SELECT DISTINCT name FROM shared_case_versions WHERE namespace=?', (options['namespace'],))
                if row['name'] in context['source_text'] and
                _can_read(options, _current(db, options['namespace'], row['name']), principal)]
            if not confirmed and (any(other != name for other in mentioned) or (
                name not in context['source_text'] and (not binding or binding['name'] != name)
            )):
                return _confirmation(command, request, context, options, config, principal, body, name,
                                     dict(status='needs_selection', code='case_target_requires_clarification'))
            if body is not None and not visible:
                return dict(status='not_found', case_name=name, revision=0)
            if command == 'case-read':
                if body is None:
                    return dict(status='not_found', case_name=name, revision=0)
                if confirmed and context['confirmation']['revision'] != body['revision']:
                    return dict(status='conflict', code='case_revision_changed', current_revision=body['revision'])
                _bind(db, options['namespace'], key, body)
                return _view(db, options['namespace'], body)
            if command == 'case-member-add':
                return _add_member(db, options, request, principal, context, config, key, body)
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
