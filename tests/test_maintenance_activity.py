"""Fictional journal replay; no host, model or Feishu access."""
import json
import unittest

from ops.maintenance_activity import activity, log_fields


def row(second, event, **fields):
    return json.dumps({'__REALTIME_TIMESTAMP': str(second * 1000000),
                      'MESSAGE': ' '.join(f'{k}={json.dumps(v)}' for k, v in
                                        dict(msg=event, **fields).items())})


def incoming(second=1, message='message-a', session='session-a'):
    return row(second, 'message received', msg_id=message, session=session,
               platform='feishu', content_len=12,
               has_images=False, has_audio=False, has_files=False)


def journey():
    return [incoming(), row(2, 'permission request', request_id='question-a', tool='AskUserQuestion'),
            incoming(3, ''), row(4, 'permission resolved', request_id='question-a'),
            row(5, 'turn complete', msg_id='message-a', session='internal-session-a')]


class MaintenanceActivityTests(unittest.TestCase):
    def check(self, rows):
        return activity('\n'.join(rows), 200)

    def test_completed_question_is_not_an_extra_turn(self):
        rows = journey()
        # The legacy helper counts the empty-ID answer as a second, unfinished turn.
        result = self.check(rows)
        self.assertEqual((1, 1, 1, 0, 195), tuple(result[k] for k in
                         ('received', 'completed', 'reconciled_callbacks', 'unclassified', 'quiet_seconds')))
        self.assertNotIn('session-a', json.dumps(result))

    def test_incomplete_or_ambiguous_activity_stays_blocked(self):
        good = journey()
        cases = {
            'unanswered': good[:2],
            'answer_without_resolution': good[:3] + good[4:],
            'resolved_but_work_running': good[:4],
            'unknown_empty_id': [incoming(1, '')],
            'wrong_session': good[:2] + [incoming(3, '', 'session-b')] + good[3:],
            'duplicate_callback': good[:3] + [incoming(3, '')] + good[3:],
            'late_callback': good + [incoming(6, '')],
            'concurrent_turn': [incoming(), incoming(1, 'message-b', 'session-b')] + good[1:] +
                               [row(6, 'turn complete', msg_id='message-b')],
            'orphan_complete': [good[-1]],
            'redelivery_after_completion': good + [incoming(6), row(7, 'turn complete', msg_id='message-a')],
            'orphan_processing': [row(1, 'processing message', session='internal-a')],
            'orphan_queue': [row(1, 'message queued for busy session', session='session-a')],
            'orphan_processing_queue': [row(1, 'processing queued message', session='session-a')],
            'orphan_question_resolved': [good[1], good[3]],
            'cross_session_queue': [incoming(), row(2, 'processing queued message', session='session-b'), good[-1]],
            'cross_session_complete': [incoming(), row(2, 'processing message', session='internal-a'), good[-1]],
        }
        for name, rows in cases.items():
            with self.subTest(name=name):
                self.assertGreater(self.check(rows)['unclassified'], 0)

    def test_normal_turn_and_quiet_time(self):
        rows = [incoming(), row(5, 'turn complete', msg_id='message-a')]
        self.assertEqual(0, self.check(rows)['unclassified'])
        before = self.check(rows)
        after = self.check(rows + [row(190, 'hosted card feedback')])
        self.assertEqual(10, after['quiet_seconds'])
        self.assertNotEqual(before['fingerprint'], after['fingerprint'])
        normal = [incoming(), row(2, 'processing message', session='internal-a'),
                  row(3, 'turn complete', msg_id='message-a', session='internal-a')]
        self.assertEqual(0, self.check(normal)['unclassified'])

    def test_invalid_or_truncated_journal_is_not_idle(self):
        for text in ('not-json', row(201, 'message received', msg_id='future'),
                     row(2, 'turn complete') + '\n' + incoming(1)):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    activity(text, 200)

    def test_missing_or_unsupported_messages_fail_closed(self):
        for fields in ({}, {'MESSAGE': None}, {'MESSAGE': [65, 66]}, {'MESSAGE': ''},
                       {'MESSAGE': '{"msg":null}'}, {'MESSAGE': 'msg=one msg=two'},
                       {'MESSAGE': '{"msg":"one","msg":"two"}'},
                       {'MESSAGE': 'level=INFO msg="truncated'}):
            with self.subTest(fields=fields):
                with self.assertRaisesRegex(ValueError, '^unsupported_journal_record$'):
                    activity(json.dumps(dict(__REALTIME_TIMESTAMP='1000000', **fields)), 200)

    def test_json_logfmt_sdk_and_default_go_text(self):
        fields = {'level': 'INFO', 'msg': 'platform ready', 'project': 'fictional-a'}
        self.assertEqual(fields, log_fields(json.dumps(fields)))
        self.assertEqual(fields, log_fields('level=INFO msg="platform ready" project=fictional-a'))
        self.assertEqual(dict(level='INFO', msg='config loaded', path='/example/config.toml'),
                         log_fields('2026/01/01 00:00:01 INFO config loaded path=/example/config.toml'))
        self.assertEqual(dict(level='ERROR', msg='websocket failed', format='sdk'),
                         log_fields('2026/01/01 00:00:01 [Error] websocket failed'))

    def test_unknown_events_and_changed_known_fields_remain_unclassified(self):
        known = {'level': 'INFO', 'msg': 'config loaded', 'path': '/example/config.toml'}
        saved = json.dumps({'__REALTIME_TIMESTAMP': '1000000', 'MESSAGE': json.dumps(known)})
        self.assertEqual(1, activity(saved, 200)['unclassified'])
        self.assertEqual(0, activity(saved, 200, known_messages=[known])['unclassified'])
        self.assertEqual(1, activity(saved.replace('config.toml', 'changed.toml'), 200,
                                    known_messages=[known])['unclassified'])
        self.assertGreater(activity(row(1, 'unknown INFO', level='INFO'), 200)['unclassified'], 0)
        sdk = json.dumps({'__REALTIME_TIMESTAMP': '1000000', 'MESSAGE': '[Error] websocket failed'})
        self.assertGreater(activity(sdk, 200)['unclassified'], 0)

    def test_rejected_intake_is_terminal_but_not_a_completed_model_turn(self):
        reject = row(2, 'file work intake rejected', msg_id='message-a',
                     platform='feishu', session='session-a', reason='file_work_association_required')
        result = self.check([incoming(), reject, incoming(3, 'message-b'),
                             row(4, 'turn complete', msg_id='message-b')])
        self.assertEqual(0, result['unclassified'])
        self.assertEqual((2, 1, 1, 0), tuple(result[k] for k in
                         ('received', 'completed', 'rejected', 'unclassified')))
        self.assertEqual(198, self.check([incoming(), reject])['quiet_seconds'])
        cases = {
            'no_intake': [reject],
            'duplicate_terminal': [incoming(), reject, reject],
            'already_started': [incoming(), row(1, 'processing message', session='internal-a'), reject],
            'queued': [incoming(), row(1, 'message queued for busy session', session='session-a'), reject],
            'pending_question': [incoming(), journey()[1], reject],
            'wrong_message': [incoming(message='message-b'), reject],
            'wrong_session': [incoming(session='session-b'), reject],
            'completed_then_rejected': [incoming(), row(1, 'turn complete', msg_id='message-a'), reject],
            'outbound_binding_failure': [incoming(), row(2, 'file work: reply association failed; message will not be resent')],
            'active_outbound_failure': [incoming(), row(1, 'processing message', session='internal-a'),
                                       row(2, 'file work: reply association failed; message will not be resent')],
        }
        for key, value in (('platform', 'other'), ('session', ''), ('reason', ''),
                           ('reason', 'file_recovery_unknown')):
            fields = dict(msg_id='message-a', platform='feishu', session='session-a', reason='file_work_association_required')
            fields[key] = value
            cases['invalid_' + key + '_' + value] = [incoming(), row(2, 'file work intake rejected', **fields)]
        for name, rows in cases.items():
            with self.subTest(name=name):
                self.assertGreater(self.check(rows)['unclassified'], 0)


if __name__ == '__main__':
    unittest.main()
