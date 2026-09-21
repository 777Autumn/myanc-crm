# Natural private file work — controlled acceptance

Recorded 2026-09-21. This supplements, and does not replace, the earlier
[file-loop evidence PR #43](https://github.com/77AutumN/myanc-crm/pull/43).
Scope: the existing Bot, `test-private`, one authorized test account, fictional
wedding sales / banquet execution / channel operations material. The operator
used Computer Use in the existing Feishu client. This is AI-operated acceptance,
not independent employee sign-off or validation of every employee workflow.

## Exact delivered sources

| Repository | PR | Reviewed base → head | Squash merge / required push CI |
| --- | --- | --- | --- |
| cc-connect-anc | [#21](https://github.com/77AutumN/cc-connect-anc/pull/21) | `8732fbb19a0f62c78a64a433910d0f6c6a8986f7` → `004584453ba2f3f4c85336308b715efe72ad8b1b` | `1445820137b1689f8d7eefe6ed48b3e90bc6cc62` / [all five jobs passed](https://github.com/77AutumN/cc-connect-anc/actions/runs/35602645650) |
| myanc-crm | [#44](https://github.com/77AutumN/myanc-crm/pull/44) | `75b7126b9aea39db03544db0df10849cd8afeccb` → `3851cc46d38220bb2555ca74b599170df7f09012` | `6df128891eaf3a8c23ded45c0718a1509a68f86a` / [passed](https://github.com/77AutumN/myanc-crm/actions/runs/35602668558) |
| myanc-crm, minimal hash workflow follow-up | [#45](https://github.com/77AutumN/myanc-crm/pull/45) | `6df128891eaf3a8c23ded45c0718a1509a68f86a` → `2d0de42aa4686e362a5d2454cadaca3b84bd7b34` | `d3913043122e5da85ef597829453014d5694734b` / [passed](https://github.com/77AutumN/myanc-crm/actions/runs/35606656199) |

Knowledge remains `88a60ba60a634fe3d6b0f68f91de326b19a39b30`, with its existing
[four required matrix jobs passed](https://github.com/77AutumN/myanc-team-brain/actions/runs/34704220632).
No knowledge source or publication journal was changed.

Independent **AI** Spec and Standards reviews are attached to the exact source
pairs: [gateway](https://github.com/77AutumN/cc-connect-anc/pull/21#issuecomment-5760727981),
[wedding Skill](https://github.com/77AutumN/myanc-crm/pull/44#issuecomment-5760273212),
[hash workflow](https://github.com/77AutumN/myanc-crm/pull/45#issuecomment-5761372431).
These are source reviews, not GitHub human approvals. Release gates and each
exact merge-SHA CI passed before normal candidate construction.

## Candidate and installation

Both candidates came from `ops/build_vps_candidate.py` using fresh exact GitHub
exports, locked assets and paired CRM / gateway / knowledge tests. Toolchain:
Go 1.25.6 (Windows/amd64 host; Linux/amd64 target), Node 24.13.0, pnpm 10.28.1,
Python 3.13.2. Each manifest lists and hashes 88 files; no live configuration,
credentials, chats, business originals, ledgers or backups are packaged.

| Candidate source combination (CRM / gateway / knowledge) | Archive SHA256 |
| --- | --- |
| `6df12889` / `14458201` / `88a60ba6` | `53eca6cfa8d0a34eee3a37d095ae8334c2ac1118219f6ac7fbcd68588c574cc7` |
| `d3913043` / `14458201` / `88a60ba6` | `14142721a9746f20edb64640b4f7950c438d6aab8362e01b72bcd17edf5f61a2` |

The first authorized maintenance installed seven candidate files through the
existing maintenance workflow. Startup identity, a stable health window, one
receiver, zero effective gateway capabilities and preserved business state were
checked. Existing ordinary accounts, permissions, authentication, network and
document dependencies were retained. File capability remains confined to the
authorized private test project; other projects were not enabled.

The second candidate differs only in `ops/skills/team-files/SKILL.md`. After the
quoted sales task completed, that one candidate file was installed with a
private backup and exact old/new hash checks. Service identity, restart count
and file ownership/mode remained unchanged; no second restart was performed.
Installed gateway SHA256: `c2619c880e2072fdbe185a71c632a743769c546def7f653fd5b8b0d0e743f6b6`.
Installed file Skill SHA256: `a205f5865470a6c80e14871ad1fb988f2ca92578a1fbcdb8973982ccb49b6aaa`.

Rollback is a separately controlled maintenance operation: restore the backed-up
code/Skill versions, verify hashes and use the existing startup checks if the
binary changes. Do not restore or rewind business ledgers. No rollback occurred.

## Actual conversations and artifacts

The employee-facing test messages contained ordinary work requests, with no
Skill names, slash commands or work identifiers. `team-banquet` and the existing
knowledge/file tools were selected by Claude. Versioned fictional material is
`DEMO-VENUE-001` v1.0 (2026-09-21). Actual company knowledge read results were
observed for service boundaries / banquet terminology; fictional hotel figures
were not presented as company policy. Raw source text and chat/tool traces stay
in protected local evidence, outside GitHub.

| Journey | Actual result | Limits |
| --- | --- | --- |
| Sales | Word and Excel received and opened. 20-table totals 81,600 / 93,600; unquoted 22-table revision 89,560 / 102,760 with 2,760 over budget, no invented discount. Previous files retained. Word table pagination improved on request. | Three inline Python hash approvals required operator assistance during the revision. |
| Execution | Explicit new-work phrase created a separate work. Busy supplement was acknowledged only after saving; private snapshots captured queued → started → completed. Initial and revised Word received and opened. Revision has 22 tables, one main table, 11:30 reception, 12:30 meal, 14:00 finish and the 1.5-hour meal risk. | Faults were not injected into the live service. |
| Return to sales | Quoting the earlier Bot **text** reply selected the original sales work, preserving 22 tables / 100,000 budget. A third Word added a highlighted excluded-cost warning. Execution remained at its own two versions. | One additional inline Python hash approval required operator assistance. The document's internal heading still says v2; delivery filename/history distinguish v3. |
| Channel operations | Word and Excel received and opened. Totals: 10,500 spend / 110 leads / 58 valid / 26 visits / 6 bookings. Zero-denominator channel costs are not computable, not zero. Three draft advertisements and follow-up cohorts (20 visited-but-unbooked, 32 valid-but-unvisited) are grounded in the fictional input. An unquoted request changed only the first Word advertisement, preserving the workbook and old Word. | No permission card on either turn after PR #45. Suggestions were not executed or published. |
| Return to execution | Quoting the earlier execution **file** returned to its original work and produced Word v3. The later reception start and unchanged one-hour reception duration were corrected; 22 tables and the 1.5-hour meal risk remained. The downloaded text diff contains only the title version and those two paragraphs. | No permission card. Two section headings still say v2, although the title and delivered filename say v3. |

The four hash approval cards were inspected and individually approved; no
session-wide permission was granted. PR #45 subsequently directs new file work
to the already-installed `sha256sum` and avoids repeated inline Python hashes.
This does not relax Claude permissions or bypass an outstanding approval.
The subsequent operations task used `sha256sum` for both initial delivery and
old-file verification / revision without approval cards. Earlier assisted turns
must not be reported as entirely unattended; this does not guarantee that every
future Claude tool call will avoid a legitimate approval.

All 11 returned files (five sales, three execution, three operations) were opened
in Feishu and downloaded through its UI. ZIP/XML checks and SHA256 matching to
host snapshots and accepted, work-bound receipts passed; originals and previous
versions remain. The [sanitized artifact manifest](2026-09-21-natural-file-artifacts.json)
records every hash, delivery version and check scope. Seven files additionally
have targeted value/text/formula assertions; this is not an automated assessment
of every business statement. The earlier PR #43 work and four artifacts remain
intact. Final session snapshots show the busy supplement completed, with no
pending inputs for the three exercised works.

Content review found an execution-v2 wording error: a one-hour reception shifted
by 30 minutes was called "compressed", and one sentence called the later start
"earlier". A reply to the actual old execution **file** corrected both in v3,
which was received, opened and downloaded. This is a generated-draft quality
issue, not evidence that the transport selected the wrong work. Four temporary
directory Write attempts were denied and recovered within the normal workspace;
one v3 text-replacement attempt found no match and was corrected before delivery.
These failed attempts remain in the private trace; permissions were not widened.

The operations workbook contains 38 uncached formulas and requests full
recalculation on open. Feishu preview displayed correct totals, ratios and
zero-denominator labels; the known SUM/IF/subtraction expressions were checked
against the fixture. The initial blanket offline "all formulas cached" check
failed: do not claim compatibility with readers that only consume cached
values (for example `openpyxl` with `data_only=True`). No formula was removed to
make the check pass.

## Regression evidence and remaining scope

The source CI and normal paired build, rather than two unrelated green badges,
cover the exact dependency combination. Relevant gateway tests include:

- `TestFileTurnPersistsBeforeAcknowledgmentAndRetainsCrashStates`,
  `TestFileTurnStorageFailureIsReportedAndCorruptionPreserved`,
  `TestFileQueueAcknowledgesOnlyAfterDurableSave`;
- `TestFileRecoveryRequiresExplicitContinueAndStopsOnUnknownDelivery`,
  `TestCUJ_FileSupplements_RestartWaitsForContinueWithoutReplay`,
  `TestDeliveryUnknownFailedAndRestartNeverResend`;
- `TestCUJ_FileSupplement_TurnFinishesDuringIntake`,
  `TestCUJ_FilePrivateConversation_SupplementTextReplyAndNewWork`,
  `TestFileStopPreservesOtherWorkSupplements`,
  `TestFileRecalledSupplementRemainsStoppedAfterReload`;
- `TestTextReplyAssociationPreservesScopeAndOriginalRoute`,
  `TestPendingAttachmentIsHostOnlyUntilItsTurnAndActivationIsIdempotent`,
  `TestNativeFileWorkOrdinaryIdentities`.

Save failures, duplicate delivery, crashes/recovery, explicit stop, unknown send
results and cross-work/account scope were tested offline. Linux suites are the
required CI evidence; the full Windows suite is **not** claimed green (existing
PTY/POSIX/symlink assumptions). No repeated live-service restarts were used for
fault testing.

The final bounded audit covers 2026-09-21 13:18:34–14:16:00 UTC, three native
sessions and 121 tool calls with paired results. Independent AI inspection of
the scripts, tool paths and deliveries found no out-of-scope write or alternate
sender. A separate read-only comparison of six existing stores found only two
new knowledge-read audit rows: earlier reads, business/publication tables,
control files and policy directories matched their frozen or installed state.
The same gateway process remained active with no additional restart. The AI
reviewer inspected these receipts; it did not independently rerun the database
comparison. Raw traces, store snapshots and identifiers stay outside GitHub.

PPT/PDF/image generation, real template compatibility (including PAGE/TOC fields),
multiple employees and independent employee acceptance are not verified here.
No external quotation/commitment, formal business write, expanded approval
platform, new sender API, queue service or additional runtime dependency is in
scope. The implementation reuses session JSON and the existing file host.
