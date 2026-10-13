"""Named banquet handoff; business state in Feishu, file provenance in the approval ledger."""
import json
import re
import secrets
from datetime import timedelta

from . import banquet, core, customers, publication_basis

FIELDS = {
    'handoff': {'banquet_id', 'purpose'},
    'stage-handoff-submit': {'banquet_id', 'recipient_ref', 'delivery_ids', 'missing'},
    'stage-handoff-accept': {'banquet_id', 'version'},
    'stage-handoff-return': {'banquet_id', 'version', 'reason'},
}


def material_labels(files):
    return [{key: f[key] for key in ('name', 'sha256', 'version')} for f in files]


def latest(store, banquet_id):
    rows = [r for r in store.list('handoffs') if r.get('banquet_id') == banquet_id]
    versions = [r.get('version') for r in rows]
    if any(type(v) not in {int, float} or v < 1 or int(v) != v for v in versions) or len(set(versions)) != len(versions):
        raise ValueError('Invalid or duplicate handoff versions; reconcile the Base.')
    return max(rows, key=lambda r: r['version']) if rows else None


def _executed_patch(change):
    patch = dict(change['handoff_patch'])
    executed_at = (change.get('receipt') or {}).get('executed_at')
    if executed_at is not None:
        key = 'submitted_at' if change['operation_type'] == 'banquet_handoff_submit' else 'acknowledged_at'
        patch[key] = core._iso(core._parse_time(executed_at, 'executed_at'))
    return patch


def publication(ledger, row):
    """Editable Base cells never grant filesystem access."""
    origin = ledger.get(row.get('publication_id', ''))
    if not origin or origin.get('operation_type') != 'banquet_handoff_submit' or origin.get('state') != 'verified':
        raise ValueError('Handoff publication is not verified.')
    approved = _executed_patch(origin)
    immutable = {key: approved.get(key) for key in ('banquet_id', 'version', 'recipient', 'submitted_by',
                                                   'materials', 'missing', 'submitted_at', 'publication_id')}
    if not banquet._matches(row, immutable):
        raise ValueError('Published material or recipient changed; submit a new handoff version.')
    if origin['receipt'].get('handoff', {}).get('record_id') != row['record_id']:
        raise ValueError('Handoff record does not match its publication.')
    status = row.get('status')
    if status == '待接手':
        if row.get('operation_id') != origin['change_id']:
            raise ValueError('Pending status does not match its publication.')
    elif status in {'已接手', '已退回'}:
        decision = ledger.get(row.get('operation_id', ''))
        wanted = 'banquet_handoff_accept' if status == '已接手' else 'banquet_handoff_return'
        if (not decision or decision.get('state') != 'verified' or decision.get('operation_type') != wanted
                or decision.get('actor', {}).get('feishu_user_id') not in customers._owner_ids(row['recipient'])
                or decision.get('handoff_before', {}).get('publication_id') != origin['change_id']
                or decision['receipt'].get('handoff', {}).get('record_id') != row['record_id']
                or not banquet._matches(row, _executed_patch(decision))):
            raise ValueError('The named recipient has not verified this acknowledgment.')
    else:
        raise ValueError('Invalid handoff state.')
    return origin


def _source(context, principal):
    context = core._mapping(context, 'host handoff context')
    core._only_keys(context, {'work_id', 'files'})
    work = core._required_text(context.get('work_id'), 'work_id', 256)
    files = context.get('files')
    if not isinstance(files, list) or not 1 <= len(files) <= 4:
        raise ValueError('One to four verified delivery snapshots are required.')
    seen = set()
    for item in files:
        core._only_keys(core._mapping(item, 'file'), {'delivery_id', 'name', 'sha256', 'version', 'message_receipt'})
        for key in ('delivery_id', 'name', 'message_receipt'):
            core._required_text(item.get(key), key, 256)
        if not re.fullmatch('[a-f0-9]{64}', item.get('sha256', '')) or type(item.get('version')) is not int or item['version'] < 1:
            raise ValueError('Invalid material version.')
        if item['delivery_id'] in seen:
            raise ValueError('Repeated material.')
        seen.add(item['delivery_id'])
    if not any(f['name'].lower().endswith('.docx') for f in files):
        raise ValueError('Include the Word handoff document.')
    return {'work_id': work, 'principal': dict(principal), 'files': files}


def _view(row, store, origin=None):
    result = banquet._display(row, store, 'handoffs')
    result['version'] = int(row['version'])
    result['materials'] = core._fence_value(json.loads(row['materials']))
    if origin:
        # Machine metadata is consumed by the host importer; the displayed
        # material list above remains fenced as untrusted business content.
        result['files'] = [{**f, 'publication_id': f"bh_{origin['change_id']}_{i}"}
                           for i, f in enumerate(material_labels(origin['handoff_source']['files']))]
    return result


def _purpose(value):
    if value not in {'current', 'revision'}:
        raise ValueError('purpose must be current or revision.')
    return value


def _access(purpose, basis, row, actor):
    if purpose == 'revision':
        if (basis['status'] != 'stale' or
                customers._owner_ids(row['submitted_by']) != [actor['feishu_user_id']]):
            raise ValueError('Revision reference requires the original submitter and a stale latest publication.')
    else:
        publication_basis.require_current(basis)
    return {'purpose': purpose, 'reference_only': purpose == 'revision',
            'publication_basis_id': basis['publication_basis_id']}


def _reject_old_bytes(source, business, customer, ledger):
    """Renaming a delivery cannot turn known stale bytes into a new publication."""
    hashes = {file['sha256'] for file in source['files']}
    for row in ledger._db.execute("SELECT change_id FROM staged_changes WHERE state='verified'"):
        origin = ledger.get(row['change_id'])
        if (origin.get('operation_type') != 'banquet_handoff_submit' or
                origin.get('handoff_patch', {}).get('banquet_id') != business['record_id']):
            continue
        if hashes.intersection(file['sha256'] for file in origin['handoff_source']['files']):
            basis = publication_basis.compare(origin, business, customer)
            if basis['status'] != 'current':
                raise ValueError('Known ' + basis['status'] + ' publication bytes cannot be republished; revise the saved files.')


def read(request, backend, ledger, config, principal, *, metadata_only=False, store=None, business=None):
    core._only_keys(request, FIELDS['handoff'])
    purpose = _purpose(request.get('purpose', 'current'))
    actor = core._actor_for_principal(principal, config)
    if store is None:
        store = banquet.Store(backend)
        store.read_schema()
        business = store.get('banquets', request.get('banquet_id'))
    if not business:
        return {'status': 'not_found'}
    row = latest(store, business['record_id'])
    if not row:
        return {'status': 'not_found'}
    if actor['feishu_user_id'] not in customers._owner_ids(row['recipient']) + customers._owner_ids(row['submitted_by']):
        return core._blocked('handoff_actor_denied', '此交接由指定提交人与接手人处理。')
    origin = publication(ledger, row)
    basis = publication_basis.read(origin, business, backend)
    from . import handoff_notifications
    result = {'status': 'found', 'handoff': _view(row, store),
            'publication_basis': basis, 'materials_read': False,
            'is_recipient': actor['feishu_user_id'] in customers._owner_ids(row['recipient'])}
    try:
        result['notifications'] = handoff_notifications.summary(ledger, row)
        result['notifications_status'] = 'read'
    except Exception:
        result['notifications_status'] = 'unavailable'
    if not metadata_only:
        try:
            access = _access(purpose, basis, row, actor)
        except ValueError as exc:
            return {**result, **core._blocked('handoff_basis_denied', str(exc))}
        result.update(access)
        result['handoff'] = _view(row, store, origin)
        result['handoff']['files'] = [{**file, **access} for file in result['handoff']['files']]
    return result


def stage(command, request, backend, ledger, config, token, principal, *, context=None, personal_backend=None, now=None):
    try:
        principal = core._principal(principal)
        actor = core._actor_for_principal(principal, config)
        core._only_keys(core._mapping(request, 'request'), FIELDS[command])
        if personal_backend is None:
            raise ValueError('A verified personal connection is required for handoff.')
        intent = ledger.note_write_intent(principal)
        store = banquet.Store(personal_backend)
        schema = store.read_schema()
        business = store.get('banquets', request.get('banquet_id'))
        if not business or business.get('stage') != '已签单':
            raise ValueError('Read a signed banquet before preparing the handoff.')
        customer = personal_backend.get_customer(business['customer_record_id'])
        core._validate_customer(customer)
        before = latest(store, business['record_id'])
        moment, change_id = core._now(now).replace(microsecond=0), 'chg_' + secrets.token_urlsafe(18)
        operation = 'banquet_' + command.removeprefix('stage-').replace('-', '_')
        source = None
        if command == 'stage-handoff-submit':
            source = _source(context, principal)
            _reject_old_bytes(source, business, customer, ledger)
            if [f['delivery_id'] for f in source['files']] != request.get('delivery_ids'):
                raise ValueError('Material selection differs from host snapshots.')
            person = ledger.get_assignee(request.get('recipient_ref'), principal)
            if person is None:
                raise ValueError('Resolve a configured recipient in this conversation first.')
            person = customers._person(person)
            if len([a for a in config['allowed_actors'].values() if a['feishu_user_id'] == person['id']]) != 1:
                raise ValueError('Recipient must be one configured team member.')
            if customers._person(backend.get_assignee(person['id'])) != person:
                raise ValueError('Recipient changed.')
            patch = {'name': business['name'] + ' · 交接', 'banquet_id': business['record_id'],
                     'version': int(before['version']) + 1 if before else 1, 'recipient': [person],
                     'submitted_by': [{'id': actor['feishu_user_id'], 'name': actor['display_name']}],
                     'materials': core._json(material_labels(source['files'])),
                     'missing': core._required_text(request.get('missing'), 'missing (explicitly state none if complete)', 2000),
                     'status': '待接手', 'submitted_at': None, 'publication_id': change_id}
        else:
            if before is None or type(request.get('version')) is not int or request['version'] != before['version']:
                raise ValueError('Handoff version changed; read again.')
            origin = publication(ledger, before)
            if customers._owner_ids(before['recipient']) != [actor['feishu_user_id']] or before['status'] != '待接手':
                raise ValueError('Only the named recipient may handle the pending version.')
            if command == 'stage-handoff-accept':
                publication_basis.require_current(publication_basis.compare(origin, business, customer))
            source = origin['handoff_source']
            patch = {'status': '已接手' if command == 'stage-handoff-accept' else '已退回',
                     'acknowledged_at': None}
            if command == 'stage-handoff-return':
                patch['return_reason'] = core._required_text(request.get('reason'), 'reason', 2000)
        binding = getattr(personal_backend.runner, 'binding', None)
        if binding is None:
            raise ValueError('Personal connection binding unavailable.')
        body = {'change_id': change_id, 'operation_type': operation, 'principal': principal, 'actor': actor,
                'customer_record_id': core._record_id(customer),
                'customer_snapshot': {'record_id': core._record_id(customer), **core._snapshot(customer)},
                'schema_hash': core._hash(schema), 'banquet_before': business,
                'handoff_before': before, 'handoff_patch': patch, 'handoff_source': source,
                'connection_binding': binding, 'created_at': core._iso(moment),
                'expires_at': core._iso(moment + timedelta(seconds=int(config.get('ttl_seconds', 600))))}
        ledger.stage(body, core._action_token_hash(token), intent_version=intent)
        return {'status': 'staged', 'change_id': change_id}
    except (ValueError, TypeError, KeyError) as exc:
        return core._blocked('invalid_handoff', str(exc))
    except Exception:
        return core._blocked('handoff_unavailable', '无法核实权限、版本或材料；未提交交接。')


def file_check(staged):
    source = staged['handoff_source']
    return {'principal': source['principal'], 'work_id': source['work_id'], 'files': source['files'],
            'published': staged['operation_type'] != 'banquet_handoff_submit'}


def apply(staged, backend, ledger, moment, *, personal_backend=None, files_verified=False, started=None):
    def perform(effective):
        change_id = staged['change_id']
        def finish(status, code, **details):
            return core._finish(ledger, change_id, status, {'status': status, 'code': code, 'change_id': change_id, **details})
        try:
            if not files_verified or personal_backend is None:
                return finish('failed', 'handoff_verification_required')
            personal_backend.runner.connections.check_version(staged['connection_binding'])
            store = banquet.Store(personal_backend)
            if core._hash(store.read_schema()) != staged['schema_hash']:
                return finish('replan_required', 'schema_changed')
            business = store.get('banquets', staged['banquet_before']['record_id'])
            before = latest(store, staged['banquet_before']['record_id'])
            if business != staged['banquet_before'] or before != staged['handoff_before']:
                return finish('replan_required', 'handoff_changed')
            customer = personal_backend.get_customer(staged['customer_record_id'])
            if not customer or {'record_id': core._record_id(customer), **core._snapshot(customer)} != staged['customer_snapshot']:
                return finish('replan_required', 'customer_changed')
            submit = staged['operation_type'] == 'banquet_handoff_submit'
            if submit:
                _reject_old_bytes(staged['handoff_source'], business, customer, ledger)
            person = (staged['handoff_patch'] if submit else before)['recipient'][0]
            if customers._person(backend.get_assignee(person['id'])) != customers._person(person):
                return finish('replan_required', 'assignee_changed')
            if not submit:
                origin = publication(ledger, before)
                if staged['operation_type'] == 'banquet_handoff_accept':
                    basis = publication_basis.compare(origin, business, customer)
                    if basis['status'] != 'current':
                        return finish('replan_required', 'handoff_basis_' + basis['status'])
                if customers._owner_ids(before['recipient']) != [staged['actor']['feishu_user_id']]:
                    return finish('failed', 'handoff_actor_denied')
            # Both identities must agree on the exact target and schema before
            # the existing shared-CRM application performs an approved write.
            writer = banquet.Store(backend)
            if writer.read_schema() != store.read_schema() or latest(writer, business['record_id']) != before:
                return finish('replan_required', 'handoff_scope_changed')
            personal_backend.runner.connections.check_version(staged['connection_binding'])
        except Exception:
            return finish('failed', 'prewrite_read_failed')
        identifier = None if submit else before['record_id']
        executed_at = core._iso(effective.replace(microsecond=0))
        time_key = 'submitted_at' if submit else 'acknowledged_at'
        fields = {**staged['handoff_patch'], time_key: executed_at, 'operation_id': change_id}
        expected = {**(before if not submit else {}), **fields}
        try:
            identifier = writer.write('handoffs', identifier, fields)
        except Exception:
            pass
        try:
            def observe():
                nonlocal identifier
                if not identifier:
                    rows = [r for r in writer.list('handoffs') if r.get('operation_id') == change_id]
                    if len(rows) != 1:
                        return None
                    identifier = rows[0]['record_id']
                actual = store.get('handoffs', identifier)
                return actual if actual and banquet._matches(actual, expected) else None
            actual = core._poll_read(observe)
        except Exception:
            actual = None
        if actual is None:
            return finish('verification_unknown', 'handoff_write_unverified')
        return finish('verified', 'handoff_write_verified', handoff=_view(actual, store), executed_at=executed_at,
                      notification_note='业务已发布；助手通知单独记录，可在交接查询查看通知状态。' if submit else
                                        '交接业务处理已完成；助手通知单独记录，可在交接查询查看通知状态。')
    import time
    if staged.get('receipt'):
        return {**staged['receipt'], 'replayed': True}
    if staged['state'] != 'staged' or not ledger.claim(staged['change_id']):
        return {'status': 'verification_unknown', 'code': 'apply_in_progress', 'change_id': staged['change_id']}
    return core._run_customer_write(staged, ledger, moment, perform, started if started is not None else time.monotonic())


def authorize_file(publication_id, backend, ledger, config, principal, *, purpose='current'):
    purpose = _purpose(purpose)
    match = re.fullmatch(r'bh_(chg_[A-Za-z0-9_-]+)_([0-3])', publication_id)
    if not match:
        raise ValueError('Invalid handoff publication.')
    origin = ledger.get(match[1])
    if not origin or origin.get('operation_type') != 'banquet_handoff_submit' or origin.get('state') != 'verified':
        raise ValueError('Unknown handoff publication.')
    store = banquet.Store(backend)
    store.read_schema()
    business = store.get('banquets', origin['banquet_before']['record_id'])
    if not business:
        raise ValueError('Banquet is not readable.')
    row = latest(store, business['record_id'])
    if not row or publication(ledger, row)['change_id'] != origin['change_id']:
        raise ValueError('Publication has been replaced.')
    actor = core._actor_for_principal(principal, config)
    if actor['feishu_user_id'] not in customers._owner_ids(row['recipient']) + customers._owner_ids(row['submitted_by']):
        raise ValueError('Not a party to this handoff.')
    access = _access(purpose, publication_basis.read(origin, business, backend), row, actor)
    source = origin['handoff_source']
    file = source['files'][int(match[2])]
    return {'status': 'authorized', 'publication_id': publication_id, **access,
            'source': {**{k: v for k, v in source['principal'].items() if k != 'message_id'},
                       'work_id': source['work_id'], **file, **access}}
