# Maintenance consolidation and pinned Claude upgrade

Status: maintenance source merged, candidate built, CLI/configuration installed;
bounded sales acceptance has first failures and a feedback-corrected revision.
Operations/private continuation is still pending. This continues the
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

The operator used the existing Feishu client, fictional project, two authorized
test accounts and Wiki v2. The task/oracle was frozen separately; expected totals
were not sent to the Bot. No Skill or output was secretly repaired during trial.

| Step | Actual result so far |
| --- | --- |
| Sales comparison, 18 tables | Actual Wiki body reads and totals 89,180 / 92,680 were correct. Word and all three Excel sheets were opened. **First result failed**: group-origin/group-delivered files were labelled private drafts, and Excel claimed private-chat input. |
| Normal change to 19 tables | The model computed 93,440 correctly, but the first pending project update would replace unresolved items with only unsigned/unpaid and lose parking, venue availability and staffing facts. It was cancelled before writing. This is a distinct first-update failure. |
| One employee correction | One message requested retention of the pending facts and corrected group/private wording; it did not supply expected totals. The new complete confirmation was approved. The Bot then automatically delivered v4 Word/Excel, using shared revision 3; no extra continuation prompt or background repair was needed. |
| Corrected sales artifacts | Word (all three pages) and Excel (all four sheets) were opened. 19 tables / 190 people, total 93,440, balance 1,560, revised times, five pending facts and group source were correct. This is **feedback-corrected business success**, not first-pass success. Word still splits a short status row across pages. |
| Operations new work and private supplement | Pending; no success claimed. |

Source diagnosis identified a pre-existing gateway prompt defect: the referenced
work branch applied `preserve private scope` to group replies as well as private
ones. The actual native input and generated files confirm that path. It is not
attributed solely to low effort or the CLI upgrade. A minimal source correction
is being prepared separately; it has not been installed during this trial.

One combined read-only Bash request was rejected by the existing gateway
`bypassPermissions` handling after the CLI requested tool approval. The model
then used an allowed separate read and completed the task. No technical approval
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
