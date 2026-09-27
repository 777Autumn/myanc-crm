#!/opt/team-files/bin/python -I
"""One-shot ordinary-user Office update/export and PDF page previews.

The gateway's shared Office validator runs before LibreOffice; the PDF boundary
runs before Poppler. No receiver, network listener, delivery or dependency setup.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import posixpath
import signal
import subprocess
import sys
import tempfile
import time
import zipfile
import xml.etree.ElementTree as ET

MAX_BYTES = 20 << 20


def xlsx_cells(data):
    """Read saved cell types/caches without evaluating or expanding sheet ranges.

    Call only after the gateway has bounded and validated this OOXML package.
    """
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    relation_ns = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    cells = {}
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        links = {node.attrib['Id']: posixpath.normpath(posixpath.join('xl', node.attrib['Target'])).lstrip('/')
                 for node in ET.fromstring(package.read('xl/_rels/workbook.xml.rels'))}
        sheets = {links[node.attrib[f'{{{relation_ns}}}id']]: node.attrib['name']
                  for node in ET.fromstring(package.read('xl/workbook.xml')).findall('s:sheets/s:sheet', ns)}
        strings = []
        if 'xl/sharedStrings.xml' in package.namelist():
            strings = [''.join(node.itertext()) for node in
                       ET.fromstring(package.read('xl/sharedStrings.xml')).findall('s:si', ns)]
        for name, title in sheets.items():
            for cell in ET.fromstring(package.read(name)).findall('s:sheetData/s:row/s:c', ns):
                value, formula = cell.find('s:v', ns), cell.find('s:f', ns)
                kind = cell.get('t', 'n')
                text = value.text if value is not None else None
                if kind == 's':
                    text = strings[int(text)]
                elif kind == 'inlineStr':
                    inline = cell.find('s:is', ns)
                    text = ''.join(inline.itertext()) if inline is not None else ''
                key = f'{title}!{cell.attrib["r"]}'
                if key in cells:
                    raise ValueError('duplicate workbook cell')
                cells[key] = {'formula': formula.text if formula is not None else None,
                              'is_formula': formula is not None, 'type': kind, 'value': text,
                              'cached': value is not None and (text is not None or kind == 'str')}
    return cells


def check_xlsx_result(before, data):
    after = xlsx_cells(data)
    formulas = {key: cell['formula'] for key, cell in before.items() if cell['is_formula']}
    saved = {key: cell['formula'] for key, cell in after.items() if cell['is_formula']}
    if formulas != saved:
        raise ValueError('saved workbook formulas changed; inspect the retained source')
    if any(cell['type'] == 'e' or (cell['is_formula'] and not cell['cached']) for cell in after.values()):
        raise ValueError('saved workbook contains an error or an uncalculated formula')
    # Only task intent distinguishes explanatory text from a formula saved as text.
    # Report the actual type; never silently convert either kind into a formula.
    text_cells = [key for key, cell in after.items() if not cell['is_formula']
                  and isinstance(cell['value'], str) and cell['value'].startswith('=')]
    for key, cell in before.items():
        if not cell['is_formula'] and isinstance(cell['value'], str) and cell['value'].startswith('='):
            if key not in after or after[key]['is_formula'] or after[key]['value'] != cell['value']:
                raise ValueError('saved workbook changed an equals-prefixed text cell')
    return {'formula_cells': sorted(formulas), 'formula_count': len(formulas),
            'formula_caches_checked': True, 'equals_text_cells': text_cells,
            'equals_text_requires_task_review': bool(text_cells)}


def run(command, *, data=None, timeout=30, env=None, memory_limit=2 << 30):
    proc = subprocess.Popen(command, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            env=env, start_new_session=True)
    try:
        if sys.platform == 'darwin':
            # macOS rejects RLIMIT_AS. Bound the whole one-shot process group
            # by sampled RSS instead; this is not a hard allocation ceiling.
            deadline = time.monotonic() + timeout
            first = True
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(command, timeout)
                try:
                    stdout, _ = proc.communicate(data if first else None, timeout=min(.1, remaining))
                    break
                except subprocess.TimeoutExpired:
                    first = False
                    usage = subprocess.check_output(['/bin/ps', '-axo', 'pgid=,rss='], timeout=2)
                    members = [int(rss) * 1024 for group, rss in
                               (line.split() for line in usage.splitlines()) if int(group) == proc.pid]
                    if not members and proc.poll() is None:
                        raise RuntimeError('document process accounting unavailable')
                    resident = sum(members)
                    if resident > memory_limit:
                        raise RuntimeError('document process group exceeded memory budget')
        else:
            stdout, _ = proc.communicate(data, timeout=timeout)
        if proc.returncode:
            raise RuntimeError('document tool failed; preserve original and inspect runtime')
        return stdout
    finally:
        # Includes the transient LibreOffice process if its worker timed out.
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        if proc.stdout is not None:
            proc.stdout.close()
        if proc.stdin is not None:
            proc.stdin.close()


def office_check(gateway, name, data):
    if run([str(gateway), 'file-check', name], data=data) != b'OFFICE_OK_V1\n':
        raise ValueError('Office preflight failed')


def pdf_check(data):
    tool = Path(__file__).with_name('team_file_pdf.py')
    if run([sys.executable, '-I', str(tool)], data=data, timeout=15) != b'PDF_OK_V1\n':
        raise ValueError('PDF preflight failed')


def prepare_paths(work_root, source, destination):
    root = Path(work_root).resolve(strict=True)
    source = Path(source).resolve(strict=True)
    outputs = root / 'outputs'
    if not outputs.is_dir() or outputs.is_symlink() or not (root / 'inputs').is_dir():
        raise ValueError('use the current work context directories')
    if not any(source.is_relative_to(root / name) for name in ('inputs', 'outputs')):
        raise ValueError('input is outside current work')
    target = Path(destination).resolve()
    if not target.is_relative_to(outputs) or target == outputs:
        raise ValueError('output must be a new directory inside current work outputs')
    if target.exists():
        raise FileExistsError('render destination already exists')
    if source.suffix.lower() not in ('.docx', '.pptx', '.xlsx', '.pdf') or not source.is_file() or not 0 < source.stat().st_size <= MAX_BYTES:
        raise ValueError('unsupported input format/size')
    return source, target, outputs


def render(work_root, source, destination, gateway):
    if os.name != 'posix' or os.geteuid() == 0:
        raise ValueError('render as the ordinary employee runtime account')
    source, target, outputs = prepare_paths(work_root, source, destination)
    with source.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if not 0 < len(data) <= MAX_BYTES:
        raise ValueError('input size changed')
    office = source.suffix.lower() != '.pdf'
    if office:
        office_check(gateway, source.name, data)
    else:
        pdf_check(data)
    spreadsheet = source.suffix.lower() == '.xlsx'
    before = xlsx_cells(data) if spreadsheet else None
    target.mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(prefix='.render-', dir=outputs) as scratch_name:
        scratch = Path(scratch_name)
        frozen = scratch / ('source' + source.suffix.lower())
        frozen.write_bytes(data)
        frozen.chmod(0o600)
        pdf = target / (source.stem + '.pdf')
        if office:
            env = {'HOME': str(scratch), 'TMPDIR': str(scratch), 'LANG': 'C.UTF-8', 'PATH': '/usr/bin:/bin', 'SAL_USE_VCLPLUGIN': 'svp'}
            if spreadsheet:
                # Bound Calc's import pool on many-core hosts under the same 2 GiB
                # worker limit; do not relax the sandbox or start an Office server.
                env['MAX_CONCURRENCY'] = '1'
            worker_python = sys.executable if sys.platform == 'darwin' else '/usr/bin/python3'
            run([worker_python, '-I', str(Path(__file__).resolve()), '--office-worker',
                 str(frozen), str(target), source.stem, str(scratch)], timeout=120, env=env)
            updated = target / (source.stem + '.docx')
            if source.suffix.lower() == '.docx':
                office_check(gateway, updated.name, updated.read_bytes())
            if spreadsheet:
                updated = target / (source.stem + '.xlsx')
                updated_data = updated.read_bytes()
                office_check(gateway, updated.name, updated_data)
                xlsx_result = check_xlsx_result(before, updated_data)
        else:
            pdf.write_bytes(data)
        pdf_check(pdf.read_bytes())
        preview_python = sys.executable if sys.platform == 'darwin' else '/usr/bin/python3'
        run([preview_python, '-I', str(Path(__file__).resolve()), '--preview-worker',
             str(pdf), str(target / 'page')], timeout=120)
    from pypdf import PdfReader
    page_count = len(PdfReader(pdf).pages)
    previews = sorted(target.glob('page-*.png'))
    if len(previews) != page_count:
        raise RuntimeError('not every PDF page has a preview')
    result = {'status': 'rendered_not_visually_verified', 'source_sha256': hashlib.sha256(data).hexdigest(),
              'pages': page_count, 'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                           for p in sorted(target.iterdir()) if p.is_file()}}
    if spreadsheet:
        result['xlsx'] = xlsx_result
    (target / 'render.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # The setgid outputs directory supplies the existing model/host handoff
    # group. Override service umask only on completed artifacts, never scratch.
    for path in target.iterdir():
        path.chmod(0o640)
    target.chmod(0o2750)
    return result


def worker_limits():
    import resource
    if os.geteuid() == 0:
        raise ValueError('ordinary identity required')
    if sys.platform != 'darwin':
        resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    resource.setrlimit(resource.RLIMIT_FSIZE, (128 << 20, 128 << 20))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def preview_worker(pdf, prefix):
    worker_limits()
    binary = '/opt/homebrew/bin/pdftoppm' if sys.platform == 'darwin' else '/usr/bin/pdftoppm'
    os.execv(binary, ['pdftoppm', '-png', '-r', '100', '-scale-to', '1800', pdf, prefix])


def office_worker(source, destination, stem, scratch):
    worker_limits()
    if sys.platform == 'darwin':
        # Signed macOS helpers cannot be launched from an external shell.
        # Run only our fixed script inside the signed Office process, with a
        # private one-shot profile. Received document macros remain disabled.
        profile = Path(scratch) / 'profile'
        scripts = profile / 'user/Scripts/python'
        scripts.mkdir(parents=True, mode=0o700)
        (scripts / 'anc_render.py').write_bytes(Path(__file__).read_bytes())
        (scripts / 'job.json').write_text(json.dumps([source, destination, stem]), encoding='utf-8')
        binary = '/Applications/LibreOffice.app/Contents/MacOS/soffice'
        os.execv(binary, [binary, '--headless', '--nologo', '--nodefault', '--norestore',
                         '-env:UserInstallation=' + profile.as_uri(),
                         'vnd.sun.star.script:anc_render.py$mac_office_job?language=Python&location=user'])
        return
    import ctypes as c

    # The installed LibreOfficeKit initializes Office in this worker. Claude's
    # Linux sandbox blocks AF_UNIX, including soffice's startup and UNO pipes.
    # Use the public stable ABI prefix; keep the existing in-process UNO methods.
    class OfficeClass(c.Structure):
        _fields_ = [('size', c.c_size_t), ('destroy', c.CFUNCTYPE(None, c.c_void_p))]

    class Office(c.Structure):
        _fields_ = [('methods', c.POINTER(OfficeClass))]

    source, target, scratch = Path(source), Path(destination), Path(scratch)
    library = c.CDLL('/usr/lib/libreoffice/program/libmergedlo.so')
    library.libreofficekit_hook_2.argtypes = [c.c_char_p, c.c_char_p]
    library.libreofficekit_hook_2.restype = c.POINTER(Office)
    office = library.libreofficekit_hook_2(b'/usr/lib/libreoffice/program', (scratch / 'profile').as_uri().encode())
    if not office or office.contents.methods.contents.size < c.sizeof(OfficeClass):
        raise RuntimeError('LibreOffice initialization failed')

    try:
        office_update(source, target, stem)
    finally:
        office.contents.methods.contents.destroy(office)


def mac_office_job(*_args):
    import uno
    # LibreOffice's script provider supplies a file URL, not a filesystem path.
    script = Path(uno.fileUrlToSystemPath(__file__))
    source, destination, stem = json.loads(script.with_name('job.json').read_text(encoding='utf-8'))
    office_update(source, destination, stem)


g_exportedScripts = (mac_office_job,)


def office_update(source, destination, stem):
    source, target = Path(source), Path(destination)

    import uno
    from com.sun.star.beans import PropertyValue
    from com.sun.star.document.MacroExecMode import NEVER_EXECUTE
    from com.sun.star.document.UpdateDocMode import NO_UPDATE

    def props(**values):
        result = []
        for name, value in values.items():
            item = PropertyValue()
            item.Name, item.Value = name, value
            result.append(item)
        return tuple(result)

    doc = None
    try:
        context = uno.getComponentContext()
        desktop = context.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop', context)
        doc = desktop.loadComponentFromURL(source.as_uri(), '_blank', 0,
                                          props(Hidden=True, ReadOnly=False, MacroExecutionMode=NEVER_EXECUTE, UpdateDocMode=NO_UPDATE))
        if doc is None:
            raise RuntimeError('LibreOffice did not load document')
        if source.suffix == '.docx':
            # Index insertion changes pagination. Reflow, refresh fields and
            # update indexes again before saving the editable Word result.
            for _ in range(2):
                doc.refresh()
                doc.getTextFields().refresh()
                indexes = doc.getDocumentIndexes()
                for index in range(indexes.getCount()):
                    indexes.getByIndex(index).update()
            doc.storeAsURL((target / (stem + '.docx')).as_uri(), props(FilterName='Office Open XML Text', Overwrite=False))
            pdf_filter = 'writer_pdf_Export'
        elif source.suffix == '.xlsx':
            doc.calculateAll()
            doc.storeAsURL((target / (stem + '.xlsx')).as_uri(),
                           props(FilterName='Calc MS Excel 2007 XML', Overwrite=False))
            pdf_filter = 'calc_pdf_Export'
        else:
            pdf_filter = 'impress_pdf_Export'
        doc.storeToURL((target / (stem + '.pdf')).as_uri(), props(FilterName=pdf_filter, Overwrite=False))
        doc.close(True)
        doc = None
    finally:
        if doc is not None:
            doc.dispose()


def main():
    if len(sys.argv) == 6 and sys.argv[1] == '--office-worker':
        office_worker(*sys.argv[2:])
        return
    if len(sys.argv) == 4 and sys.argv[1] == '--preview-worker':
        preview_worker(*sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work-root', required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--gateway', default='/usr/local/bin/cc-connect-anc', help='matching candidate binary; local validation only')
    args = parser.parse_args()
    try:
        result = render(args.work_root, args.input, args.output_dir, args.gateway)
    except FileExistsError:
        parser.exit(1, 'Output directory already exists; preserve it and choose a new directory name '
                    'inside this work outputs; do not create it beforehand. No delivery was attempted.\n')
    except (OSError, ValueError, RuntimeError, KeyError, IndexError, TypeError,
            zipfile.BadZipFile, ET.ParseError, subprocess.SubprocessError):
        parser.exit(1, 'Document preparation failed; originals retained. No delivery was attempted.\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
