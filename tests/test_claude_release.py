"""Keep the native artifact and managed version gate deployable as one pair."""
import json
from pathlib import Path
import unittest


class ClaudeReleaseTests(unittest.TestCase):
    def test_native_pin_matches_managed_policy_and_scoped_model_configuration(self):
        root = Path(__file__).parents[1] / 'ops' / 'runtime'
        release = json.loads((root / 'claude-release.json').read_text(encoding='utf-8'))
        managed = json.loads((root / 'claude-managed-settings.json').read_text(encoding='utf-8'))
        version = release['version']
        self.assertEqual(version, managed['requiredMinimumVersion'])
        self.assertEqual(version, managed['requiredMaximumVersion'])
        self.assertGreaterEqual(tuple(map(int, version.split('.'))), (2, 1, 280))
        origin = 'https://downloads.claude.ai/claude-code-releases/' + version
        self.assertEqual(origin + '/linux-x64/claude', release['url'])
        self.assertEqual(origin + '/manifest.json', release['manifest_url'])
        for key in ('sha256', 'manifest_sha256'):
            self.assertRegex(release[key], r'^[0-9a-f]{64}$')
        self.assertGreater(release['size'], 0)
        self.assertEqual('claude-opus-5-5', release['model'])
        self.assertEqual('low', release['reasoning_effort'])
        self.assertCountEqual(['claude-local', 'owner-group', 'test-private', 'test-group'],
                              release['explicit_model_entries'])
        self.assertEqual('1', managed['env']['DISABLE_UPDATES'])
