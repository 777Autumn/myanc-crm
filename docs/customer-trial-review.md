# Customer trial review — 2026-09-06

This is a review of the new customer trial, not authorization to select real
data or deploy. The fixed feature baselines are CRM `972a8b2e` and gateway
`d72a3466`. Initial reviewed feature commits: CRM `a32346b1`, gateway `4ac91d37`.
Three independent agents reviewed standards, spec, and senior/complexity concerns.

## Standards

No clear new documented-standard violations. Two labelled heuristic findings:

- P2, possible Duplicated Code: customer staging accepted a 128-character phone
  while the fixed writer accepted 64. A 65-character value reached approval but
  could not be written. Resolution: share the domain text limits and reject this
  input before staging; add a regression test.
- P3, possible Feature Envy: child preparation queried the temporary Ledger's
  private SQLite connection and serialization directly. Resolution: canonical
  proposal retrieval now stays inside `Ledger.planned_body`.

Standards total: 0 hard violations, 2 heuristic findings; highest severity P2.

## Spec

No scope creep was identified. Three P2 findings:

- Child preparation failure was hidden by generic “separate approval” copy in
  the green parent card. Resolution: `unavailable/not_published` produces explicit
  no-new-card, unsubmitted-follow-up and manual-recovery instructions while
  preserving parent success. Test the actual adapter Execute receipt.
- An observed but not fully verified creation was absent from the customer's
  latest-operation lookup. Resolution: preserve the returned/observed record ID
  separately from the frozen proposal. It enables result lookup only; unknown
  outcomes still cannot prepare a child. Test actual CLI/SQLite lookup.
- Cancelling repair of a partially successful child falsely said its follow-up
  was never submitted. Resolution: preserve the durable partial receipt, show
  retained follow-up and manual summary repair, and keep the parent success.
  Test partial write → new repair approval → cancel → related result, plus cards.

Spec total: 3 findings; highest severity P2.

## Independent senior and Ponytail review

The senior reviewer agreed with the child-preparation failure finding and the
existing narrow branch/card-publisher design. No MCP, SDK, extra service or
general workflow abstraction is needed.

Two complexity reductions were accepted: remove an immediate duplicate assignee
read (the fixed backend already verifies it; stage/apply still recheck), and
remove a redundant new SQL operation-type column. The immutable proposal already
stores and fingerprints operation type. Any existing extra column is left alone;
there is no destructive database migration. Original review estimate: 7 lines
removable, not a measured product performance claim.

An inherited issue was also reproduced: terminal approval replay happened before
original card-ID validation. Validation now precedes terminal replay. Historical
tests now bind emitted cards before superseding them, matching the real lifecycle.

## Verification and release boundary

Local compilation, Python regression tests, isolated real Python IPC journeys and
targeted gateway tests are separate evidence from model and live Feishu behavior.
Linux CI initially exposed a missing execute bit on a temporary wrapper test;
the test fixture now sets it explicitly. Keep the failed CI history.

The paired customer model cases must run in the existing opt-in isolated native
Claude harness with semantic review. Authored cases or skipped tests are not a
pass. Same-app personnel permissions/visibility, actual fictional card delivery,
other Feishu abilities and one receiver remain live acceptance checks.

Draft PRs: [CRM #5](https://github.com/77AutumN/myanc-crm/pull/5) and
[gateway #2](https://github.com/77AutumN/cc-connect-anc/pull/2). Review resolutions
and CI must pass before merge. Real CRM creation/switching still requires separate
confirmation after merge; no real records, private configuration or ledger are
included in these changes.
