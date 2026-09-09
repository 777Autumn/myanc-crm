"""Bounded OS locks for one protected ledger; never leases or write retries."""

import errno
import os
import stat
import time
from contextlib import contextmanager


WRITE_WAIT_SECONDS = 10.0


class WriteBlocked(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class _Contended(Exception):
    pass


def _try_lock(fd):
    if os.name == "posix":
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    elif os.name == "nt":
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        raise OSError("Unsupported locking platform")


@contextmanager
def acquire(directory, scopes):
    if directory is None:  # An isolated in-memory ledger has no other processes.
        yield
        return
    deadline = time.monotonic() + WRITE_WAIT_SECONDS
    held = []
    try:
        while True:
            try:
                for scope in scopes:
                    fd = os.open(directory / (scope + ".lock"),
                                 os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
                    held.append(fd)
                    info = os.fstat(fd)
                    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                            (os.name == "posix" and
                             (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600))):
                        raise ValueError("Unsafe CRM lock file")
                    try:
                        _try_lock(fd)
                    except OSError as exc:
                        if exc.errno not in (errno.EACCES, errno.EAGAIN):
                            raise
                        raise _Contended from exc
                break
            except _Contended:
                for fd in reversed(held):
                    os.close(fd)
                held.clear()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise WriteBlocked("crm_write_busy", "Another CRM operation is busy; no write was started. Preview and approve again.")
                time.sleep(min(0.05, remaining))
        yield
    finally:
        # Never unlink: another process may already be waiting on these inodes.
        for fd in reversed(held):
            os.close(fd)
