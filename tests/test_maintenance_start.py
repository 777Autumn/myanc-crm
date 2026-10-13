import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import sys
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

    def test_duplicate_failure_retains_second_identity_after_protective_stop(self):
        details = [{'pid': '43', 'observation': 'complete', 'ppid': '42',
                    'process_start': '456', 'state': 'S', 'uid': 1001,
                    'expected_exe': True, 'exe_path_sha256': 'a' * 64,
                    'cgroup_sha256': 'b' * 64}]
        backend = FakeSystemd([sample(receivers=['42', '43'], receiver_details=details)])
        with self.assertRaisesRegex(m.StartError, 'duplicate_receiver'):
            self.start(backend)
        self.assertEqual(backend.commands, ['start', 'stop'])
        failure = self.receipts['start-failed.json']['last_sample']
        self.assertEqual(failure['receiver_pids'], ['42', '43'])
        self.assertEqual(failure['receiver_details'], details)
        self.assertEqual(backend.state['receivers'], [])

    def test_receiver_detail_errors_preserve_pid_without_private_error_text(self):
        for error, category in ((FileNotFoundError('private path'), 'disappeared_during_read'),
                                (PermissionError('private path'), 'permission_denied'),
                                (OSError('private path'), 'unreadable')):
            with self.subTest(category=category), patch.object(Path, 'read_text', side_effect=error):
                detail = m.receiver_detail(Path('/proc/43'))
                self.assertEqual(detail['pid'], '43')
                self.assertEqual(detail['observation'], category)
                self.assertNotIn('private', json.dumps(detail))

    def test_healthy_samples_remain_identical_for_existing_stable_window(self):
        state = sample()
        output = '\n'.join(key + '=' + state[key] for key in m.CONFIG_KEYS + m.STATE_KEYS)
        proc_stat = '42 (cc-connect-anc) S 1 ' + '0 ' * 17 + '123'
        def read(path):
            return 'cc-connect-anc' if path.name == 'comm' else proc_stat
        with patch.object(m.subprocess, 'check_output', return_value=output), \
                patch.object(Path, 'glob', return_value=[Path('/proc/42/comm')]), \
                patch.object(Path, 'read_text', autospec=True, side_effect=read), \
                patch.object(Path, 'resolve', return_value=Path(m.EXE)), \
                patch.object(m, 'receiver_detail', side_effect=[{'time': 1}, {'time': 2}]) as detail:
            first, second = m.Systemd().sample(), m.Systemd().sample()
        self.assertEqual(first, second)  # Existing running() compares whole samples.
        self.assertNotIn('receiver_details', first)  # Frozen normal schema unchanged.
        detail.assert_not_called()

    def test_receiver_detail_detects_pid_reuse_and_hashes_private_paths(self):
        before = '43 (name with spaces) S 42 ' + '0 ' * 17 + '456'
        after = before.replace('456', '789')
        with patch.object(Path, 'read_text', side_effect=[before, 'Uid:\t1001\t1001', after]), \
                patch.object(Path, 'resolve', return_value=Path('/private/executable')), \
                patch.object(Path, 'read_bytes', return_value=b'0::/private/service'):
            detail = m.receiver_detail(Path('/proc/43'))
        self.assertEqual(detail['observation'], 'changed_during_read')
        self.assertEqual(detail['process_start'], '456')
        self.assertEqual(detail['process_start_after'], '789')
        self.assertEqual(detail['ppid'], '42')
        self.assertEqual(detail['uid'], 1001)
        self.assertNotIn('private', json.dumps(detail))

    @unittest.skipUnless(sys.platform == 'linux', 'Linux fork/exec evidence fixture')
    def test_real_fork_inherits_comm_then_exec_changes_identity(self):
        # No gateway, network or actual systemctl. Pipes freeze the pre-exec child.
        import ctypes
        import select
        import signal
        libc = ctypes.CDLL(None, use_errno=True)
        old_name = Path('/proc/self/comm').read_bytes().strip()
        self.assertEqual(libc.prctl(15, b'cc-connect-anc', 0, 0, 0), 0)
        go_read, go_write = os.pipe()
        ack_read, ack_write = os.pipe()
        child = None
        try:
            os.set_inheritable(go_read, True)
            os.set_inheritable(ack_write, True)
            child = os.fork()
            if child == 0:
                try:
                    os.read(go_read, 1)
                    code = f'import os; os.write({ack_write}, b"x"); os.read({go_read}, 1)'
                    os.execv(sys.executable, [sys.executable, '-c', code])
                finally:
                    os._exit(99)
            os.close(ack_write)
            ack_write = None
            state = sample(pid=str(os.getpid()))
            output = '\n'.join(key + '=' + state[key] for key in m.CONFIG_KEYS + m.STATE_KEYS)
            with patch.object(m.subprocess, 'check_output', return_value=output):
                inherited = m.Systemd().sample()
                self.assertIn(str(child), inherited['receivers'])
                self.assertIn(str(os.getpid()), inherited['receivers'])
                details = {d['pid']: d for d in inherited['receiver_details']}
                parent_detail, child_detail = details[str(os.getpid())], details[str(child)]
                self.assertEqual(child_detail['observation'], 'complete')
                self.assertEqual(child_detail['ppid'], str(os.getpid()))
                self.assertEqual(child_detail['exe_path_sha256'], parent_detail['exe_path_sha256'])
                self.assertEqual(child_detail['cgroup_sha256'], parent_detail['cgroup_sha256'])
                self.assertIn(str(child), m.diagnostic(inherited)['receiver_pids'])
                os.write(go_write, b'x')
                self.assertTrue(select.select([ack_read], [], [], 5)[0], 'exec acknowledgement timeout')
                self.assertEqual(os.read(ack_read, 1), b'x')
                after = m.Systemd().sample()
                self.assertNotIn(str(child), after['receivers'])
                self.assertEqual(m.receiver_detail(Path('/proc') / str(child))['process_start'],
                                 child_detail['process_start'])
        finally:
            if child:
                try:
                    os.kill(child, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                os.waitpid(child, 0)
            libc.prctl(15, old_name, 0, 0, 0)
            for fd in (go_read, go_write, ack_read, ack_write):
                if fd is not None:
                    os.close(fd)

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


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.backend = FakeSystemd([sample(), sample()])
        self.now = 0
        self.controls_count = 0
        self.snapshots = dict(controls_sha256='a' * 64, business_state_sha256='b' * 64,
                              installed_manifest_sha256='e' * 64)
        attempt = dict(candidate_sha256='c' * 64, manifest_sha256='d' * 64,
                       installed_manifest_sha256='e' * 64)
        request = dict(unit=m.UNIT, identity_sha256=hashlib.sha256(
            json.dumps(m.unit_identity(sample('inactive')), sort_keys=True).encode()).hexdigest())
        self.expected = dict(attempt,
                             attempt_sha256=self.put('attempt.json', attempt),
                             start_request_sha256=self.put('start-requested.json', request),
                             failure_sha256=self.put('failed.json', {'category': 'fixture_health_failure'}),
                             failure_receipt='failed.json')
        self.diagnosis = dict(self.expected, **self.snapshots,
                              cause='Fixture classifier rejected known shutdown after a verified stop.',
                              maintainer_reference='fixture-maintainer-review')
        self.expected['diagnosis_sha256'] = self.put('recovery-diagnosis.json', self.diagnosis)

    def put(self, name, value):
        raw = json.dumps(value, sort_keys=True).encode()
        (self.root / name).write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def read(self, name):
        return (self.root / name).read_bytes()

    def record(self, name, value):
        with (self.root / name).open('xb') as stream:
            stream.write(json.dumps(value, sort_keys=True).encode())
            stream.flush()
            os.fsync(stream.fileno())

    def controls(self):
        self.controls_count += 1

    def sleep(self, seconds):
        self.now += seconds

    def recover(self, **overrides):
        args = dict(record=self.record, read_record=self.read, verify_controls=self.controls,
                    verify_reconciled=lambda: dict(self.snapshots), expected=self.expected,
                    backend=self.backend, timeout=2, clock=lambda: self.now, sleep=self.sleep)
        args.update(overrides)
        return m.recover_once(**args)

    def test_health_failure_recovers_once_and_retains_original_receipts(self):
        original = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.assertEqual(self.recover()['pid'], '42')
        self.assertEqual(self.backend.commands, ['start'])
        self.assertTrue((self.root / 'recovery-started.json').is_file())
        for name, raw in original.items():
            self.assertEqual(self.read(name), raw)
        with self.assertRaisesRegex(m.StartError, 'recovery_already_requested'):
            self.recover()
        self.assertEqual(self.backend.commands, ['start'])

    def test_start_failure_can_be_the_bound_failure(self):
        self.expected['failure_receipt'] = 'start-failed.json'
        self.expected['failure_sha256'] = self.put('start-failed.json', {'failed': True, 'category': 'StartError'})
        self.diagnosis.update({key: value for key, value in self.expected.items() if key != 'diagnosis_sha256'})
        self.expected['diagnosis_sha256'] = self.put('recovery-diagnosis.json', self.diagnosis)
        self.recover()
        self.assertEqual(self.backend.commands, ['start'])

    def append_missing_attempt_binding(self, attempt=None):
        installation = self.read('attempt.json')
        (self.root / 'recovery-installation-attempt.json').write_bytes(installation)
        self.expected['attempt_sha256'] = self.put('attempt.json', {} if attempt is None else attempt)
        binding = {key: self.expected[key] for key in
                   ('attempt_sha256', 'candidate_sha256', 'manifest_sha256', 'installed_manifest_sha256')}
        binding.update(installation_attempt_sha256=hashlib.sha256(installation).hexdigest(),
                       maintainer_reference='fixture-reviewed-original-installation')
        self.expected['attempt_binding_sha256'] = self.put('recovery-attempt-binding.json', binding)
        self.diagnosis.update({key: value for key, value in self.expected.items() if key != 'diagnosis_sha256'})
        self.expected['diagnosis_sha256'] = self.put('recovery-diagnosis.json', self.diagnosis)

    def test_missing_attempt_digests_use_append_only_same_root_evidence_once(self):
        self.append_missing_attempt_binding()
        original = {p.name: p.read_bytes() for p in self.root.iterdir()}
        self.assertEqual(self.recover()['pid'], '42')
        for name, raw in original.items():
            self.assertEqual(self.read(name), raw)
        with self.assertRaisesRegex(m.StartError, 'recovery_already_requested'):
            self.recover()
        self.assertEqual(self.backend.commands, ['start'])

    def test_binding_cannot_override_present_or_partial_attempt_fields(self):
        for attempt in ({'candidate_sha256': 'c' * 64}, {'candidate_sha256': 'f' * 64}, {'candidate_sha256': None},
                        {key: self.expected[key] for key in ('candidate_sha256', 'manifest_sha256', 'installed_manifest_sha256')}):
            with self.subTest(attempt=attempt):
                # Keep the source installation attempt complete for each case.
                self.put('attempt.json', {key: self.expected[key] for key in
                         ('candidate_sha256', 'manifest_sha256', 'installed_manifest_sha256')})
                self.append_missing_attempt_binding(attempt)
                with self.assertRaisesRegex(m.StartError, 'recovery_attempt_binding_invalid'):
                    self.recover()
        self.assertEqual(self.backend.commands, [])

    def test_append_only_binding_and_source_are_rechecked_after_consumption(self):
        for name in ('recovery-attempt-binding.json', 'recovery-installation-attempt.json'):
            with self.subTest(name=name):
                # Each case gets an independent protected fixture directory.
                self.setUp()
                self.append_missing_attempt_binding()
                def mutate_after_marker(receipt, value):
                    self.record(receipt, value)
                    if receipt == 'recovery-requested.json':
                        (self.root / name).write_bytes(self.read(name) + b' ')
                with self.assertRaisesRegex(m.StartError, 'recovery_receipt_changed'):
                    self.recover(record=mutate_after_marker)
                self.assertTrue((self.root / 'recovery-requested.json').exists())
                self.assertEqual(self.backend.commands, [])

    def test_missing_or_mismatched_installation_evidence_cannot_start(self):
        self.append_missing_attempt_binding()
        source = self.root / 'recovery-installation-attempt.json'
        source.unlink()
        with self.assertRaises(FileNotFoundError):
            self.recover()
        self.assertFalse((self.root / 'recovery-requested.json').exists())
        self.assertEqual(self.backend.commands, [])

    def test_reviewed_supplement_must_match_original_and_installation(self):
        self.append_missing_attempt_binding()
        original = json.loads(self.read('recovery-attempt-binding.json'))
        for changes in ({'attempt_sha256': 'f' * 64}, {'maintainer_reference': ''},
                        {'candidate_sha256': 'f' * 64}, {'installation_attempt_sha256': None}):
            with self.subTest(changes=changes):
                binding = dict(original, **changes)
                self.expected['attempt_binding_sha256'] = self.put('recovery-attempt-binding.json', binding)
                with self.assertRaises(m.StartError):
                    self.recover()
        installation = {key: self.expected[key] for key in
                        ('candidate_sha256', 'manifest_sha256', 'installed_manifest_sha256')}
        installation['candidate_sha256'] = 'f' * 64
        original['installation_attempt_sha256'] = self.put('recovery-installation-attempt.json', installation)
        self.expected['attempt_binding_sha256'] = self.put('recovery-attempt-binding.json', original)
        with self.assertRaisesRegex(m.StartError, 'recovery_candidate_changed'):
            self.recover()
        self.assertEqual(self.backend.commands, [])
        self.assertFalse((self.root / 'recovery-requested.json').exists())

    def test_incomplete_attempt_without_reviewed_supplement_still_rejects(self):
        self.expected['attempt_sha256'] = self.put('attempt.json', {})
        with self.assertRaisesRegex(m.StartError, 'recovery_candidate_changed'):
            self.recover()
        self.assertEqual(self.backend.commands, [])

    def test_outer_startup_failure_is_bound_without_rewriting_original(self):
        self.expected['failure_receipt'] = 'startup-failed.json'
        self.expected['failure_sha256'] = self.put('startup-failed.json', {
            'error_type': 'AssertionError', 'safety': 'paused', 'pause_error': None})
        self.diagnosis.update({key: value for key, value in self.expected.items() if key != 'diagnosis_sha256'})
        self.expected['diagnosis_sha256'] = self.put('recovery-diagnosis.json', self.diagnosis)
        original = self.read('startup-failed.json')
        (self.root / 'startup-failed.json').write_bytes(original + b' ')
        with self.assertRaisesRegex(m.StartError, 'recovery_receipt_changed'):
            self.recover()
        (self.root / 'startup-failed.json').write_bytes(original)
        self.assertFalse((self.root / 'recovery-requested.json').exists())
        self.assertEqual(self.recover()['pid'], '42')
        self.assertEqual(self.read('startup-failed.json'), original)
        with self.assertRaisesRegex(m.StartError, 'recovery_already_requested'):
            self.recover()
        self.assertEqual(self.backend.commands, ['start'])

    def test_outer_startup_failure_requires_its_actual_error_field(self):
        self.expected['failure_receipt'] = 'startup-failed.json'
        for failure in ({'category': 'invented'}, {'error_type': ''}, {'error_type': 1}):
            with self.subTest(failure=failure):
                self.expected['failure_sha256'] = self.put('startup-failed.json', failure)
                self.diagnosis.update({key: value for key, value in self.expected.items() if key != 'diagnosis_sha256'})
                self.expected['diagnosis_sha256'] = self.put('recovery-diagnosis.json', self.diagnosis)
                with self.assertRaisesRegex(m.StartError, 'invalid_original_failure'):
                    self.recover()
        self.assertFalse((self.root / 'recovery-requested.json').exists())
        self.assertEqual(self.backend.commands, [])

    def test_missing_changed_or_unbound_receipts_reject_before_consumption(self):
        for name in ('attempt.json', 'start-requested.json', 'failed.json', 'recovery-diagnosis.json'):
            with self.subTest(name=name):
                old = self.read(name)
                (self.root / name).write_bytes(old + b' ')
                with self.assertRaisesRegex(m.StartError, 'recovery_receipt_changed'):
                    self.recover()
                (self.root / name).unlink()
                with self.assertRaises(FileNotFoundError):
                    self.recover()
                (self.root / name).write_bytes(old)
        self.assertEqual(self.backend.commands, [])
        self.assertFalse((self.root / 'recovery-requested.json').exists())

    def test_candidate_or_unknown_cause_cannot_be_relabelled(self):
        self.diagnosis['candidate_sha256'] = 'f' * 64
        self.expected['diagnosis_sha256'] = self.put('recovery-diagnosis.json', self.diagnosis)
        with self.assertRaisesRegex(m.StartError, 'recovery_diagnosis_unbound'):
            self.recover()
        self.diagnosis['candidate_sha256'] = self.expected['candidate_sha256']
        self.diagnosis['cause'] = ''
        self.expected['diagnosis_sha256'] = self.put('recovery-diagnosis.json', self.diagnosis)
        with self.assertRaisesRegex(m.StartError, 'recovery_not_diagnosed'):
            self.recover()
        self.assertEqual(self.backend.commands, [])

    def test_actual_reconciliation_failure_blocks_pending_business_or_unknown_send(self):
        for reason in ('unfinished_work', 'unknown_delivery', 'installed_inventory_not_new:partial',
                       'installed_inventory_not_new:unknown', 'unexplained_business_change'):
            def check():
                raise ValueError(reason)
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                self.recover(verify_reconciled=check)
        with self.assertRaisesRegex(m.StartError, 'reconciliation_changed'):
            self.recover(verify_reconciled=lambda: True)
        with self.assertRaisesRegex(m.StartError, 'reconciliation_changed'):
            self.recover(verify_reconciled=lambda: dict(self.snapshots, installed_manifest_sha256='f' * 64))
        self.assertEqual(self.backend.commands, [])

    def test_active_duplicate_or_changed_unit_is_rejected(self):
        for state in (sample(), sample('inactive', receivers=['99']),
                      sample('inactive', ExecStart=exec_status(argv='replacement'))):
            self.backend.state = state
            with self.subTest(state=state), self.assertRaises(m.StartError):
                self.recover()
        self.assertEqual(self.backend.commands, [])

    def test_changed_controls_do_not_consume_or_start(self):
        def changed():
            raise ValueError('frozen_controls_changed')
        with self.assertRaisesRegex(ValueError, 'frozen_controls_changed'):
            self.recover(verify_controls=changed)
        self.assertFalse((self.root / 'recovery-requested.json').exists())
        self.assertEqual(self.backend.commands, [])

    def test_state_changes_after_marker_consume_the_allowance(self):
        checks = 0
        def check():
            nonlocal checks
            checks += 1
            return self.snapshots if checks == 1 else dict(self.snapshots, business_state_sha256='f' * 64)
        with self.assertRaisesRegex(m.StartError, 'reconciliation_changed'):
            self.recover(verify_reconciled=check)
        self.assertTrue((self.root / 'recovery-requested.json').exists())
        self.assertTrue((self.root / 'recovery-failed.json').exists())
        with self.assertRaisesRegex(m.StartError, 'recovery_already_requested'):
            self.recover()
        self.assertEqual(self.backend.commands, [])

    def test_marker_write_uncertainty_never_starts_or_grants_another_attempt(self):
        def uncertain(name, value):
            self.record(name, value)
            raise OSError('disk sync outcome unknown')
        with self.assertRaises(OSError):
            self.recover(record=uncertain)
        with self.assertRaisesRegex(m.StartError, 'recovery_already_requested'):
            self.recover()
        self.assertEqual(self.backend.commands, [])

    def test_marker_save_failure_before_persistence_never_starts(self):
        def full(name, value):
            raise OSError('disk full')
        with self.assertRaises(OSError):
            self.recover(record=full)
        self.assertEqual(self.backend.commands, [])

    def test_concurrent_recovery_has_at_most_one_start(self):
        def run():
            try:
                return self.recover()
            except (m.StartError, FileExistsError):
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(self.backend.commands, ['start'])

    def test_interruption_keeps_marker_and_stops_through_original_helper(self):
        self.backend.sequence = [sample(exe=None, receivers=[])]
        def interrupt(seconds):
            raise KeyboardInterrupt()
        with self.assertRaises(m.StartError):
            self.recover(sleep=interrupt)
        self.assertEqual(self.backend.commands, ['start', 'stop'])
        self.assertTrue((self.root / 'recovery-start-failed.json').exists())
        with self.assertRaisesRegex(m.StartError, 'recovery_already_requested'):
            self.recover()

    def test_second_start_error_is_recorded_and_cannot_retry(self):
        self.backend.start_error = TimeoutError('untrusted command output')
        with self.assertRaises(m.StartError):
            self.recover()
        self.assertEqual(self.backend.commands, ['start', 'stop'])
        with self.assertRaisesRegex(m.StartError, 'recovery_already_requested'):
            self.recover()
        self.assertEqual(self.backend.commands, ['start', 'stop'])


if __name__ == '__main__':
    unittest.main()
