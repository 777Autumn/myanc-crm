"""Read-only activity classification for a complete, single-process journal.

Returns the existing idle-check fields, plus reconciled callback counts. Callers
must still check the quiet interval, receiver identity and business state. No
host access or permission to stop a service is provided by this function.
"""
import hashlib
import json
import shlex


EVENTS = {'message received', 'turn complete', 'processing message',
          'message queued for busy session', 'processing queued message',
          'hosted card feedback', 'permission request', 'permission resolved'}


def activity(journal, now):
    """Unknown/ambiguous events remain unfinished; malformed input raises."""
    rows = []
    previous = 0
    for line in journal.splitlines():
        record = json.loads(line)
        message = record.get('MESSAGE')
        if not isinstance(message, str):
            continue  # journald metadata, not a gateway message
        fields = (json.loads(message) if message.startswith('{') else
                  dict(part.split('=', 1) for part in shlex.split(message) if '=' in part))
        if fields.get('msg') not in EVENTS:
            continue
        stamp = int(record['__REALTIME_TIMESTAMP'])
        if not previous <= stamp <= now * 1000000:
            raise ValueError('activity_time_order')
        previous = stamp
        rows.append((stamp, fields))

    active, questions = {}, {}
    received, completed = set(), set()
    unknown = 0
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
                                          completed=None)
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
            elif event == 'processing message':
                matches[0]['model_session'] = session
        elif event == 'permission request':
            request = fields.get('request_id')
            if not request or request in questions:
                unknown += 1
                continue
            if len(active) != 1:
                unknown += 1
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
                received=len(received), completed=len(completed),
                reconciled_callbacks=reconciled,
                unclassified=len(active) + unknown + unresolved + len(callbacks) - reconciled,
                fingerprint=hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest())
