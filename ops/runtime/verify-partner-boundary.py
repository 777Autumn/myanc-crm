#!/usr/bin/env python3
"""Post-maintenance six-UID acceptance; creates and removes only its own canaries.

Does not provision users, copy credentials, start services or access CRM.
Run as root after installing the reviewed fixed directory/group configuration.
"""

import os
from pathlib import Path
import stat
import tempfile


RUNTIMES = ("claude", "claude-owner-group", "claude-partner-private", "claude-partner-group", "claude-test-private", "claude-test-group")
CANARY = b"fictional-partner-isolation-probe\n"


def read_as(uid, gid, groups, path):
    child = os.fork()
    if child == 0:
        try:
            os.setgroups(groups)
            os.setgid(gid)
            os.setuid(uid)
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            content = os.read(fd, len(CANARY) + 1)
            os.close(fd)
            os._exit(0 if content == CANARY else 4)
        except PermissionError:
            os._exit(2)
        except BaseException:
            os._exit(3)  # Missing files and other failures are NOT isolation.
    return os.waitstatus_to_exitcode(os.waitpid(child, 0)[1])


def plain_directory(path):
    path = Path(path)
    for parent in (path, *path.parents):
        value = parent.lstat()
        if not stat.S_ISDIR(value.st_mode) or stat.S_ISLNK(value.st_mode):
            raise RuntimeError("directory is missing, not a directory, or a symlink")
    return path


def verify_canary(directory, owner, readers, file_uid, file_gid, mode):
    directory = plain_directory(directory)
    fd, filename = tempfile.mkstemp(prefix=".partner-isolation-", dir=directory)
    saved = os.fstat(fd)
    try:
        os.write(fd, CANARY)
        os.fchown(fd, file_uid, file_gid)
        os.fchmod(fd, mode)
        saved = os.fstat(fd)
        os.close(fd)
        fd = -1
        # Supervisor proves existence and contents before testing denials.
        if Path(filename).read_bytes() != CANARY:
            raise RuntimeError("probe fixture was not created correctly")
        for index, (uid, gid, groups) in enumerate(readers):
            result = read_as(uid, gid, groups, filename)
            if result != (0 if index == owner else 2):
                raise RuntimeError(f"isolation failed for runtime index {index}: probe result {result}")
    finally:
        if fd >= 0:
            os.close(fd)
        current = os.lstat(filename)
        if saved is not None and (current.st_dev, current.st_ino) == (saved.st_dev, saved.st_ino):
            os.unlink(filename)
        else:
            raise RuntimeError("probe entry changed; automatic cleanup refused")


def main():
    import pwd
    if os.geteuid() != 0:
        raise SystemExit("Run as root; this check must test actual runtime UIDs.")
    people = [pwd.getpwnam(name) for name in RUNTIMES]
    if len({p.pw_uid for p in people}) != 6 or any(p.pw_uid == 0 for p in people):
        raise SystemExit("Six distinct non-root UIDs are required.")
    readers = [(p.pw_uid, p.pw_gid, os.getgrouplist(p.pw_name, p.pw_gid)) for p in people]
    supervisor = pwd.getpwnam("ccconnect")
    for index, person in enumerate(people):
        expected_home = "/home/" + person.pw_name
        if person.pw_dir != expected_home:
            raise SystemExit("Runtime HOME differs from its reviewed fixed path.")
        workspace = plain_directory(Path(expected_home) / "ClaudeRemote")
        for directory in (workspace, plain_directory(Path(expected_home) / ".claude")):
            verify_canary(directory, index, readers, person.pw_uid, person.pw_gid, 0o644)
        cache = plain_directory(workspace / ".cc-connect/attachments/images")
        info = cache.stat()
        members = {p.pw_name for p in people if info.st_gid in os.getgrouplist(p.pw_name, p.pw_gid)}
        if info.st_uid != supervisor.pw_uid or stat.S_IMODE(info.st_mode) != 0o2750 or members != {person.pw_name}:
            raise SystemExit("Image cache must be gateway-owned with exactly its runtime in the read group.")
        verify_canary(cache, index, readers, supervisor.pw_uid, info.st_gid, 0o440)
    print("PASS: 18 existing canaries; each readable by its runtime and denied to the other five. Canary files removed.")


if __name__ == "__main__":
    main()
