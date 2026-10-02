# Runtime templates

These selected templates were backfilled from the existing local operations
assets on 2026-09-09. They are inputs for a separately authorized maintenance
workflow, not an installer. The base service and partner drop-in are used
together; production identity mapping, auth, config and ledgers remain external.

The guard tests use synthetic commands/paths. `test_partner_boundary.py` needs
Linux root only to exercise temporary numeric UIDs; it creates no user accounts
or services and must never be repurposed as a production fault injector.

Historical one-time deployment/recovery scripts remain outside this repository.
Their fixed PID assumptions and maintenance context make them **non-reusable**.
The supported future candidate entrance is described in [../RELEASE.md](../RELEASE.md).

The unpublished business-display and operations-alert templates are described in
[../OPS-ALERTS.md](../OPS-ALERTS.md). They require separate approved maintenance;
adding a template to git does not enable it on any of the six live environments.

## Proposal document runtime

`team-files-requirements.txt` pins the existing Python packages plus presentation,
image and PDF libraries. `team-files-system-packages.txt` records the Debian 12
Writer/Impress/Calc, UNO, Poppler and CJK-font versions actually tested. Preserve the
existing package versions; resolve and record the installation transaction before
the authorized maintenance window. These files do not run an installer.

Install `team_file_pdf.py` as a gateway-owned executable in a protected directory
and point only the approved file-work projects' `document_validator` setting at
it. Its Python shebang is `/opt/team-files/bin/python -I`. The executable accepts
stdin bytes and emits only `PDF_OK_V1` on acceptance; its detailed protocol is in
the paired gateway `ops/FILE_FORMATS.md`. No employee-controlled path is a host
validation command. No management socket is used.

Install the root-owned, employee-readable `team_file_render.py` at
`/usr/local/libexec/team_file_render.py`. Run it as the existing employee account
with the current work root, selected input and a new output subdirectory; its
`--help` describes the arguments. The default paired binary is
`/usr/local/bin/cc-connect-anc`; the optional `--gateway` selects a candidate
binary for offline checks, not a sending endpoint. The script first invokes the
gateway's read-only `file-check`, then uses a private profile and the installed
LibreOfficeKit inside the worker, refreshes Word fields/indexes through UNO,
recalculates XLSX into a new editable copy, exports PDF and renders every page.
Calc uses `MAX_CONCURRENCY=1` within the existing resource limits. Saved formulas
must retain their type and expression; changed formulas, error cells or missing
caches fail preparation. Equals-prefixed text is reported for task-specific review,
never silently converted. PDF previews show print layout; inspect the employee's
spreadsheet interface separately. No Unix socket or sandbox exception is needed. The worker
uses `/usr/bin/python3` with distro UNO; the caller uses the locked virtualenv.
Timeout cleanup targets only the spawned process group. It rejects root execution.
Office and preview workers share memory/CPU/file-size limits. Completed output
files use `0640` inside a `2750` directory, inheriting the existing outputs
handoff group; scratch and profiles stay private even with service umask `0077`.

Offline actual rendering is enabled by `TEAM_FILES_TEST_GATEWAY=<paired binary>`:
the ordinary renderer tests apply the existing Linux `libseccomp.so.2` filter
to deny `socket(AF_UNIX)` before rendering, matching the managed Claude sandbox.
run the runtime unit tests as an ordinary account with the listed dependencies.
Without that explicit binary the actual rendering case reports **skipped**, not
passed. Source tests can independently check paths/protocols; only the paired run
establishes Go/Python/LibreOffice interoperability. Render success does not assert
visual or employee acceptance. Original files and previous outputs are retained.
In a disposable Linux environment only, run `HandoffRenderTests` with the same
binary setting as a privileged fixture initializer. It creates temporary numeric
identities, renders/revises as the ordinary model UID and reads every completed
artifact as a different ordinary gateway UID. It also checks that the legacy
private directory and an unrelated UID are denied. No accounts or services change.

### Native macOS candidate (not installed)

The Mac worker uses `/Applications/LibreOffice.app/Contents/MacOS/soffice` and
the caller's pinned Python. A private one-shot profile contains a copy of this
fixed renderer and a JSON job; Office runs that fixed script with its embedded
Python/UNO. This avoids externally launching its signed helper, whose parent
launch constraint rejects a shell. No signature changes, document macro enablement,
UNO listening socket or persistent Office process are needed. The same
`office_update` handles Word fields/indexes, XLSX recalculation and PDF export.
Poppler's Apple Silicon path is `/opt/homebrew/bin/pdftoppm`; availability and its
exact dependencies still require a frozen native install list.

macOS rejects `RLIMIT_AS`. The one-shot conversion supervisor checks its process
group's aggregate RSS every 100 ms while waiting (2 GiB), and kills the group on
excess or accounting failure. The PDF parser stays in its caller-owned process;
a thread samples its high-water RSS (512 MiB) and terminates that process on
excess or accounting failure. Host cancellation therefore cannot orphan a parser
subprocess. CPU, file-size, wall-time and core-dump limits remain. These are
sampled memory budgets, not Linux's hard allocation ceiling: transient excess
is possible, and the PDF monitor cannot run while native code holds the GIL.

An accounting failure retains the fixed operation (`listpids`, `pidinfo` or
`empty_group`), PID, returned/expected byte counts and numeric errno in the
existing private failure record. `empty_group` counts members rather than bytes.
An OS cleanup error also retains its numeric errno. These fields contain no
command line, exception text or document path. A zero-byte enumeration with a
nonzero errno is a failed read, not an empty group ([Apple libproc wrapper](https://github.com/apple-oss-distributions/xnu/blob/main/libsyscall/wrappers/libproc/libproc.c#L40-L54)). Missing historical fields
leave the original cause unknown; no automatic retry, successful-conversion
claim or cleanup permission follows from these diagnostics.

Package exploration used official LibreOffice 26.8.0 ARM64 (reported 26.8.0.3),
SHA256 `8858d8058da4f862f47559486814e65efc27294da67c5e4bb56b006b1ee59f89`,
and Python 3.13.15 universal2 installer, SHA256
`3b7eaf7f29825f796e8267024435540ddf1f17fc9a97ad58095daa7a75bfdcd3`.
Both hashes and Apple signatures were checked. These are explored candidate
versions, not a completed dependency lock or installed runtime. An ordinary
identity converted fictional DOCX/XLSX through the signed read-only Office bundle,
retaining originals and seven cached formulas; this does not cover Poppler,
all native dependencies, model sandbox execution or employee visual acceptance.
The first export lacked Chinese glyphs. The worker now explicitly includes
`/System/Library/Fonts` and `/Library/Fonts` in its private Fontconfig file; its
cache stays in the disposable profile. A subsequent native export rendered the
Chinese text using installed system fonts. The failed PDFs remain as evidence;
no new font package was installed. Freeze the actual fonts used with the final
installation list, and do not assume a requested font family is installed.
Sources: [Office package/hash](https://download.documentfoundation.org/libreoffice/stable/26.8.0/mac/aarch64/LibreOffice_26.8.0_MacOS_aarch64.dmg.mirrorlist),
[Python package/hash](https://www.python.org/downloads/release/python-31315/).
