import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location('maintenance_inventory', Path(__file__).parents[1] / 'ops/maintenance_inventory.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.files = {}
        for name in ('runtime', 'client'):
            path = Path(self.temp.name) / name
            path.write_bytes(b'old')
            old = m.file_identity(path)
            path.write_bytes(b'new')
            self.files[str(path)] = {'old': old, 'new': m.file_identity(path)}
            path.write_bytes(b'old')

    def test_old_partial_new_are_reported_without_mutation(self):
        self.assertEqual(m.inspect_inventory(self.files)['state'], 'old')
        paths = list(self.files)
        Path(paths[0]).write_bytes(b'new')
        result = m.inspect_inventory(self.files)
        self.assertEqual(result['state'], 'partial')
        self.assertEqual(list(result['files'].values()), ['new', 'old'])
        with self.assertRaisesRegex(ValueError, 'not_new:partial'):
            m.verify_new_inventory(self.files)
        self.assertEqual(Path(paths[1]).read_bytes(), b'old')
        Path(paths[1]).write_bytes(b'new')
        self.assertEqual(m.verify_new_inventory(self.files)['state'], 'new')

    def test_unknown_missing_or_unreadable_file_blocks(self):
        path = Path(next(iter(self.files)))
        path.write_bytes(b'unreviewed')
        self.assertEqual(m.inspect_inventory(self.files)['state'], 'unknown')
        path.unlink()
        self.assertEqual(m.inspect_inventory(self.files)['state'], 'unknown')
        with patch.object(m, 'file_identity', side_effect=PermissionError()):
            self.assertEqual(m.inspect_inventory(self.files)['state'], 'unknown')

    def test_permissions_are_part_of_identity(self):
        first = next(iter(self.files))
        observed = dict(self.files[first]['new'], uid=self.files[first]['new']['uid'] + 1)
        with patch.object(m, 'file_identity', return_value=observed):
            self.assertEqual(m.inspect_inventory({first: self.files[first]})['state'], 'unknown')

    def test_file_changed_during_hashing_is_unknown(self):
        first = next(iter(self.files))
        original = m.hashlib.file_digest
        def changed(stream, algorithm):
            result = original(stream, algorithm)
            Path(first).write_bytes(b'changed while being inspected')
            return result
        with patch.object(m.hashlib, 'file_digest', side_effect=changed):
            self.assertEqual(m.inspect_inventory({first: self.files[first]})['state'], 'unknown')

    def test_unchanged_file_does_not_make_complete_install_partial(self):
        for path, versions in self.files.items():
            Path(path).write_bytes(b'new')
        first = next(iter(self.files))
        self.files[first]['old'] = self.files[first]['new']
        self.assertEqual(m.verify_new_inventory(self.files)['state'], 'new')
        self.assertEqual(m.inspect_inventory(self.files)['files'][first], 'unchanged')

    def test_new_file_must_have_been_absent(self):
        first = next(iter(self.files))
        self.files = {first: dict(self.files[first], old=None)}
        Path(first).unlink()
        self.assertEqual(m.inspect_inventory(self.files)['state'], 'old')
        Path(first).write_bytes(b'new')
        self.assertEqual(m.verify_new_inventory(self.files)['state'], 'new')

    def test_invalid_freeze_is_rejected(self):
        for manifest in ({}, {'relative': next(iter(self.files.values()))},
                         {next(iter(self.files)): {'old': None, 'new': None}}):
            with self.subTest(manifest=manifest), self.assertRaises(ValueError):
                m.inspect_inventory(manifest)

    def test_symlink_is_not_accepted_as_installation(self):
        first, second = map(Path, self.files)
        first.unlink()
        try:
            first.symlink_to(second)
        except OSError:
            self.skipTest('symlink creation requires platform permission')
        self.assertEqual(m.inspect_inventory(self.files)['files'][str(first)], 'unknown')


if __name__ == '__main__':
    unittest.main()
