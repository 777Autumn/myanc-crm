# Final-file read binding: case B repair

The scoped B repair passes the three-case live acceptance: six actual delivered
files, all six PDF pages and all 78 final content segments were independently
checked. Source delivery and the second Mac cutover are complete. The prior
acceptance report and both failed first-live attempts remain unchanged.

## Scope and implementation

The old preparation path accepted caller-reported inspection without proving
that the actual final editable file had been returned for inspection. The repair
reuses work context, file references, render manifests and the existing file
host. A persisted read record binds work, final relative path, actual file SHA-256
and extracted-content SHA-256. Preparation and new delivery require that record;
changed bytes invalidate prior coverage. Permissions, Office/formula validation,
accepted-delivery idempotency and uncertain-send reconciliation remain enforced.

The first implementation returned a whole final file in one tool response.
Actual V27/V28 retests exposed native output truncation despite host completion.
Both are retained as process failures. The second repair returns sequential
bounded segments: each serialized host response is at most 8191 bytes (8192 with
the client newline), without shortening the content. ReadVersion 2 reaches
complete only after all segments; skipped segments reject, duplicates do not
advance, and a restart resumes persisted progress. The 512 KiB full-content limit
remains. Schema 7 reads earlier ledgers without treating legacy single-response
coverage as authorization for a new send. No business ledger rollback was used.

Host provision cannot prove downstream display or understanding. Live acceptance
therefore separately checks every actual tool output, reconstructs the content
hash, verifies final-byte identity and examines every delivered PDF page.

## Source delivery and runtime

First implementation: CRM [#171](https://github.com/777Autumn/myanc-crm/pull/171),
merge `d1849bee392870ebd46dca697c3f1e5b8b0cb536`; gateway
[#73](https://github.com/777Autumn/cc-connect-anc/pull/73), merge
`14f584609b5fcc3de796c5bc8ee742ac86671a9f`. Independent reviews and exact merge
push CI passed; this did not make its two live process failures pass.

Bounded-read repair: CRM [#172](https://github.com/777Autumn/myanc-crm/pull/172),
merge `c7044108296857eb448547fcf471953b55c105f1`; gateway
[#74](https://github.com/777Autumn/cc-connect-anc/pull/74), merge
`e766dd3475a688c69b6bebc5ea4d3c94ceadc6ec`. Distinct Spec and Standards reviews
passed on exact heads. PR runs `38837702050` / `38837712252` and exact merge push
runs `38838003732` / `38839196377` passed all required jobs, including both gateway
Mac jobs and CRM maintenance. Local full Go tests/build, CRM 633 tests (18 skips),
runtime 101 tests (29 skips) and 19 spike tests passed at their recorded inputs;
final exact-source CI covers subsequent bounded-response changes. The retained
real Word fixture reproduced an 87390-byte old response before the bounded fix.
Focused tests cover sequential coverage, restart, same-path revision and byte
limits. Earlier invalid fixtures, stale-schema assertions, boundary failures and
unrelated OpenCode timing failures remain in the local evidence.

The deployed Darwin/arm64 candidate SHA-256 is
`618d659a1005f709b36896e45e8e35a8345166286b3b89e204de4ecefa205136`;
manifest SHA-256 is `13c6df9f14dffa675be29caa964c7b801fd43dcced30e31edbc89671549b3b55`.
The second maintenance updated 14 frozen targets with 419 controls checked.
Knowledge remains `ada437cac33d156634b70b20948dc7abc09bec7e` and was not repackaged.
Its normal start was independently reviewed; the process absence interval is
bounded at 35.937–49.947 seconds, while user-visible outage is unknown. The
130.383-second stable observation is not downtime.

The first cutover had a protective startup failure involving an unidentified
physical process, followed by exactly one reviewed recovery. Its root cause
remains unknown; the retained pause-to-recovered-process interval is about
12.5 minutes. Do not describe that cutover as clean or apply its recovery receipt
to the second cutover. This report-only change requires no further deployment.

## Live acceptance

Original B material (V27), retained first-live failure material (V28), and new
post-code-freeze holdout (V29) used
fresh contexts in the two authorized private chats. Only natural file-check
requests were sent; frozen answers and tool procedures were not supplied.

| Case | Final Word / PDF segments | Delivered PDF pages | Process and actual-file result |
| --- | ---: | ---: | --- |
| V27, original B | 22 / 2 | 2 | Pass; revised v2 was reread and reinspected before sending; 14 critical fact/source checks pass |
| V28, retained truncation failure | 34 / 2 | 2 | Pass; 15 fact/source checks pass; version-conflict recovery retained |
| V29, new held-out material | 16 / 2 | 2 | Pass; discarded v1 coverage was not reused for v2; 19 fact/source checks pass |

Every final Word XML part and every final PDF text part reconstructed from the
model's actual untruncated outputs matches the downloaded file's content using
the project's pinned PDF extractor. File SHA-256, content SHA-256, final path,
work boundary, read version, complete segment counts and accepted receipts agree.
Every final PDF page was independently rendered and viewed after downloading;
the native traces also show the final-page image calls before preparation/send.
The trace collector omits image pixels, so an image-call record alone is not
claimed as visual correctness. V29's PDF text-layer ordering remains irregular;
its actual rendered pages are readable and were checked separately.

V28 prepared both requests before sending the first. Its PDF attempt then failed
with `file_version_conflict`. The assistant checked current work context, saw the
Word already accepted, prepared the PDF against the new version, and sent it
once. No extra accepted delivery or unknown outcome appears in these three work
boundaries. V29's old v1 read stopped at 3/60 segments; it was not prepared or sent.
The replacement v2 received its own complete reads and page checks. Both events
remain in the evidence; neither is silently converted into a clean first attempt.

The first-live V28 source-page issue (AF-01) did not recur in the second V28:
the intended date is attributed to source page 1. Its original failure remains.
V27 has one new nonblocking wording issue: the source's generic event was called
a wedding event. Requested dates, table counts, payment facts and provenance are
correct; this unsupported type wording is retained as V27-NB-01 for a later batch.

Post-live verification at 03:24:52 UTC found the same gateway process, sockets and
installed controls as after the second maintenance. The selected fictional
business record, its customer/handoffs and five ledger table snapshots are
unchanged. Counts remain approvals 53, staged changes 53, write intents 4, write
fences 0 and handoff events 12. This is not a whole-tenant audit. Preservation at
03:25:30 UTC confirmed all 38 original dirty files, 344 prior-round evidence files
and 1580 files from the older frozen index unchanged; the external dependency
junction was retained without traversing it.

## Remaining priorities

1. Keep source type and page attribution exact. AF-01 occurred once in the first
   V28 and did not recur; V27-NB-01 shows unsupported event-type narrowing in the
   second run. The smallest follow-up is to carry the existing source wording and
   per-claim page references through final comparison, without inventing types.
   These samples do not establish recurrence frequency.
2. Reduce the observed avoidable preparation conflict. V28 recovered safely but
   required an extra failed attempt, state lookup and preparation. Prepare each
   request immediately before its send using current work state; retain version
   rejection and status-first recovery. Do not add a generic batching framework.
3. Investigate the first maintenance startup failure separately using retained
   process evidence. Its root cause is unknown, despite successful recovery and
   the second clean start. No production rule is changed to conceal it.

Simple-query performance and unexplained waits remain a separate measurement
plan, requiring correlated client/queue/tool/host/reply boundaries before any
refactor. This file-generation acceptance is not a query benchmark or P95 claim.

## Remaining scope and limits

No production Docling/EvoOntology integration, database replacement, permission
relaxation or performance refactor is included. File and content hashes establish
identity and coverage, not semantic truth or visual understanding. Arbitrarily
small downstream output budgets can still truncate a bounded response; this is
why actual returned segments remain part of the acceptance evidence. These three
cases cannot establish reliability for every document or load pattern.

Raw fictional materials, chats, native traces, images, protected receipts,
failures and intermediate outputs remain local. The
[sanitized companion JSON](2026-10-16-final-file-read-binding.json) binds
conclusions to evidence hashes without exposing message identities.
