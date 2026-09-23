#!/opt/team-files/bin/python -I
"""Host PDF boundary: bounded stdin, no paths/network, fixed success token.

Install this file as a host-owned executable in a protected directory. The
gateway passes snapshot bytes through stdin and applies its own wall timeout.
This checks structure/content policy, not visual quality or business facts.
"""
import io
import sys

MAX_BYTES = 20 << 20
MAX_EXPANDED = 100 << 20
MAX_PAGES = 200
FORBIDDEN = frozenset({
    '/AA', '/OpenAction', '/JS', '/JavaScript', '/EmbeddedFiles', '/EF',
    '/AcroForm', '/XFA', '/RichMedia', '/RichMediaContent', '/Launch',
    '/GoToR', '/GoToE', '/SubmitForm', '/ImportData', '/Rendition',
    '/Sound', '/Movie', '/3D', '/Filespec', '/URI',
})


def validate_pdf(data):
    from pypdf import PdfReader
    from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject, StreamObject

    if not 0 < len(data) <= MAX_BYTES or not data.startswith(b'%PDF-'):
        raise ValueError('invalid PDF size/header')
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted or not 0 < len(reader.pages) <= MAX_PAGES:
        raise ValueError('encrypted or unsupported page count')
    pending, seen = [(reader.trailer, 0)], set()
    expanded = nodes = 0
    while pending:
        obj, depth = pending.pop()
        nodes += 1
        if nodes > 200_000 or depth > 128:
            raise ValueError('PDF structure budget exceeded')
        if isinstance(obj, IndirectObject):
            key = (obj.idnum, obj.generation)
            if key in seen:
                continue
            seen.add(key)
            obj = obj.get_object()
            if obj is None:
                raise ValueError('unresolved PDF object')
        if isinstance(obj, NameObject) and obj in FORBIDDEN:
            raise ValueError('active or external PDF content')
        if isinstance(obj, DictionaryObject):
            if FORBIDDEN.intersection(obj):
                raise ValueError('active or external PDF content')
            if '/S' in obj and obj['/S'] in ('/GoToR', '/GoToE', '/Launch', '/JavaScript', '/URI', '/SubmitForm', '/ImportData', '/Rendition'):
                raise ValueError('unsupported PDF action')
            if isinstance(obj, StreamObject):
                if '/F' in obj or '/FFilter' in obj:
                    raise ValueError('external PDF stream')
                expanded += len(obj.get_data())
                if expanded > MAX_EXPANDED:
                    raise ValueError('PDF stream budget exceeded')
            pending.extend((value, depth + 1) for value in obj.values())
        elif isinstance(obj, ArrayObject):
            pending.extend((value, depth + 1) for value in obj)
    # Force parsing page content operators as well as the object graph.
    for page in reader.pages:
        box = page.mediabox
        if not 0 < float(box.width) <= 14400 or not 0 < float(box.height) <= 14400:
            raise ValueError('unsupported PDF page dimensions')
        content = page.get_contents()
        if content is not None:
            _ = content.operations
    return len(reader.pages)


def main():
    # Limits precede parser import/decompression. The production host is Linux.
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (512 << 20, 512 << 20))
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if len(sys.argv) != 1:
        return 2
    try:
        validate_pdf(sys.stdin.buffer.read(MAX_BYTES + 1))
    except Exception:
        # Never put received document content in host or CI logs.
        return 1
    sys.stdout.write('PDF_OK_V1\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
