"""Fictional journal replay; no host, model or Feishu access."""
import json
import unittest

from ops.maintenance_activity import activity


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


if __name__ == '__main__':
    unittest.main()
