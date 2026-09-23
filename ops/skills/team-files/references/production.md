# Document production and paired revisions

Use only the current work's selected originals and output directory. Keep material
source/version beside the facts it supports. Business calculations and confirmed
versus proposed states belong to `team-banquet`; apply its saved-file readback.

## Read materials

Use `python-docx` for Word, `openpyxl` for Excel, `python-pptx` for slides and
`pypdf` for PDF structure/text. For scanned pages, render the original PDF with
the installed tool below, then read the resulting page images. State which
figures remain illegible and need verification. Preserve the original PDF;
extracted text does not preserve its layout and is not an editable replacement.
Native Feishu images appear in `work-context.inputs`, with saved paths and hashes.
An attachment mentioned inside a document is not an attachment you have read.
If its original is absent, cite it as that document's reference, not as inspected
or reused material. Label a newly drawn illustration as your own concept drawing.

## Make the editable originals

- Create PPTX with `python-pptx`: real text boxes, shapes, tables and pictures.
  Prices, captions and main layout shapes must stay editable. Use shapes/tables
  for the first charts; embedded chart workbooks are not supported.
- Make a poster as a single-slide PPTX master. Export its PDF and PNG preview;
  deliver the editable master alongside the PNG. Use Pillow for cropping, code
  drawing and composition of selected materials. Existing photos need their
  source; drawings/style boards must say “概念示意”, not “场馆实拍”.
- Use `python-docx` for Word templates. Preserve headers/footers, table structure
  and supported fields. Apply heading styles for a TOC. Unknown fields require
  explaining the compatibility gap; silently deleting or flattening them is not
  a successful template round trip. Complex real templates remain individually
  unverified until actually opened and checked.
- Use `openpyxl` or `XlsxWriter` for the editable budget. Store assumptions,
  sources, selected items and pending decisions in the workbook itself.

## Update, render, inspect

Keep the managed workspace as the shell's working directory. Use absolute paths
from the current work context; file preparation needs no `cd` or temporary
extraction directory. Run the installed helper as one command:

```sh
/opt/team-files/bin/python /usr/local/libexec/team_file_render.py \
  --work-root '<current work root: parent of output_dir>' \
  --input '<selected DOCX, PPTX or PDF path>' \
  --output-dir '<output_dir/new unique render directory>'
```

Inspect its returned files in separate permitted read calls. Do not append
directory switches, relative `ls` probes or other shell diagnostics to this
command: compound commands can require a native permission exception even when
the renderer itself is permitted. This guidance grants no additional permission;
if an operation is denied, preserve the stop rule and report the unfinished step.

Let the helper create the new render directory; pass a path that does not yet
exist. If it reports an existing output directory, preserve that directory and
choose a new name; this input error does not require broader permissions.

The helper validates Office content through the existing gateway binary before
conversion. For DOCX it refreshes fields and indexes, saves a new editable DOCX,
then exports PDF. PPTX exports PDF without flattening or replacing its editable
original. PDF input is retained unchanged. Every PDF page receives a PNG preview;
`render.json` records hashes and page count. It deliberately says
`rendered_not_visually_verified`: this is preparation, not acceptance.

Open every page/slide preview. Fix missing Chinese glyphs, clipped text, overflow,
overlaps, distortion and inconsistent spacing/style; rerender after changes.
Check poster prices and small-print legibility. Inspect saved PPTX text/shapes to
confirm editability. For Word, compare the saved DOCX's TOC entries, page fields
and total pages with the exported PDF after added content moves headings. A
successful export alone is not proof of correct pagination. Inspect the reopened
Excel's formulas, rows and totals as well as the slide/Word/PDF summary amounts.

If installed tools or fonts are missing, preserve the prepared originals and
report the missing runtime capability. Do not install packages or substitute a
different model/provider from inside an employee task.

## Revise the set and deliver

On a changed table count, package or visual style, list all affected outputs,
revise their editable sources, then regenerate dependent PDFs/PNGs. Compare
amounts, table counts, selected items, status and source versions across the saved
set. Preserve earlier files; write revisions under new names/directories.
An imported colleague's artifact is the selected source, not access to their
private history. Ask for an absent editable original when required for revision.

Deliver through the existing `file-deliver` protocol only after readback and
visual inspection. Refresh `latest_version` between file deliveries. Keep the
set's revision label in each filename/content so PPT, PDF, poster and budget can
be identified together; no new manifest or task platform is required. If a send
becomes unknown, stop further delivery and reconcile its receipt before sending
another member of the set. Do not send previews or `render.json` as business
deliverables unless requested.
