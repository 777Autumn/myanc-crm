"""Mac worker seams; fictional paths, no Office install or real messages."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import MagicMock, patch

import team_file_pdf
import team_file_render as render


class MacOfficeTests(unittest.TestCase):
    def test_native_accounting_is_group_scoped_and_rejects_uncertainty(self):
        for returned, info_size, error, expected in ((8, 96, 0, [1234, 1234]),
                                                   (4, 0, render.errno.ESRCH, []),
                                                   (4, 0, render.errno.EPERM, None),
                                                   (-1, 96, 0, None), (512, 96, 0, None),
                                                   (3, 96, 0, None)):
            with self.subTest(returned=returned, info_size=info_size, error=error):
                lib = MagicMock()

                def list_pids(kind, group, pids, size):
                    self.assertEqual((kind, group, size), (2, 42, 512))
                    pids[0], pids[1] = 42, 43
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
                        with self.assertRaisesRegex(RuntimeError, 'accounting unavailable'):
                            render.mac_group_memory(42)
                    else:
                        self.assertEqual(render.mac_group_memory(42), expected)

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
            source = str(root / 'fictional "quoted".xlsx')
            with patch.object(sys, 'platform', 'darwin'), patch.object(render, 'worker_limits'), \
                    patch.dict(os.environ, {}, clear=True), \
                    patch.object(render.os, 'execv', create=True) as execute:
                render.office_worker(source, str(root / 'output'), 'fictional', str(root))
                self.assertEqual(os.environ['FONTCONFIG_FILE'], str(root / 'profile/fonts.conf'))
            fonts = ET.parse(root / 'profile/fonts.conf').getroot()
            self.assertEqual([item.text for item in fonts.findall('dir')], ['/System/Library/Fonts', '/Library/Fonts'])
            self.assertEqual(fonts.find('cachedir').text, str(root / 'profile/font-cache'))
            scripts = root / 'profile/user/Scripts/python'
            self.assertEqual((scripts / 'anc_render.py').read_bytes(), Path(render.__file__).read_bytes())
            self.assertEqual(json.loads((scripts / 'job.json').read_text()), [source, str(root / 'output'), 'fictional'])
            binary, argv = execute.call_args.args
            self.assertEqual(binary, '/Applications/LibreOffice.app/Contents/MacOS/soffice')
            self.assertIn('-env:UserInstallation=' + (root / 'profile').as_uri(), argv)
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
                        patch.object(render.signal, 'SIGKILL', 9, create=True), \
                        patch.object(render.os, 'killpg', create=True) as kill:
                    if rejects:
                        with self.assertRaises((RuntimeError, ValueError)):
                            render.run(['fixture'], data=b'fictional', memory_limit=512 << 10)
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
