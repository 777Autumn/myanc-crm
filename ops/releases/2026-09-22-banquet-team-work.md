# Linked fictional banquet team acceptance

Recorded 2026-09-22 (Asia/Shanghai). The existing Owner and test accounts used the
existing Bot and test group through Computer Use. Sales preparation, selecting A,
cross-account execution handoff, timing revision and capacity clarification ran
with real model calls and real DOCX/XLSX delivery. Seven linked-source files were
opened and downloaded. This is AI-operated acceptance, not employee sign-off or
connection to a real hotel's operations.

The final combined handoff is usable on its own after one explicit follow-up.
The earlier sales spreadsheets omitted detailed draft times; do not treat this
as evidence that every first draft automatically satisfies the handoff checklist.
The [previous two-account evidence](2026-09-22-group-file-work.md) remains intact.

## Source, CI and candidate

| Change | Reviewed base / head | Merge and required push CI |
| --- | --- | --- |
| [CRM #53](https://github.com/77AutumN/myanc-crm/pull/53), linked fixture and handoff | `1f8d410d45a727e881663ffcd77369bd15477f02` / `2cfe3d4d8c21e47c644b7bd163c6c45ac01c0d63` | `c4acdb08ee1abf7f9f727cfbf7153e1f0ee20fb4`, [35654725348](https://github.com/77AutumN/myanc-crm/actions/runs/35654725348) passed |
| [CRM #54](https://github.com/77AutumN/myanc-crm/pull/54), explicit fixture selection | `c4acdb08ee1abf7f9f727cfbf7153e1f0ee20fb4` / `9fd79093c6e169dfeba6f1c12c8594e2a5427664` | `d9d9b83a561fdd61071bb516bcbebbe31c5022a8`, [35656971381](https://github.com/77AutumN/myanc-crm/actions/runs/35656971381) passed |

Independent AI Spec and Standards reviews are preserved on
[#53](https://github.com/77AutumN/myanc-crm/pull/53#issuecomment-5767451067) and
[#54](https://github.com/77AutumN/myanc-crm/pull/54#issuecomment-5767715371).
Both used the normal release gate; these are source reviews, not human approvals.
#54 PR CI [35656830805](https://github.com/77AutumN/myanc-crm/actions/runs/35656830805)
also passed. The actual runtime combination is:

- CRM candidate source: `d9d9b83a561fdd61071bb516bcbebbe31c5022a8`.
- Gateway unchanged: `ee7afd38ec40dc4d95f3d02084dfb5f3b6c72523`, exact CI
  [35642199523](https://github.com/77AutumN/cc-connect-anc/actions/runs/35642199523).
- Knowledge unchanged: `88a60ba60a634fe3d6b0f68f91de326b19a39b30`, four required
  matrix jobs passed in [34704220632](https://github.com/77AutumN/myanc-team-brain/actions/runs/34704220632).

The normal builder exported these three exact commits from GitHub. It passed CRM
331 tests (seven existing platform skips), 18 spikes, knowledge 71 tests (two
existing skips), and all four paired CRM/knowledge Journey/CUJ tests. Three
targeted banquet tests passed, including linked references, calculations/capacity
and old-case compatibility. Full Linux coverage remains exact-SHA CI evidence.

- Final candidate: `candidate-d9d9b83a-ee7afd38-88a60ba6.tar.gz`, 30,812,719 bytes.
- SHA256: `20ca1eabc7b506484f5891a102a2122149606f10838d9c9955b4885dc7cf49bc`.
- All 98 archive files matched the frozen manifest, with no extras.
- Toolchain: Go 1.25.6, Node 24.13.0, pnpm 10.28.1, Python 3.13.2.
- Private manifest/build/maintenance/acceptance evidence:
  `D:/MYANC/file-loop-evidence/banquet-team-20260922/` (final candidate in `routing/`).

The earlier #53 candidate was 30,812,656 bytes, SHA256
`94db0dc5286a539c0db9bdd83de8d156542e82a71e8b80038405a5665a2afe25`.
It is retained with the first unsuccessful linked-source attempt, not relabeled
as the final candidate.

## Narrow installation and first failed attempt

#53 installed the Skill entrypoint and two linked references into each of the two
existing group workspaces (six targets). The first live request loaded the new
Skill but read the old standalone venue fixture. Its Word/Excel were delivered
and preserved; they do not pass linked-team source acceptance.

#54 makes selection of the linked team/customer/handoff reference explicit before
drafting. Only the two existing Skill entrypoints were updated in its maintenance
step. Both subsequent model traces loaded the linked Skill, read its Markdown and
JSON and kept source `DEMO-TEAM-001`, version 1.0. No gateway/knowledge code, account,
permission, dependency, credential, network setting or business rule changed.
There was no service stop/start or second receiver in either step.

- Installed Skill SHA256: `2a02098da4643c894bac046382c6ab104f52614a148c8793b2ede877ef980a54`.
- Linked Markdown: `1e51cd6aaf0217505c5eeafe6be6d419e43cceb94c9526a70b954adf3ba5005b`.
- Linked JSON: `b0148702ef79c8ce3115972d48bf5d30a93c35f466d31e80062a826403497c7a`.
- Unchanged gateway binary: `859bb6efbf9930ba7c835be0343b9c96dcd8349620bb1d1f18fd7ffb5a68cec4`.
- Frozen one-time #54 maintenance script:
  `36bd835cdf236262097868906d457ff2e41ae75c0cecc9900ced0b9231d403a9`.

Raw one-time scripts, configuration, logs and backups are private and must not be
repurposed as installers. Existing gateway/model identity separation remains unchanged.

## Actual work and results

The full observation window was 2026-09-21 21:12:00–22:13:55 UTC; the linked-source
rerun began at 21:30. Requests used ordinary work descriptions and native file
replies, without Skill names, commands or work numbers.

| Step | Checked result |
| --- | --- |
| Owner sales v1 | Word and Excel for 20 tables/200 people: A 81,600, B 93,600; budget balances 18,400 and 6,400. No package selected; date availability remains pending. |
| Owner sales v2 | 22 tables/220 people, explicitly selected A: 89,560, leaving 10,440. B remains unselected comparison: 102,760, over budget by 2,760. Old versions preserved. |
| test quotes Owner's latest Excel | The host imported the exact accepted v2 Excel snapshot; a separate test work read it and produced execution v1 for selected A/22 tables with roles, times, source/version and pending items. It also read the versioned team source, not Owner's private history. |
| test quotes execution v1 | Execution v2 moves reception to 11:30 and meal to 12:30, retains 14:00 finish, 09:00 setup and 10:30 check. It flags the 1.5-hour meal window and asks catering to confirm 22-table service capacity; budget stays 89,560. |
| test requests 26 tables | Claude identifies the 24-table limit and 105,480 total, 5,480 over budget. A business clarification offers alternatives. The operator chooses to retain 22 tables; no executable 26-table revision is delivered. |
| Explicit completeness follow-up | Quoting execution v2 produces a combined sales/execution handoff, filename business v1, host work version 3. Eight sheets contain current facts, A/B budgets, every current time, roles, source 1.0, version history, unadopted 26-table request and pending risks. It preserves prior files. |

The [artifact checks](2026-09-22-banquet-team-artifacts.json) record all nine real
downloads: two from the failed initial source selection and seven from the linked
journey. Every download matched an accepted receipt and immutable snapshot; inputs,
original outputs and earlier versions remained intact. Recipients were fixed to
the same test group. Employee-facing file versions are per document; host versions
are per work, not one global counter.

The sales v1/v2 Excel files only contained the event date/lunch designation and
referred to Word for detailed draft times. That violated the intended standalone
handoff quality. Execution read the versioned source for those draft times; the
explicit follow-up repaired the final combined artifact. This did not change the
Skill again and does not prove the first-draft omission is eliminated. Sales Word
v2 predates the later execution time change; use the final combined workbook for
current conditions, not an older document in isolation.

63 scoped native tool calls/results were paired (four Skill, eight Read, 45 Bash,
five Write, one AskUserQuestion). Two Owner tool errors were recovered inside the
allowed workspace. No malformed/unscoped trace events or unmatched calls/results
were found. No technical permission cards were observed; gateway counts show zero
technical permission events and two layer records for the single business question.
The resolved choice and final answer were observed in Feishu and native trace.

Six formal business/knowledge stores were unchanged from the pre-install baseline;
installed controls, directory policies and Skill hashes matched. The gateway stayed
on the same process with zero automatic restarts, one receiver and its existing
owned listener. The old private idle helper returned `busy_session`: it counts the
business-question callback's empty message ID as an unfinished turn. This failure
is retained, not called a pass. Separate bounded correlation found seven real
messages, seven completed turns and one resolved callback. No installation or
service action was performed after this closeout helper failure; a future
maintenance precheck must reconcile it before proceeding.

## Limits and rollback

All company/venue/customer data in this trial is explicitly fictional, versioned
exercise material, separate from formal knowledge and CRM. It does not validate
live availability, real prices, customer commitments or SaaS read/write access.
Current CRM approval requirements remain unchanged. Different works of one account
are not independent OS sandboxes. This trial does not extend to other employees.

Feishu previews opened all files and displayed recalculated budgets. The workbook
totals and literal formulas were independently checked from downloaded XML; no
generated code or formulas were executed by the checker. Desktop Excel and readers
requiring formula caches were not tested. PAGE/TOC and other DOCX fields remain
rejected, never silently removed; desensitized real-template compatibility remains
unverified. PPT/PDF, acquisition workflows and broader rollout were not retested.

Rollback is a scoped restoration of the changed Skill/references from protected
maintenance backups. Keep the schema-2-aware gateway, ledgers, original materials,
snapshots and all versions; never rewind business records. This evidence-only
commit changes no runtime and requires no additional candidate or installation.
