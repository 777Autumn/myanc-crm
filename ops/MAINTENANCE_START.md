# Gateway maintenance startup

For future authorized cutovers, use `maintenance_start.start_once` from the frozen
candidate's `ops/` directory. Keep historical one-time installers immutable. This
module replaces their immediate process-name startup check and pre-exec pause
check; it is not a deployment CLI, a Bot tool, or permission to restart production.

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
either the original outer `failed.json` (including application-health failure) or
`start-failed.json`. The helper verifies `attempt.json`, `start-requested.json`,
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

Name-matched receiver diagnostics additionally retain up to 32 PIDs and their
PPID, UID, process state/start ticks, observation time, executable-path and cgroup
hashes before protective stop. The full count still controls rejection; truncation
is explicit. Disappearing, unreadable or changing processes remain name matches,
with an uncertainty category rather than a benign classification. No environment,
command line or raw cgroup/executable path is collected. These observations are
best-effort, non-atomic evidence, not permission to ignore a child process: fork
can inherit a name and executable before exec. An isolated Linux regression
demonstrates that mechanism; it does not identify the missing second process in
either historical failed startup. Existing consumed attempts stay consumed.

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
