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
