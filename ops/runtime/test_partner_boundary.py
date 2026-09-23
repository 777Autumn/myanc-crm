#!/usr/bin/env python3
"""Use real temporary numeric UIDs, without creating OS accounts or services."""

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location("partner_boundary", Path(__file__).with_name("verify-partner-boundary.py"))
boundary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(boundary)


@unittest.skipUnless(os.name == "posix" and os.geteuid() == 0, "requires local Linux root fixture")
class PartnerBoundaryTests(unittest.TestCase):
    def test_published_wiki_is_readable_but_only_own_drafts_are_writable(self):
        with tempfile.TemporaryDirectory(prefix='wiki-uids-') as temp:
            os.chmod(temp, 0o755)
            for uid in (61000, 61001, 61002):
                workspace = Path(temp) / str(uid)
                workspace.mkdir(mode=0o750)
                os.chown(workspace, uid, uid)
                published = workspace / '.claude/skills/team-banquet/references/mock-wiki'
                published.mkdir(parents=True)
                index = published / 'index.md'
                index.write_bytes(boundary.CANARY)
                index.chmod(0o444)
            for uid in (61000, 61001, 61002):
                workspace = Path(temp) / str(uid)
                index = workspace / '.claude/skills/team-banquet/references/mock-wiki/index.md'
                self.assertEqual(0, boundary.read_as(uid, uid, [uid], index))
                child = os.fork()
                if child == 0:
                    try:
                        os.setgroups([uid])
                        os.setgid(uid)
                        os.setuid(uid)
                        (workspace / 'draft.md').write_bytes(boundary.CANARY)
                        try:
                            index.write_bytes(b'not allowed')
                        except PermissionError:
                            os._exit(0)
                        os._exit(4)
                    except BaseException:
                        os._exit(3)
                self.assertEqual(0, os.waitstatus_to_exitcode(os.waitpid(child, 0)[1]))
                self.assertEqual(boundary.CANARY, index.read_bytes())
                self.assertEqual(boundary.CANARY, (workspace / 'draft.md').read_bytes())
            for uid in (61000, 61001, 61002):
                for other in (61000, 61001, 61002):
                    self.assertEqual(0 if uid == other else 2, boundary.read_as(
                        uid, uid, [uid], Path(temp) / str(other) / 'draft.md'))
            # This POSIX check covers file access. Native sandbox + workspace
            # guard separately protect .claude from ancestor rename/replacement.

    def test_six_real_uids_and_existing_fixtures(self):
        with tempfile.TemporaryDirectory(prefix="partner-boundary-") as temp:
            os.chmod(temp, 0o755)
            readers = [(61000 + n, 61000 + n, [61000 + n]) for n in range(6)]
            for n, (uid, gid, _) in enumerate(readers):
                directory = Path(temp) / str(n)
                directory.mkdir(mode=0o750)
                os.chown(directory, uid, gid)
                boundary.verify_canary(directory, n, readers, uid, gid, 0o644)
                self.assertEqual([], list(directory.iterdir()))
            # A deliberately readable directory is a failure, not a pass.
            os.chmod(Path(temp) / "0", 0o755)
            with self.assertRaisesRegex(RuntimeError, "isolation failed"):
                boundary.verify_canary(Path(temp) / "0", 0, readers, 61000, 61000, 0o644)
            # Missing fixtures must also not count as permission denials.
            self.assertEqual(3, boundary.read_as(*readers[1], Path(temp) / "absent"))


if __name__ == "__main__":
    unittest.main()
