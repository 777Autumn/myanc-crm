"""Only the new simulation overrides legacy knowledge routing."""
from pathlib import Path
import importlib.util
import json
import os
import re
import tempfile
import unittest

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location('mock_wiki', ROOT / 'ops/mock_wiki.py')
wiki = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wiki)


class MockWikiRoutingTests(unittest.TestCase):
    def test_simulation_has_a_single_explicit_source_workflow(self):
        policy = (ROOT / 'ops/CLAUDE.vps.md').read_text(encoding='utf-8')
        skill = (ROOT / 'ops/skills/team-banquet/SKILL.md').read_text(encoding='utf-8')
        workflow = (ROOT / 'ops/skills/team-banquet/references/local-wiki.md').read_text(encoding='utf-8')
        self.assertIn('DEMO-WIKI-001', policy)
        self.assertLess(policy.index('DEMO-WIKI-001'), policy.index('Other team-work'))
        self.assertIn('references/local-wiki.md', skill)
        self.assertIn('其他公司资料按现有', skill)
        self.assertIn('只选择一个对应分支', skill)
        self.assertIn('提到公司名称即已指定案例', skill)
        self.assertIn('此分支不使用下列旧演练资料', skill)
        self.assertIn('未指定公司或案例、未提供独立材料', skill)
        self.assertLess(skill.index('references/mock-wiki/index.md'), skill.index('references/fictional-venue.md'))
        # Contract checks protect the pointers; real model source selection still needs a CUJ.
        self.assertIn('mock-wiki/03-套餐与报价.md', workflow)
        self.assertIn('读到本文不代表已读取公司资料', workflow)
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

    def test_published_candidate_links_facts_and_calculations(self):
        root = ROOT / 'ops' / wiki.RELATIVE_ROOT
        metadata = json.loads((root / 'metadata.json').read_text(encoding='utf-8'))
        self.assertEqual(metadata['source_materials'], ['DEMO-WIKI-001-SOURCE-01 v1'])
        self.assertEqual(len(metadata['draft_sha256']), 7)
        for page in root.glob('*.md'):
            content = page.read_text(encoding='utf-8')
            for target in re.findall(r'\]\(\./([^\)]+)\)', content):
                self.assertTrue((root / target).is_file(), f'{page.name}: {target}')
            self.assertNotIn('4,080', content)
        prices = (root / '03-套餐与报价.md').read_text(encoding='utf-8')
        rows = {label.strip(): int(price.replace(',', '')) for label, price in re.findall(
            r'^\|\s*([^|]+?)\s*\|\s*([\d,]+)(?: 元(?:/瓶)?)?\s*\|', prices, re.M)}
        def total(package, decoration):
            return 22 * (rows[package] + 6 * rows['酒水']) + rows['固定服务费'] + rows['主持'] + rows[decoration]
        self.assertEqual(total('A 清雅', '主题布置 · 基础'), 101520)
        self.assertEqual(total('A 清雅', '主题布置 · 升级'), 107520)
        self.assertEqual(total('B 丰盛', '主题布置 · 基础'), 114720)
        flow = (root / '05-流程与状态口径.md').read_text(encoding='utf-8')
        for fact in ('09:00', '90 分钟', '30 分钟', '明确批准材料'):
            self.assertIn(fact, flow)
        self.assertNotIn('08:00', flow)
        self.assertFalse((root / 'SOURCE.json').exists(), 'source commit is generated after merge, never guessed')


class MockWikiManifestTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / 'index.md').write_text('# 虚构演练\n', encoding='utf-8')
        (self.root / 'metadata.json').write_text(json.dumps({
            'company_id': 'DEMO-WIKI-001', 'data_scope': '虚构演练', 'version': 1}), encoding='utf-8')
        self.commit = 'a' * 40
        self.saved = wiki.manifest(self.root, self.commit)
        (self.root / 'SOURCE.json').write_text(json.dumps(self.saved), encoding='utf-8')

    def test_exact_snapshot_and_version_are_required(self):
        self.assertEqual(self.saved, wiki.verify(self.root, self.commit, 1))
        for commit, version in [('b' * 40, 1), (self.commit, 2)]:
            with self.assertRaises(ValueError):
                wiki.verify(self.root, commit, version)
        (self.root / 'index.md').write_text('# changed\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            wiki.verify(self.root, self.commit, 1)

    def test_missing_extra_and_invalid_files_do_not_pass(self):
        extra = self.root / 'unpublished.md'
        extra.write_text('draft', encoding='utf-8')
        with self.assertRaises(ValueError):
            wiki.verify(self.root, self.commit, 1)
        extra.unlink()
        (self.root / 'index.md').unlink()
        with self.assertRaises(ValueError):
            wiki.verify(self.root, self.commit, 1)
        with self.assertRaises(ValueError):
            wiki.manifest(self.root, 'short')

    @unittest.skipUnless(os.name == 'posix', 'symbolic links checked on Linux CI')
    def test_symbolic_link_cannot_supply_published_source(self):
        (self.root / 'alias.md').symlink_to(self.root / 'index.md')
        with self.assertRaises(ValueError):
            wiki.manifest(self.root, self.commit)


if __name__ == '__main__':
    unittest.main()
