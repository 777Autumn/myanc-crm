"""Only the new simulation overrides legacy knowledge routing."""
from pathlib import Path
import unittest

ROOT = Path(__file__).parents[1]


class MockWikiRoutingTests(unittest.TestCase):
    def test_simulation_has_a_single_explicit_source_workflow(self):
        policy = (ROOT / 'ops/CLAUDE.vps.md').read_text(encoding='utf-8')
        skill = (ROOT / 'ops/skills/team-banquet/SKILL.md').read_text(encoding='utf-8')
        workflow = (ROOT / 'ops/skills/team-banquet/references/local-wiki.md').read_text(encoding='utf-8')
        self.assertIn('DEMO-WIKI-001', policy)
        self.assertLess(policy.index('DEMO-WIKI-001'), policy.index('Other team-work'))
        self.assertIn('references/local-wiki.md', skill)
        self.assertIn('其他公司资料按现有', skill)
        self.assertIn('mock-wiki/SOURCE.json', workflow)
        self.assertIn('尚未发布', workflow)
        self.assertIn('不调用旧飞书知识', workflow)
        self.assertIn('workspace-role.md', workflow)
        self.assertFalse((ROOT / 'ops/skills/team-brain').exists())

    def test_initial_material_contains_only_current_fictional_facts(self):
        material = (ROOT / 'ops/acceptance/mock-wiki-v1-material.md').read_text(encoding='utf-8')
        self.assertIn('全部为虚构演练设定', material)
        self.assertIn('每桌3980元', material)
        self.assertNotIn('4080', material)
        self.assertNotIn('103720', material)
        self.assertIn('具体档期与宴会日期没有提供', material)


if __name__ == '__main__':
    unittest.main()
