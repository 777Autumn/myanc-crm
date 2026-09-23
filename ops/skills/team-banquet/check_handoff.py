"""Read saved handoffs and flag rule-first confirmation labels; never edit them.

This narrow lint catches a reproduced copying error. Zero findings are not proof
of business confirmation: sources, missing statuses and cross-file consistency
still require the Skill's full readback.
"""
import re
import sys
from pathlib import Path

RULE = r'(?:经营基础规则|耗时规则|推算|计算得出)'
# ponytail: catches explicit rule-first labels; other wording needs source review.
COPIED_CONFIRMATION = re.compile(r'^已确认\s*[（(:：]\s*' + RULE)


def conflicts(rows):
    """Locate current labels needing evidence review, not quoted/negated examples."""
    status_cols, basis_cols = [], []
    for number, row in enumerate(rows, 1):
        cells = [str(value or '').strip() for value in row]
        headers = [i for i, value in enumerate(cells) if value in ('状态', '状态/依据', '确认状态', '确认状态/依据')]
        # Word handoffs also use two-column label/value rows, not column headers.
        if len(cells) == 2 and headers == [0] and cells[1].startswith(
                ('已确认', '未确认', '待确认', '计划', '待执行', '已发生', '待核实')):
            if COPIED_CONFIRMATION.match(cells[1]):
                yield number, 2
            continue
        if headers:
            status_cols = headers
            basis_cols = [i for i, value in enumerate(cells) if value in ('依据', '来源', '确认依据', '状态/依据', '确认状态/依据')]
            continue
        for index, text in enumerate(cells):
            # A confirmed input in a task description is not the task's status.
            if status_cols and index not in status_cols:
                continue
            direct = COPIED_CONFIRMATION.search(text)
            separated = text == '已确认' and any(
                i < len(cells) and re.match(r'^' + RULE, cells[i]) for i in basis_cols)
            if direct or separated:
                yield number, index + 1


def inspect(path):
    if path.suffix.lower() == '.xlsx':
        from openpyxl import load_workbook
        book = load_workbook(path, read_only=True, data_only=False)
        try:
            for sheet in book:
                for row, col in conflicts(sheet.values):
                    yield f'{path.name}: {sheet.title} row {row}, column {col}'
        finally:
            book.close()
    elif path.suffix.lower() == '.docx':
        from docx import Document
        doc = Document(path)
        for row, _ in conflicts([[p.text] for p in doc.paragraphs]):
            yield f'{path.name}: paragraph {row}'
        for number, table in enumerate(doc.tables, 1):
            for row, col in conflicts([[c.text for c in r.cells] for r in table.rows]):
                yield f'{path.name}: table {number}, row {row}, column {col}'
    else:
        raise ValueError('expected a saved .xlsx or .docx file')


def main(paths):
    if not paths:
        raise ValueError('provide the saved handoff Excel and Word paths')
    findings = [finding for path in paths for finding in inspect(Path(path))]
    for finding in findings:
        print(f'{finding}: confirmation basis starts with a rule/calculation; review any specific confirmation source before delivery')
    if not findings:
        print('No rule-first confirmation labels found. Full source/status/content readback is still required.')
    return bool(findings)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
