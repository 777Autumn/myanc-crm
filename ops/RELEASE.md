# CRM / gateway delivery contract

This is the authoritative development handoff and VPS release contract for the
private repositories `77AutumN/myanc-crm`, `77AutumN/cc-connect-anc` and
`77AutumN/myanc-team-brain` when the knowledge runtime is in the candidate.

## Completion

Report these separately at every implementation handoff:

1. Local implementation: scoped changes, applicable tests and unresolved findings.
2. GitHub delivery: exact head, independent Spec and Standards evidence, PR CI,
   squash merge, and successful exact merge-SHA push CI for each affected repo.
3. Online release: authorized maintenance, frozen candidate manifest, installed
   hashes and actual acceptance evidence. A GitHub-only task does not deploy.

Write **incomplete** for every required stage lacking evidence. A working bot is
not evidence that source delivery is complete. Preserve unrelated worktrees and
dirty files; start scoped branches from live origin/main.

## Normal delivery

Keep runtime changes and governance changes scoped. Before publishing, inspect
the diff for secrets and private customer/chat content. Review both code standards
and requirements independently against the exact head and base. Save reviews
outside that candidate commit (for example PR comments plus an external JSON).
Subagent review is source review, never a GitHub human approval.

The external review JSON has `repo`, full `head`, full `base`, and two `reviews`:
each has `axis` (`spec` or `standards`), distinct `reviewer`, `result: "pass"`,
and an `evidence` reference. Re-review changes when head or base changes.

Run `python ops/release_gate.py merge --help`; its default checks only, while
`--execute` performs the head-matched squash merge. It fixes the target to main
and the CI workflow to `.github/workflows/ci.yml`. Required jobs live in the
tool's REPOS mapping. Missing, failed, pending or skipped jobs reject delivery.
After merging, run the release check against all candidate merge SHAs; scheduled
workflows and old green attempts are not substitutes.

## VPS candidate

The supported VPS candidate entrance is `ops/build_vps_candidate.py`. Supply the
two full merge SHAs and a new output filename. Use the intended Python, Go, Node
and pnpm toolchain on PATH; the builder records versions and requires pnpm 10.
It exports fresh source directly from those GitHub commits, rebuilds locked Web
assets, explicitly pairs the CRM fixture with gateway Journey/CUJ tests, and
cross-builds Linux/amd64. Full Linux suites remain required in exact-SHA CI.
It packages code and versioned runtime templates, never production configuration,
credentials, SQLite ledgers, real chats or historical research binaries.

For a knowledge change, also supply `--knowledge-sha <full-merged-SHA>` to both
the release check and candidate builder. The original two-SHA interface remains
for candidates that do not change knowledge; it does not verify or package a
knowledge version. The catalog release requires all three SHAs. Knowledge CI must
pass all four `test (runner, python)` matrix jobs (Ubuntu/Windows, 3.11/3.13), not
an unrelated or aggregate `test` green light.

Three-source builds export the exact knowledge commit, run its tests, and set
`MYANC_TEAM_BRAIN_ROOT` as well as `MYANC_SPIKE_CRM_ROOT` to fresh exports. The
named catalog Engine/Brain journey must actually pass, not skip. Ambient local
knowledge paths and live-model canary flags are removed. The bundle includes
knowledge runtime/client, skill with its protocol, and non-sensitive host templates;
it excludes bootstrap/first-install scripts. Every packaged file is hashed.

An existing knowledge host must be upgraded, not reinitialized. Before a later
authorized maintenance window, reconcile installed wrapper/runtime/client/skill
hashes and any historical compatibility patches with these source versions. Back
up and retain the existing protected configuration and publication journal. Do not
rerun first installation, bootstrap seed registration, or roll a business journal
back to an earlier snapshot. Candidate creation is not cutover authorization.

The candidate manifest records source SHAs, CI, toolchain, parameters and hashes.
This command has no installation or VPS access. Existing Makefile targets remain
general development/upstream builds, not substitutes for this VPS entry.
Installation still uses the existing approved maintenance workflow and business
safety checks. Save sanitized acceptance and version mappings under `ops/releases/`.

## Emergency exception and shared state

All worktrees share `D:/MYANC/.release-state/state.json`; the tool fails closed
when it is missing, unreadable or invalid. After reconciliation, explicitly
initialize it using `release_gate.py state initialize --evidence <external-json>`.
The evidence must identify the Owner authorization, audit reference and completed
reconciliation. Initialization cannot overwrite existing state.

Only explicit Owner authorization for that incident and frozen candidate permits
repair before GitHub completion. Commit locally, freeze both SHAs and candidate
digest, validate, back up, then record `state open` with `id`, `owner_approval`,
`audit_reference`, `crm_sha`, `gateway_sha`, `candidate_sha256`, `validation` and
`backup`. The ordinary candidate entrance stays blocked until the debt is closed;
there is no persistent bypass switch or automatic installation path.

Include `knowledge_sha` when the incident candidate contains knowledge. Closing
requires exactly the repositories recorded at incident creation; a two-source
mapping cannot discharge three-source debt. Existing two-source incidents remain
compatible and do not acquire an invented historical knowledge version.

Use `state close` only after backfill. Its evidence binds the same incident and
contains `mappings` keyed by each repository: `original`, `merged`, and an audited
`evidence` reference explaining equivalence or differences. The tool checks both
merged PRs and their exact push CI before closing. Never clear debt by expiration,
restart or removing state. A stale state lock requires explicit audited operator
reconciliation; it is not automatically stolen.

## Limits

These private repositories currently lack server-enforced branch protection on
the selected free plan. This is a tested process gate, not an administrator-proof
security boundary: GitHub UI/direct commands and edited local evidence can bypass
it. Head matching protects the merge head; a base can still race after the final
check. Exact merged-SHA CI and the candidate check are required afterward.

Historical backfill uses actual recording time. An old `vcs.modified=true`
binary remains a dirty historical build; a later clean merge is not retroactive
proof of its build inputs. Keep original private one-time scripts as historical
evidence and explicitly non-reusable; store only sanitized summaries here.
