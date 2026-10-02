"""Mac worker seams; fictional paths, no Office install or real messages."""
from contextlib import contextmanager, ExitStack, redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

import team_file_pdf
import team_file_render as render


class MacOfficeTests(unittest.TestCase):
    def test_run_records_first_failure_and_known_exit_without_retry(self):
        profile = Path(tempfile.gettempdir()) / 'fictional-office-profile'
        private = 'fictional document /private/path FAKE_AUTH=not-a-real-secret'
        for stage, code, cleanup in (('spawn', None, False), ('wait', None, False),
                                     ('accounting', None, False), ('exit', 1, False),
                                     ('exit', -15, True), ('cleanup', 0, True)):
            with self.subTest(stage=stage, code=code, cleanup=cleanup):
                original = OSError(private) if stage == 'spawn' else subprocess.TimeoutExpired([private], 1)
                proc = MagicMock(pid=42, returncode=code)
                proc.communicate.return_value = (private.encode(), b'')
                proc.poll.return_value = code
                if stage in ('wait', 'accounting'):
                    proc.communicate.side_effect = original
                accounting = RuntimeError('document process accounting unavailable')
                closing = OSError(private)
                if cleanup:
                    proc.stdout.close.side_effect = closing

                def waited(**_kwargs):
                    proc.returncode = -9  # Cleanup must not invent the earlier exit status.

                proc.wait.side_effect = waited
                with patch.object(sys, 'platform', 'darwin' if stage == 'accounting' else 'linux'), \
                        patch.object(render.subprocess, 'Popen', side_effect=original if stage == 'spawn' else None,
                                     return_value=proc) as spawn, \
                        patch.object(render, 'mac_group_memory', side_effect=accounting), \
                        patch.object(render.signal, 'SIGKILL', 9, create=True), \
                        patch.object(render.os, 'killpg', create=True), \
                        patch.object(render, 'write_office_failure') as diagnostic:
                    with self.assertRaises((OSError, RuntimeError, subprocess.TimeoutExpired)) as stopped:
                        render.run([private], diagnostic_profile=profile, stage='office_worker')
                    if stage in ('spawn', 'wait'):
                        self.assertIs(stopped.exception, original)
                    elif stage == 'accounting':
                        self.assertIs(stopped.exception, accounting)
                    elif stage == 'cleanup':
                        self.assertIs(stopped.exception, closing)
                    diagnostic.assert_called_once()
                    self.assertEqual(diagnostic.call_args.args[:3], (profile, 'parent', 'office_worker_' + stage))
                    self.assertIs(diagnostic.call_args.args[3], stopped.exception)
                    self.assertEqual(diagnostic.call_args.kwargs.get('returncode'), code)
                    if cleanup and stage != 'cleanup':
                        self.assertIs(diagnostic.call_args.kwargs.get('cleanup_error'), closing)
                    spawn.assert_called_once()
                    self.assertEqual(proc.communicate.call_count, int(stage != 'spawn'))
                    self.assertEqual(proc.wait.call_count, int(stage != 'spawn'))

    @contextmanager
    def mac_run_fixture(self, replies, *, memory=(), pids=()):
        proc = MagicMock(pid=42, returncode=None)
        results = iter(replies)

        def communicate(data, timeout):
            result = next(results)
            if isinstance(result, BaseException):
                raise result
            proc.returncode = result
            return b'validated protocol output', None

        proc.communicate.side_effect = communicate
        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, 'platform', 'darwin'))
            spawn = stack.enter_context(patch.object(render.subprocess, 'Popen', return_value=proc))
            sample = stack.enter_context(patch.object(render, 'mac_group_memory', return_value=list(memory)))
            members = stack.enter_context(patch.object(render, 'mac_group_pids', return_value=list(pids)))
            kill = stack.enter_context(patch.object(render.os, 'killpg', create=True))
            stack.enter_context(patch.object(render.signal, 'SIGKILL', 9, create=True))
            diagnostic = stack.enter_context(patch.object(render, 'write_office_failure'))
            yield proc, sample, members, kill, diagnostic
            spawn.assert_called_once()
            proc.stdout.close.assert_called_once()
            proc.stdin.close.assert_called_once()

    def test_exit_window_finishes_once_without_resending_input_or_signalling_empty_group(self):
        timeout = subprocess.TimeoutExpired(['fixture'], .1)
        with self.mac_run_fixture([timeout, 0]) as (proc, sample, members, kill, diagnostic):
            self.assertEqual(render.run(['fixture'], data=b'one input'), b'validated protocol output')
            self.assertEqual([c.args[0] for c in proc.communicate.call_args_list], [b'one input', None])
            self.assertTrue(all(0 < c.kwargs['timeout'] <= .1 for c in proc.communicate.call_args_list))
            sample.assert_called_once_with(42)
            self.assertEqual(members.call_count, 2, 'terminal check and cleanup each require a fresh raw list')
            kill.assert_not_called(); diagnostic.assert_not_called()
            proc.wait.assert_called_once_with(timeout=5)

    def test_empty_sample_never_accepts_live_child_nonempty_group_or_unknown_enumeration(self):
        timeout = subprocess.TimeoutExpired(['fixture'], .1)
        for finish, pids in ((timeout, []), (0, [42]), (0, [43])):
            with self.subTest(finish=type(finish).__name__, pids=pids), \
                    self.mac_run_fixture([timeout, finish], pids=pids) as (proc, sample, members, kill, diagnostic):
                with self.assertRaises(RuntimeError) as stopped:
                    render.run(['fixture'])
                self.assertEqual(stopped.exception.accounting['operation'], 'empty_group')
                self.assertEqual(proc.communicate.call_count, 2)
                kill.assert_called_once(); proc.wait.assert_called_once_with(timeout=5)
                self.assertIs(diagnostic.call_args.args[3], stopped.exception)
        unknown = render.accounting_failure('listpids', 42, 0, 512, render.errno.EPERM)
        with self.mac_run_fixture([timeout, 0]) as (proc, sample, members, kill, diagnostic):
            members.side_effect = unknown
            with self.assertRaises(RuntimeError) as stopped:
                render.run(['fixture'])
            self.assertIs(stopped.exception, unknown)
            kill.assert_called_once()
            diagnostic.assert_called_once()

    def test_terminal_wait_does_not_extend_deadline_and_nonzero_exit_still_fails(self):
        timeout = subprocess.TimeoutExpired(['fixture'], .1)
        for now, code in ((.97, 1), (1.01, 0)):
            with self.subTest(now=now), self.mac_run_fixture([timeout, code]) as (proc, sample, members, kill, diagnostic), \
                    patch.object(render.time, 'monotonic', side_effect=[0, .9, now]):
                with self.assertRaises(RuntimeError) as stopped:
                    render.run(['fixture'], timeout=1)
                if now < 1:
                    self.assertAlmostEqual(proc.communicate.call_args.kwargs['timeout'], .03)
                    self.assertIn('document tool failed', str(stopped.exception))
                    self.assertEqual(diagnostic.call_args.kwargs['returncode'], 1)
                else:
                    self.assertEqual(proc.communicate.call_count, 1)
                    self.assertEqual(stopped.exception.accounting['operation'], 'empty_group')

    def test_resident_budget_still_sums_members_and_does_not_enter_terminal_grace(self):
        timeout = subprocess.TimeoutExpired(['fixture'], .1)
        with self.mac_run_fixture([timeout], memory=[6, 7], pids=[42, 43]) as (proc, sample, members, kill, diagnostic):
            with self.assertRaisesRegex(RuntimeError, 'memory budget'):
                render.run(['fixture'], memory_limit=12)
            self.assertEqual(proc.communicate.call_count, 1)
            kill.assert_called_once()

    def test_cleanup_permission_and_timeout_remain_visible_and_close_both_pipes(self):
        for original in (None, ValueError('first failure')):
            for wait_error in (None, subprocess.TimeoutExpired(['fixture'], 5)):
                with self.subTest(original=original, wait_error=wait_error), \
                        self.mac_run_fixture([original or 0], pids=[43]) as (proc, sample, members, kill, diagnostic):
                    denied = PermissionError(render.errno.EPERM, 'synthetic cleanup denial')
                    kill.side_effect = denied
                    proc.wait.side_effect = wait_error
                    with self.assertRaises((PermissionError, ValueError)) as stopped:
                        render.run(['fixture'])
                    self.assertIs(stopped.exception, original or denied)
                    self.assertIs(diagnostic.call_args.kwargs['cleanup_error'], denied)
                    self.assertEqual(diagnostic.call_args.kwargs['returncode'], None if original else 0)
                    proc.wait.assert_called_once_with(timeout=5)
        timeout = subprocess.TimeoutExpired(['fixture'], 5)
        with self.mac_run_fixture([0]) as (proc, sample, members, kill, diagnostic):
            proc.wait.side_effect = timeout
            proc.stdout.close.side_effect = OSError('later close error')
            with self.assertRaises(subprocess.TimeoutExpired) as stopped:
                render.run(['fixture'])
            self.assertIs(stopped.exception, timeout)
            self.assertIs(diagnostic.call_args.kwargs['cleanup_error'], timeout)

    def test_raw_members_survive_all_esrch_memory_sample(self):
        lib = MagicMock()
        def list_pids(kind, group, pids, size):
            pids[0] = 42
            return 4
        def pid_info(*_args):
            render.ctypes.set_errno(render.errno.ESRCH)
            return 0
        lib.proc_listpids.side_effect = list_pids
        lib.proc_pidinfo.side_effect = pid_info
        with patch.object(render.ctypes, 'CDLL', return_value=lib):
            self.assertEqual(render.mac_group_memory(42), [])
            self.assertEqual(render.mac_group_pids(42), [42])

    def test_office_update_records_stage_and_dispose_without_hiding_original(self):
        private = 'fictional document /private/path FAKE_AUTH=not-a-real-secret'
        modules = {'uno': MagicMock(), 'com.sun.star.beans': SimpleNamespace(PropertyValue=SimpleNamespace),
                   'com.sun.star.document.MacroExecMode': SimpleNamespace(NEVER_EXECUTE=4),
                   'com.sun.star.document.UpdateDocMode': SimpleNamespace(NO_UPDATE=0)}
        source = Path(tempfile.gettempdir()).resolve() / 'fictional.xlsx'
        for stage, method in (('load', 'loadComponentFromURL'), ('update', 'calculateAll'),
                              ('save', 'storeAsURL'), ('pdf', 'storeToURL'), ('close', 'close'),
                              (None, None)):
            for dispose_fails in (False, True) if stage else (False,):
                with self.subTest(stage=stage, dispose_fails=dispose_fails):
                    desktop, doc = MagicMock(), MagicMock()
                    modules['uno'].getComponentContext.return_value.ServiceManager.createInstanceWithContext.return_value = desktop
                    desktop.loadComponentFromURL.return_value = doc
                    original, cleanup = ValueError(private), OSError(private)
                    if stage:
                        getattr(desktop if stage == 'load' else doc, method).side_effect = original
                    if dispose_fails:
                        doc.dispose.side_effect = cleanup
                    with patch.dict(sys.modules, modules), patch.object(render, 'write_office_failure') as diagnostic:
                        if stage:
                            with self.assertRaises(ValueError) as stopped:
                                render.office_update(source, source.parent, 'fictional', diagnostic_profile=source.parent)
                            self.assertIs(stopped.exception, original)
                            diagnostic.assert_called_once()
                            self.assertEqual(diagnostic.call_args.args, (source.parent, 'worker', stage, original))
                            self.assertIs(diagnostic.call_args.kwargs.get('cleanup_error'),
                                          cleanup if dispose_fails and stage != 'load' else None)
                        else:
                            render.office_update(source, source.parent, 'fictional', diagnostic_profile=source.parent)
                            diagnostic.assert_not_called()
                    desktop.loadComponentFromURL.assert_called_once()
                    self.assertEqual(doc.dispose.call_count, int(stage is not None and stage != 'load'))
                    for name in ('calculateAll', 'storeAsURL', 'storeToURL', 'close'):
                        self.assertLessEqual(getattr(doc, name).call_count, 1)

    def test_diagnostic_io_failure_cannot_replace_office_error_or_expose_details(self):
        private = 'fictional document /private/path FAKE_AUTH=not-a-real-secret'
        modules = {'uno': MagicMock(), 'com.sun.star.beans': SimpleNamespace(PropertyValue=SimpleNamespace),
                   'com.sun.star.document.MacroExecMode': SimpleNamespace(NEVER_EXECUTE=4),
                   'com.sun.star.document.UpdateDocMode': SimpleNamespace(NO_UPDATE=0)}
        source = Path(tempfile.gettempdir()).resolve() / 'fictional.xlsx'
        for failure_point in ('open', 'fsync'):
            with self.subTest(failure_point=failure_point):
                doc, stream = MagicMock(), MagicMock()
                modules['uno'].getComponentContext.return_value.ServiceManager.createInstanceWithContext.return_value.loadComponentFromURL.return_value = doc
                original = ValueError(private)
                doc.storeAsURL.side_effect = original
                stream.fileno.return_value = 124
                with patch.dict(sys.modules, modules), \
                        patch.object(render.os, 'geteuid', return_value=451, create=True), \
                        patch.object(render.os, 'O_DIRECTORY', 0, create=True), \
                        patch.object(render.os, 'O_NOFOLLOW', 0, create=True), \
                        patch.object(render.os, 'open', side_effect=[123, OSError(private) if failure_point == 'open' else 124]) as opened, \
                        patch.object(render.os, 'fstat', return_value=SimpleNamespace(st_mode=render.stat.S_IFDIR | 0o700, st_uid=451)), \
                        patch.object(render.os, 'fdopen') as fdopen, \
                        patch.object(render.os, 'fsync', side_effect=OSError(private)) as synced, \
                        patch.object(render.os, 'close'), \
                        redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()) as stderr:
                    fdopen.return_value.__enter__.return_value = stream
                    with self.assertRaises(ValueError) as stopped:
                        render.office_update(source, source.parent, 'fictional', diagnostic_profile=source.parent)
                    self.assertIs(stopped.exception, original)
                    self.assertEqual(opened.call_count, 2)
                    self.assertEqual(synced.call_count, int(failure_point == 'fsync'))
                    self.assertEqual(stdout.getvalue() + stderr.getvalue(), '')
                    raw = ''.join(call.args[0] for call in stream.write.call_args_list)
                    self.assertNotIn(private, raw)
                    if raw:
                        self.assertEqual(json.loads(raw)['error_type'], 'ValueError')
                doc.storeAsURL.assert_called_once()
                doc.dispose.assert_called_once()
                doc.storeToURL.assert_not_called()

    @unittest.skipUnless(os.name == 'posix' and os.geteuid() != 0, 'requires ordinary POSIX owner/mode/dir_fd')
    def test_failure_records_are_private_exclusive_sanitized_and_best_effort(self):
        private = 'fictional document /private/path FAKE_AUTH=not-a-real-secret'
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            profile.chmod(0o700)
            error = type('com.sun.star.io.IOException', (Exception,), {})(private)
            render.write_office_failure(profile, 'worker', 'save', error, cleanup_error=OSError(private))
            path = profile / 'office-worker-failure.json'
            raw = path.read_bytes()
            self.assertEqual(json.loads(raw), {'stage': 'save', 'error_type': 'IOException',
                                              'returncode': None, 'cleanup_error_type': 'OSError'})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(path.stat().st_uid, os.geteuid())
            render.write_office_failure(profile, 'worker', 'job', RuntimeError(private))
            self.assertEqual(path.read_bytes(), raw, 'fallback must preserve the first failure')
            render.write_office_failure(profile, 'parent', 'office_worker_exit', RuntimeError(private), returncode=-15)
            self.assertEqual(json.loads((profile / 'office-parent-failure.json').read_bytes())['returncode'], -15)
            self.assertNotIn(private.encode(), raw)
            for failure_point in ('open', 'fsync'):
                with self.subTest(failure_point=failure_point), tempfile.TemporaryDirectory() as fresh:
                    with patch.object(render.os, failure_point, side_effect=OSError(private)):
                        render.write_office_failure(Path(fresh), 'worker', 'save', error)
            with tempfile.TemporaryDirectory() as fresh:
                invalid = Path(fresh)
                render.write_office_failure(invalid, 'worker', private, type(private, (Exception,), {})(private))
                for item in invalid.iterdir():
                    self.assertNotIn(private, item.read_text())
            with tempfile.TemporaryDirectory() as fresh:
                unsafe = Path(fresh)
                unsafe.chmod(0o755)
                render.write_office_failure(unsafe, 'worker', 'save', error)
                self.assertEqual(list(unsafe.iterdir()), [])
                unsafe.chmod(0o700)
                with patch.object(render.os, 'geteuid', return_value=0):
                    render.write_office_failure(unsafe, 'worker', 'save', error)
                self.assertEqual(list(unsafe.iterdir()), [])
                with patch.object(render.os, 'geteuid', return_value=os.geteuid() + 1):
                    render.write_office_failure(unsafe, 'worker', 'save', error)
                self.assertEqual(list(unsafe.iterdir()), [])
                link = unsafe / 'symlink'
                linked = unsafe / 'real-profile'
                linked.mkdir(mode=0o700)
                link.symlink_to(linked, target_is_directory=True)
                render.write_office_failure(link, 'worker', 'save', error)
                self.assertEqual(list(linked.iterdir()), [])
            render.write_office_failure(None, 'worker', 'save', error)

    def test_mac_job_uses_profile_and_preserves_worker_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            profile = Path(directory)
            script = profile / 'user/Scripts/python/anc_render.py'
            script.parent.mkdir(parents=True)
            job = ['fictional source', 'fictional target', 'fictional stem']
            script.with_name('job.json').write_text(json.dumps(job), encoding='utf-8')
            uno = SimpleNamespace(fileUrlToSystemPath=lambda value: str(script))
            original = ValueError('fictional document /private/path FAKE_AUTH=not-a-real-secret')
            for fails in (False, True):
                with self.subTest(fails=fails), patch.dict(sys.modules, {'uno': uno}), \
                        patch.object(render, 'office_update', side_effect=original if fails else None) as update, \
                        patch.object(render, 'write_office_failure') as diagnostic:
                    if fails:
                        with self.assertRaises(ValueError) as stopped:
                            render.mac_office_job()
                        self.assertIs(stopped.exception, original)
                        diagnostic.assert_called_once_with(profile, 'worker', 'job', original)
                    else:
                        render.mac_office_job()
                        diagnostic.assert_not_called()
                    update.assert_called_once_with(*job, diagnostic_profile=profile)
            script.with_name('job.json').write_text('{fictional malformed', encoding='utf-8')
            with patch.dict(sys.modules, {'uno': uno}), patch.object(render, 'office_update') as update, \
                    patch.object(render, 'write_office_failure') as diagnostic:
                with self.assertRaises(json.JSONDecodeError):
                    render.mac_office_job()
                update.assert_not_called()
                self.assertEqual(diagnostic.call_args.args[:3], (profile, 'worker', 'job'))

    def test_only_flock_eagain_marks_office_profile_busy(self):
        for code in (render.errno.EAGAIN, render.errno.EBADF):
            lock = MagicMock()
            lock.flock.side_effect = BlockingIOError(code, 'synthetic native error')
            with self.subTest(code=code), patch.dict(sys.modules, {'fcntl': lock}), \
                    patch.object(render, 'os') as identity:
                identity.geteuid.return_value = 501
                identity.fstat.return_value = MagicMock(st_mode=render.stat.S_IFREG | 0o600,
                                                       st_uid=501, st_nlink=1)
                with self.assertRaises(BlockingIOError) as stopped:
                    with render.mac_office_profile(Path(tempfile.gettempdir()).resolve()):
                        self.fail('busy or failed lock accepted')
                self.assertEqual(stopped.exception.errno, code)
                self.assertEqual(stopped.exception.strerror,
                                 'Office profile lock busy' if code == render.errno.EAGAIN else 'synthetic native error')
                identity.close.assert_called_once()

    def test_socket_matches_gateway_unicode_uri_vector(self):
        profile = PurePosixPath('/private/var/fictional work/婚宴 %/outputs/.office-profile')
        self.assertEqual(render.mac_office_socket(profile, 501).name,
                         'OSL_PIPE_501_SingleOfficeIPC_786cfa4b1e5213eb148ce155790654d')
        self.assertNotEqual(render.mac_office_socket(profile, 501), render.mac_office_socket(profile, 502))

    @unittest.skipUnless(sys.platform == 'darwin', 'requires native flock/ordinary UID')
    def test_profile_serializes_and_preserves_stale_or_failed_state(self):
        with tempfile.TemporaryDirectory() as directory:
            outputs = Path(directory).resolve()
            profile = outputs / '.office-profile'
            with render.mac_office_profile(outputs):
                (profile / 'fictional').write_text('private scratch')
                with self.assertRaises(BlockingIOError) as busy:
                    with render.mac_office_profile(outputs):
                        self.fail('parallel profile accepted')
                self.assertIn(busy.exception.errno, (render.errno.EAGAIN, render.errno.EWOULDBLOCK))
                self.assertEqual(busy.exception.strerror, 'Office profile lock busy')
            self.assertFalse(profile.exists())
            inode = (outputs / '.office-profile.lock').stat().st_ino
            with self.assertRaisesRegex(ValueError, 'synthetic failure'):
                with render.mac_office_profile(outputs):
                    raise ValueError('synthetic failure')
            self.assertTrue(profile.is_dir())
            diagnostic = profile / 'office-parent-failure.json'
            recorded = diagnostic.read_bytes()
            with self.assertRaisesRegex(RuntimeError, 'stale Office'):
                with render.mac_office_profile(outputs):
                    self.fail('failed profile reused')
            self.assertEqual(diagnostic.read_bytes(), recorded, 'stale rejection must not rewrite old evidence')
            diagnostic.unlink()  # Remove only this test's own synthetic failure record.
            profile.rmdir()  # Controlled fixture reconciliation, never production retry.
            profile.symlink_to(outputs, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, 'stale Office'):
                with render.mac_office_profile(outputs):
                    self.fail('symlink profile accepted')
            profile.unlink()
            socket = render.mac_office_socket(profile, os.geteuid())
            with patch.object(render, 'mac_path_present', side_effect=lambda p: p == socket):
                with self.assertRaisesRegex(RuntimeError, 'stale Office'):
                    with render.mac_office_profile(outputs):
                        self.fail('stale socket accepted')
            self.assertEqual((outputs / '.office-profile.lock').stat().st_ino, inode)
            (outputs / '.office-profile.lock').unlink()
            (outputs / '.office-profile.lock').symlink_to(outputs / 'missing')
            with self.assertRaises(OSError):
                with render.mac_office_profile(outputs):
                    self.fail('symlink lock accepted')

    def test_metadata_uncertainty_is_not_absence(self):
        for error in (PermissionError, OSError):
            with patch.object(Path, 'lstat', side_effect=error('synthetic metadata failure')):
                with self.assertRaises(error):
                    render.mac_path_present(Path('/fictional'))
        with patch.object(Path, 'lstat', side_effect=FileNotFoundError):
            self.assertFalse(render.mac_path_present(Path('/fictional')))

    @unittest.skipUnless(sys.platform == 'darwin', 'requires native profile lifecycle')
    def test_socket_metadata_failure_preserves_profile_and_stops(self):
        for code in (render.errno.EACCES, render.errno.EIO):
            for at_exit in (False, True):
                with self.subTest(code=code, at_exit=at_exit), tempfile.TemporaryDirectory() as directory:
                    outputs = Path(directory).resolve()
                    error = OSError(code, 'synthetic metadata failure')
                    checks = [False, False, error] if at_exit else [False, error]
                    with patch.object(render, 'mac_path_present', side_effect=checks):
                        with self.assertRaises(OSError):
                            with render.mac_office_profile(outputs):
                                self.assertTrue(at_exit)
                    self.assertEqual((outputs / '.office-profile').exists(), at_exit)

    def test_native_accounting_is_group_scoped_and_rejects_uncertainty(self):
        for returned, list_error, info_size, error, expected in ((8, 0, 96, 0, [1234, 1234]),
                                                               (4, 0, 0, render.errno.ESRCH, []),
                                                               (4, 0, 0, render.errno.EPERM, None),
                                                               (-1, 0, 96, 0, None), (512, 0, 96, 0, None),
                                                               (3, 0, 96, 0, None),
                                                               (0, render.errno.EPERM, 96, 0, None),
                                                               (0, 0, 96, 0, [])):
            with self.subTest(returned=returned, list_error=list_error, info_size=info_size, error=error):
                lib = MagicMock()

                def list_pids(kind, group, pids, size):
                    self.assertEqual((kind, group, size), (2, 42, 512))
                    pids[0], pids[1] = 42, 43
                    render.ctypes.set_errno(list_error)
                    return returned

                def pid_info(pid, flavor, arg, info, size):
                    self.assertIn(pid, (42, 43))
                    self.assertEqual((flavor, arg, size), (4, 0, 96))
                    info[1] = 1234
                    render.ctypes.set_errno(error)
                    return info_size

                lib.proc_listpids.side_effect = list_pids
                lib.proc_pidinfo.side_effect = pid_info
                with patch.object(render.ctypes, 'CDLL', return_value=lib):
                    if expected is None:
                        with self.assertRaisesRegex(RuntimeError, 'accounting unavailable') as stopped:
                            render.mac_group_memory(42)
                        if returned == 4:
                            self.assertEqual(stopped.exception.accounting,
                                             dict(operation='pidinfo', pid=42, returned=info_size, expected=96, errno=error))
                        else:
                            self.assertEqual(stopped.exception.accounting,
                                             dict(operation='listpids', pid=42, returned=returned, expected=512, errno=list_error))
                    else:
                        self.assertEqual(render.mac_group_memory(42), expected)

    def test_accounting_failure_records_bounded_fields_without_private_details(self):
        private = 'fictional document /private/path FAKE_AUTH=not-a-real-secret'
        valid = dict(operation='pidinfo', pid=42, returned=0, expected=96, errno=render.errno.EPERM)
        for details, included in ((valid, True), ({**valid, 'pid': True}, False),
                                  ({**valid, 'operation': private}, False),
                                  ({**valid, 'errno': 1 << 32}, False),
                                  ({**valid, 'private_path': private}, False)):
            with self.subTest(details=details):
                failure = RuntimeError('document process accounting unavailable')
                failure.accounting = details
                stream = io.StringIO()
                with patch.object(render.os, 'geteuid', return_value=451, create=True), \
                        patch.object(render.os, 'O_DIRECTORY', 0, create=True), \
                        patch.object(render.os, 'O_NOFOLLOW', 0, create=True), \
                        patch.object(render.os, 'open', side_effect=[123, 124]), \
                        patch.object(render.os, 'fstat', return_value=SimpleNamespace(st_mode=render.stat.S_IFDIR | 0o700, st_uid=451)), \
                        patch.object(render.os, 'fdopen') as fdopen, \
                        patch.object(render.os, 'fsync'), patch.object(render.os, 'close'):
                    destination = MagicMock()
                    destination.write.side_effect = stream.write
                    destination.fileno.return_value = 124
                    fdopen.return_value.__enter__.return_value = destination
                    render.write_office_failure(Path('fictional-profile'), 'parent', 'office_worker_accounting', failure,
                                                cleanup_error=PermissionError(render.errno.EPERM, private))
                raw = stream.getvalue(); value = json.loads(raw)
                self.assertNotIn(private, raw)
                self.assertEqual(value['cleanup_error_type'], 'PermissionError')
                self.assertEqual(value['cleanup_errno'], render.errno.EPERM)
                self.assertEqual('accounting' in value, included)
                if included:
                    self.assertEqual(value['accounting'], valid)

    @unittest.skipUnless(sys.platform == 'darwin', 'requires native macOS process accounting')
    def test_actual_mac_memory_and_timeout_cleanup(self):
        self.assertNotEqual(os.geteuid(), 0)
        started = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, 'memory budget'):
            render.run([sys.executable, '-I', '-c', 'import time; data=bytearray(64<<20); time.sleep(10)'],
                       timeout=5, memory_limit=32 << 20)
        self.assertLess(time.monotonic() - started, 5)
        with self.assertRaises(subprocess.TimeoutExpired):
            render.run([sys.executable, '-I', '-c', 'import time; time.sleep(10)'], timeout=.3)
        # The PDF parser stays in its caller-owned process. Its thread guard
        # terminates that same PID instead of leaving a new parser process group.
        program = ('import sys, time; sys.path.insert(0, ' + repr(str(Path(__file__).parent)) + '); '
                   'import team_file_pdf as pdf; pdf.MAX_MEMORY=32<<20; pdf.mac_memory_guard(); '
                   'data=bytearray(64<<20); time.sleep(5)')
        checked = subprocess.run([sys.executable, '-I', '-c', program], timeout=3)
        self.assertEqual(checked.returncode, 2)

    def test_fixed_script_and_json_job_use_private_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scratch = root / 'scratch'
            scratch.mkdir()
            profile = root / '.office-profile'
            profile.mkdir()
            source = str(root / 'fictional "quoted".xlsx')
            with patch.object(sys, 'platform', 'darwin'), patch.object(render, 'worker_limits'), \
                    patch.dict(os.environ, {}, clear=True), \
                    patch.object(render.os, 'execv', create=True) as execute:
                render.office_worker(source, str(root / 'output'), 'fictional', str(scratch))
                self.assertEqual(os.environ['FONTCONFIG_FILE'], str(profile / 'fonts.conf'))
            fonts = ET.parse(profile / 'fonts.conf').getroot()
            self.assertEqual([item.text for item in fonts.findall('dir')], ['/System/Library/Fonts', '/Library/Fonts'])
            self.assertEqual(fonts.find('cachedir').text, str(profile / 'font-cache'))
            scripts = profile / 'user/Scripts/python'
            self.assertEqual((scripts / 'anc_render.py').read_bytes(), Path(render.__file__).read_bytes())
            self.assertEqual(json.loads((scripts / 'job.json').read_text()), [source, str(root / 'output'), 'fictional'])
            binary, argv = execute.call_args.args
            self.assertEqual(binary, '/Applications/LibreOffice.app/Contents/MacOS/soffice')
            self.assertIn('-env:UserInstallation=' + profile.as_uri(), argv)
            self.assertEqual(argv[-1], 'vnd.sun.star.script:anc_render.py$mac_office_job?language=Python&location=user')
            self.assertNotIn(source, argv)
            self.assertFalse(any('--accept' in item for item in argv))

    def test_memory_monitor_counts_only_own_group_and_cleans_up(self):
        for usage, rejects in (([300 << 10, 300 << 10], True),
                               ([100 << 10], False), ([], True)):
            with self.subTest(usage=usage):
                proc = MagicMock(pid=42, returncode=0)
                proc.poll.return_value = None
                proc.communicate.side_effect = [subprocess.TimeoutExpired('fixture', .1), (b'done', b'')]
                with patch.object(sys, 'platform', 'darwin'), patch.object(render.subprocess, 'Popen', return_value=proc), \
                        patch.object(render, 'mac_group_memory', return_value=usage), \
                        patch.object(render, 'mac_group_pids', return_value=[42]), \
                        patch.object(render.signal, 'SIGKILL', 9, create=True), \
                        patch.object(render.os, 'killpg', create=True) as kill:
                    if rejects:
                        with self.assertRaises((RuntimeError, ValueError)) as stopped:
                            render.run(['fixture'], data=b'fictional', memory_limit=512 << 10)
                        if not usage:
                            self.assertEqual(stopped.exception.accounting,
                                             dict(operation='empty_group', pid=42, returned=0, expected=1, errno=0))
                    else:
                        self.assertEqual(render.run(['fixture'], data=b'fictional', memory_limit=512 << 10), b'done')
                        self.assertIsNone(proc.communicate.call_args.args[0])
                    kill.assert_called_once()
                    proc.wait.assert_called_once()

    def test_mac_pdf_parser_does_not_spawn_an_orphan_on_host_cancellation(self):
        for fails in (False, True):
            with self.subTest(fails=fails), patch.object(sys, 'platform', 'darwin'), \
                    patch.object(sys, 'argv', ['pdf']), patch.object(sys, 'stdin', MagicMock(buffer=io.BytesIO(b'%PDF-fictional'))), \
                    patch.object(sys, 'stdout', io.StringIO()), \
                    patch.dict(sys.modules, {'resource': MagicMock(), 'pypdf': MagicMock()}), \
                    patch.object(team_file_pdf, 'mac_memory_guard', create=True) as guard, \
                    patch.object(team_file_pdf, 'validate_pdf', side_effect=ValueError if fails else None), \
                    patch.object(subprocess, 'Popen', side_effect=AssertionError('parser child must not exist')):
                self.assertEqual(team_file_pdf.main(), 1 if fails else 0)
                guard.assert_called_once()
                guard.return_value.set.assert_called_once()


if __name__ == '__main__':
    unittest.main()
