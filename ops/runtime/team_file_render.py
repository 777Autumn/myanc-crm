#!/opt/team-files/bin/python -I
"""One-shot ordinary-user Office update/export and PDF page previews.

The gateway's shared Office validator runs before LibreOffice; the PDF boundary
runs before Poppler. No receiver, network listener, delivery or dependency setup.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import uuid

MAX_BYTES = 20 << 20


def run(command, *, data=None, timeout=30, env=None):
    proc = subprocess.Popen(command, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            env=env, start_new_session=True)
    try:
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
    if not target.is_relative_to(outputs) or target == outputs or target.exists():
        raise ValueError('output must be a new directory inside current work outputs')
    if source.suffix.lower() not in ('.docx', '.pptx', '.pdf') or not source.is_file() or not 0 < source.stat().st_size <= MAX_BYTES:
        raise ValueError('unsupported input format/size')
    return source, target, outputs


def render(work_root, source, destination, gateway):
    if os.name != 'posix' or os.geteuid() == 0:
        raise ValueError('render as the ordinary employee runtime account on Linux')
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
    target.mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(prefix='.render-', dir=outputs) as scratch_name:
        scratch = Path(scratch_name)
        frozen = scratch / ('source' + source.suffix.lower())
        frozen.write_bytes(data)
        frozen.chmod(0o600)
        pdf = target / (source.stem + '.pdf')
        if office:
            env = {'HOME': str(scratch), 'TMPDIR': str(scratch), 'LANG': 'C.UTF-8', 'PATH': '/usr/bin:/bin', 'SAL_USE_VCLPLUGIN': 'svp'}
            run(['/usr/bin/python3', '-I', str(Path(__file__).resolve()), '--office-worker',
                 str(frozen), str(target), source.stem, str(scratch)], timeout=120, env=env)
            updated = target / (source.stem + '.docx')
            if source.suffix.lower() == '.docx':
                office_check(gateway, updated.name, updated.read_bytes())
        else:
            pdf.write_bytes(data)
        pdf_check(pdf.read_bytes())
        run(['/usr/bin/python3', '-I', str(Path(__file__).resolve()), '--preview-worker',
             str(pdf), str(target / 'page')], timeout=120)
    from pypdf import PdfReader
    page_count = len(PdfReader(pdf).pages)
    previews = sorted(target.glob('page-*.png'))
    if len(previews) != page_count:
        raise RuntimeError('not every PDF page has a preview')
    result = {'status': 'rendered_not_visually_verified', 'source_sha256': hashlib.sha256(data).hexdigest(),
              'pages': page_count, 'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                           for p in sorted(target.iterdir()) if p.is_file()}}
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
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    resource.setrlimit(resource.RLIMIT_FSIZE, (128 << 20, 128 << 20))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def preview_worker(pdf, prefix):
    worker_limits()
    os.execv('/usr/bin/pdftoppm', ['pdftoppm', '-png', '-r', '100', '-scale-to', '1800', pdf, prefix])


def office_worker(source, destination, stem, scratch):
    worker_limits()
    import uno
    from com.sun.star.beans import PropertyValue
    from com.sun.star.document.MacroExecMode import NEVER_EXECUTE
    from com.sun.star.document.UpdateDocMode import NO_UPDATE

    source, target, scratch = Path(source), Path(destination), Path(scratch)
    pipe = 'teamfiles_' + uuid.uuid4().hex
    profile = (scratch / 'profile').as_uri()
    process = subprocess.Popen(['/usr/bin/soffice', '-env:UserInstallation=' + profile,
                                '--headless', '--invisible', '--nodefault', '--norestore', '--nofirststartwizard',
                                '--accept=pipe,name=' + pipe + ';urp;StarOffice.ComponentContext'],
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def props(**values):
        result = []
        for name, value in values.items():
            item = PropertyValue()
            item.Name, item.Value = name, value
            result.append(item)
        return tuple(result)

    doc = None
    try:
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', local)
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError('LibreOffice exited during startup')
            try:
                context = resolver.resolve('uno:pipe,name=' + pipe + ';urp;StarOffice.ComponentContext')
                break
            except Exception:
                time.sleep(.1)
        else:
            raise RuntimeError('LibreOffice startup timeout')
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
        else:
            pdf_filter = 'impress_pdf_Export'
        doc.storeToURL((target / (stem + '.pdf')).as_uri(), props(FilterName=pdf_filter, Overwrite=False))
        doc.close(True)
        doc = None
        desktop.terminate()
        process.wait(timeout=10)
    finally:
        if doc is not None:
            doc.dispose()
        if process.poll() is None:
            process.kill()
        process.wait()


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
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        parser.exit(1, 'Document preparation failed; originals retained. No delivery was attempted.\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
