"""Read-only activity classification for a complete, single-process journal.

Returns the existing idle-check fields, plus reconciled callback counts. Callers
must still check the quiet interval, receiver identity and business state. No
host access or permission to stop a service is provided by this function.
"""
import hashlib
import json
import re
import shlex


EVENTS = {'message received', 'turn complete', 'processing message',
          'message queued for busy session', 'processing queued message',
          'hosted card feedback', 'permission request', 'permission resolved',
          'file work intake rejected'}


def _object(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise ValueError('duplicate_log_field')
        fields[key] = value
    return fields


def log_fields(message):
    """Parse a complete gateway/SDK message; never turn missing data into {}."""
    if not isinstance(message, str) or not message.strip():
        raise ValueError('unsupported_journal_message')
    try:
        if message.lstrip().startswith('{'):
            fields = json.loads(message, object_pairs_hook=_object)
        else:
            # Go's default slog handler is used before the configured handler.
            text = re.fullmatch(r'\d{4}/\d\d/\d\d \d\d:\d\d:\d\d (DEBUG|INFO|WARN|ERROR) (.+)', message)
            sdk = re.fullmatch(r'(?:\d{4}/\d\d/\d\d \d\d:\d\d:\d\d )?\[(Debug|Info|Warn|Error)\] (.+)', message)
            if sdk:
                return dict(level=sdk[1].upper(), msg=sdk[2], format='sdk')
            tokens = shlex.split(text[2] if text else message)
            pairs = []
            words = []
            for token in tokens:
                if '=' in token:
                    key, value = token.split('=', 1)
                    if not key:
                        raise ValueError('invalid_log_field')
                    pairs.append((key, value))
                elif text and not pairs:
                    words.append(token)
                else:
                    raise ValueError('unsupported_journal_message')
            fields = _object(pairs)
            if text:
                if 'level' in fields or 'msg' in fields or not words:
                    raise ValueError('invalid_text_log')
                fields.update(level=text[1], msg=' '.join(words))
        if not isinstance(fields, dict) or not isinstance(fields.get('msg'), str) or not fields['msg']:
            raise ValueError('unsupported_journal_message')
        if 'level' in fields:
            if not isinstance(fields['level'], str) or fields['level'].upper() not in {'DEBUG', 'INFO', 'WARN', 'ERROR'}:
                raise ValueError('unsupported_log_level')
            fields['level'] = fields['level'].upper()
        return fields
    except (TypeError, ValueError):
        # Never include message content or decoder excerpts in diagnostics.
        raise ValueError('unsupported_journal_message') from None


def log_key(fields):
    """Exact reviewed fields; only the emission time is allowed to vary."""
    return hashlib.sha256(json.dumps({k: v for k, v in fields.items() if k != 'time'},
                                    sort_keys=True).encode()).hexdigest()


def parse_journal(journal, now):
    """Require full journalctl JSON output (--all), ordered and not in future."""
    rows = []
    previous = 0
    for line in journal.splitlines():
        try:
            record = json.loads(line, object_pairs_hook=_object)
            stamp = int(record['__REALTIME_TIMESTAMP'])
            fields = log_fields(record.get('MESSAGE'))
        except (KeyError, TypeError, ValueError):
            raise ValueError('unsupported_journal_record') from None
        if not previous <= stamp <= now * 1000000:
            raise ValueError('activity_time_order')
        previous = stamp
        rows.append((stamp, fields))
    return rows


def activity(journal, now, *, known_messages=()):
    """Unknown/ambiguous events remain unfinished; malformed input raises."""
    all_rows = parse_journal(journal, now)
    known = {log_key(fields) for fields in known_messages}
    rows = [(stamp, fields) for stamp, fields in all_rows if fields['msg'] in EVENTS]

    active, questions = {}, {}
    received, completed, rejected = set(), set(), set()
    unknown = sum(fields['msg'] not in EVENTS and (log_key(fields) not in known
                  or fields.get('level') in {'WARN', 'ERROR'}) for _, fields in all_rows)
    callbacks = []
    for stamp, fields in rows:
        event = fields['msg']
        message_id = fields.get('msg_id')
        if event == 'message received':
            if message_id:
                if message_id in received:
                    unknown += 1  # A redelivery is not proof the first intake finished.
                received.add(message_id)
                active[message_id] = dict(session=fields.get('session'),
                                          platform=fields.get('platform'), model_session=None,
                                          started=False, completed=None)
                continue
            # ponytail: this log lacks per-question session/index metadata. Only
            # one active turn/question is attributable; concurrency stays blocked.
            pending = [q for q in questions.values() if q['resolved'] is None]
            candidate = pending[0] if len(pending) == len(active) == 1 else None
            turn = next(iter(active.values()), None)
            if (candidate and candidate['tool'] == 'AskUserQuestion'
                    and candidate['turn'] is turn and not candidate['callbacks']
                    and fields.get('session') and fields['session'] == turn['session']
                    and fields.get('platform') == turn['platform'] == 'feishu'
                    and int(fields.get('content_len', 0)) > 0
                    and all(fields.get(k) in (False, 'false')
                            for k in ('has_images', 'has_audio', 'has_files'))):
                candidate['callbacks'].append(stamp)
                callbacks.append(candidate)
            else:
                unknown += 1
        elif event in {'processing message', 'message queued for busy session', 'processing queued message'}:
            session = fields.get('session')
            matches = [t for t in active.values() if session and session in
                       (t['session'], t['model_session'])]
            if event == 'processing message' and not matches:
                matches = [t for t in active.values() if t['model_session'] is None]
            if not session or len(matches) != 1:
                unknown += 1
            else:
                matches[0]['started'] = True
                if event == 'processing message':
                    matches[0]['model_session'] = session
        elif event == 'file work intake rejected':
            turn = active.get(message_id)
            if (turn and not turn['started'] and fields.get('reason')
                    and fields['reason'] != 'file_recovery_unknown'
                    and fields.get('session') and fields['session'] == turn['session']
                    and fields.get('platform') and fields['platform'] == turn['platform']):
                rejected.add(message_id)
                del active[message_id]
            else:
                unknown += 1
        elif event == 'permission request':
            request = fields.get('request_id')
            if not request or request in questions:
                unknown += 1
                continue
            if len(active) != 1:
                unknown += 1
            else:
                next(iter(active.values()))['started'] = True
            questions[request] = dict(tool=fields.get('tool'),
                                      turn=next(iter(active.values())) if len(active) == 1 else None,
                                      resolved=None, callbacks=[])
        elif event == 'permission resolved':
            question = questions.get(fields.get('request_id'))
            if question is None or question['resolved'] is not None:
                unknown += 1
            else:
                question['resolved'] = stamp
        elif event == 'turn complete':
            turn = active.pop(message_id, None)
            if not message_id or turn is None:
                unknown += 1
            else:
                if turn['model_session'] and fields.get('session') != turn['model_session']:
                    unknown += 1
                turn['completed'] = stamp
                completed.add(message_id)

    reconciled = sum(q['resolved'] is not None and q['turn']['completed'] is not None
                     and q['callbacks'][0] <= q['resolved'] <= q['turn']['completed']
                     for q in callbacks)
    unresolved = sum(q['resolved'] is None for q in questions.values())
    latest = rows[-1][0] if rows else now * 1000000
    return dict(quiet_seconds=round(now - latest / 1000000),
                received=len(received), completed=len(completed), rejected=len(rejected),
                reconciled_callbacks=reconciled,
                unclassified=len(active) + unknown + unresolved + len(callbacks) - reconciled,
                fingerprint=hashlib.sha256(json.dumps(all_rows, sort_keys=True).encode()).hexdigest())
