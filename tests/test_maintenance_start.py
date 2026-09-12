import copy
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('maintenance_start', Path(__file__).parents[1] / 'ops/maintenance_start.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def sample(active='active', exe=m.EXE, pid='42', **changes):
    value = dict(Id=m.UNIT, LoadState='loaded', Type='simple', User='ccconnect', Group='ccconnect',
                 WorkingDirectory='/var/lib/cc-connect', KillMode='control-group',
                 FragmentPath='/etc/systemd/system/cc-connect.service', DropInPaths='',
                 ExecStart=exec_status(pid='0' if active == 'inactive' else pid), NeedDaemonReload='no',
                 MainPID=pid, InvocationID='fixture-invocation', ActiveState=active,
                 SubState='running', NRestarts='0', exe=exe, process_start='123', receivers=[pid])
    if active == 'inactive':
        value.update(MainPID='0', InvocationID='', SubState='dead', exe=None, process_start=None, receivers=[])
    value.update(changes)
    return value


def exec_status(pid='42', argv='fixed', ignore='no'):
    start = 'n/a' if pid == '0' else 'Sat 2026-09-12 00:00:01 UTC'
    return ('{ path=' + m.EXE + ' ; argv[]=' + argv + ' ; ignore_errors=' + ignore
            + ' ; start_time=[' + start + '] ; stop_time=[n/a] ; pid=' + pid
            + ' ; code=(null) ; status=0/0 }')


class FakeSystemd:
    def __init__(self, sequence):
        self.sequence = list(sequence)
        self.state = sample('inactive')
        self.commands = []
        self.start_error = None

    def sample(self):
        if self.commands and self.commands[-1] == 'start' and self.sequence:
            self.state = self.sequence.pop(0)
        return copy.deepcopy(self.state)

    def command(self, verb):
        self.commands.append(verb)
        if verb == 'stop':
            self.state = sample('inactive')
        elif self.start_error:
            raise self.start_error


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.receipts = {}
        self.control_checks = 0

    def sleep(self, seconds):
        self.now += seconds

    def record(self, name, payload):
        if name in self.receipts:
            raise FileExistsError(name)
        self.receipts[name] = payload

    def controls(self):
        self.control_checks += 1

    def start(self, backend):
        return m.start_once(self.record, self.controls, backend=backend, timeout=2,
                            clock=lambda: self.now, sleep=self.sleep)

    def test_delayed_exec_does_not_trigger_false_failure(self):
        backend = FakeSystemd([sample(exe=None, receivers=[], process_start=None),
                               sample(exe='/usr/lib/systemd/systemd', receivers=[]), sample(), sample()])
        result = self.start(backend)
        self.assertEqual(result['pid'], '42')
        self.assertGreater(self.now, 0)
        self.assertEqual(backend.commands, ['start'])
        self.assertNotIn('start-failed.json', self.receipts)

    def test_never_ready_times_out_then_stops_pre_exec_unit(self):
        backend = FakeSystemd([sample(exe=None, receivers=[], process_start=None)])
        with self.assertRaisesRegex(m.StartError, 'startup_timeout'):
            self.start(backend)
        self.assertEqual(backend.commands, ['start', 'stop'])
        self.assertGreaterEqual(self.now, 2)
        self.assertNotIn('started.json', self.receipts)

    def test_same_invocation_pause_does_not_require_target_exe(self):
        backend = FakeSystemd([])
        backend.state = sample(exe='/usr/lib/systemd/systemd', receivers=[])
        identity = m.unit_identity(backend.sample())
        self.assertEqual(m.pause_verified(backend, identity, 'fixture-invocation', self.controls), 'paused')
        self.assertEqual(backend.commands, ['stop'])

    def test_two_ready_samples_required(self):
        backend = FakeSystemd([sample(), sample(exe=None, receivers=[]), sample(), sample()])
        self.start(backend)
        self.assertEqual(self.now, 0.75)
        self.assertEqual(backend.commands, ['start'])

    def test_zero_pid_then_exec_is_allowed(self):
        backend = FakeSystemd([sample(active='activating', pid='0', receivers=[], exe=None,
                                     process_start=None, InvocationID=''), sample(), sample()])
        self.start(backend)
        self.assertEqual(backend.commands, ['start'])

    def test_duplicate_receiver_or_auto_restart_rejects(self):
        for changes, reason in (({'receivers': ['42', '43']}, 'duplicate_receiver'),
                                ({'NRestarts': '1'}, 'unexpected_restart'),
                                ({'ActiveState': 'failed'}, 'startup_exited')):
            with self.subTest(reason=reason):
                self.receipts.clear()
                backend = FakeSystemd([sample(**changes)])
                with self.assertRaisesRegex(m.StartError, reason):
                    self.start(backend)
                self.assertEqual(backend.commands, ['start', 'stop'])

    def test_pid_change_and_pid_reuse_fail(self):
        for changed, reason in ((sample(pid='43'), 'startup_pid_changed'),
                                (sample(process_start='456'), 'startup_pid_reused')):
            with self.subTest(reason=reason):
                self.receipts.clear()
                backend = FakeSystemd([sample(), changed])
                with self.assertRaisesRegex(m.StartError, reason):
                    self.start(backend)
                self.assertEqual(backend.commands, ['start', 'stop'])

    def test_changed_invocation_is_not_stopped(self):
        backend = FakeSystemd([sample(), sample(InvocationID='replacement')])
        with self.assertRaisesRegex(m.StartError, 'startup_invocation_changed'):
            self.start(backend)
        self.assertEqual(backend.commands, ['start'])
        self.assertEqual(self.receipts['start-failed.json']['pause_error'], 'pause_invocation_changed')

    def test_changed_unit_is_not_stopped(self):
        backend = FakeSystemd([sample(User='someone-else')])
        with self.assertRaisesRegex(m.StartError, 'unexpected_unit'):
            self.start(backend)
        self.assertEqual(backend.commands, ['start'])

    def test_existing_request_consumed_no_second_start(self):
        self.receipts['start-requested.json'] = {}
        backend = FakeSystemd([sample(), sample()])
        with self.assertRaises(FileExistsError):
            self.start(backend)
        self.assertEqual(backend.commands, [])

    def test_active_service_not_touched(self):
        backend = FakeSystemd([])
        backend.state = sample()
        with self.assertRaisesRegex(m.StartError, 'service_not_stopped'):
            self.start(backend)
        self.assertEqual(backend.commands, [])

    def test_post_exec_receipt_error_stops_before_failure_record(self):
        backend = FakeSystemd([sample(), sample()])
        sequence = []
        def record(name, payload):
            sequence.append((name, list(backend.commands)))
            if name == 'started.json':
                raise OSError('sensitive path must not be emitted')
            self.record(name, payload)
        with self.assertRaises(m.StartError) as caught:
            m.start_once(record, self.controls, backend=backend, timeout=2,
                         clock=lambda: self.now, sleep=self.sleep)
        self.assertEqual(sequence[-1], ('start-failed.json', ['start', 'stop']))
        self.assertNotIn('sensitive', str(caught.exception))

    def test_command_error_after_acceptance_pauses_without_retry(self):
        backend = FakeSystemd([sample(exe=None, receivers=[])])
        backend.start_error = TimeoutError('private output')
        with self.assertRaises(m.StartError) as caught:
            self.start(backend)
        self.assertEqual(backend.commands, ['start', 'stop'])
        self.assertNotIn('private output', str(caught.exception))

    def test_interruption_and_failure_record_error_still_pause(self):
        backend = FakeSystemd([sample(exe=None, receivers=[])])
        def record(name, payload):
            if name == 'start-failed.json':
                raise OSError('full')
            self.record(name, payload)
        def interrupt(seconds):
            raise KeyboardInterrupt()
        with self.assertRaises(m.StartError) as caught:
            m.start_once(record, self.controls, backend=backend, sleep=interrupt)
        self.assertEqual(backend.commands, ['start', 'stop'])
        self.assertIn('receipt_failed', str(caught.exception))

    def test_preflight_control_failure_never_starts(self):
        backend = FakeSystemd([])
        with self.assertRaises(OSError):
            m.start_once(self.record, lambda: (_ for _ in ()).throw(OSError('drift')), backend=backend)
        self.assertEqual(backend.commands, [])

    def test_invalid_or_pending_reload_unit_is_rejected(self):
        for changes in ({'NeedDaemonReload': 'yes'}, {'KillMode': 'process'},
                        {'ExecStart': '{ path=/other ; }'}, {'Id': 'other.service'}):
            with self.subTest(changes=changes), self.assertRaises(m.StartError):
                m.unit_identity(sample(**changes))

    def test_systemctl_mutation_is_fixed_no_shell(self):
        with patch.object(m.subprocess, 'run') as run:
            m.Systemd().command('start')
            self.assertEqual(run.call_args.args[0], ['systemctl', 'start', m.UNIT])
            with self.assertRaises(m.StartError):
                m.Systemd().command('restart')
            self.assertEqual(run.call_count, 1)

    def test_dynamic_exec_status_is_not_configuration_drift(self):
        before = sample('inactive')
        after = sample(ExecStart=exec_status().replace('stop_time=[n/a]', 'stop_time=[Sat 2026-09-12 00:01:00 UTC]')
                       .replace('code=(null)', 'code=exited').replace('status=0/0', 'status=1'))
        self.assertEqual(m.unit_identity(before), m.unit_identity(after))

    def test_static_exec_arguments_and_flags_remain_pinned(self):
        before = m.unit_identity(sample('inactive'))
        for changed in (exec_status(argv='changed'), exec_status(ignore='yes')):
            self.assertNotEqual(before, m.unit_identity(sample(ExecStart=changed)))

    def test_unknown_or_multiple_exec_display_fails_closed(self):
        for value in ('{ path=' + m.EXE + ' ; argv[]=fixed ; }', exec_status() + ' ' + exec_status()):
            with self.subTest(value=value), self.assertRaisesRegex(m.StartError, 'unsupported_exec_format'):
                m.unit_identity(sample(ExecStart=value))

    def test_show_failure_propagates_instead_of_empty_success(self):
        with patch.object(m.subprocess, 'check_output', side_effect=TimeoutError('private output')):
            with self.assertRaises(TimeoutError):
                m.Systemd().sample()

    def test_missing_show_properties_rejected(self):
        with patch.object(m.subprocess, 'check_output', return_value='MainPID=0\n'):
            with self.assertRaisesRegex(m.StartError, 'incomplete_unit_state'):
                m.Systemd().sample()

    @unittest.skipUnless(Path('/proc/self/stat').exists(), 'Linux /proc adapter test')
    def test_real_proc_sample_with_stubbed_systemctl_only(self):
        # Actual /proc executable/starttime sampling; no real service command.
        state = sample(pid=str(os.getpid()))
        output = '\n'.join(key + '=' + state[key] for key in m.CONFIG_KEYS + m.STATE_KEYS)
        with patch.object(m.subprocess, 'check_output', return_value=output):
            observed = m.Systemd().sample()
        self.assertEqual(observed['exe'], str(Path('/proc/self/exe').resolve()))
        self.assertTrue(observed['process_start'].isdecimal())
        self.assertEqual(observed['MainPID'], str(os.getpid()))

    def test_pause_refuses_control_drift_without_touching_service(self):
        backend = FakeSystemd([])
        backend.state = sample(exe=None, receivers=[])
        identity = m.unit_identity(backend.sample())
        def drift():
            raise OSError('changed controls')
        with self.assertRaises(OSError):
            m.pause_verified(backend, identity, 'fixture-invocation', drift)
        self.assertEqual(backend.commands, [])

    def test_stop_error_recorded_with_last_safe_sample(self):
        backend = FakeSystemd([sample(exe=None, receivers=[])])
        original = backend.command
        def command(verb):
            if verb == 'stop':
                raise TimeoutError('private credential must be hidden')
            original(verb)
        backend.command = command
        with self.assertRaises(m.StartError) as caught:
            self.start(backend)
        failure = self.receipts['start-failed.json']
        self.assertEqual(failure['pause_error'], 'TimeoutError')
        self.assertFalse(failure['last_sample']['expected_exe'])
        self.assertNotIn('private credential', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
