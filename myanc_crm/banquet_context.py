"""Bounded, read-only context; each optional source keeps its own outcome."""
from . import banquet, core, handoffs


def read(request, backend, ledger, config, principal, *, private):
    core._actor_for_principal(core._principal(principal), config)
    core._only_keys(core._mapping(request, 'request'), banquet.FIELDS['banquet-context'])
    store = banquet.Store(backend)
    try:
        store.read_schema(('banquets',))
        business = store.get('banquets', request.get('banquet_id'))
        if not business:
            raise ValueError('Banquet is not readable.')
    except Exception:
        return core._blocked('banquet_unavailable', '无法读取指定婚宴；请先用宴会查询核对明确编号。')
    result = {'status': 'found', 'banquet': banquet._display(business, store), 'materials_read': False,
              'sources': {}, 'missing': [], 'history_limit': 10, 'history_has_more': None}

    def source(name, status, **details):
        result['sources'][name] = {'status': status, 'read_at': core._iso(core._now(None)), **details}
        if status not in {'read', 'empty', 'not_applicable'}:
            result['status'] = 'partial'
            result['missing'].append(name)

    source('banquet', 'read', record_id=business['record_id'], url=store.url('banquets', business['record_id']))
    try:
        customer = backend.get_customer(business['customer_record_id'])
        core._validate_customer(customer)
        if customer['record_id'] != business['customer_record_id']:
            raise ValueError('Customer relationship changed.')
        result['customer'] = core._display_customer(customer, backend)
        source('customer', 'read', record_id=customer['record_id'],
               url=core._safe_url(getattr(backend, 'customer_url', None), customer['record_id']))
    except Exception:
        source('customer', 'unavailable')
    try:
        store.read_schema(('followups',))
        history = [r for r in store.list('followups') if r['banquet_id'] == business['record_id']]
        history.sort(key=lambda r: (core._parse_time(r['occurred_at'], 'occurred_at'), r['record_id']), reverse=True)
        result['history'] = [banquet._display(r, store, 'followups') for r in history[:10]]
        result['history_has_more'] = len(history) > 10
        source('followups', 'read' if history else 'empty', limit=10, truncated=len(history) > 10,
               record_ids=[r['record_id'] for r in history[:10]])
    except Exception:
        source('followups', 'unavailable')
    if not private:
        source('handoff', 'private_required', message='交接材料与通知状态请在本人私聊读取。')
        return result
    try:
        store.read_schema(('handoffs',))
        value = handoffs.read({'banquet_id': business['record_id']}, backend, ledger, config, principal,
                              metadata_only=True, store=store, business=business)
        if value['status'] == 'found':
            for key in ('handoff', 'is_recipient', 'publication_basis'):
                result[key] = value[key]
            source('handoff', 'read', record_id=value['handoff']['record_id'], url=value['handoff']['url'])
            if 'notifications' in value:
                result['notifications'] = value['notifications']
            source('notifications', value['notifications_status'],
                   publication_basis_id=value['publication_basis']['publication_basis_id'])
            if value['publication_basis']['status'] != 'current':
                result['material_block_reason'] = 'publication_basis_' + value['publication_basis']['status']
            if value['publication_basis']['status'] in {'unknown', 'unavailable'}:
                result['status'] = 'partial'
                result['missing'].append('publication_basis')
        elif value['status'] == 'not_found':
            source('handoff', 'empty')
            source('notifications', 'not_applicable', reason='no_handoff')
        else:
            source('handoff', 'denied', message=value['message'])
    except Exception:
        source('handoff', 'unavailable')
    return result
