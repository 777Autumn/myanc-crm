"""Offline rendering only: fictional sources, no models or external messages."""
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile
import xml.etree.ElementTree as ET
from unittest.mock import patch

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from pptx import Presentation
from pptx.util import Inches
from pypdf import PdfReader

from team_file_render import office_check, prepare_paths, render, run


def deny_unix_sockets():
    """Match the deployed Linux sandbox's AF_UNIX denial in the actual worker."""
    import ctypes as c
    import socket
    assert os.geteuid() != 0
    class Arg(c.Structure):
        _fields_ = [('arg', c.c_uint), ('op', c.c_uint), ('a', c.c_uint64), ('b', c.c_uint64)]
    lib = c.CDLL('libseccomp.so.2')
    lib.seccomp_init.restype = c.c_void_p
    lib.seccomp_rule_add_array.argtypes = [c.c_void_p, c.c_uint32, c.c_int, c.c_uint, c.POINTER(Arg)]
    lib.seccomp_load.argtypes = [c.c_void_p]
    lib.seccomp_release.argtypes = [c.c_void_p]
    lib.seccomp_syscall_resolve_name.argtypes = [c.c_char_p]
    context = lib.seccomp_init(0x7fff0000)  # SCMP_ACT_ALLOW
    assert context
    try:
        # SCMP_ACT_ERRNO(EPERM), argument 0 == AF_UNIX (SCMP_CMP_EQ).
        syscall = lib.seccomp_syscall_resolve_name(b'socket')
        assert syscall >= 0
        assert lib.seccomp_rule_add_array(context, 0x50001, syscall, 1, c.byref(Arg(0, 4, socket.AF_UNIX, 0))) == 0
        assert lib.seccomp_load(context) == 0
    finally:
        lib.seccomp_release(context)
    try:
        with socket.socket(socket.AF_UNIX):
            raise AssertionError('AF_UNIX unexpectedly allowed')
    except PermissionError:
        pass


def add_field(paragraph, code):
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), code)
    run_node = OxmlElement('w:r')
    text = OxmlElement('w:t')
    text.text = '0'
    run_node.append(text)
    field.append(run_node)
    paragraph._p.append(field)


def fictional_template(path, extra=False):
    doc = Document()
    for style in ('Normal', 'Heading 1', 'Heading 2'):
        doc.styles[style].font.name = 'Noto Sans CJK SC'
        doc.styles[style]._element.get_or_add_rPr().get_or_add_rFonts().set(qn('w:eastAsia'), 'Noto Sans CJK SC')
    doc.styles['Normal'].font.size = Pt(11)
    doc.sections[0].header.paragraphs[0].text = '虚构婚宴演练资料 v1'
    footer = doc.sections[0].footer.paragraphs[0]
    footer.add_run('Page ')
    add_field(footer, 'PAGE')
    footer.add_run(' of ')
    add_field(footer, 'NUMPAGES')
    doc.add_paragraph('目录')
    add_field(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u')
    doc.add_page_break()
    doc.add_heading('第一章 客户需求', level=1)
    doc.add_paragraph('虚构客户，22 桌，220 人。来源：模拟套餐资料 v1。')
    if extra:
        for i in range(3):
            doc.add_page_break()
            doc.add_paragraph(f'新增演练说明 {i+1}，非真实业务。')
    doc.add_page_break()
    doc.add_heading('第二章 执行安排', level=1)
    table = doc.add_table(rows=1, cols=3)
    for cell, text in zip(table.rows[0].cells, ('序号', '工作', '状态')):
        cell.text = text
    for i in range(65):
        for cell, text in zip(table.add_row().cells, (str(i+1), '虚构工作条目', '待确认')):
            cell.text = text
    doc.save(path)


class RenderBoundaryTests(unittest.TestCase):
    def test_paths_preserve_originals_and_reject_wrong_work_or_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'inputs').mkdir()
            (root / 'outputs').mkdir()
            source = root / 'inputs' / 'fictional.docx'
            source.write_bytes(b'fictional')
            self.assertEqual(prepare_paths(root, source, root / 'outputs' / 'v1')[0], source.resolve())
            for target in (root, root / 'outputs', root / 'elsewhere'):
                with self.assertRaises(ValueError):
                    prepare_paths(root, source, target)
            wrong = root / 'unselected.docx'
            wrong.write_bytes(b'fictional')
            with self.assertRaises(ValueError):
                prepare_paths(root, wrong, root / 'outputs' / 'v1')

    def test_office_preflight_requires_exact_protocol(self):
        with patch('team_file_render.run', return_value=b'wrong'):
            with self.assertRaises(ValueError):
                office_check('/candidate/gateway', 'fictional.docx', b'fictional')

    @unittest.skipUnless(os.name == 'posix', 'process-group cleanup is Linux runtime behavior')
    def test_timeout_kills_transient_process_group(self):
        with tempfile.TemporaryDirectory() as temp:
            pid_file = Path(temp) / 'child.pid'
            started = time.monotonic()
            with self.assertRaises(subprocess.TimeoutExpired):
                run(['/bin/sh', '-c', 'sleep 30 & echo $! > "$1"; wait', 'fixture', str(pid_file)], timeout=.5)
            self.assertLess(time.monotonic() - started, 3)
            status = Path('/proc') / pid_file.read_text().strip() / 'stat'
            for _ in range(100):
                try:
                    state = status.read_text().split(') ')[1]
                except (FileNotFoundError, ProcessLookupError):
                    break  # Reaping can race opening/reading the proc entry.
                if state.startswith('Z'):
                    break
                time.sleep(.01)
            else:
                self.fail('spawned child remains alive after timeout')

    @unittest.skipUnless(os.name == 'posix' and os.geteuid() != 0, 'ordinary Linux worker limits')
    def test_poppler_inherits_limits_before_exec(self):
        probe = '''
import json, resource
from unittest.mock import patch
from team_file_render import preview_worker
with patch('team_file_render.os.execv') as execute:
    preview_worker('/fixture/input.pdf', '/fixture/page')
    assert execute.call_args.args[0] == '/usr/bin/pdftoppm'
    print(json.dumps([resource.getrlimit(key) for key in (resource.RLIMIT_AS, resource.RLIMIT_CPU, resource.RLIMIT_FSIZE, resource.RLIMIT_CORE)]))
'''
        output = subprocess.check_output([sys.executable, '-B', '-c', probe], cwd=Path(__file__).parent)
        self.assertEqual(json.loads(output), [[2 << 30] * 2, [90] * 2, [128 << 20] * 2, [0, 0]])


@unittest.skipUnless(os.environ.get('TEAM_FILES_TEST_GATEWAY'), 'requires matching candidate binary and Linux Office packages')
class ActualRenderTests(unittest.TestCase):
    def test_chinese_slides_and_word_toc_revision(self):
        self.assertNotEqual(os.geteuid(), 0, 'acceptance must use an ordinary identity')
        deny_unix_sockets()
        gateway = os.environ['TEAM_FILES_TEST_GATEWAY']
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'inputs').mkdir()
            (root / 'outputs').mkdir()
            pages = []
            for version in (1, 2):
                source = root / 'inputs' / f'fictional-v{version}.docx'
                fictional_template(source, extra=version == 2)
                original = hashlib.sha256(source.read_bytes()).hexdigest()
                target = root / 'outputs' / f'v{version}'
                result = render(root, source, target, gateway)
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), original)
                reader = PdfReader(target / (source.stem + '.pdf'))
                text = [p.extract_text() for p in reader.pages]
                self.assertIn('第一章', text[0])
                self.assertIn('第二章', text[0])
                self.assertNotIn('Error!', '\n'.join(text))
                self.assertEqual(result['pages'], len(text))
                self.assertTrue((target / (source.stem + '.docx')).is_file())
                with zipfile.ZipFile(target / (source.stem + '.docx')) as package:
                    xml = ET.fromstring(package.read('word/document.xml'))
                    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                    saved_paragraphs = [''.join(p.itertext()) for p in xml.findall('.//w:p', ns)]
                for heading in ('第一章 客户需求', '第二章 执行安排'):
                    actual = next(number for number, page in enumerate(text[1:], 2) if heading in page)
                    entry = re.search(re.escape(heading) + r'\.+\s*(\d+)', text[0])
                    self.assertIsNotNone(entry, 'rendered TOC entry missing')
                    self.assertEqual(int(entry.group(1)), actual, 'TOC points to wrong PDF page')
                    self.assertTrue(any(p.endswith(heading + str(actual)) for p in saved_paragraphs),
                                    'saved DOCX TOC differs from actual page')
                for number, page in enumerate(text, 1):
                    self.assertIn(f'Page {number} of {len(text)}', ' '.join(page.split()))
                pages.append(len(text))
            self.assertGreater(pages[1], pages[0])
            deck = Presentation()
            slide = deck.slides.add_slide(deck.slide_layouts[6])
            shape = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(8), Inches(2))
            shape.text = '虚构婚宴方案：22 桌，预算 101,520 元'
            for paragraph in shape.text_frame.paragraphs:
                for item in paragraph.runs:
                    item.font.name = 'Noto Sans CJK SC'
            source = root / 'inputs' / 'fictional-slides.pptx'
            deck.save(source)
            result = render(root, source, root / 'outputs' / 'slides', gateway)
            self.assertEqual(result['pages'], 1)
            text = PdfReader(root / 'outputs' / 'slides' / 'fictional-slides.pdf').pages[0].extract_text()
            self.assertIn('虚构婚宴', text)
            self.assertIn('101,520', text)
            self.assertEqual(Presentation(source).slides[0].shapes[0].text, shape.text)


@unittest.skipUnless(os.name == 'posix' and os.geteuid() == 0 and os.environ.get('TEAM_FILES_TEST_GATEWAY'),
                     'requires disposable Linux numeric-UID initializer and document packages')
class HandoffRenderTests(unittest.TestCase):
    def test_model_render_and_revision_readable_by_ordinary_gateway_only(self):
        # Root only provisions the fixture; rendering and reading drop all groups
        # except the same restricted handoff group used by the deployed accounts.
        gateway_uid, model_uid, shared_gid = 61000, 61001, 61002
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            root.chmod(0o755)
            work = root / 'work'
            work.mkdir()
            os.chown(work, gateway_uid, shared_gid)
            work.chmod(0o2750)
            for name, mode in (('inputs', 0o2750), ('outputs', 0o2770)):
                path = work / name
                path.mkdir()
                os.chown(path, gateway_uid, shared_gid)
                path.chmod(mode)

            def as_user(uid, script, *args, group=shared_gid):
                return subprocess.run([sys.executable, '-B', '-c', script, str(work), *args],
                                      user=uid, group=group, extra_groups=[], umask=0o077,
                                      cwd=Path(__file__).parent, capture_output=True, text=True, timeout=120)

            made = as_user(model_uid, '''
import json, os, sys
from pathlib import Path
from test_team_file_render import fictional_template, deny_unix_sockets
from team_file_render import render
assert os.geteuid() == 61001
assert 'CapEff:\t0000000000000000' in Path('/proc/self/status').read_text()
deny_unix_sockets()
root = Path(sys.argv[1])
legacy = root / 'outputs' / 'legacy-private'
legacy.mkdir(mode=0o700)
(legacy / 'result').write_text('fictional')
for version in (1, 2):
    source = root / 'outputs' / f'source-v{version}.docx'
    fictional_template(source, extra=version == 2)
    render(root, source, root / 'outputs' / f'v{version}', os.environ['TEAM_FILES_TEST_GATEWAY'])
''')
            self.assertEqual(made.returncode, 0, made.stderr)
            checked = as_user(gateway_uid, '''
import hashlib, json, os, sys
from pathlib import Path
assert os.geteuid() == 61000
assert 'CapEff:\t0000000000000000' in Path('/proc/self/status').read_text()
root = Path(sys.argv[1]) / 'outputs'
try:
    (root / 'legacy-private' / 'result').read_bytes()
except PermissionError:
    pass
else:
    raise AssertionError('ordinary host bypassed old private output')
pages = []
for version in (1, 2):
    target = root / f'v{version}'
    record = json.loads((target / 'render.json').read_text())
    for name, digest in record['files'].items():
        path = target / name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        assert path.stat().st_uid == 61001 and path.stat().st_gid == 61002
        assert path.stat().st_mode & 0o777 == 0o640
    pages.append(record['pages'])
assert pages[1] > pages[0]
print(json.dumps(pages))
''')
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertGreater(json.loads(checked.stdout)[1], json.loads(checked.stdout)[0])
            denied = as_user(61003, 'from pathlib import Path; import sys; (Path(sys.argv[1]) / "outputs/v1/render.json").read_bytes()', group=61003)
            self.assertNotEqual(denied.returncode, 0)
            self.assertIn('PermissionError', denied.stderr)


if __name__ == '__main__':
    unittest.main()
