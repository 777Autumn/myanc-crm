"""Offline migration primitives for a frozen, reviewed maintenance inventory.

The maintenance caller verifies protected paths, route/session ownership, source
hashes and a stopped/drained gateway, backs up state, then atomically writes the
returned snapshots with their original ownership. No CLI, token or business
ledger is changed here. This is not a Bot command or a startup migration.
"""
import copy
from datetime import datetime, timezone
import hashlib
import re

from myanc_crm.connections import Connections, ROUTE_FIELDS


def native_work_session(session):
    """Match Go ID@CreatedAt.UnixNano without floating point truncation."""
    match = re.fullmatch(r"(.{19})(?:\.(\d{1,9}))?(Z|[+-]\d\d:\d\d)", session['created_at'])
    if not match:
        raise ValueError('invalid session timestamp')
    whole, fraction, offset = match.groups()
    date = datetime.fromisoformat(whole + offset.replace('Z', '+00:00'))
    delta = date.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    nanos = (delta.days * 86400 + delta.seconds) * 10**9 + int((fraction or '').ljust(9, '0'))
    return session['id'] + '@' + str(nanos)


def plan_history(config, works, snapshots, entrances, rows, bindings):
    """Inputs are read-only snapshots; entrances come from verified host routes.

    An entrance supplies principal, session_key, snapshot and any old native IDs
    positively attributed to it but absent from the host snapshot. Missing tool
    logs never establish that an unbound work is clean.
    """
    connections = Connections(config)
    updated = copy.deepcopy(snapshots)
    current = {r['subject']: r for r in rows}
    bound = {r['work']: r for r in bindings}
    additions, decisions = {}, []
    seen = set()
    for entrance in entrances:
        principal = entrance['principal']
        if connections.route(principal) != 'private':
            raise ValueError('migration requires an explicit private route')
        subject = connections.key(principal)
        if subject not in current:
            raise ValueError('connection missing from frozen registry')
        identity = (entrance['snapshot'], entrance['session_key'])
        if identity in seen:
            raise ValueError('duplicate migration entrance')
        seen.add(identity)
        snapshot = updated[entrance['snapshot']]
        key = entrance['session_key']
        sessions = snapshot['sessions']
        ids = snapshot['user_sessions'].get(key, [])
        if len(ids) != len(set(ids)) or any(sid not in sessions for sid in ids):
            raise ValueError('invalid session ownership')
        by_native = {native_work_session(sessions[sid]): sessions[sid] for sid in ids}
        covered = set()
        for work_id, work in works.items():
            if not all(work['Principal'].get(field) == principal.get(field) for field in ROUTE_FIELDS):
                continue
            if work['ID'] != work_id or work['Principal'].get('session_key') != key:
                raise ValueError('work identity conflicts with protected entrance')
            record = bound.get(work_id)
            row = current[subject]
            if record and record['subject'] != subject:
                raise ValueError('work binding subject conflict')
            valid = bool(record and record['version'] == row['version'] and
                         (not record['requires_connection'] or row['status'] == 'connected'))
            if not record:
                additions[work_id] = dict(work=work_id, subject=subject, version=-1, requires_connection=1)
            session = by_native.get(work['SessionID'])
            if session:
                covered.add(session['id'])
                if not valid:
                    session['connection_expired'] = True
            decisions.append(dict(work=work_id, disposition='preserve' if valid else 'expire'))
        for sid in ids:
            session = sessions[sid]
            context = any(session.get(k) for k in ('agent_session_id', 'past_agent_session_ids', 'history', 'file_turns'))
            if sid not in covered and context:
                session['connection_expired'] = True
        # Keep orphan IDs as denied native bindings, not as new file work.
        known = {native for sid in ids for native in
                 [sessions[sid].get('agent_session_id', ''), *sessions[sid].get('past_agent_session_ids', [])] if native}
        for native in entrance.get('orphan_native_ids', []):
            if not isinstance(native, str) or not native or native == '__continue__':
                raise ValueError('invalid orphan native ID')
            if native in known:
                continue
            sid = 'connection-expired-' + hashlib.sha256((key + '\0' + native).encode()).hexdigest()
            if sid in sessions:
                raise ValueError('orphan marker conflict')
            sessions[sid] = dict(id=sid, name='Expired personal work', agent_session_id=native,
                                 connection_expired=True, created_at='1970-01-01T00:00:00Z',
                                 updated_at='1970-01-01T00:00:00Z')
            snapshot['user_sessions'].setdefault(key, []).append(sid)
            known.add(native)
        active = snapshot['active_session'].get(key)
        if active and sessions[active].get('connection_expired'):
            # GetOrCreateActive opens a clean Session on the next new request.
            del snapshot['active_session'][key]
    return dict(connections=[{k: r[k] for k in ('subject', 'status', 'version')} for r in rows],
                bindings=list(bindings), additions=list(additions.values()), snapshots=updated, decisions=decisions)


def apply_registry(db, plan):
    """Use an existing registry, under stopped maintenance; never initialize it."""
    db.execute('BEGIN IMMEDIATE')
    try:
        actual = sorted(tuple(r) for r in db.execute('SELECT subject,status,version FROM connections'))
        expected = sorted((r['subject'], r['status'], r['version']) for r in plan['connections'])
        if actual != expected:
            raise ValueError('connection generation changed after inventory')
        for row in plan['bindings'] + plan['additions']:
            value = (row['work'], row['subject'], row['version'], row['requires_connection'])
            existing = db.execute('SELECT work,subject,version,requires_connection FROM connection_work WHERE work=?',
                                  (row['work'],)).fetchone()
            if existing is not None and tuple(existing) != value:
                raise ValueError('work binding changed after inventory')
            if existing is None and row in plan['bindings']:
                raise ValueError('frozen work binding disappeared')
        for row in plan['additions']:
            db.execute('INSERT OR IGNORE INTO connection_work VALUES(?,?,?,?)',
                       (row['work'], row['subject'], row['version'], row['requires_connection']))
        db.commit()
    except BaseException:
        db.rollback()
        raise
