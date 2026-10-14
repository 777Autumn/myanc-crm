"""Lifetime of a native CLI fixture, before its temporary files are removed."""
import os
import signal
import subprocess
import time


def stop_codex_process(process):
    """Stop a fixture started with start_new_session=True, including its writers."""
    try:
        if process.stdin and not process.stdin.closed:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
    finally:
        # Codex can exit before its background plugin clone finishes writing.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
        deadline = time.monotonic() + 5
        while True:
            # macOS can deny signal 0 for an exiting group; zombies cannot write.
            rows = subprocess.check_output(['/bin/ps', '-axo', 'pgid=,stat='],
                                           text=True, timeout=5).splitlines()
            members = [row.split() for row in rows if row.strip()]
            if not any(int(group) == process.pid and not state.startswith('Z')
                       for group, state in members):
                break
            if time.monotonic() >= deadline:
                raise RuntimeError('native fixture process group still has live members')
            time.sleep(.01)
