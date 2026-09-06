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

## Re-review and current handoff

The independent Standards re-review of CRM `44c4e24` and gateway `afab16cc`
closed both heuristic findings with zero outstanding findings. The independent
Spec re-review closed all three P2 findings, reran the eight customer-journey
tests and two gateway receipt tests, and reproduced the uncertain-create path.

Current local checks: 176 Python tests and 16 spike tests pass; the full gateway
CRM adapter suite (including both real Python IPC journeys), core CUJs, targeted
approval/Feishu tests and compilation pass. CRM Linux CI passed on `44c4e24`.
Gateway Linux CI initially exposed inherited baseline lint issues. The fixes did
not change lint rules or skip the full suite. All five Linux CI jobs subsequently
passed on gateway `d366d2ce`; CRM CI passed on `539fadb7`.

The 14 customer model cases are wired into the existing native harness with
paired graders and semantic rubrics. Complete-input grading now checks both the
actual tool input and frozen follow-up draft, including invented optional fields;
ten adversarial grader variants pass. The full CRM adapter suite, including both
Python IPC journeys, passed again after that change.

Correction to the earlier SSH diagnosis: the bare alias omitted the remote user
and selected the local Windows username. The existing helper explicitly selects
the intended account. Using that documented account with the existing key and
trusted host key succeeds. No SSH, account or key change was necessary. The
actual service binary is Claude Code 2.1.259; 2.1.236 is only the older user-path
binary, not the running service's configured command.

On 2026-09-06, the isolated native run passed artifact checksums, four runner
tests, private supervisor environment validation, exact binary verification and
local auth-status inspection. The actual model-auth smoke then returned
`oauth_token_revoked`, and the runner stopped with exit 3 before the first case.
The selected credential source matches the service's Claude run-as user and has
an expired access token. Local `loggedIn` status is not proof of model access.
All 42 customer behavior trials and independent semantic review remain
**NOT RUN**. Do not merge on authored cases or deterministic tests alone.

The runner reused the proven private mount/PID namespace path, mounted existing
credentials read-only, and used the alternate fixture listener with synthetic
CRM data only. No live Feishu call, production restart or credential change was
performed. Retain this failed preflight as evidence; after the user completes
official login, use a fresh isolated directory for the next run.

The new `ops/CLAUDE.vps.md` is a candidate policy, not an installed live policy.
It covers the narrow customer commands, one-question collection, frozen parent
draft and separate approvals. A review correction explicitly preserves earlier
partial writes when a repair card is pending, unavailable or cancelled: describe
effects from durable receipts, not from card availability. Final incremental
Standards review has zero open hard violations or heuristic findings; Spec has
zero new findings. Neither static review substitutes for actual model trials.

The subsequent independent senior review found one additional P2: a child-card
activation may succeed in Feishu while its response times out, so the parent
delivery-error notice cannot assert that the follow-up was not submitted. The
gateway's five-language notice and same-path log now report uncertainty and
direct the user to durable results. A regression retains an activated/bound
child through activation and fallback timeouts, permits its independent callback,
and rejects the former zero-write assertion. Hosted/i18n tests, the full CUJs and
Feishu hosted-card/refresh tests pass. Execution, authorization and retry logic
were not expanded. These latest local changes still require fresh CI and the
blocked real-model gates; earlier green CI applies only to its recorded commits.

Both PRs remain drafts and unmerged while these gates are outstanding. The
running installation, Sandbox, production configuration and ledger are unchanged.
