"""Runtime policy routing/package contract; no model or production access."""
from pathlib import Path
import hashlib
import re
import subprocess
import sys
import tempfile
import unittest


OPS = Path(__file__).parents[1] / "ops"


class RuntimeSkillsTests(unittest.TestCase):
    def test_documented_artifact_hashes_saved_bytes_and_fails_for_missing_file(self):
        skill = (OPS / 'skills/team-files/SKILL.md').read_text(encoding='utf-8')
        code = skill.split('```python\n', 1)[1].split('\n```', 1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / '虚构 预算.xlsx'
            content = b'fictional saved artifact\x00\xff'
            path.write_bytes(content)
            command = [sys.executable, '-I', '-X', 'utf8', '-c', code]
            result = subprocess.run(command + [str(path)], capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), hashlib.sha256(content).hexdigest() + '  ' + str(path))
            self.assertEqual(path.read_bytes(), content)
            self.assertNotEqual(subprocess.run(command + [str(path) + '.missing'], capture_output=True).returncode, 0)

    def test_thin_policy_routes_to_single_authoritative_protocols(self):
        policy = (OPS / "CLAUDE.vps.md").read_text(encoding="utf-8")
        self.assertLess(len(policy.splitlines()), 200)
        for name, marker in (("team-crm", "CRM_HOST_TOOLS_V1"),
                             ("team-reminders", "REMINDER_HOST_TOOLS_V1"),
                             ("team-files", "FILE_HOST_TOOLS_V1")):
            skill = (OPS / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            reference = (OPS / "skills" / name / "references/tools.md").read_text(encoding="utf-8")
            self.assertIn(f".claude/skills/{name}/SKILL.md", policy)
            frontmatter = skill.split("---", 2)[1]
            self.assertEqual({"name", "description"}, set(re.findall(r"^(\S+):", frontmatter, re.M)))
            self.assertIn(f"name: {name}", frontmatter)
            self.assertIn("references/tools.md", skill)
            self.assertIn(marker, reference)
            self.assertNotIn(marker, policy)
            self.assertNotIn(marker, skill)
        self.assertIn(".claude/skills/team-brain/SKILL.md", policy)
        self.assertFalse((OPS / "skills/team-brain").exists(), "knowledge skill must not be copied or replaced")

    def test_existing_boundaries_and_cross_skill_handoff_remain(self):
        policy = (OPS / "CLAUDE.vps.md").read_text(encoding="utf-8")
        crm = (OPS / "skills/team-crm/references/tools.md").read_text(encoding="utf-8")
        reminder = (OPS / "skills/team-reminders/references/tools.md").read_text(encoding="utf-8")
        for text in ("REMOTE_WORKSPACE_BOUNDARY_V3", "REMOTE_SIDE_EFFECT_APPROVAL_V3",
                     "Partner conversation boundary", "Image input and conversation continuity",
                     "missing or unreadable", "does not prove success or zero writes"):
            self.assertIn(text, policy)
        self.assertEqual(1, crm.count('entire\n   conversational reply must be exactly: "方案见审批卡，执行状态以卡片为准。"'))
        for text in ("next_request", "history_offset", "backfill=true", "related_operations",
                     "durable_change_state", "without exposing/changing personal reminders"):
            self.assertIn(text, crm)
        for text in ("current user turn", "private_list_queued", "may_be_in_flight",
                     "requires its CRM approval card", "leaving the CRM plan", "next_id"):
            self.assertIn(text, reminder)

    def test_banquet_files_route_to_the_existing_business_skill(self):
        files = (OPS / "skills/team-files/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`team-banquet` Skill before interpreting or revising business content", files)
        self.assertIn("when only reorganizing a colleague's file", files)
        self.assertIn("without claiming business validation", files)
        self.assertTrue((OPS / "skills/team-banquet/check_handoff.py").is_file())

    def test_file_delivery_exception_requires_enabled_host_capability(self):
        policy = (OPS / "CLAUDE.vps.md").read_text(encoding="utf-8")
        delivery = policy.split("## Controlled file delivery\n", 1)[1].split("\n## ", 1)[0]
        for text in ("only when a fresh host `work-context`", "`enabled: true`",
                     "/usr/local/bin/cc-connect-file", "host-bound work",
                     "exact artifact version", "host alone selects",
                     "grants no CRM write or knowledge publication",
                     "disabled, missing or unavailable", "delivery is unavailable",
                     "Do not substitute", "management API or another recipient",
                     "none proves that the employee received and opened"):
            self.assertIn(text, delivery)
        self.assertIn("A missing specialized skill does not block ordinary file preparation", policy)


if __name__ == "__main__":
    unittest.main()
