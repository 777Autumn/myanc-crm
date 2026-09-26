# Maintenance consolidation and pinned Claude upgrade

Status: maintenance source merged, candidate built, CLI/configuration installed;
bounded sales acceptance has first failures and a feedback-corrected revision.
Operations files and a later time explanation needed employee corrections;
private continuation is recorded separately. This continues the
[recorded colloquial trial](../acceptance/2026-09-26-colloquial-trial.md).

## Change and compatibility

Reuse the existing maintenance startup, activity and candidate paths. Complete
journal parsing now rejects omitted/null messages and keeps unknown activity
blocked. Reviewed startup and clean-exit checks move out of one-time scripts;
the three historical unsolicited INFO events remain unexplained. Frozen file
inventories distinguish old/new/partial/unknown installations. Consistent updates
run with the existing receiver stopped and start only after all files match.

The Owner approved one explicit, diagnosed recovery per candidate in the
original receipt root. The [maintenance contract](../MAINTENANCE_START.md)
defines its immutable bindings, fresh reconciliation and consumed-attempt rules.
It is not an automatic retry or permission to replay business operations.

The official native CLI artifact and its hash are pinned in
[`claude-release.json`](../runtime/claude-release.json). The managed version gate
must match it. Installers preserve all other installed managed settings, including
site-specific protections; the template is not a replacement for live policy.
Only the four listed owner/test entries receive explicit model/effort settings.
The shared CLI affects all six entries. Preserve existing authentication, native
file execution and ordinary identities; no Node or other dependency upgrade.

## Source, candidate and installation evidence

- Base: CRM `7192143e079c6e9e9ab94cbf184b482ee0be1653`.
- Unchanged gateway: `6e7c014ed3ea200007b86a6636fc76a6b9ec5e00`.
- Unchanged knowledge: `88a60ba60a634fe3d6b0f68f91de326b19a39b30`.
- CRM [PR94](https://github.com/77AutumN/myanc-crm/pull/94) was independently
  reviewed on both AI axes at head `1c6464242bb1c87450b0aafcd41618cbfa2da07a`,
  then merged as `e761f1c4eb1999652383075a2944239227839109`.
  [Exact merge push CI](https://github.com/77AutumN/myanc-crm/actions/runs/36269640051)
  passed, including Linux ordinary-identity checks.
- The normal three-source candidate contains 145 payload files. Archive SHA-256:
  `2c6e6d96f0a2d0535b849b75b163b9146c669873b5aadb101e2f21bb0265fdd9`;
  manifest SHA-256:
  `31889a7a735feebfc67bb49a0e9417d49c313ad41fcc3f6c7e57b674880ad30f`.
  It was built from fresh GitHub exports using Python 3.13.2, Go 1.25.6,
  Node 24.13.0 and pnpm 10.28.1. All seven paired CRM/knowledge journeys ran
  and passed. Local CRM: 446 tests with nine platform skips; spikes: 18 passed;
  knowledge: 71 tests with two platform skips. Skips are not local passes.
- The official 2.1.283 Linux x64 CLI has 241,556,664 bytes and SHA-256
  `1859583ce32920595c61ef868bee52e1b1594f7486db209935e01f1e5e804ae2`.
  Download and official manifest sources are pinned in `claude-release.json`.
- One normal controlled stop/install/start completed. Only the shared CLI,
  managed minimum/maximum version and four entries' model/effort options changed.
  The other two entries retained their model-selection defaults. All six ordinary
  identities reported 2.1.283; native file execution, authentication, hooks,
  permissions, Wiki, sessions and business stores were preserved.
- The stable window was **127.834 seconds / 17 samples** with a unique ordinary
  receiver, one SDK connection and all six ready entries. Recovery was not used.
  Installed inventory SHA-256:
  `d4c567a5035e27559f4fa3dd71b514aed061f58754eabd4bf1a9eb8f289d10ba`;
  successful private receipt SHA-256:
  `441a39b5a0f95ffa134b9a4112b2cde5d2ccb9cb1a98fde2f83aa9e6361b61a8`.
- Maintenance helpers came from the verified merged candidate. The unchanged CRM
  business runtime remains `482bd97092994e53fd7c3b0f4abfdffa6dc62292`; it was not
  reinstalled or relabelled as a new business runtime. Gateway and knowledge above
  remain unchanged. [Installation evidence](https://github.com/77AutumN/myanc-crm/pull/94#issuecomment-5849749282)
  distinguishes these versions.
- The known CRM sandbox blocker, earlier file-quality limits and all previous
  maintenance failures remain in the [follow-up index](../FOLLOWUPS.md).

The installation inventory binds the normal merged candidate, CLI artifact,
service identity and three changed live files (CLI, version pins, gateway options).
Rollback restores their paired runtime/configuration backups; it never restores
business databases, chat histories or artifacts to an older snapshot. New CLI
sessions are not presumed compatible with an older CLI after rollback.

## Actual model and bounded employee trial

The first sales task resumed an existing native session. Its ordinary-user process
had `--model claude-opus-5-5 --effort low`; native assistant records returned
`claude-opus-5-5`. This is actual invocation/response evidence, not model self-report.
Metadata-only evidence SHA-256:
`6f2d0ca70f2483d13b4288ab769f9e31e82a0fe57782ef5d92eca3e4321772bb`.
The process had no effective capabilities. No model or effort fallback occurred.

Operations started a new ordinary-user native session, without `--resume`, using
the same explicit model/effort. Assistant response metadata also returned the
target model. Evidence SHA-256:
`e0c1b3303fe62d568fcdaba6bcb0e367a2d27ad2fef6857940307ce4ab192d6d`.
These two actual tasks cover resumed and new sessions; six CLI version checks
do not claim six separate model-task acceptances.

The operator used the existing Feishu client, fictional project, two authorized
test accounts and Wiki v2. The task/oracle was frozen separately; expected totals
were not sent to the Bot. No Skill or output was secretly repaired during trial.

| Step | Actual result so far |
| --- | --- |
| Sales comparison, 18 tables | Actual Wiki body reads and totals 89,180 / 92,680 were correct. Word and all three Excel sheets were opened. **First result failed**: group-origin/group-delivered files were labelled private drafts, and Excel claimed private-chat input. |
| Normal change to 19 tables | The model computed 93,440 correctly, but the first pending project update would replace unresolved items with only unsigned/unpaid and lose parking, venue availability and staffing facts. It was cancelled before writing. This is a distinct first-update failure. |
| One employee correction | One message requested retention of the pending facts and corrected group/private wording; it did not supply expected totals. The new complete confirmation was approved. The Bot then automatically delivered v4 Word/Excel, using shared revision 3; no extra continuation prompt or background repair was needed. |
| Corrected sales artifacts | Word (all three pages) and Excel (all four sheets) were opened. 19 tables / 190 people, total 93,440, balance 1,560, revised times, five pending facts and group source were correct. This is **feedback-corrected business success**, not first-pass success. Word still splits a short status row across pages. |
| Operations new work | Read shared revision 3, imported and actually read the sales v4 artifacts, and read Wiki pages. Word retained the correct 19-table terms and pending facts. **First Excel failed**: five genuine calculations were stored as text, so the displayed total and balance were formulas rather than amounts. All three Word pages and five Excel sheets were opened. |
| One operations correction | Ordinary employee feedback described the display failure without supplying expected amounts. The Bot returned v6 Excel with five genuine formulas and numeric caches; total 93,440 and balance 1,560 were visible in Feishu, with the total formula also verified in its formula bar. All other business cell values stayed unchanged; original v5 files remained. This is **feedback-corrected success**, not first-pass success. The overview title still says v5; filename and source note correctly say v6. |
| Private supplement | The test account requested a private personal reminder and explicitly prohibited sharing. The Bot replied only in that private chat. Bounded native evidence showed no tool call; all shared case versions and artifact rows matched the saved pre-private baseline. |
| Owner readback | The owner re-read the latest shared revision and sales/operations files, with correct current tables, amounts, pending facts and no private reminder in the displayed answer. **First explanation failed**: it described an 11:00 inspection finish and 11:30 welcome as adjacent. One employee correction led to the accurate 30-minute minimum gap, versus 45 minutes for the unchanged 11:45 plan. The corrected explanation distinguishes minimum buffer from extra slack. No project update or new file was requested. |

The bounded privacy audit checked the owner's actual input, tool results and
output, not only the visible reply. All shared case versions and artifact rows
stayed identical through both readback turns. Owner readback used a new native
session, then resumed that session for the correction; the earlier sales task
separately proves old-session continuation. Audit SHA-256:
`37cb05da7b97e11ed77bbb3cb178af629b4b63a8269e9ede829819b2db6a8aad`.

The trial used eight employee text messages, including three corrections and one
normal requirement change; one incomplete proposal was cancelled and one corrected
proposal confirmed. There were no backstage business-file, Skill or state repairs.
One local test firewall dialog interrupted desktop operation; the Owner cancelled
it and no network permission changed. UI targeting retries are recorded separately
from employee messages and model waiting.

Receipt timing from the observed send (rounded to seconds) to both files accepted
was about 129 seconds for the failed sales first draft and 131 seconds for the
failed operations first draft. Corrected sales files arrived about 94 seconds
after the valid confirmation; corrected operations Excel arrived about 39 seconds
after feedback. File acceptance is not quality acceptance. Recorded file-viewing
intervals were approximate (sales first 20:49–20:55 UTC, corrected sales
21:01–21:03, operations first 21:11–21:15); the later Excel fee check was around
21:22. Audit, account switching and developer interruptions are not employee
efficiency gains. No speed comparison or long-term stability claim is made.

Final business-use artifacts, with original and failed versions retained:

| Artifact | SHA-256 |
| --- | --- |
| Sales Word v4 | `fd8c0059b91efc34b8602254fe80a06093490a43c059d945ded52f67e3607d7f` |
| Sales Excel v4 | `e39113ce3d8e36a67662b66ffed403a788b23b543f067fd48fd78bbbc0ce72dd` |
| Operations Word v5 | `d7c8aab87248ea737adeabb63fd97604c9963894a8d504277e8360a6e79d575f` |
| Corrected operations Excel v6 | `1b89363b7332f5cc552cf5b4c1b1904bd15cbd9494eaee8200bf762751eb7700` |

Source diagnosis identified a pre-existing gateway prompt defect: the referenced
work branch applied `preserve private scope` to group replies as well as private
ones. The actual native input and generated files confirm that path. It is not
attributed solely to low effort or the CLI upgrade. The minimal correction in
[gateway PR39](https://github.com/77AutumN/cc-connect-anc/pull/39) was independently
reviewed at head `6bc774ebdb151f1f7ae7a26960c36620d8a07e3f`, passed
[PR CI](https://github.com/77AutumN/cc-connect-anc/actions/runs/36271730344),
and merged as `9ec266d37bf7adb5779197c930e9c62dcad15312`. Merge CI and candidate
preparation are tracked in that PR. It has not been installed during this trial.

The operations formula failure came from its generated workbook helper forcing
single-equals formulas to text. The existing rule already required preserving
legitimate formulas, but the first self-check only recalculated totals outside
the workbook. Feedback caused a saved-file cell-type/value comparison. No new
platform, dependency or silent backend repair was introduced. Reliable uncoached
first delivery remains a quality limit.

A read-only snapshot briefly saw an empty prepared artifact row. Exact work and
request-key correlation placed the snapshot between the v6 delivery call and
its accepted response; the same row subsequently contained the confirmed v6
receipt/hash. No extra or unknown send was evidenced; the intermediate snapshot
remains preserved.

During sales, one combined read-only Bash request was rejected by the existing gateway
`bypassPermissions` handling after the CLI requested tool approval. The model
then used an allowed separate read and completed the task. Owner readback had a
similar compound workbook-read denial followed by a successful allowed read.
No technical approval
card was sent to the employee. The CLI's underlying reason was not recorded;
neither a specific permission cause nor a CLI compatibility defect is inferred.

The generic activity classifier still does not automatically reconcile all old
card events. This maintenance used an independent exact-prefix review of two
completed updates and one cancelled invitation. The three older unknown INFO
events belong to a different failed invocation and remain unexplained.

Trial receipts and original artifacts stay in the private evidence directory;
only de-identified results and hashes belong in GitHub. Initial failures are
retained. Operational stability beyond this window, real-company use, the blocked
CRM sandbox and reliable uncoached document quality remain unverified.
