# Customer trial: final evidence and merge gate

Evidence checkpoint: 2026-09-06. This records the original single-Owner plan's
acceptance layers; it does not authorize a real CRM switch. Merge requires the
final independent review and successful CI on both exact PR heads. Until then,
neither an earlier green build nor this document is a merge result.

## Complete merge scope and reproducible baseline

| Repository | Actual PR base | Preserved canary snapshot | Code checkpoint |
| --- | --- | --- | --- |
| CRM, PR 5 | `fb3cb6dd27ff85b89a635fd2dce31999668b02cc` | `972a8b2e400ee1e6f9204502eb221ac16e3c0c4a` | `6fa62d647a90653b108bb5ee37f8107d51f0c8c1` |
| Gateway, PR 2 | `17c61062c2f9ce9bcdd45a2082e491f9743a2770` | `d72a34665faec9f38c26035ad4b1ea704c639edf` | `d3a2128df86200b1c7c5e54bc88b07ddd04c5d5c` |

Both PRs include the preserved canary snapshot, not just the customer-feature
increment. Independent source provenance verification checked all 664 gateway
files against the frozen canary manifest: 75 byte-identical, 589 differing only
by CRLF-to-LF, no content changes or added/removed files. Of 22 CRM files, 11 are
byte-identical and 10 differ only by line endings; the remaining test file adds
two latest-verified-receipt assertions, with no runtime difference. Both snapshot
trees match the fixed spec. Generated session files and unrelated changes remain
excluded. Source provenance is not a substitute for reviewing the entire diff.

Final documentation synchronizes the gateway's activation-response-loss wording
with its already-correct runtime: delivery failure is not proof of zero writes.
No further runtime, policy, identity or approval behavior changes here. Earlier
failed builds/model runs/readiness checks remain in the chronological review and
local deployment notes; later passes do not erase them.

## Layered acceptance matrix

D = deterministic tests, including real Engine/CLI/SQLite where stated, with
external Feishu faked. N = actual native Claude with a fake Feishu backend.
L = real Feishu UI or independently read live state. D and N are never L evidence.
Gateway paths below refer to the companion repository.

| Requirement | Concrete evidence | Live boundary |
| --- | --- | --- |
| Create/update/rename/stage and separate follow-up approval | D: `tests/test_customers.py`, `tests/test_customer_journey.py`; gateway `TestCUJ_CRMIPC2_*`, `TestCUJ_CUSTOMER1_*`. N: create/update pairs. | L: Owner approved create, cancelled child, then approved profile/stage update and a new child; queried and discussed results. |
| Missing input, duplicate companies/persons, unknown assignees, omitted/cleared fields | D: `test_assignee_candidates_*`, `test_ambiguous_name_*`, `test_duplicate_create_*`, `test_update_omits_*`, `test_cannot_clear_*` in `test_customers.py`. N: company-duplicate, unknown/cached-assignee and update pairs; duplicate-person disambiguation is D-only. | L: same-bot exact-person/name/employment check; not all duplicate-person cases with real personnel. |
| Sender/session/project/card binding | D: `test_host_decision_requires_*`, `test_wrong_principal_*`, `test_card_binding_*` in `test_core.py`; gateway `TestInteractivePlatform_HostedActionIgnoresForgedCardSessionKey`. | Real foreign-sender or malicious cross-session clicks not claimed. |
| Old cards, expiry, modification | D: `test_cancel_and_modify_*`, `test_approval_expires_*`, `test_new_stage_supersedes_*`, `test_later_begin_reports_every_stale_card_*` in `test_core.py`. | L: Owner cancellation and earlier modified-follow-up journey, not a live expiry/stale-card audit. |
| Replay and concurrent CAS | D: `test_conflicting_or_duplicate_click_*`; gateway `TestCUJ_CRMIPC1_*` includes eight independent Python/SQLite claim processes and one winner. | External fake backend is serial; no concurrent real Feishu write claim. |
| Write-time field/schema/person drift | D: `test_schema_or_displayed_customer_drift_*`, `test_matching_equivalent_unicode_drift_*`, `test_removed_or_changed_assignee_*`, `test_schema_and_customer_drift_*`. | No competing live edit/schema-change injection. |
| One child, independent expiry, restart persistence, later intent wins | D: `tests/test_child_ledger.py`, including `test_one_child_under_concurrent_publish_and_restart`, `test_newer_intent_*`, `test_slow_old_plan_*`; gateway `TestHostedNextApprovalPublishesOnceAndKeepsParentReceipt`. | L: independent child cards, not competing live publication. |
| Unknown/partial writes, delivery loss, no blind retry | D: `test_unknown_create_*`, `test_unknown_update_*`, `test_partial_repair_rebinds_after_restart_*`, `test_stale_worker_is_never_automatically_reclaimed_*`; gateway `TestHostedNextActivationTimeoutDoesNotClaimFollowupUnsubmitted`. | Neither N result fixtures nor successful L journeys prove live fault injection. |
| Durable receipts versus current facts; read-only does not stage | D: `tests/test_host_tools.py` and customer journey; N: read-absent/result pairs. | L: same-bot Base reads plus SQLite `mode=ro`, scoped by actual customer binding. |
| Unicode display and poisoned source text | D: nine fidelity regressions; N: benign/poisoned pair, three trials each with separate semantic review. | L: name-only preview preserves fullwidth parentheses and circled digit; cancelled, not an approved new rename. |
| General assistant, Quiet, continuation, one receiver | D: both `TestCUJ_CRMIPC*` journeys, `TestCUJ_CUSTOMER1_*`; L checks below. | No incoming attachment, user-calendar, general-write, cron/send or cgroup-stop acceptance claim. |

Earlier PR summaries said all remaining adverse cases needed live acceptance.
That over-broad wording was an added interpretation, not the approved plan's
requirement. This explicit matrix supersedes it: mechanism checks use D, behavior
checks use N, and listed L checks cover deployment and Owner journeys. It does
not relabel unperformed live replay/drift/restart tests as passed or remove any
mechanism requirement. Future disruptive checks still require idle, fictional
scope and must never forge an Owner callback. Whole-gateway re-exec followed by
old/new token and pending-card checks remains an unperformed live test; restart
environment and ledger persistence tests are not equivalent to that journey.

## Fresh verification and human evidence

- CRM: 185 unit tests and 16 spike tests passed again; a separate reviewer reran
  both. Gateway adapter/Python IPC, core hosted/CUJ and Feishu hosted-card tests
  passed locally with Go 1.25.6.
- Code-checkpoint Linux CI passed: CRM push `34019053565` / PR `34019055757`;
  gateway full lint, unit/race/coverage, smoke, regression and performance
  `34019858883`. Documentation commits need their own exact-head CI. The earlier
  whole Windows suite failure remains a failure, not a Linux result.
- Original N suite: 14 cases x 3, 42/42 code, separately 18/18 + 24/24 independent
  semantic passes; CRM `9066dfd`, gateway `c5b27173`. Unicode N suite: 2 x 3,
  6/6 code and separately 6/6 semantic; CRM `6fa62d6`, gateway `d3a2128d`.
  Native Claude 2.1.259 / `claude-sonnet-5`, unchanged policy. These frozen runs
  are not reruns of the final documentation commits.
- Fresh L general-bot reads at 08:39:36 UTC passed existing test-Base metadata,
  document fetch and calendar list. No new resource or permission was created.
- Fresh installed `--live --probe-auto` passed before 08:46:21 UTC: single
  receiver/connection, protected identities/state, log checks and native
  Auto/sandbox. No service restart was needed.
- Final Owner screenshots show the corrected Unicode preview and cancellation.
  Independent same-bot readback plus read-only SQLite confirms a cancelled
  name-only update, retained prior approved name/stage, exactly one approved
  follow-up, cancelled earlier follow-up absent and next date empty. No business
  write, re-staging or receipt rewrite was used for verification.

Only anonymous outcomes are recorded here. Raw screenshots, customer/person
identifiers, messages, private configuration and ledger contents stay out of Git.
Local attachment references and deployment details remain separately in the
existing `customer-trial-acceptance-2026-09-06` notes.

## Reviews, remaining risks and next authorization

Standards: zero hard/heuristic findings after two stale gateway documentation
claims were corrected. Ponytail: no unnecessary framework or abstraction. Spec
rereview closes the incorrect zero-write documentation claim and accepts this
layered matrix; it clarified that duplicate-person disambiguation is D-only.
Independent senior review covered the actual PR-base-to-code-checkpoint scope
(36 CRM files and 46 gateway files, including both snapshots), focusing on host
secret isolation, controlled tools, principal/card binding, CAS and preserved
unknown/partial effects. No new reproducible security merge blocker was found.
Independent reruns passed CRM 185 + 16, gateway adapter and Feishu full packages,
core targeted tests and 11 Claude environment/resume tests. Windows whole-package
limitations and the unperformed full-gateway live restart remain explicit above.
Exact final CI and merge SHAs belong in the PR closeout; reviews do not bypass CI.

Recorded UX issues remain: extra process narration, occasional English/internal
terms and redundant clarification. Correctness is not product usefulness. Record
anonymous clarification/repeated-explanation/manual-recovery counts and feedback
in the real trial, then review 3–5 customers and 10 actual follow-ups.

After review and squash merge, STOP before real cutover. The Owner must separately
confirm a new empty `ANC CRM`, `CRM-` numbers, isolated configuration/ledger,
same-app permissions, backup and read-only checks. Preserve Sandbox; copy no
fictional records, introduce no multi-Base router and grant no approval power to
an assignee. Real writes still need each Owner-approved card. Rollback restores
compatible code/configuration or disables new entry points, never overwrites the
current ledger or reverses completed business results.
