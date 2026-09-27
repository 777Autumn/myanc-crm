"""Fictional native state; no production launchctl mutations."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / 'ops' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load('maintenance_start')
n = load('maintenance_launchd')


def sample(loaded=True, **changes):
    state = dict(manager='launchd', identity={'manager': 'launchd', 'label': n.LABEL,
                 'plist_sha256': 'a' * 64}, boot_session='00000000-0000-0000-0000-000000000001',
                 loaded=loaded, state='running' if loaded else 'unloaded',
                 runs=1 if loaded else 0, pid='42' if loaded else '0',
                 coalition='100' if loaded else None, exe=n.EXE if loaded else None,
                 process_start='123.000001' if loaded else None,
                 receivers=['42'] if loaded else [], receiver_details=[])
    state.update(changes)
    return state


class FakeLaunchd(n.Launchd):
    def __init__(self, sequence):
        self.sequence = list(sequence)
        self.state = sample(False)
        self.commands = []

    def sample(self):
        if self.commands and self.commands[-1] == 'start' and self.sequence:
            self.state = self.sequence.pop(0)
        return copy.deepcopy(self.state)

    def command(self, verb):
        self.commands.append(verb)
        if verb == 'stop':
            self.state = sample(False)


PRINT = '''system/com.myanc.cc-connect = {
	path = /Library/LaunchDaemons/com.myanc.cc-connect.plist
	type = LaunchDaemon
	state = running
	program = /usr/local/bin/cc-connect-anc
	arguments = {
		/usr/local/bin/cc-connect-anc
		-config
		/usr/local/etc/cc-connect/config.toml
	}
	working directory = /var/lib/cc-connect
	domain = system
	username = _ancgateway
	group = _ancgateway
	runs = 1
	pid = 42
	resource coalition = {
		ID = 100
		type = resource
		state = active
	}
}
'''


class LaunchdTests(unittest.TestCase):
    def setUp(self):
        self.receipts = {}
        self.now = 0

    def record(self, name, payload):
        if name in self.receipts:
            raise FileExistsError(name)
        self.receipts[name] = payload

    def sleep(self, seconds):
        self.now += seconds

    def start(self, backend):
        return m.start_once(self.record, lambda: None, backend=backend, timeout=1,
                            clock=lambda: self.now, sleep=self.sleep)

    def test_native_state_starts_once_without_fabricated_systemd_fields(self):
        backend = FakeLaunchd([sample(exe=None, receivers=[]), sample(), sample()])
        result = self.start(backend)
        self.assertEqual(result['invocation'], [sample()['boot_session'], '100'])
        self.assertEqual(result['native_sample']['manager'], 'launchd')
        self.assertNotIn('InvocationID', json.dumps(self.receipts))
        self.assertEqual(self.receipts['start-requested.json']['unit'], n.Launchd.unit)
        self.assertEqual(backend.commands, ['start'])
        with self.assertRaises(FileExistsError):
            self.start(FakeLaunchd([]))

    def test_restart_duplicate_pid_reuse_and_exit_fail_then_stop(self):
        for changed, reason in ((sample(runs=2), 'unexpected_restart'),
                                (sample(receivers=['42', '43']), 'duplicate_receiver'),
                                (sample(process_start='123.000002'), 'startup_pid_reused'),
                                (sample(pid='0', state='not running'), 'startup_exited')):
            with self.subTest(reason=reason):
                self.receipts.clear()
                backend = FakeLaunchd([sample(), changed])
                with self.assertRaisesRegex(m.StartError, reason):
                    self.start(backend)
                self.assertEqual(backend.commands, ['start', 'stop'])

    def test_replacement_registration_not_stopped(self):
        backend = FakeLaunchd([sample(), sample(coalition='101')])
        with self.assertRaisesRegex(m.StartError, 'startup_invocation_changed'):
            self.start(backend)
        self.assertEqual(backend.commands, ['start'])
        self.assertEqual(self.receipts['start-failed.json']['pause_error'], 'pause_invocation_changed')

    def test_boot_change_not_stopped(self):
        backend = FakeLaunchd([sample(), sample(boot_session='replacement')])
        with self.assertRaisesRegex(m.StartError, 'startup_invocation_changed'):
            self.start(backend)
        self.assertEqual(backend.commands, ['start'])

    def test_timeout_stops_verified_preexec_registration(self):
        backend = FakeLaunchd([sample(exe=None, receivers=[])])
        with self.assertRaisesRegex(m.StartError, 'startup_timeout'):
            self.start(backend)
        self.assertEqual(backend.commands, ['start', 'stop'])

    def test_absent_registration_with_orphan_blocks(self):
        backend = FakeLaunchd([])
        backend.state = sample(False, receivers=['43'])
        with self.assertRaisesRegex(m.StartError, 'service_not_stopped'):
            self.start(backend)
        self.assertEqual(backend.commands, [])

    def test_receipt_failure_never_starts(self):
        backend = FakeLaunchd([])
        with self.assertRaises(OSError):
            m.start_once(lambda *_: (_ for _ in ()).throw(OSError('full')), lambda: None,
                         backend=backend)
        self.assertEqual(backend.commands, [])

    def test_native_print_parser_ignores_nested_fields_rejects_ambiguity(self):
        parsed = n.parse_print(PRINT)
        self.assertEqual((parsed['state'], parsed['type'], parsed['coalition']),
                         ('running', 'LaunchDaemon', '100'))
        for bad in (PRINT.replace('\tstate = running', '\tstate = running\n\tstate = waiting'),
                    PRINT.replace('system/com.myanc.cc-connect', 'user/501/other'),
                    PRINT.replace('\targuments = {', '\tunknown = {')):
            with self.assertRaises(RuntimeError):
                n.parse_print(bad)

    def test_commands_are_fixed_bootstrap_and_bootout_never_kickstart(self):
        with patch.object(n, 'frozen_plist'), patch.object(n.subprocess, 'run') as run:
            backend = n.Launchd()
            backend.command('start')
            self.assertEqual(run.call_args.args[0], ['/bin/launchctl', 'bootstrap', 'system', str(n.PLIST)])
            backend.command('stop')
            self.assertEqual(run.call_args.args[0], ['/bin/launchctl', 'bootout', backend.unit])
            with self.assertRaises(RuntimeError):
                backend.command('restart')
            self.assertEqual(run.call_count, 2)

    def test_query_permission_errors_are_not_stopped_state(self):
        with patch.object(n, 'frozen_plist', return_value=sample()['identity']), \
                patch.object(n.subprocess, 'check_output', return_value=sample()['boot_session']), \
                patch.object(n.subprocess, 'run', return_value=subprocess.CompletedProcess(
                    [], 113, '', 'permission denied')):
            with self.assertRaisesRegex(RuntimeError, 'launchd_query_failed'):
                n.Launchd().sample()

    def test_sampler_reads_loaded_state_and_refuses_different_arguments(self):
        output = subprocess.CompletedProcess([], 0, PRINT, '')
        detail = dict(exe='/usr/libexec/xpcproxy', process_start='123.000001')
        with patch.object(n, 'frozen_plist', return_value=sample()['identity']), \
                patch.object(n.subprocess, 'check_output', side_effect=[sample()['boot_session'], '42 /usr/libexec/xpcproxy\n']), \
                patch.object(n.subprocess, 'run', return_value=output), \
                patch.object(n, 'process', return_value=detail):
            result = n.Launchd().sample()
            self.assertEqual(result['coalition'], '100')
            self.assertEqual(result['process_start'], '123.000001')
            self.assertFalse(n.Launchd.view(result)['stopped'])
        output.stdout = PRINT.replace('\t\t-config\n', '\t\t-other\n')
        with patch.object(n, 'frozen_plist', return_value=sample()['identity']), \
                patch.object(n.subprocess, 'check_output', return_value=sample()['boot_session']), \
                patch.object(n.subprocess, 'run', return_value=output):
            with self.assertRaisesRegex(RuntimeError, 'arguments_mismatch'):
                n.Launchd().sample()

    def test_native_recovery_uses_original_receipts_once(self):
        snapshots = dict(controls_sha256='a'*64, business_state_sha256='b'*64,
                         installed_manifest_sha256='c'*64)
        records = {}
        def put(name, value):
            raw = json.dumps(value, sort_keys=True).encode()
            records[name] = raw
            return hashlib.sha256(raw).hexdigest()
        attempt = dict(candidate_sha256='d'*64, manifest_sha256='e'*64,
                       installed_manifest_sha256='c'*64)
        expected = dict(attempt, attempt_sha256=put('attempt.json', attempt),
            start_request_sha256=put('start-requested.json', dict(unit=n.Launchd.unit,
                identity_sha256=hashlib.sha256(json.dumps(sample()['identity'], sort_keys=True).encode()).hexdigest())),
            failure_sha256=put('failed.json', dict(category='fixture_health_failure')),
            failure_receipt='failed.json')
        diagnosis = dict(expected, **snapshots, cause='fictional known failure',
                         maintainer_reference='fixture-review')
        expected['diagnosis_sha256'] = put('recovery-diagnosis.json', diagnosis)
        original = dict(records)
        def record(name, value):
            if name in records:
                raise FileExistsError(name)
            put(name, value)
        backend = FakeLaunchd([sample(), sample()])
        def recover():
            return m.recover_once(record, lambda name: records[name] if name in records else
                (_ for _ in ()).throw(FileNotFoundError(name)), lambda: None, lambda: snapshots,
                expected=expected, backend=backend, clock=lambda: self.now, sleep=self.sleep)
        self.assertEqual(recover()['native_sample']['manager'], 'launchd')
        self.assertTrue(all(records[key] == value for key, value in original.items()))
        with self.assertRaisesRegex(m.StartError, 'recovery_already_requested'):
            recover()
        self.assertEqual(backend.commands, ['start'])

    def test_template_rejects_automatic_restart_or_changed_account(self):
        template = Path(__file__).parents[1] / 'ops/runtime/com.myanc.cc-connect.plist'
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'service.plist'
            target.write_bytes(template.read_bytes())
            observed = type('Stat', (), dict(st_mode=0o100644, st_uid=0, st_ino=1,
                            st_mtime_ns=1, st_size=target.stat().st_size))()
            with patch.object(n, 'PLIST', target), patch.object(Path, 'lstat', return_value=observed):
                n.frozen_plist()
                for key, value in [('KeepAlive', True), ('UserName', 'root'), ('GroupName', 'staff')]:
                    data = plistlib.loads(template.read_bytes())
                    data[key] = value
                    target.write_bytes(plistlib.dumps(data))
                    with self.assertRaisesRegex(RuntimeError, 'unexpected_launchd_plist'):
                        n.frozen_plist()

    @unittest.skipUnless(sys.platform == 'darwin', 'requires actual libproc')
    def test_actual_native_process_start_identity(self):
        detail = n.process(os.getpid())
        self.assertEqual(detail['pid'], str(os.getpid()))
        self.assertEqual(detail['uid'], os.geteuid())
        self.assertRegex(detail['process_start'], r'^\d+\.\d{6}$')
        self.assertEqual(n.process(os.getpid()), detail)
        self.assertTrue(Path(detail['exe']).is_file())

    @unittest.skipUnless(sys.platform == 'darwin' and os.environ.get('ANC_LAUNCHD_FIXTURE') == '1',
                         'isolated macOS CI fixture only')
    def test_real_launchdaemon_runs_ordinary_child_and_stops(self):
        import grp
        import pwd
        self.assertEqual(os.geteuid(), 0)  # setup/control only; the daemon must not be root
        account = pwd.getpwnam(os.environ['SUDO_USER'])
        self.assertNotEqual(account.pw_uid, 0)
        label = 'com.myanc.maintenance-fixture-' + uuid.uuid4().hex
        plist = Path('/Library/LaunchDaemons') / (label + '.plist')
        with tempfile.TemporaryDirectory(prefix='anc-launchd-') as tmp:
            root = Path(tmp).resolve()
            root.chmod(0o755)
            source = root / 'fixture.c'
            source.write_text('#include <unistd.h>\nint main(void) { for (;;) pause(); }\n')
            exe = root / 'cc-connect-anc'
            subprocess.run(['/usr/bin/clang', str(source), '-o', str(exe)], check=True, timeout=30)
            exe.chmod(0o755)
            config = root / 'fictional.toml'
            config.write_text('# no bot, network or credentials\n')
            values = dict(LABEL=label, PLIST=plist, EXE=str(exe), USER=account.pw_name,
                          GROUP=grp.getgrgid(account.pw_gid).gr_name, CWD=str(root),
                          CONFIG=str(config), STDOUT=str(root / 'stdout'), STDERR=str(root / 'stderr'))
            data = dict(Label=label, ProgramArguments=[str(exe), '-config', str(config)],
                UserName=values['USER'], GroupName=values['GROUP'], WorkingDirectory=str(root),
                RunAtLoad=True, KeepAlive=False, AbandonProcessGroup=False, ProcessType='Background',
                ExitTimeOut=30, Umask=0o077, StandardOutPath=values['STDOUT'], StandardErrorPath=values['STDERR'],
                EnvironmentVariables={'HOME': str(root), 'PATH': '/usr/bin:/bin:/usr/sbin:/sbin'})
            with plist.open('xb') as stream:
                stream.write(plistlib.dumps(data))
            plist.chmod(0o644)
            with patch.multiple(n, **values), patch.object(n.Launchd, 'unit', 'system/' + label), \
                    patch.object(n.Launchd, 'exe', str(exe)):
                backend = n.Launchd()
                try:
                    initial = backend.sample()
                    self.assertTrue(backend.view(initial)['stopped'])
                    result = m.start_once(self.record, n.frozen_plist, backend=backend)
                    self.assertEqual(n.process(int(result['pid']))['uid'], account.pw_uid)
                    self.assertEqual(result['native_sample']['runs'], 1)
                    self.assertEqual(m.pause_verified(backend, initial['identity'],
                        result['invocation'], n.frozen_plist), 'paused')
                    stopped = backend.sample()
                    self.assertFalse(stopped['loaded'])
                    self.assertEqual(stopped['receivers'], [])
                finally:
                    # Only this random, isolated CI label. Never retry a start.
                    subprocess.run(['/bin/launchctl', 'bootout', backend.unit],
                                   capture_output=True, timeout=55)
                    plist.unlink()


if __name__ == '__main__':
    unittest.main()
