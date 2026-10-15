"""Actual PNG transformation contract; no OCR or claimed visual understanding."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image
import team_file_render


class SourcePageDetailsTests(unittest.TestCase):
    def test_source_page_views_preserve_pixels_and_cover_every_edge(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / 'page-02.png'
            # Every row has distinct pixels; header/body/footer mistakes are visible.
            image = Image.new('RGB', (30, 101))
            image.putdata([(x, y, (x + y) % 256) for y in range(101) for x in range(30)])
            image.save(source)
            before = source.read_bytes()
            result = team_file_render.source_page_details(source)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(result['page'], 2)
            self.assertEqual(result['page_file'], source.name)
            self.assertEqual(result['page_sha256'], hashlib.sha256(before).hexdigest())
            self.assertEqual(result['size'], [30, 101])
            self.assertEqual([part['box'] for part in result['regions']],
                             [[0, 0, 30, 41], [0, 30, 30, 71], [0, 60, 30, 101]])
            covered = set()
            for part in result['regions']:
                saved = root / part['file']
                self.assertFalse(saved.name.startswith('page-'))
                self.assertEqual(hashlib.sha256(saved.read_bytes()).hexdigest(), part['sha256'])
                left, top, right, bottom = part['box']
                covered.update(range(top, bottom))
                with Image.open(saved) as detail:
                    self.assertEqual(detail.size, (right - left, bottom - top))
                    self.assertEqual(detail.tobytes(), image.crop(tuple(part['box'])).tobytes())
            self.assertEqual(covered, set(range(101)))
            self.assertEqual(len(list(root.glob('page-*.png'))), 1)
            image.close()

    def test_tiny_and_landscape_pages_keep_complete_pixels(self):
        for size in [(1, 1), (1800, 7)]:
            with self.subTest(size=size), tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary) / 'page-1.png'
                with Image.new('RGB', size, 'navy') as image:
                    image.save(source)
                result = team_file_render.source_page_details(source)
                covered = set()
                for part in result['regions']:
                    box = part['box']
                    self.assertEqual((box[0], box[2]), (0, size[0]))
                    self.assertTrue(0 <= box[1] < box[3] <= size[1])
                    covered.update(range(box[1], box[3]))
                self.assertEqual(covered, set(range(size[1])))

    def test_invalid_source_preview_never_creates_detail_files(self):
        for name, size, fmt in [('page-0.png', (30, 101), 'PNG'),
                                ('page-201.png', (30, 101), 'PNG'),
                                ('other.png', (30, 101), 'PNG'),
                                ('page-1.png', (1801, 10), 'PNG'),
                                ('page-1.png', (10, 1801), 'PNG'),
                                ('page-1.png', (30, 101), 'JPEG')]:
            with self.subTest(name=name, size=size, fmt=fmt), tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary) / name
                with Image.new('RGB', size) as image:
                    image.save(source, format=fmt)
                before = source.read_bytes()
                with self.assertRaises(ValueError):
                    team_file_render.source_page_details(source)
                self.assertEqual(source.read_bytes(), before)
                self.assertFalse(list(Path(temporary).glob('detail-*.png')))

    def test_existing_detail_is_preserved_on_retry(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'page-1.png'
            with Image.new('RGB', (30, 101)) as image:
                image.save(source)
            result = team_file_render.source_page_details(source)
            before = {part['file']: (source.parent / part['file']).read_bytes()
                      for part in result['regions']}
            with self.assertRaises(FileExistsError):
                team_file_render.source_page_details(source)
            self.assertEqual(before, {name: (source.parent / name).read_bytes() for name in before})

    @unittest.skipUnless(os.name == 'posix', 'POSIX symbolic link boundary')
    def test_symbolic_source_preview_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with Image.new('RGB', (30, 101)) as image:
                image.save(root / 'actual.png')
            (root / 'page-1.png').symlink_to(root / 'actual.png')
            with self.assertRaises(ValueError):
                team_file_render.source_page_details(root / 'page-1.png')
            self.assertFalse(list(root.glob('detail-*.png')))


@unittest.skipUnless(os.name == 'posix' and os.geteuid() != 0 and
                     Path('/opt/homebrew/bin/pdftoppm' if sys.platform == 'darwin'
                          else '/usr/bin/pdftoppm').is_file(),
                     'requires ordinary native runtime with installed Poppler')
class SourcePdfRenderTests(unittest.TestCase):
    def test_actual_cli_preserves_pdf_pages_and_hashes_all_detail_views(self):
        from pypdf import PdfWriter
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / 'inputs').mkdir()
            (root / 'outputs').mkdir()
            source = root / 'inputs' / 'fictional-source.pdf'
            writer = PdfWriter()
            writer.add_blank_page(300, 400)
            writer.add_blank_page(400, 300)
            with source.open('wb') as stream:
                writer.write(stream)
            before = source.read_bytes()
            target = root / 'outputs' / 'review'
            result = subprocess.run([sys.executable, '-B', str(Path(team_file_render.__file__).resolve()),
                                     '--work-root', str(root), '--input', str(source),
                                     '--output-dir', str(target)], capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            receipt = json.loads(result.stdout)
            manifest = json.loads(Path(receipt['manifest']).read_text(encoding='utf-8'))
            self.assertEqual(receipt['source_detail_views'], 6)
            self.assertEqual(receipt['files'], [str(target / source.name)])
            self.assertEqual(manifest['status'], 'rendered_not_visually_verified')
            self.assertEqual(manifest['pages'], 2)
            self.assertEqual([page['page'] for page in manifest['source_details']], [1, 2])
            self.assertEqual(len(list(target.glob('page-*.png'))), 2)
            self.assertEqual(len(list(target.glob('detail-*.png'))), 6)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(manifest['source_sha256'], hashlib.sha256(before).hexdigest())
            for name, digest in manifest['files'].items():
                self.assertEqual(hashlib.sha256((target / name).read_bytes()).hexdigest(), digest)
                self.assertEqual((target / name).stat().st_mode & 0o777, 0o640)
            for page in manifest['source_details']:
                self.assertEqual(manifest['files'][page['page_file']], page['page_sha256'])
                for region in page['regions']:
                    self.assertEqual(manifest['files'][region['file']], region['sha256'])


if __name__ == '__main__':
    unittest.main()
