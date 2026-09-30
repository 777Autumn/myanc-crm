# Gateway maintenance startup

For future authorized cutovers, use `maintenance_start.start_once` from the frozen
candidate's `ops/` directory. Keep historical one-time installers immutable. This
module replaces their immediate process-name startup check and pre-exec pause
check; it is not a deployment CLI, a Bot tool, or permission to restart production.

## Native Mac backend

Use `maintenance_launchd.Launchd()` with the same `start_once`, `pause_verified`
and `recover_once` callbacks. Capture the configuration identity with
`backend.identity(backend.sample())`. Existing Linux callers and receipt shapes
remain unchanged. Mac receipts identify `system/com.myanc.cc-connect` and include
the native sample; they do not invent systemd states or a `/proc` start time.

The frozen template is `runtime/com.myanc.cc-connect.plist`. It runs the gateway
as `_ancgateway` with its own group, no desktop session, no automatic restart and
no abandoned process group. It is not an installer: freeze and verify all paths,
accounts, credentials, permissions and binaries before copying anything. KeepAlive
must stay false so a failed start cannot silently retry outside the receipt gate.
Pre-create the two log files owned by `_ancgateway` and its dedicated group with
mode `0640`; verify parent traversal and file writability as that ordinary user.
The frozen installation list includes these ownership/mode checks. A root-created
test directory alone does not demonstrate that launchd can open logs after changing UID.

The base plist leaves business hosts disabled. For the approved four-entrance Mac
migration, explicitly add `maintenance_launchd.HOST_ENV` to its environment before
freezing the installation. This exact opt-in variant reconnects the existing CRM,
shared cases, reminders and owner alerts; partial or arbitrary overrides are rejected.
Secret values remain in protected files, never the plist. Provision and verify the
fixed helper paths, four-project mappings, secret file and fresh reminder/alert
stores before starting. Add the complete `KNOWLEDGE_ENV` pair only when that host's
protected configuration and existing publication journal are also provisioned and
verified. A Mac migration carrying only the selected local mock Wiki leaves this
pair absent: do not create an empty journal and report the old knowledge as connected.
Local Wiki reads and fresh shared cases remain available; report the separate
knowledge-tool limitation explicitly. Keep model credentials and private workspace state outside
these host paths. This variant requires the paired gateway's four-project startup
support and does not initialize storage or enable anything by importing the module.

Mac start requires an unloaded service and zero matching receivers, then issues
one `launchctl bootstrap`. Stop targets only the verified service with `bootout`.
The helper pins the boot-session UUID and resource coalition, PID and the native
microsecond process start identity from libproc. More than one run, an unexpected
loaded command, ambiguous query output, another receiver or changed identity
blocks success. A replacement registration is not stopped. An unloaded service
with a lingering receiver is not considered stopped. `started.json` remains a
process check, not application or Feishu readiness.

The observed `xpcproxy` and `SIGTERMed` states are transitions, never readiness.
After the one stop command, wait at most 40 seconds for unload and zero receivers;
every sample rechecks controls, registration and any pinned PID/start identity.
A replacement, duplicate receiver, unknown state or failed query still blocks.
Unknown native states remain in failure diagnostics instead of discarding the
observation. A diagnostic failure must not replace the original start error.

`launchctl print` is a diagnostic text interface, so this bounded parser accepts
the observed required fields and rejects unknown state/ambiguous results. Validate
it again after macOS changes. Source references: [Apple's process ABI](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/proc_info.h)
and the installed `launchctl(1)` manual. The Mac CI job creates a temporary,
random-labelled LaunchDaemon with a compiled sleeping fixture, uses root only for
service setup/control and verifies the daemon's ordinary UID. It has no model,
Bot, network or credentials. This evidence cannot replace the installed candidate's
permissions, unique-receiver and 125-second application stability checks.

### Codex workspace rules and Skills

Keep one canonical copy of the published workspace policy and Skills. For each
approved Codex workspace, install `CLAUDE.vps.md` as `CLAUDE.md`, a relative
`AGENTS.md -> CLAUDE.md` link, and `.agents/skills -> ../.claude/skills`.
Preserve the current `.claude/skills` contents, role references and Wiki versions;
linking them does not publish new knowledge or import private conversation history.
Use Codex's native [AGENTS and Skills discovery](https://learn.chatgpt.com/docs/customization/overview),
including its [supported skill symlinks](https://learn.chatgpt.com/docs/build-skills).

The matching `runtime/codex.config.example.toml` uses the `anc-work` named native
permission profile. Select that same profile in the gateway agent options. Keep
each entry's HOME and CODEX_HOME private and install the config as root-owned;
device login remains per identity. The tool sandbox denies the authentication
directory and protects rule paths, `AGENTS.override.md` and link anchors. OS ownership, dedicated
groups and the existing host capabilities remain required. The loopback network
rule is hostname-wide, not a port ACL, and does not authorize an administration
socket. Do not add unrestricted network/HOME access to make a failed tool work.

For the paired gateway's optional `shared_app_server=true`, select `anc-shared`
instead. Its base allows only system/tool reads; the gateway adds each fixed
entrance's workspace and current file work to that thread. All four approved
entrances use one exact `run_as_user`, `codex_home`, pinned CLI and process proxy
configuration. The one native app-server owns the login; do not copy auth files
or put session capability tokens into its process environment. The native
sandbox and trusted host scope isolate entrances under this common ordinary
identity; this does not claim separate OS users for those model threads.

Freeze the actual ordinary gateway/owner identities, dedicated handoff group,
root-owned rules/configuration and workspace paths before installing. Never use
`staff` or a readable shared HOME. Dynamic chat workspace creation is unsupported
in this fixed-entrance mode. Native thread unload must be confirmed before a cold
resume refreshes its work capabilities; uncertain unload blocks that entrance.
Process failure requires inspection, not an automatic new authentication owner.
The opt-in profile does not change the legacy default. Final native boundary and
paired installation evidence remain required; changing this template alone
neither enables the Bot nor proves an employee journey.

Run `ANC_CODEX_BIN=/path/to/pinned/codex python -m unittest discover -s tests -p
test_codex_workspace.py -v` as an ordinary Mac identity. The test uses temporary
fictional files, calls the actual CLI's `skills/list` and sandboxed `command/exec`,
and makes no model turn. It checks rule/Skill readability, saved revisions,
protected writes/renames and credential read denial. It does not prove model
compliance, installed ownership or cross-account isolation; verify those against
the frozen installation before enabling the Bot.

## Integration

After the existing install phase has stopped the service, backed up business state
and verified the installed file manifest and account boundaries:

```python
from maintenance_start import start_once, pause_verified, Systemd, unit_identity
from maintenance_inventory import verify_new_inventory

backend = Systemd()
# frozen_files maps each absolute destination to its old/new file identity.
# verify_installed_controls also checks unit/config/permission boundaries.
verify_new_inventory(frozen_files)
# Capture only after verifying the frozen systemd configuration and files.
identity = unit_identity(backend.sample())
started = start_once(record, verify_installed_controls, backend=backend)
# Persisted started.json means process identity ready, not application health.
try:
    verify_existing_stable_health_window(started['pid'])
except BaseException:
    pause_verified(backend, identity, started['invocation'], verify_installed_controls)
    raise
```

`record(name, payload)` is the maintenance script's durable, root-only,
non-overwriting receipt writer. An existing `start-requested.json` must reject
before any start, including after an uncertain or failed prior attempt. Use the
same protected receipt directory for that candidate; never choose a fresh directory
to retry a consumed request. The bounded recovery below is the only reusable second
start path and retains that directory. Failure handlers save their own separate receipt after
attempting safety cleanup, even if pause fails. Convert TERM/HUP to an exception in
the calling script; KeyboardInterrupt is handled. SIGKILL and host failure cannot
be intercepted. A success receipt may already exist if its writer fails after
persisting it; any failure receipt/error takes precedence pending reconciliation.

`verify_installed_controls()` must fail on changes to the frozen executable, unit
fragment/drop-ins, credentials/configuration, ownership, modes or protected paths.
It runs before start, before success and before protective stop; preserve the
existing full manifest/backup/ledger checks around it. The helper also pins the
loaded unit properties, including ExecStart's static path/argv/ignore-errors fields,
and rejects a pending daemon reload. ExecStart's start/stop time, PID and exit
status are runtime observations, not configuration identity. Unknown display
formats fail closed; no static command field is silently dropped. It does not grant a
new authorization or replace external coordination between maintenance operators.

## Frozen installation state

Before installation, preserve the existing `attempt.json` with the candidate and
candidate-manifest SHA-256 values, and add `installed_manifest_sha256`: the digest
returned by `maintenance_inventory.inventory_sha256(frozen_files)`. Keep the full
frozen list in protected maintenance evidence. Each absolute destination has an
`old` and `new` identity containing `sha256`, `uid`, `gid`, and integer `mode`;
`old: null` means the new file was previously absent. The list includes the CLI,
its managed version lock, candidate files, and changed configuration as applicable.

`inspect_inventory` reads only that list and reports every destination as old,
new, unchanged or unknown, plus an overall old/new/partial/unknown state. A file
with changed content or permissions, a missing required file, a symlink or an
unreadable file is unknown. Unchanged entries do not turn an otherwise complete
installation into a partial one. This is not a directory scanner: the existing
protected-control verifier remains responsible for the list's completeness and
directory boundaries.

Perform a consistent multi-file installation only after stopping the service.
Record the inspection result on failure; never automatically continue or roll
back a partial/unknown installation. `verify_installed_controls` must call
`verify_new_inventory` before a normal or recovery start and before reporting
success. All-new content alone does not prove account isolation or application
health. An old historical attempt without this binding is not made eligible by
rewriting its evidence.

## One explicit recovery of the same candidate

`recover_once(record, read_record, verify_installed_controls, verify_reconciled,
expected=..., backend=backend)` is for a maintainer whose existing authorization
covers this exact candidate and diagnosed recovery. It is not exposed to Claude,
invoked automatically by failure handlers, or granted by a model's statement that
the user approved something. Retain the original failed startup and health records.

Both receipt callbacks must use the same original, root-protected directory and
reject symlinks or untrusted ownership/modes. `read_record(name)` returns exact
bytes. `record` atomically creates without overwrite, flushes the file and parent
directory, and returns only after durable persistence. Do not change roots,
delete a consumed marker, or reuse an empty alternate directory.

Freeze `expected` with these SHA-256 fields: `attempt_sha256`,
`start_request_sha256`, `failure_sha256`, `diagnosis_sha256`, `candidate_sha256`,
`manifest_sha256`, and `installed_manifest_sha256`. Its `failure_receipt` is
the original outer `failed.json` or `startup-failed.json` (including application-health
failure), or `start-failed.json`. The existing `startup-failed.json` format uses
`error_type`; the other two use `category`. Bind the original bytes and filename
directly, without renaming, rewriting or replacing the failure with a summary.
The helper verifies `attempt.json`, `start-requested.json`,
that failure, and `recovery-diagnosis.json` against these exact bytes. Diagnosis
must repeat the bindings except its own digest, describe the established `cause`,
identify a `maintainer_reference`, and freeze `controls_sha256` and
`business_state_sha256`. Unexplained historical warnings remain unexplained; an
unknown message cannot be relabelled as a known benign event to permit recovery.

`verify_reconciled()` must freshly verify the actual installed list is all-new,
frozen configuration/permissions/version, explained business changes, no unfinished
business and no unknown delivery outcome. It returns exactly `controls_sha256`,
`business_state_sha256`, and `installed_manifest_sha256` from those checks. The
last comes from the verified inventory's `inventory_sha256`, and must match the
original attempt; all three must match the diagnosis. This callback is trusted maintenance code;
passing booleans or copying the diagnosis is not verification. The helper also
checks the real stopped unit, zero receivers and the original unit identity.

After verification, it durably creates `recovery-requested.json`, rechecks the
bindings and live conditions, then invokes the unchanged `start_once` using the
fixed `recovery-start-requested.json`, `recovery-started.json`, and
`recovery-start-failed.json` receipt names. Exclusive marker creation admits only
one concurrent caller. Interruption, failed rechecking or a command/receipt error
does not refund that allowance. A marker-write error stops before any start; even
when persistence is uncertain or no marker is visible, require manual storage
reconciliation rather than automatically retrying. A second failure stops the
workflow. The caller still performs the normal health/stable-window checks and
saves a distinct outer recovery failure receipt if those fail after return.

## Lifecycle and evidence

Exactly one start request is issued. Process identity polling uses a monotonic
40-second budget after that command returns, with 250ms intervals and two matching
ready samples. Each real systemd query is bounded to 5 seconds; start/stop commands
are bounded to 55 seconds. Control/receipt callbacks must also be bounded. There
is no implicit start retry or `reset-failed`. Application initialization, six-engine
routing, SDK WebSocket lifecycle, the unique listener, stable-window health and
unchanged business state still require the existing subsequent checks.

While waiting, a zero PID, unreadable-yet executable or pre-exec process can be
transient. Success requires the fixed executable, unique receiver, active/running
unit, unchanged PID/starttime/invocation and zero automatic restarts. Unit or
invocation replacement is rejected; startup timeout or interruption invokes
protective stop only against the unchanged, verified unit. That stop does not
require the child to have reached its final executable, fixing the earlier gap.
Changed control files, ambiguous query results or a replacement invocation require
manual reconciliation rather than stopping an unverified replacement.

Errors preserve the last safe sample and separate pause failure category, without
printing command output, command arguments, arbitrary executable paths or business
content. Keep the original failed and successful observational receipts distinct.

Unexpected name-matched receiver sets additionally retain up to 32 PIDs and their
PPID, UID, process state/start ticks, observation time, executable-path and cgroup
hashes before protective stop. The full count still controls rejection; truncation
is explicit. Disappearing, unreadable or changing processes remain name matches,
with an uncertainty category rather than a benign classification. No environment,
command line or raw cgroup/executable path is collected. These observations are
best-effort, non-atomic evidence, not permission to ignore a child process: fork
can inherit a name and executable before exec. An isolated Linux regression
demonstrates that mechanism; it does not identify the missing second process in
either historical failed startup. Existing consumed attempts stay consumed.
Normal single-receiver/stopped samples keep their original shape and equality so
existing whole-sample stable-window checks need no changes.

## Verification scope

The historical failure is consistent with `Type=simple` returning before process
exec/readiness; exact failure-time process details were not retained, so the
incident's precise root cause is not claimed proven. The
[systemd service specification](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml)
documents that early-return behavior. Local regression reproduced the immediate
check failure on a delayed-exec fixture; the bounded-wait implementation passes it.
Tests also cover protected pre-exec stop, uncertainty, replacement, PID reuse,
receipts and interruption. CI exercises the real Linux `/proc` adapter with
systemctl stubbed, never stopping or starting an actual service.
Independent Spec review found that the first helper revision incorrectly pinned
ExecStart's dynamic status; actual-format fixtures reproduced the failure before
the parser was corrected. The
[official display implementation](https://github.com/systemd/systemd/blob/main/src/systemctl/systemctl-show.c)
defines that format. This review failure is retained, not counted as a passed revision.

This fix is code/CI delivery only. No VPS invocation, production restart, model
call, credential change, candidate rebuild or real startup-race reproduction is
part of this task. A future maintenance window must integrate this frozen module
and record its actual application-health and safety outcomes separately.

Subsequent integration: the [September 16 CRM/Skills maintenance](releases/2026-09-16-crm-skills-live.md)
used the frozen helper for two separately verified stages, each with one start
request and a successful 130-second application-health window. This is real
integration evidence, not a reproduction or retrospective diagnosis of the old race.
