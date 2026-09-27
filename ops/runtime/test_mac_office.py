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
from unittest.mock import MagicMock, patch

import team_file_pdf
import team_file_render as render


class MacOfficeTests(unittest.TestCase):
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

    def test_fixed_script_and_json_job_use_private_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = str(root / 'fictional "quoted".xlsx')
            with patch.object(sys, 'platform', 'darwin'), patch.object(render, 'worker_limits'), \
                    patch.object(render.os, 'execv', create=True) as execute:
                render.office_worker(source, str(root / 'output'), 'fictional', str(root))
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
        for usage, rejects in ((b'42 300\n42 300\n9 9000000\n', True),
                               (b'42 100\n9 9000000\n', False),
                               (b'unparseable\n', True), (b'', True)):
            with self.subTest(usage=usage):
                proc = MagicMock(pid=42, returncode=0)
                proc.poll.return_value = None
                proc.communicate.side_effect = [subprocess.TimeoutExpired('fixture', .1), (b'done', b'')]
                with patch.object(sys, 'platform', 'darwin'), patch.object(render.subprocess, 'Popen', return_value=proc), \
                        patch.object(render.subprocess, 'check_output', return_value=usage), \
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

    def test_mac_pdf_parser_is_monitored_before_importing_pypdf(self):
        for output, expected in ((b'PDF_OK_V1\n', 0), (b'wrong', 1)):
            with self.subTest(output=output), patch.object(sys, 'platform', 'darwin'), \
                    patch.object(sys, 'argv', ['pdf']), patch.object(sys, 'stdin', MagicMock(buffer=io.BytesIO(b'%PDF-fictional'))), \
                    patch.object(sys, 'stdout', MagicMock(buffer=io.BytesIO())), \
                    patch.object(render, 'run', return_value=output) as run:
                self.assertEqual(team_file_pdf.main(), expected)
                command = run.call_args.args[0]
                self.assertEqual(command[-1], '--bounded-worker')
                self.assertEqual(run.call_args.kwargs['memory_limit'], 512 << 20)
                self.assertEqual(run.call_args.kwargs['data'], b'%PDF-fictional')


if __name__ == '__main__':
    unittest.main()
