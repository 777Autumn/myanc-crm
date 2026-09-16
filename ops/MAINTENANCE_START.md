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

backend = Systemd()
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
to retry a consumed request. Failure handlers save their own separate receipt after
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
