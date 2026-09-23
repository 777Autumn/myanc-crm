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
Writer/Impress, UNO, Poppler and CJK-font versions actually tested. Preserve the
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
exports PDF and renders every page. No Unix socket or sandbox exception is needed. The worker
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
