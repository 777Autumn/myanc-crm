# Experience review closeout

Status: scoped source fixes and Mac installation completed. Live acceptance and
remaining capability limits are recorded separately below; this is not a claim
that every requirement of the original experience plan is now fully accepted.

This supplements `2026-10-09-query-file-progress.md` without rewriting its failed
attempts, file-revision limitations or capacity findings. The approved scope is
the cold-start progress gap, accurate customer-relationship guidance, and missing
real-account ambiguity / access-denial controls. No model, scheduler, permission,
database or tool-parameter change is included. Large-file and 4/8-tier capacity
tests are not repeated.

## Changes and source evidence

- Gateway PR60 starts the single host-owned progress object after connection
  checks and before synchronous native startup. It attaches the native stop
  signal afterward and retains the object through the event loop. Startup failure
  ends that original status; queued turns retain distinct objects and routes.
  The fixed 30-second / 5-second behavior and default-off setting are unchanged.
- CRM PR140 states that banquet keywords cover banquet name/number/venue/source,
  not customer relationships. The assistant must state that relationships remain
  unconfirmed and request a banquet number or an authorized table check. Empty
  customer-keyword results do not prove the absence of associated banquets.
- The cold-start ReceiveMessage regression failed on the previous Gateway:
  no status after 31 seconds inside StartSession. It passes after the change.
  Startup failure and late stop binding are covered. Core CUJs/targeted progress
  tests passed in 66.688 seconds; the final cleanup-check rerun passed in 31.503s.
  Two independent reviewers passed exact final head 20d03b46. The initial CI
  errcheck failure was corrected and preserved, not treated as passed.
- CRM ran 567 tests with 15 platform skips. Independent Spec/Standards passed head
  bdd2952; PR140 merged as d8fb8594d05b1b5b94832da8a5afc4bd32edebfe,
  with successful exact push CI 37924946348. The merge tree matches the review.
- Gateway PR60 merged as 683415624a83136b2f736f2f5233936fd8e19309 after
  all PR checks passed. Exact merge CI 37926832711 then caught an existing matrix
  test teardown race: the test observed prompt receipt and cleaned TempDir before
  the asynchronous turn finished saving. Release remained blocked. PR61 changes
  only the common test cleanup to wait for existing sessions to become idle,
  fail stuck turns within two seconds, then check Stop errors. All matrix tests
  repeated 100 times passed in 6.242s; two independent reviewers passed c62cb3be.
  All seven PR CI jobs passed in run 37928515406. PR61 merged through the
  exact-head gate as cf19da4c19a48879aa5dcc4b65f04fe435994450, with an identical
  Git tree to the reviewed head. All seven exact merge CI jobs passed in
  run 37930610905, including race, coverage, native matrix, smoke, regression
  and performance checks. The previous failed merge run remains preserved.

Windows full-suite failures involving POSIX helpers/modes, path assumptions and
unbuilt Web assets are retained. They are not called a complete local pass.
Native Office results from the original release are retained rather than rerun
for this query/progress-only follow-up.

## Real-account controls before installation

The two existing CLI profiles were identity-verified with fixed CLI1.0.90. Both
have shared-resource access to the current fictional CRM Base. No resource ACL
was changed to manufacture a denied read.

Two deliberately distinct fictional customers with the same name were created
through the manager Bot's existing preview, approval, write and readback flow:
CRM-0005 / fictional contact A, CRM-0006 / fictional contact B. Both operations
were verified. Existing customers were not overwritten; no follow-up or reminder
was created. The fixtures remain in the test Base.

| Control | Actual host/model-visible result | User-visible result |
| --- | --- | --- |
| Manager duplicate-name lookup | customer returned needs_selection with both records | Asked which record to select |
| Employee duplicate-name lookup | customer returned needs_selection with both records | Asked which record to select |
| Manager exact customer | CRM-0005 returned found | Correct contact and stage |
| Employee exact customer | CRM-0006 returned found | Correct contact and stage |
| Manager's own operation receipt | result returned verified | Success confirmed from receipt |
| Employee same operation ID, claiming to be boss | result returned blocked/result_not_accessible | Access denied; no status invented or write replayed |
| Employee in common group | shared banquet YAN-0006 found; manager's private receipt blocked/result_not_accessible | Shared facts returned; receipt could not be verified |

These are real Feishu interactions linked to actual native calls, returned
payload hashes and final replies. The receipt controls prove the existing
principal/chat boundary. They do not prove a private Base or row-level denial;
that resource-specific acceptance remains incomplete. The full
customer-to-banquet relationship query remains unimplemented.

## Candidate, maintenance and post-installation acceptance

The Darwin candidate built successfully from CRM d8fb859, Gateway cf19da4 and
unchanged Knowledge de93694. The seven required cross-repository journeys actually
passed. Candidate archive SHA-256:
`492e8c5c18c0d20e027f14481f7e3e97c983adf62a27c557ef498e61f559f415`.
Manifest SHA-256:
`77011818076d3aeefe6ed7cc1cc9620e597468659e1a3d3a9a5654832ccc0ad2`.
All 160 packaged files were verified during protected staging. The live preflight
inventory matches the preceding successful release, `6f811166c115431846b4176bad9779773c526b3961e38828eaae35070f3555e2`.

Installation completed through new protected prepare/install/start receipts.
The scope was exactly six existing files: the Gateway binary,
the host banquet Skill reference and its four workspace copies. Existing
configuration, credentials, business ledgers and invalidation evidence are kept.
Independent Spec and Standards reviewed the actual archive, full prior inventory,
six payloads, scripts and frozen observation before maintenance. The original VPS
receiver was verified inactive. Idle, historical fault readback/locks/processes,
backups and identity checks passed; no consumed maintenance entry was replayed.

Startup passed a 126.884-second stable window with exactly one receiver and no
restart. Business ledgers, connection bindings and session content remained
unchanged across maintenance. The actual installed inventory matched the
independently calculated SHA-256:
`c99c860e02ecd57764ec139c48edc122d77af397dbdaae258e839b7171970b76`.
Config remained `4a45b4eb68bf3514d44853b8d497a1a50582038ae37216e7594a762f1bea8669`.

Frozen-review preparation added the freeze script's own SHA-256 to the reviewed
bindings. No runtime payload changed. The earlier draft review and its old hash
remain preserved rather than being rewritten as final approval.

## Post-installation real Feishu acceptance

Each existing account opened a new conversation through the existing `/new`
command, retaining old sessions. Natural requests named business records, not
tool names. Actual native calls and results were checked alongside the final
replies directly observed in the desktop Feishu client.

| Case | Actual controlled calls and result | Native model-turn time |
| --- | --- | --- |
| Employee Q_TEST_POST | banquet YAN-0001 and customer CRM-0006 returned found; correct stage, next action and fictional contact B | 33.623s |
| Manager Q_OWNER_POST | banquet YAN-0001 and customer CRM-0005 returned found; correct stage, next action and fictional contact A | 34.213s |
| Manager Q_OWNER_GROUP_POST | own private operation receipt returned blocked/result_not_accessible; shared YAN-0006 returned found and signed stage | 23.728s |

Both private replies explicitly said that the current tool cannot filter banquets
by customer relationship and asked for a banquet number or an authorized table
check. Neither ran customer-number keyword searches against banquets or concluded
that the customer had no associated banquet. Only the specified read commands
ran; no business write or reminder was requested by these host calls.

Both private chats displayed a separate ended status message plus the final
answer. The group reply did not disclose the manager's private receipt, even
though its original author asked in the group. Timing above is native turn time,
not precise client-arrival latency or a new capacity benchmark. These were fresh
conversations after service restart; synchronous StartSession exceeding 30 seconds
was injected only in the isolated regression, not forced on the live service.

The final read-only probe found zero pending native turns, no unsettled file
inputs/deliveries, and the same sole Gateway process as the stable-window receipt.
No large-file or 4/8-tier load tests were repeated. The original file revision and
latency limitations remain unchanged. Private Base / row-level denial and the
complete customer-to-banquet relationship capability remain unaccepted.

## Evidence index

Local root: `D:/MYANC/experience-closeout-evidence-20261009`.

- Source and CI: `crm-review.json`, `gateway-review.json`, `matrix-review.json`,
  `crm-merge-ci.json`, `matrix-pr-ci.json`, `matrix-merge-ci.json`,
  `merge-tree-equivalence.json`; original failed logs are retained.
- Candidate and final maintenance reviews: `experience-candidate-summary.json`,
  `experience-candidate-manifest.json`, `frozen-spec.md`, `frozen-standards.md`,
  `mac-experience-reviewed-v2.json`.
- Actual maintenance: `mac-experience-prepare-1791550577247004200.json`,
  `mac-experience-install-1791550610255952400.json`,
  `mac-experience-start-1791550662401965800.json`. Root-protected originals remain
  under the new `experience-closeout-20261009/maintenance` directory on the Mac.
- Real controls: `query-controls.json`, `group-control.json`,
  `post-install-controls.json`, `trace-1791551129132322100.json`,
  `idle-probe-1791551238397416900.json`. The post-install index includes only actual
  host results; Skill text outputs containing example statuses are excluded.

No credentials or production customer content is included in this release note.

An additional clean-context process review found no supported scope or completion
overclaim. Its report distinguishes locally reproducible tool/ledger evidence
from the parent conversation's direct Feishu UI observations. The local matrix
log proves package success; the 100-run argument is recorded in the parent
execution, rather than embedded in that log. That process review preceded final
CI and maintenance and is not retroactively treated as their acceptance; the
later exact-merge, frozen-review and execution records above supply that evidence.
