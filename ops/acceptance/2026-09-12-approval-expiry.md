# Approval execution elapsed-time fix

Recorded 2026-09-12, Beijing time. Scope: [Issue #27](https://github.com/77AutumN/myanc-crm/issues/27).
This is source/test evidence, not a deployment receipt.

## Change and boundary

The host execution entry now samples the monotonic start alongside its trusted
wall-clock time and carries that start through customer create/update and follow-up
execution to the existing shared expiry guard. Approval reads, change claims and
lock acquisition all count toward elapsed time. Direct in-process customer callers
start at their own entry. No command field, dependency, clock service, schema,
approval/identity rule or write-lock policy was added or relaxed.

This fixes the reproduced entry-to-guard gap. The existing check admits execution
after lock acquisition and before backend pre-write validation; it does not promise
that every network request finishes before expiry. Existing-effect reconciliation,
partial/unknown outcomes and no-blind-retry behavior remain unchanged.

The old contention test started a release Timer before execution, so setup delays
could consume its expected lock wait. The revised test observes a real OS lock
rejection before advancing its deterministic clock and releasing the other process.
It still checks actual contention, expired receipt, zero writes and fence cleanup;
no larger sleep or weaker assertion substitutes for synchronization.

## Local red / green evidence

- On base `68e51a0d2487969fd0aae3ee3c006dd50728b1e4`, the new pre-lock test had
  six failing subcases: approval-read and claim delays for each of create, update
  and follow-up incorrectly wrote after expiry. Six shorter-delay controls passed.
- With the fix, all twelve subcases passed, including expired receipt replay with
  zero additional writes and cleanup of owned fences. Windows Python 3.13.2.
- WSL Ubuntu/Python 3.10.6: all twelve partner-concurrency tests passed, including
  real cross-process contention, busy deadline, crash fence, parallel customers,
  expired lock wait and the new elapsed-time test.
- Windows Python 3.13.2: complete `tests` suite passed (247 tests, 6 platform skips).
- The local WSL full suite is **not passed**: 247 tests, four failures/five errors.
  The available Python 3.10.6 lacks the `tarfile` extraction-filter API and has
  existing host-result incompatibilities. One representative host-result failure
  and the extraction-filter error were also reproduced on the unchanged earlier
  source-display worktree. Do not weaken checks or claim this as full Linux proof;
  the supported Python 3.11 Linux CI remains required.

Only temporary fixture SQLite stores and fake business backends were used. No
production incident, misuse or data modification is established by these tests.

## Delivery and remaining work

Exact-head independent Spec/Standards reviews, PR CI, squash merge and exact
main-SHA CI must be recorded outside the candidate commit before GitHub delivery
is complete. Source changes here do not automatically close those gates.

No VPS install, restart, configuration, credentials or ledger change occurred.
Online release remains **incomplete**. Use the existing fixed-SHA candidate entry
and a separately authorized maintenance window; do not reuse earlier approval.
Keep the original failing CI run and historical diagnostic evidence.
