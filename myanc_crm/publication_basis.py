"""Read-only comparison of a verified publication's original business evidence."""
import math

from . import core


BANQUET_FIELDS = ('name', 'number', 'customer_record_id', 'estimated_tables', 'banquet_date',
                  'date_status', 'date_note', 'session', 'venue', 'budget')
CUSTOMER_FIELDS = ('customer_number', 'name', 'contact', 'phone', 'email')


def _value(key, value):
    if value is None:
        return None
    if key in {'estimated_tables', 'budget'}:
        if type(value) not in {int, float} or not math.isfinite(value) or value < 0:
            raise ValueError('Invalid numeric evidence.')
        return value
    if key == 'banquet_date':
        return core._parse_time(value, key)
    if not isinstance(value, str):
        raise ValueError('Invalid text evidence.')
    return value


def compare(origin, business, customer):
    """Missing keys stay missing; never fill historical evidence from today's data."""
    result = {'status': 'unknown', 'publication_basis_id': origin.get('change_id'),
              'differences': [], 'missing': [], 'checked_at': core._iso(core._now(None)),
              'scope': {'banquet': list(BANQUET_FIELDS), 'customer': list(CUSTOMER_FIELDS)},
              'content_verified': False}
    old_business, old_customer = origin.get('banquet_before'), origin.get('customer_snapshot')
    for label, old, fields in (('banquet', old_business, BANQUET_FIELDS),
                               ('customer', old_customer, CUSTOMER_FIELDS)):
        for key in ('record_id', *fields):
            if not isinstance(old, dict) or key not in old:
                result['missing'].append('publication.' + label + '.' + key)
    if result['missing']:
        return result
    if (not old_business['record_id'] or not old_customer['record_id'] or
            old_business['customer_record_id'] != old_customer['record_id']):
        result['missing'].append('publication.customer_relationship')
        return result
    for label, old, fields in (('banquet', old_business, BANQUET_FIELDS),
                               ('customer', old_customer, CUSTOMER_FIELDS)):
        for key in fields:
            try:
                _value(key, old[key])
            except (TypeError, ValueError):
                result['missing'].append('publication.' + label + '.' + key)
    if result['missing']:
        return result
    result['status'] = 'unavailable'
    for label, current, fields in (('banquet', business, BANQUET_FIELDS),
                                   ('customer', customer, CUSTOMER_FIELDS)):
        for key in ('record_id', *fields):
            if not isinstance(current, dict) or key not in current:
                result['missing'].append('current.' + label + '.' + key)
    if result['missing']:
        return result
    if business['record_id'] != old_business['record_id'] or customer['record_id'] != business['customer_record_id']:
        result['missing'].append('current.record_relationship')
        return result
    for label, old, current, fields in (('banquet', old_business, business, BANQUET_FIELDS),
                                       ('customer', old_customer, customer, CUSTOMER_FIELDS)):
        for key in fields:
            try:
                value = _value(key, current[key])
            except (TypeError, ValueError):
                result['missing'].append('current.' + label + '.' + key)
                continue
            if _value(key, old[key]) != value:
                result['differences'].append({'source': label, 'field': key,
                    'published': core._fence_value(old[key]), 'current': core._fence_value(current[key])})
    if not result['missing']:
        result['status'] = 'stale' if result['differences'] else 'current'
    return result


def read(origin, business, backend):
    try:
        customer = backend.get_customer(business['customer_record_id']) if business else None
    except Exception:
        customer = None
    return compare(origin, business, customer)


def require_current(basis):
    if basis['status'] != 'current':
        raise ValueError('Publication business basis is ' + basis['status'] + '; revise and publish new materials.')
