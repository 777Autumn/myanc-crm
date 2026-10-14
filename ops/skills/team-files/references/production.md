# Document production and paired revisions

Use only the current work's selected originals and output directory. Keep material
source/version beside the facts it supports. Business calculations and confirmed
versus proposed states belong to `team-banquet`; apply its saved-file readback.

## Read materials

Use `python-docx` for Word, `openpyxl` for Excel, `python-pptx` for slides and
`pypdf` for PDF structure/text. For scanned pages or extraction with garbled,
misordered, missing or otherwise unreadable text, render the selected original
PDF with the installed tool below and visually read the affected page images
before answering, including read-only requests. If affected pages cannot be
identified, inspect every page. Use `render.json` to reconcile page coverage;
rendering alone does not complete reading. Inspection previews stay inside this
work and need no new business delivery or approval. If the supported render/read
actually fails or permission is denied, preserve the evidence and stop under the
existing rules; report the affected pages and remaining uncertainty. State which
figures remain illegible after inspection and need verification. Preserve the original PDF;
extracted text does not preserve its layout and is not an editable replacement.
Native Feishu images appear in `work-context.inputs`, with saved paths and hashes.

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
  Generate XLSX first, then use the installed helper below to recalculate it and
  export its companion PDF through LibreOffice. This workflow does not require
  `reportlab`; do not add an unrelated PDF-library import as a prerequisite.
  Diagnose unavailable conversion from the supported workflow's actual error,
  while preserving the existing permission-denial stop rule and no-install rule.
  Write explanations as text (`write_string`, or an explicit string cell type),
  especially text beginning with `=`. Use formulas only for actual calculations;
  preserve valid formulas when revising an imported workbook.
  For a new budget, put a short business title on its own row and retain long
  source/test identifiers on a separate wrapped row. Set wrap and sufficient
  row height explicitly for merged titles. Set column widths, orientation,
  repeated headers and one pagination strategy before the first render; check
  these on every sheet, including summaries. Preserve required source identifiers.
  For long detail tables, budget the printable page height against repeated title
  rows and body row heights; oversized repeated headings can double the page count.
  Keep body text readable while adjusting margins and row heights to the requested
  page range, then verify the actual exported pages.

## Update, render, inspect

Keep the managed workspace as the shell's working directory. Use absolute paths
from the current work context; file preparation needs no `cd` or temporary
extraction directory. Run the installed helper as one command:

```sh
/opt/team-files/bin/python /usr/local/libexec/team_file_render.py \
  --work-root '<current work root: parent of output_dir>' \
  --input '<selected DOCX, XLSX, PPTX or PDF path>' \
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

On macOS, convert files within the same work one at a time. Wait for each
converter to finish before starting the next; the work has one protected Office
profile. On the pinned Mac runtime, call `exec_command` and `write_stdin` directly;
they are unavailable inside JavaScript `functions.exec` wrappers. In Codex,
retain the full `exec_command` result, including `session_id`
and `exit_code`, instead of returning only `output`. A returned `session_id`
means the command is still running: wait on that same session with `write_stdin`
until it exits, then check the result and `render.json` before inspecting pages.
An empty output alone means neither completion nor failure. After interrupted
observation, check the existing conversion's result before starting another.
A busy or stale profile is a stop condition, not permission to delete
its lock or bypass the helper. This does not serialize different employees' work.
On a failed Mac conversion, preserve any `office-parent-failure.json` and
`office-worker-failure.json` inside the retained private profile. These contain
only bounded stage/type fields, the parent's exit code observed before cleanup
(possibly unknown), and a separate cleanup error type. Missing diagnostics do
not prove success. They do not authorize another conversion or identify an
earlier failure whose diagnostics were not captured.

The helper validates Office content through the existing gateway binary before
conversion. For DOCX it refreshes fields and indexes, saves a new editable DOCX,
then exports PDF. PPTX exports PDF without flattening or replacing its editable
original. XLSX produces a recalculated editable copy and a PDF with page previews;
the input workbook stays unchanged. PDF input is retained unchanged. Every PDF page receives a PNG preview;
`render.json` records hashes and page count. It deliberately says
`rendered_not_visually_verified`: this is preparation, not acceptance.
The CLI returns a compact receipt with artifact paths, page count, formula-check
summary and the `manifest` path. Read that `render.json` for complete page names,
hashes and formula coordinates; bounded sections avoid truncated inspection.

Before delivery, reopen the saved outputs and read all relevant cells,
paragraphs, tables, summaries, statuses and sources. If readback is truncated or
reports omitted content, read the remainder in bounded sections. Use each final
`render.json`'s `pages` count and `files` entries named `page-*.png` to account for
every page, including source pages. Count a page only after an actual Read call
returns its image and you visually inspect it; reuse an earlier inspection only
when its preview hash matches the final image. Fix missing Chinese glyphs,
clipped text, overflow, overlaps, distortion, spacing and pagination defects,
then rerender and reconcile the final page list again. Inspection is complete
only when saved-content readback has no gaps and every final page is covered.
Rendering and technical checks do not establish visual correctness. Keep this
reconciliation internal; explain actual blocked or unverified parts in ordinary
language under the existing permission and delivery rules.

For each revision, identify the observed defect by page, sheet or cell and the
specific correction. Collect the defects found in the current inspection and
fix them together before rendering again. Preserve already-correct styling;
revise layout only to fix an observed defect or an explicit user request. After
rerendering, recheck each defect at its actual location, including summary titles.
Aim for one consolidated revision; unresolved defects still require correction
or an honest unfinished result, never unchecked delivery to meet that target.

Check poster prices and small-print legibility. Inspect saved PPTX text/shapes to
confirm editability. For Word, compare the saved DOCX's TOC entries, page fields
and total pages with the exported PDF after added content moves headings. A
successful export alone is not proof of correct pagination. Inspect the reopened
Excel's formulas, rows and totals as well as the slide/Word/PDF summary amounts.
Reopen Excel with formulas and cached values separately. Inspect each intended
calculation cell's saved `data_type`: it must be `f`, not a text string that only
looks like a formula. Explanation cells, including those beginning with `=`, must
remain text. Check stored error cells. A blank formula cache is not an error and
is not evidence of a calculated result. Independently recompute
table count × unit price, item totals, verified receipts and balance from the
current cited inputs; compare the actual saved cells and each document's summary.
Reopen the helper's returned XLSX and check its formulas and cached results;
deliver that checked copy. Check long titles, notes, wrapping, row heights and
readable scaling in the final page inspection above. Print layout does not
establish Feishu's interactive display. If rendering is unavailable, state the
remaining limit.

For Word tables, repeat header rows, prevent splitting short rows across pages,
and keep headings with their next paragraph/table. Allow long tables to span
pages. In the final page inspection, check isolated headings, unnecessary blank
space and missing repeated headers; fix only observed layout defects.

Before delivery, internally compare the saved outputs' cited source names, IDs
and versions with materials actually read
in this work. For an absent attachment only mentioned in another document, write
“据<已读材料>转述，原件未提供／未读取”. Label your new drawing “根据本次需求新绘”;
an unread image cannot be its production source. Keep original source IDs and
versions separate from the output revision. Correct mismatches in the files and
any planned reply, then reread before delivery. Keep this audit in tool work;
the employee receives the useful result and actual limits, not a checking log.

Check negative business claims against their sources too: absent payment or
contract evidence means “未提供凭证，实际状态待核实”, not “未付款／未发生”.
Use a definite negative only when the supplied evidence establishes it.

If installed tools or fonts are missing, preserve the prepared originals and
report the missing runtime capability. Do not install packages or substitute a
different model/provider from inside an employee task.

## Revise the set and deliver

On a changed table count, package or visual style, list all affected outputs,
revise their editable sources, then regenerate dependent PDFs/PNGs. Compare
amounts, table counts, selected items, status and source versions across the saved
set. Check the new revision label in every title, overview sheet, header/footer
and filename; keep historical source versions unchanged. Preserve earlier files;
write revisions under new names/directories.
An imported colleague's artifact is the selected source, not access to their
private history. Ask for an absent editable original when required for revision.

Deliver through the existing `file-deliver` protocol only after readback and
visual inspection. Refresh `latest_version` between file deliveries. Keep the
set's revision label in each filename/content so PPT, PDF, poster and budget can
be identified together; no new manifest or task platform is required. If a send
becomes unknown, stop further delivery and reconcile its receipt before sending
another member of the set. Do not send previews or `render.json` as business
deliverables unless requested.
