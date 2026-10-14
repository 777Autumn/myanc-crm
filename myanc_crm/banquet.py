"""Fixed Feishu banquet records, using the existing host approval ledger."""
from __future__ import annotations

import math
import json
import re
import secrets
import time
from datetime import date, timedelta, timezone
from urllib.parse import urlencode, urlsplit, urlunsplit

from . import core, customers
from . import lark


STAGES = {'新线索', '跟进中', '已约到店', '已到店', '已签单', '已流失'}
SCHEMA = {
    'name': ('宴会名称', 'text'), 'number': ('业务编号', 'auto_number'),
    'customer_record_id': ('关联客户', 'link'), 'source': ('来源', 'text'),
    'owner': ('销售负责人', 'user'), 'banquet_date': ('宴会日期', 'datetime'),
    'date_note': ('日期待确认说明', 'text'), 'date_status': ('日期确认状态', 'select'),
    'session': ('宴会时段', 'text'), 'venue': ('场地', 'text'),
    'estimated_tables': ('预计桌数', 'number'), 'budget': ('预算', 'number'),
    'visit_at': ('到店安排', 'datetime'), 'visited_at': ('实际到店时间', 'datetime'),
    'stage': ('销售阶段', 'select'), 'next_action': ('下一步', 'text'),
    'next_followup_at': ('跟进时间', 'datetime'), 'followup_status': ('跟进状态', 'select'),
    'operation_id': ('操作ID', 'text'), 'updated_at': ('更新时间', 'updated_at'),
}
HANDOFF_SCHEMA = {
    'name': ('交接标题', 'text'), 'banquet_id': ('关联婚宴', 'link'),
    'version': ('交接版本', 'number'), 'recipient': ('指定接手人', 'user'),
    'submitted_by': ('提交人', 'user'), 'materials': ('材料清单', 'text'),
    'missing': ('待补事项', 'text'), 'status': ('确认状态', 'select'),
    'return_reason': ('退回原因', 'text'), 'submitted_at': ('提交时间', 'datetime'),
    'acknowledged_at': ('确认时间', 'datetime'), 'publication_id': ('发布操作ID', 'text'),
    'operation_id': ('最后操作ID', 'text'), 'updated_at': ('更新时间', 'updated_at'),
}
EDIT_FIELDS = set(SCHEMA) - {'number', 'customer_record_id', 'owner', 'operation_id', 'updated_at'} | {'owner_ref'}
FIELDS = {
    'banquet-context': {'banquet_id'},
    'banquet': {'banquet_id'},
    'banquets': {'keyword', 'owner', 'stages', 'date_from', 'date_to', 'offset'},
    'stage-banquet-create': EDIT_FIELDS | {'customer_query'},
    'stage-banquet-update': {'banquet_id', 'changes'},
    'stage-banquet-followup': {'banquet_id', 'occurred_at', 'content', 'channel'},
}
OPERATIONS = {'banquet_create', 'banquet_update', 'banquet_followup'}


def open_workbench(request, config, principal):
    core._only_keys(request, {'target'})
    actor = core._actor_for_principal(principal, config)
    labels = {'banquet-mine': '我的待跟进', 'banquet-visits': '到店安排', 'banquet-stages': '销售阶段',
              'handoff-pending': '待交接', 'handoff-mine': '我的待接手'}
    target = request.get('target')
    if target not in labels:
        raise ValueError('Unknown banquet workbench.')
    views = core._mapping(config.get('banquet_workbench'), 'banquet workbench')
    core._only_keys(views, set(labels) | {'base_token', 'table_id', 'handoff_table_id'})
    schema = config['banquet']
    if views['base_token'] != config['base_token'] or any(views[k] != schema[k] for k in ('table_id', 'handoff_table_id')):
        raise ValueError('Workbench points to another resource.')
    view = views.get(target)
    if view is not None and target in {'banquet-mine', 'handoff-mine'}:
        view = core._mapping(view, 'personal views').get(actor['feishu_user_id'])
    if not isinstance(view, str) or not re.fullmatch(r'vew[A-Za-z0-9]+', view):
        return {'status': 'blocked', 'code': 'banquet_workbench_unconfigured'}
    parts = urlsplit(lark._base_url(config['base_url']))
    if parts.path.rstrip('/') != '/base/' + config['base_token']:
        raise ValueError('Workbench URL belongs to another Base.')
    table = schema['handoff_table_id'] if target == 'handoff-mine' else schema['table_id']
    url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode({'table': table, 'view': view}), ''))
    return {'status': 'available', 'target': target, 'label': labels[target], 'url': url,
            'message': '按当前飞书权限打开；视图筛选不构成数据权限隔离。'}


class Store:
    """No model-selected resource; transport and credentials stay in LarkCliBackend."""
    def __init__(self, backend):
        self.backend = backend
        options = core._mapping(getattr(backend, 'banquet_config', None), 'banquet configuration')
        core._only_keys(options, {'table_id', 'fields', 'followup_field_id', 'handoff_table_id', 'handoff_fields'})
        table = lark._table_id('banquet table', options.get('table_id'))
        if table in {backend.customer_table_id, backend.followup_table_id}:
            raise ValueError('Banquets require a separate table.')
        fields = core._mapping(options.get('fields'), 'banquet fields')
        if set(fields) != set(SCHEMA) or len(set(fields.values())) != len(fields):
            raise ValueError('Incomplete or duplicate banquet field mapping.')
        if any(not isinstance(v, str) or not lark._FIELD_ID.fullmatch(v) for v in fields.values()):
            raise ValueError('Invalid banquet field IDs.')
        link = options.get('followup_field_id')
        if not isinstance(link, str) or not lark._FIELD_ID.fullmatch(link) or link in backend.followup_fields.values():
            raise ValueError('A distinct follow-up banquet link is required.')
        self.tables = {'banquets': table, 'followups': backend.followup_table_id}
        self.fields = {'banquets': dict(fields), 'followups': {**backend.followup_fields, 'banquet_id': link}}
        self.schemas = {'banquets': SCHEMA, 'followups': {
            **{key: (name, lark._FOLLOWUP_SCHEMA[name]) for key, name in lark._FOLLOWUP_CANONICAL.items()},
            'banquet_id': ('关联婚宴', 'link')}}
        handoff_table = lark._table_id('handoff table', options.get('handoff_table_id'))
        handoff_fields = core._mapping(options.get('handoff_fields'), 'handoff fields')
        if handoff_table in {*self.tables.values(), backend.customer_table_id} or set(handoff_fields) != set(HANDOFF_SCHEMA):
            raise ValueError('A distinct handoff table with complete fields is required.')
        if len(set(handoff_fields.values())) != len(handoff_fields) or any(
            not isinstance(v, str) or not lark._FIELD_ID.fullmatch(v) for v in handoff_fields.values()):
            raise ValueError('Invalid handoff field IDs.')
        self.tables['handoffs'], self.fields['handoffs'], self.schemas['handoffs'] = handoff_table, dict(handoff_fields), HANDOFF_SCHEMA

    def read_schema(self, kinds=None):
        result = {}
        for kind, table in self.tables.items():
            if kinds is not None and kind not in kinds:
                continue
            actual = self.backend._read_table_schema(table, 'read banquet schema')
            schema, fields = self.schemas[kind], self.fields[kind]
            expected = {name: typ for name, typ in schema.values()}
            self.backend._validate_schema(actual, expected, {key: value[0] for key, value in schema.items()},
                                          fields, 'banquet ' + kind)
            for key, target in [('customer_record_id', self.backend.customer_table_id),
                                ('banquet_id', self.tables['banquets'])]:
                if key in schema and lark._link_target(actual[schema[key][0]]) != target:
                    raise ValueError('Banquet relationship points to a different table.')
            result[kind] = lark._stable_schema(actual, expected, include_rules=True)
        return {'base': self.backend.base_token, 'tables': self.tables, 'fields': self.fields, 'schema': result}

    def _row(self, kind, raw):
        cells, result = lark._fields(raw), {'record_id': lark._record_id(raw.get('record_id'))}
        for key, (name, typ) in self.schemas[kind].items():
            value = lark._cell(cells, name, self.fields[kind][key])
            if typ == 'select':
                value = lark._first(value)
            elif typ == 'link':
                if value is not None and (not isinstance(value, list) or len(value) > 1):
                    raise ValueError('A banquet relationship must name exactly one record.')
                value = lark._linked_id(value)
            elif typ == 'user':
                value = lark._customer_owner(value)
            result[key] = value
        return result

    def get(self, kind, identifier):
        if kind == 'banquets' and isinstance(identifier, str) and re.fullmatch(r'YAN-[0-9]{4,}', identifier):
            matches = [row for row in self.list(kind) if row.get('number') == identifier]
            if len(matches) > 1:
                raise ValueError('Duplicate banquet number; reconcile the Base.')
            if not matches:
                return None
            row = self.get(kind, matches[0]['record_id'])
            if row is None or row.get('number') != identifier:
                raise ValueError('Banquet number changed; read again.')
            return row
        identifier = lark._record_id(identifier)
        rows = self.backend._read_records(['base', '+record-get', '--base-token', self.backend.base_token,
            '--table-id', self.tables[kind], '--record-id', identifier], tuple(self.fields[kind].values()), 'read banquet record')
        if len(rows) > 1:
            raise ValueError('Ambiguous record response.')
        row = self._row(kind, rows[0]) if rows else None
        if row and row['record_id'] != identifier:
            raise ValueError('Record response does not match request.')
        return row

    def list(self, kind):
        # ponytail: at most 2000 rows in the test Base; add native filter pagination
        # when the pilot exceeds this ceiling. Overflow fails, never looks complete.
        page = self.backend._read_record_page(['base', '+record-list', '--base-token', self.backend.base_token,
            '--table-id', self.tables[kind], '--limit', '2000'], tuple(self.fields[kind].values()), 'list banquet records')
        if page['has_more'] or len(page['items']) > 2000:
            raise ValueError('Banquet read ceiling reached; refine the deployed query implementation.')
        rows = [self._row(kind, row) for row in page['items']]
        if len({row['record_id'] for row in rows}) != len(rows):
            raise ValueError('Duplicate record response.')
        return rows

    def write(self, kind, identifier, fields):
        record = {}
        for key, value in fields.items():
            typ = self.schemas[kind][key][1]
            if typ in {'auto_number', 'updated_at', 'created_at'}:
                raise ValueError('System field cannot be written.')
            if value is not None:
                if typ == 'select':
                    value = [value]
                elif typ == 'link':
                    value = [{'id': lark._record_id(value)}]
                elif typ == 'user':
                    value = [{'id': lark._open_id(person['id'])} for person in value]
            record[self.fields[kind][key]] = value
        payload = {'update_records': {lark._record_id(identifier): record}} if identifier else {'create_records': [record]}
        result = self.backend._write_records(self.tables[kind], '+record-batch-update' if identifier else '+record-batch-create',
                                              payload, 'write banquet record')
        if identifier:
            return identifier
        ids = lark._record_ids(result)
        if len(ids) != 1:
            raise ValueError('Unknown create result; reconcile before retrying.')
        return lark._record_id(ids[0])

    def url(self, kind, identifier):
        return self.backend._record_url(self.tables[kind], lark._record_id(identifier))


def _validate(raw):
    raw = core._mapping(raw, 'banquet fields')
    core._only_keys(raw, EDIT_FIELDS)
    result = {}
    for key, value in raw.items():
        if value is None:
            if key in {'name', 'stage', 'owner_ref'}:
                raise ValueError('Name, owner and stage cannot be cleared.')
        elif key in {'estimated_tables', 'budget'}:
            if type(value) not in {int, float} or not math.isfinite(value) or value < 0 or value > 1_000_000_000:
                raise ValueError('Tables and budget require a finite nonnegative number.')
        else:
            value = core._required_text(value, key, 1000 if key in {'next_action', 'date_note'} else 256)
            if key == 'banquet_date':
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                    raise ValueError('An exact banquet date is required; put estimates in date_note.')
                value = date.fromisoformat(value).isoformat() + 'T00:00:00+08:00'
            elif key in {'visit_at', 'visited_at', 'next_followup_at'}:
                value = core._parse_time(value, key).isoformat()
            elif key == 'stage' and value not in STAGES:
                raise ValueError('Invalid banquet sales stage.')
            elif key == 'date_status' and value not in {'待确认', '预计', '已确认'}:
                raise ValueError('Invalid date certainty.')
            elif key == 'followup_status' and value not in {'待跟进', '已完成', '已取消'}:
                raise ValueError('Invalid follow-up status.')
        result[key] = value
    return result


def _display(row, store, kind='banquets'):
    result = core._fence_value({k: v for k, v in row.items() if k not in {'operation_id', 'change_id', 'record_id'}})
    result['record_id'] = row['record_id']
    result['url'] = store.url(kind, row['record_id'])
    return result


def read(command, request, backend, config, principal):
    core._actor_for_principal(core._principal(principal), config)
    core._only_keys(core._mapping(request, 'request'), FIELDS[command])
    store = Store(backend)
    store.read_schema(('banquets', 'followups') if command == 'banquet' else ('banquets',))
    if command == 'banquet':
        row = store.get('banquets', request.get('banquet_id'))
        if row is None:
            return {'status': 'not_found'}
        history = [r for r in store.list('followups') if r['banquet_id'] == row['record_id']]
        history.sort(key=lambda r: (r.get('occurred_at') or '', r['record_id']), reverse=True)
        return {'status': 'found', 'banquet': _display(row, store),
                'history': [_display(r, store, 'followups') for r in history[:10]], 'history_has_more': len(history) > 10}
    owner = request.get('owner', 'me')
    if owner not in {'me', 'all'}:
        raise ValueError('owner must be me or all within the current user permissions.')
    offset = request.get('offset', 0)
    if type(offset) is not int or not 0 <= offset <= 2000:
        raise ValueError('Invalid page offset.')
    stages = request.get('stages', [])
    if not isinstance(stages, list) or any(stage not in STAGES for stage in stages):
        raise ValueError('Invalid stages.')
    keyword = core._normal(core._required_text(request['keyword'], 'keyword', 256)) if 'keyword' in request else ''
    bounds = {key: date.fromisoformat(request[key]) for key in ('date_from', 'date_to') if key in request}
    if len(bounds) == 2 and bounds['date_from'] > bounds['date_to']:
        raise ValueError('Date range is reversed.')
    actor = core._actor_for_principal(principal, config)['feishu_user_id']
    rows = []
    for row in store.list('banquets'):
        if owner == 'me' and actor not in customers._owner_ids(row.get('owner')):
            continue
        if stages and row.get('stage') not in stages:
            continue
        if keyword and not any(keyword in core._normal(row.get(k)) for k in ('name', 'number', 'venue', 'source')):
            continue
        if bounds:
            if not row.get('banquet_date'):
                continue
            day = core._parse_time(row['banquet_date'], 'banquet_date').astimezone(timezone(timedelta(hours=8))).date()
            if ('date_from' in bounds and day < bounds['date_from']) or ('date_to' in bounds and day > bounds['date_to']):
                continue
        rows.append(row)
    rows.sort(key=lambda r: r['record_id'])
    return {'status': 'found', 'items': [_display(r, store) for r in rows[offset:offset + 20]],
            'has_more': offset + 20 < len(rows), 'next_offset': offset + 20 if offset + 20 < len(rows) else None}


def stage(command, request, backend, ledger, config, token, principal, now=None, *, assignee_lookup=None):
    try:
        principal = core._principal(principal)
        actor = core._actor_for_principal(principal, config)
        binding = None
        if 'personal_connections' in config:
            from .connections import access
            connection = access(config, command, principal)
            if connection is not None:
                binding = backend.runner.binding
                connection.check_version(binding)
        token_hash = core._action_token_hash(token)
        intent = ledger.note_write_intent(principal)
        core._only_keys(core._mapping(request, 'request'), FIELDS[command])
        operation = command.removeprefix('stage-').replace('-', '_')
        if operation not in OPERATIONS:
            raise ValueError('Unsupported banquet operation.')
        raw = ({k: v for k, v in request.items() if k != 'customer_query'} if operation == 'banquet_create'
               else request.get('changes', {}) if operation == 'banquet_update' else {})
        patch = _validate(raw)
        if operation == 'banquet_update' and not patch:
            raise ValueError('At least one field must change.')
        store = Store(backend)
        schema = store.read_schema()
        before, person = None, None
        if operation == 'banquet_create':
            required = [k for k in ('name', 'stage', 'owner_ref') if not patch.get(k)]
            if required or not request.get('customer_query'):
                return {'status': 'needs_input', 'missing_fields': required + ([] if request.get('customer_query') else ['customer_query'])}
            matches, _ = core._resolve_customer(core._required_text(request['customer_query'], 'customer_query', 256), backend)
            if len(matches) != 1:
                return {'status': 'needs_selection', 'candidates': [core._display_customer(r, backend) for r in matches]}
            customer = backend.get_customer(core._record_id(matches[0]))
        else:
            before = store.get('banquets', request.get('banquet_id'))
            if before is None:
                return {'status': 'not_found'}
            customer = backend.get_customer(before['customer_record_id'])
        core._validate_customer(customer)
        if 'owner_ref' in patch:
            person = ledger.get_assignee(patch.pop('owner_ref'), principal)
            if person is None:
                raise ValueError('Resolve the owner in this conversation first.')
            person = customers._person(person)
            if customers._person((assignee_lookup or backend.get_assignee)(person['id'])) != person:
                raise ValueError('Owner changed; resolve again.')
            patch['owner'] = [person]
        if operation == 'banquet_create':
            patch['customer_record_id'] = core._record_id(customer)
        effective = {**(before or {}), **patch}
        if effective.get('date_status') == '已确认' and not effective.get('banquet_date'):
            raise ValueError('A confirmed date requires an exact date.')
        if operation == 'banquet_followup':
            core._required_text(request.get('content'), 'content', 2000)
            followup = core._followup({k: v for k, v in request.items() if k != 'banquet_id'})
            patch = {k: followup[k] for k in ('occurred_at', 'content', 'channel') if k in followup}
            patch.update(title=before['name'] + ' · ' + followup['occurred_at'],
                         customer_record_id=core._record_id(customer), banquet_id=before['record_id'],
                         created_by=[{'id': actor['feishu_user_id'], 'name': actor['display_name']}])
        moment = core._now(now)
        ttl = config.get('ttl_seconds', 600)
        if type(ttl) is not int or ttl <= 0:
            raise ValueError('Invalid approval lifetime.')
        body = {'change_id': 'chg_' + secrets.token_urlsafe(18), 'operation_type': operation,
                'principal': principal, 'actor': actor, 'customer_record_id': core._record_id(customer),
                'customer_snapshot': {'record_id': core._record_id(customer), **core._snapshot(customer)}, 'schema_hash': core._hash(schema),
                'banquet_before': before, 'banquet_patch': patch, 'assignee': person, 'connection_binding': binding,
                'created_at': core._iso(moment), 'expires_at': core._iso(moment + timedelta(seconds=ttl))}
        ledger.stage(body, token_hash, intent_version=intent)
        return {'status': 'staged', 'change_id': body['change_id'], 'preview': approval_preview(body, backend)}
    except (ValueError, TypeError, KeyError) as exc:
        return core._blocked('invalid_banquet_request', str(exc))
    except Exception:
        return core._blocked('banquet_stage_unavailable', '无法核实婚宴记录；未写入，请重新查询。')


def approval_preview(staged, backend):
    if staged['operation_type'].startswith('banquet_handoff_'):
        handoff = {**(staged['handoff_before'] or {}), **staged['handoff_patch']}
        handoff['materials'] = json.loads(handoff['materials'])
        return {'operation_type': staged['operation_type'], 'actor': staged['actor']['display_name'],
                'banquet': core._fence_value(staged['banquet_before']),
                'handoff': core._fence_value(handoff),
                'expires_at': staged['expires_at']}
    return {'operation_type': staged['operation_type'], 'actor': staged['actor']['display_name'],
            'customer': core._display_customer(staged['customer_snapshot'], backend),
            'banquet': core._fence_value(staged['banquet_before'] or {}),
            'banquet_changes': [{**change, 'after': core._fence_value(change['after'])}
                                for change in core._field_changes(staged['banquet_before'] or {}, staged['banquet_patch'])],
            'expires_at': staged['expires_at']}


def apply(staged, backend, ledger, moment, *, personal_backend=None, started=None):
    started = time.monotonic() if started is None else started
    change_id = staged['change_id']
    if staged.get('receipt'):
        return {**staged['receipt'], 'replayed': True}
    if staged['state'] != 'staged' or not ledger.claim(change_id):
        return {'status': 'verification_unknown', 'code': 'apply_in_progress', 'change_id': change_id}
    return core._run_customer_write(staged, ledger, moment,
        lambda effective: _apply(staged, backend, ledger, effective, personal_backend), started)


def _apply(staged, backend, ledger, moment, personal_backend):
    change_id = staged['change_id']
    def finish(status, code, **details):
        return core._finish(ledger, change_id, status, {'status': status, 'code': code, 'change_id': change_id, **details})
    try:
        if staged.get('connection_binding'):
            if personal_backend is None:
                return finish('failed', 'personal_connection_required')
            personal_backend.runner.connections.check_version(staged['connection_binding'])
        reader = personal_backend or backend
        store = Store(reader)
        if core._hash(store.read_schema()) != staged['schema_hash']:
            return finish('replan_required', 'schema_changed')
        customer = reader.get_customer(staged['customer_record_id'])
        if customer is None or {'record_id': core._record_id(customer), **core._snapshot(customer)} != staged['customer_snapshot']:
            return finish('replan_required', 'customer_changed')
        person = staged.get('assignee')
        if person and customers._person(backend.get_assignee(person['id'])) != person:
            return finish('replan_required', 'assignee_changed')
        before = staged['banquet_before']
        if before is not None and store.get('banquets', before['record_id']) != before:
            return finish('replan_required', 'banquet_changed')
    except Exception:
        return finish('failed', 'prewrite_read_failed')
    kind = 'followups' if staged['operation_type'] == 'banquet_followup' else 'banquets'
    identifier = before['record_id'] if staged['operation_type'] == 'banquet_update' else None
    key = 'change_id' if kind == 'followups' else 'operation_id'
    fields = {**staged['banquet_patch'], key: change_id}
    expected = {**(before if identifier else {}), **fields}
    actual = None
    try:
        if staged.get('connection_binding'):
            personal_backend.runner.connections.check_version(staged['connection_binding'])
        identifier = Store(backend).write(kind, identifier, fields)
    except Exception:
        # The transport may have committed before failing. Reconcile reads only;
        # never send the write twice or claim a failed response rolled it back.
        pass
    try:
        def observe():
            nonlocal actual, identifier
            if identifier:
                actual = store.get(kind, identifier)
            else:
                rows = [r for r in store.list(kind) if r.get(key) == change_id]
                if len(rows) != 1:
                    return None
                actual, identifier = rows[0], rows[0]['record_id']
            return actual if actual and _matches(actual, expected) else None
        verified = core._poll_read(observe)
    except Exception:
        verified = None
    if verified is None:
        return finish('verification_unknown', 'banquet_write_unverified', message='写入结果未核实，请人工核对，不要重复提交。')
    return finish('verified', 'banquet_write_verified',
                  **{'followup' if kind == 'followups' else 'banquet': _display(actual, store, kind)},
                  message='已写入并读回核实。此操作不创建个人提醒；原生提醒是否启用须以部署验收记录为准。')


def _matches(actual, expected):
    for key, value in expected.items():
        if key in {'updated_at', 'created_at'}:
            continue
        got = actual.get(key)
        if key in {'owner', 'created_by', 'recipient', 'submitted_by'}:
            if customers._owner_ids(got) != customers._owner_ids(value):
                return False
        elif key in {'banquet_date', 'visit_at', 'visited_at', 'next_followup_at', 'occurred_at', 'submitted_at', 'acknowledged_at'} and value is not None:
            if got is None or core._parse_time(got, key) != core._parse_time(value, key):
                return False
        elif got != value:
            return False
    return True
