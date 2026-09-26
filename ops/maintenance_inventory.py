"""Read-only comparison of the operator's frozen old/new installation list.

Only listed regular files are read. Directory boundaries and the completeness of
that list remain part of the existing protected-control verification.
"""
import hashlib
import json
import os
from pathlib import Path
import stat


def inventory_sha256(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_identity(path):
    """Return content and permission identity; refuse links or a changing file."""
    before = Path(path).lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('inventory_not_regular_file')
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(stream.fileno())
    current = Path(path).lstat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns,
                          s.st_mode, s.st_uid, s.st_gid)
    # Windows path-stat and descriptor-stat expose different ctime semantics.
    # Compare each source with itself; all platforms still pin the same inode.
    if (not identity(before) == identity(opened) == identity(after) == identity(current)
            or before.st_ctime_ns != current.st_ctime_ns or opened.st_ctime_ns != after.st_ctime_ns):
        raise ValueError('inventory_file_changed')
    return dict(sha256=digest, uid=after.st_uid, gid=after.st_gid,
                mode=stat.S_IMODE(after.st_mode))


def inspect_inventory(files):
    """Classify the exact frozen list without installing, continuing or undoing it."""
    if not isinstance(files, dict) or not files:
        raise ValueError('invalid_installation_list')
    states = {}
    for path, versions in files.items():
        if (not isinstance(path, str) or not Path(path).is_absolute()
                or not isinstance(versions, dict) or set(versions) != {'old', 'new'}):
            raise ValueError('invalid_installation_entry')
        for version in ('old', 'new'):
            value = versions[version]
            if value is None and version == 'old':
                continue  # A newly introduced file must have been absent before.
            if (not isinstance(value, dict) or set(value) != {'sha256', 'uid', 'gid', 'mode'}
                    or not isinstance(value['sha256'], str) or len(value['sha256']) != 64
                    or any(c not in '0123456789abcdef' for c in value['sha256'])
                    or any(type(value[k]) is not int or value[k] < 0 for k in ('uid', 'gid', 'mode'))
                    or value['mode'] > 0o7777):
                raise ValueError('invalid_file_identity')
        try:
            actual = file_identity(path)
        except FileNotFoundError:
            actual = None
        except (OSError, ValueError):
            states[path] = 'unknown'
            continue
        old, new = actual == versions['old'], actual == versions['new']
        states[path] = 'unchanged' if old and new else 'new' if new else 'old' if old else 'unknown'
    kinds = set(states.values())
    state = ('unknown' if 'unknown' in kinds else 'partial' if {'old', 'new'} <= kinds
             else 'old' if 'old' in kinds else 'new')
    return dict(state=state, files=states, inventory_sha256=inventory_sha256(files))


def verify_new_inventory(files):
    result = inspect_inventory(files)
    if result['state'] != 'new':
        raise ValueError('installed_inventory_not_new:' + result['state'])
    return result
