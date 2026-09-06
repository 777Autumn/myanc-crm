"""Offline fixture checks, separate from model semantic grading."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from host_tool_fixture import PersistentFakeFeishu


class OwnerFixtureTests(unittest.TestCase):
    def test_paired_term_seeds_are_persistent_facts_not_business_writes(self):
        for seed in ("term-ambiguous", "term-defined"):
            with self.subTest(seed=seed), tempfile.TemporaryDirectory() as path:
                with mock.patch.dict(os.environ, {"MYANC_SPIKE_SEED": seed}):
                    first = PersistentFakeFeishu(Path(path))
                with mock.patch.dict(os.environ, {"MYANC_SPIKE_SEED": ""}):
                    reopened = PersistentFakeFeishu(Path(path))
                self.assertEqual(first.customers, reopened.customers)
                self.assertEqual([], reopened.actions)
                rows = reopened.read_customer_history("rec-1", 10)
                self.assertEqual(1, len(rows))
                self.assertEqual(reopened.customers["rec-1"]["last_followup_content"],
                                 rows[0]["content"])
                self.assertEqual(seed == "term-defined", "5%" in rows[0]["content"])

    def test_unknown_seed_is_rejected_instead_of_silently_changing_a_case(self):
        with tempfile.TemporaryDirectory() as path:
            with mock.patch.dict(os.environ, {"MYANC_SPIKE_SEED": "typo"}):
                with self.assertRaises(ValueError):
                    PersistentFakeFeishu(Path(path))


if __name__ == "__main__":
    unittest.main()
