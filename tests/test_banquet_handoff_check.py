"""Synthetic regression for saved handoff labels; no model, host or Feishu calls."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('handoff_check', Path(__file__).parents[1] / 'ops/skills/team-banquet/check_handoff.py')
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class HandoffCheckTests(unittest.TestCase):
    def test_copied_rules_are_not_confirmation(self):
        rows = [['时间/环节', '状态/依据'],
                ['布场', '已确认（经营基础规则：布场90分钟）'],
                ['检查', '已确认（经营基础规则：检查30分钟）'],
                ['缓冲', '已确认（经营基础规则：缓冲30分钟）']]
        self.assertEqual(list(check.conflicts(rows)), [(2, 2), (3, 2), (4, 2)])
        self.assertEqual(list(check.conflicts([['状态', '依据'], ['已确认', '耗时规则：90分钟']])), [(2, 1)])

    def test_preserve_actual_confirmation_and_distinguish_task_from_inputs(self):
        rows = [['时间/环节', '状态/依据', '任务'],
                ['入场', '已确认（本场场地确认单V2）', '据已确认入场条件安排工作'],
                ['布场', '计划／待执行（经营基础规则：90分钟）', '按已确认桌数备货'],
                ['检查', '已确认（本场检查时段签字确认单V3）', '检查30分钟'],
                ['LED', '未确认', '等待客户确认']]
        self.assertEqual(list(check.conflicts(rows)), [])

    def test_quotes_negation_and_specific_confirmation_are_not_downgraded(self):
        self.assertEqual(list(check.conflicts([
            ['旧版“已确认（经营基础规则：90分钟）”无依据，本版改计划'],
            ['不能写为已确认（经营基础规则：90分钟）'],
            ['已确认（本场确认单V3明确批准该时段；经营基础规则：90分钟）'],
        ])), [])
        # Mixed evidence with a rule first asks for review; it never rewrites or
        # decides that an explicit confirmation later in the cell is invalid.
        self.assertEqual(list(check.conflicts([
            ['已确认（经营基础规则：90分钟；另有本场确认单V3批准该时段）'],
        ])), [(1, 1)])

    def test_saved_excel_and_word_tables_are_read_and_originals_unchanged(self):
        from openpyxl import Workbook
        from docx import Document
        with tempfile.TemporaryDirectory() as folder:
            xlsx, docx = Path(folder)/'fictional.xlsx', Path(folder)/'fictional.docx'
            book = Workbook(); sheet = book.active
            sheet.append(['环节', '状态/依据'])
            sheet.append(['布场', '已确认（经营基础规则：90分钟）']); book.save(xlsx)
            doc = Document(); table = doc.add_table(rows=2, cols=2)
            table.cell(0, 0).text = '环节'; table.cell(0, 1).text = '状态/依据'
            table.cell(1, 0).text = '检查'; table.cell(1, 1).text = '已确认（推算：30分钟）'
            key_value = doc.add_table(rows=2, cols=2)
            key_value.cell(0, 0).text = '事项'; key_value.cell(0, 1).text = '布场'
            key_value.cell(1, 0).text = '状态'; key_value.cell(1, 1).text = '已确认（经营基础规则：90分钟）'
            doc.save(docx)
            before = [p.read_bytes() for p in (xlsx, docx)]
            self.assertEqual(len(list(check.inspect(xlsx))), 1)
            self.assertEqual(len(list(check.inspect(docx))), 2)
            self.assertEqual([p.read_bytes() for p in (xlsx, docx)], before)
            table.cell(1, 1).text = '计划／待执行（推算：30分钟）'
            key_value.cell(1, 1).text = '计划／待执行（经营基础规则：90分钟）'; doc.save(docx)
            sheet.cell(2, 2).value = '计划／待执行（经营基础规则：90分钟）'; book.save(xlsx)
            self.assertEqual(list(check.inspect(xlsx)) + list(check.inspect(docx)), [])


if __name__ == '__main__':
    unittest.main()
