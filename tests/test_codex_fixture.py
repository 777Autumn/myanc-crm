"""Real background writers must stop before native fixture directory cleanup."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from codex_fixture import stop_codex_process


@unittest.skipUnless(os.name == 'posix', 'native fixture process groups require POSIX')
class CodexFixtureTests(unittest.TestCase):
    def test_timeout_stops_live_process_and_preserves_failure(self):
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, start_new_session=True)
        try:
            with self.assertRaises(subprocess.TimeoutExpired):
                try:
                    process.communicate(timeout=.05)
                finally:
                    stop_codex_process(process)
            self.assertIsNotNone(process.returncode)
            with self.assertRaises(ProcessLookupError):
                os.killpg(process.pid, 0)
        finally:
            process.stdout.close()
            process.stderr.close()

    def test_exited_parent_cannot_leave_writer_in_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            child = """import os,pathlib,sys,time
p=pathlib.Path(sys.argv[1])
(p/'child').write_text(str(os.getpid()))
while not (p/'release').exists(): time.sleep(.01)
(p/'late-plugin-file').write_text('background plugin clone')
"""
            parent = """import pathlib,subprocess,sys,time
subprocess.Popen([sys.executable,'-c',sys.argv[2],sys.argv[1]],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
while not (pathlib.Path(sys.argv[1])/'child').exists(): time.sleep(.01)
"""
            try:
                process = subprocess.Popen([sys.executable, '-c', parent, tmp, child],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
                try:
                    self.assertEqual(process.wait(timeout=5), 0)
                    self.assertTrue((root / 'child').is_file())
                finally:
                    stop_codex_process(process)
                (root / 'release').touch()
                deadline = time.monotonic() + .5
                while time.monotonic() < deadline and not (root / 'late-plugin-file').exists():
                    time.sleep(.01)
                self.assertFalse((root / 'late-plugin-file').exists(),
                                 'parent exited but its child still writes into the fixture')
            finally:
                if (root / 'child').exists():
                    try:
                        os.kill(int((root / 'child').read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass


if __name__ == '__main__':
    unittest.main()
