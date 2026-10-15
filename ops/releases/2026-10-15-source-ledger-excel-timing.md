# Source ledger, XLSX recovery and query timing verification

Status: **functional acceptance failed; verification complete**. Source delivery
and the candidate 05 runtime switch are verified. Document-output failures remain;
the completed evidence review does not turn those outcomes into passes.

## Scope

This round checks source dates and payment qualifiers against saved ledgers,
recovery after an incorrect Excel input path, and the cost of simple CRM reads.
Only fictional material and the two dedicated private test conversations are
authorized. No formal handoff, approval, or CRM business write is part of these
tests. Docling is not deployed; EvoOntology remains deferred.

Original workspace changes, first-run failures and diagnostic retries are
retained separately. Raw documents, conversation content, rendered pages,
runtime captures and private grading keys remain local. A successful rerun does
not replace a failed first attempt.

## Source delivery

| Change | Pull request | Merge |
| --- | --- | --- |
| Source-ledger rules, registered bounded XLSX reader, one fewer redundant banquet read, helper phase instrumentation | [CRM #165](https://github.com/777Autumn/myanc-crm/pull/165) | `68356cfe8e9665e0e7eadbe86183b7b44ba83032` |
| Gateway query correlation and numeric helper timing | [Gateway #71](https://github.com/777Autumn/cc-connect-anc/pull/71) | `52475fdf497a1b1ebd198ad200fd396627eff8e0` |
| Paired fixture support for the recheck argument | [CRM #166](https://github.com/777Autumn/myanc-crm/pull/166) | `6c2f6c3083a55fecc97eb72c05c5226bf86ce66b` |
| Emit helper query timing only for an authenticated business trace | [Gateway #72](https://github.com/777Autumn/cc-connect-anc/pull/72) | `d4d2aa6ef2327bb343a82f139a00765a803c2134` |
| Preserve source-page detail views and estimated-table qualifiers | [CRM #167](https://github.com/777Autumn/myanc-crm/pull/167) | `662719a930d2a784e668d96afcdf61605ed0f1aa` |

All five deliveries have independent exact-head Spec and Standards reviews,
successful PR CI and successful exact merge-SHA push CI. Gateway #72 passed all
seven jobs on both PR run `38721624032` and merge run `38723405150`. Candidate 04
was built by the canonical builder from the listed CRM #166 and Gateway #72
merges; independent inspection verified all 171 payload hashes and source
provenance. Its SHA256 is
`8a75620fb41db36d11e911b48c29f96a4f6c19d2b3aca27dd814b95cceddd69f`.

CRM #167 passed PR run `38734039691` and exact merge run `38734561008`.
Candidate 05 pairs that merge with the unchanged Gateway #72 merge. Its 172
payload hashes were independently checked, including five changed source blobs
and the generated source-commit metadata. The archive SHA256 is
`8319b8ab38d754eddac1d1de2010e40291bc7f5ae35651cf26435cb111fe5520`.
The canonical build passed 633 CRM tests (18 skipped), 19 spike tests and the
paired journeys; retained resource and web-build warnings are not suppressed.
The installation plan changes 12 existing renderer/reference paths, retains all
419 controls and leaves the installed knowledge version unchanged. Independent
maintenance reviews passed. Actual prepare, install, startup and independent
runtime readback succeeded. New Feishu acceptance is recorded separately below.

## Regression evidence

- The original saved ledger omitted a readable date and did not reliably keep
  page-specific payment evidence and conditions together. The revised protocol
  requires source quotes, per-page qualifiers, saved-file readback and correction
  of a mismatched persisted record. Rules alone do not prove model accuracy.
- The original XLSX attempt used an incorrect path, refreshed work context, then
  stopped without completing the read. Local recovery uses the actual original
  workbook with fresh context and the registered reader: 48 rows, 234 nonempty
  cells and 38 formulas/saved values were checked. This local replay is distinct
  from a naturally occurring wrong-path retry in Feishu.
- Four background-helper process cases fail before the trace-scope fix and pass
  afterward. Business measurements still use a real authenticated action-tool
  context, with numeric Text/JSON and private-stderr checks.
- Independent review exposed a new test-fixture cleanup race. The final fixture
  waits for completed and persisted assistant history. Twenty targeted runs
  passed; the original failure remains retained. The earlier Windows full suite
  had 63 failures and is not reported as fully passing.

## Runtime maintenance

The initial candidate changed 30 control paths. Its normal startup failed the
strict health check because expected startup fields omitted the new protected
reader and background helper timing rows. A reviewed single recovery attempt
also failed when natural authorization renewal added connection CLI phases.
Both attempts were protectively stopped and their failed receipts retained.

The old controls were restored from verified backups: 24 files restored and six
new files removed, with no business, connection-binding or session rollback.
The old process passed 125.512 seconds of stable observation, 24 samples and
three established Feishu sockets. An independent readback confirmed the same
process, sockets and installed hashes. This proves old-version recovery, not
acceptance of the new fixes.

Candidate 04 uses the changed Gateway source. Its maintenance procedure
binds the completed rollback chain, derives the four reader warnings from the
installation inventory, and retains the strict startup matcher. Directory ACL
and protected-receipt checks were added after independent review. No background
helper-log exemption is used.

A local freezer also failed before contacting the Mac because a POSIX path was
compared using Windows separators. The one-line correction and actual-input
regression passed independent review; the failed assembly and failed dependent
invocation are retained. Final maintenance review checked the real staged
candidate, 419 control files, 30 changed paths and six added paths. Actual
prepare, install and startup succeeded. Stable observation covered 125.794 seconds,
24 samples and three established sockets. Independent readback confirmed the same
process and all 419 installed control hashes. Installed-manifest SHA256:
`55ed1648b3bc2e8e3f03b928efd0f63dca4d043ef188ccdb3c28135215d61934`.

Candidate 05 was staged and its next maintenance baseline frozen while candidate
04 remained live. The pre-switch audit covers all 7,078 physical log records,
including 186 added since the successful installation baseline. It reconciles
15 received messages with 13 completed native turns and two new-session
commands, plus five completed queue pairs. Two reply-association errors and
eight slow-send warnings remain recorded. The warning-to-turn association uses
message IDs and the persisted principal/session mapping; identically named
`session` log fields have different meanings and are not compared directly.

Corrected read-only captures verified unchanged old records: 145 file works,
210 connection-session links, 93 work links and 73 scope links. Only the two
authorized test works and their links were added. The two private session stores
each append one session; their prior session lists and histories remain intact.
The earlier boundary's 31 recorded message IDs become 39 through four later
query inputs and four bot replies.

A fixed, read-only platform probe retrieved exactly those four stored reply IDs,
using four message GETs and two tenant-token requests. Each reply belongs to the
expected private chat and configured bot app, and each parent ID matches one
specific query. Creation followed the corresponding native completion by
0.670–0.867 s. All four are interactive cards: body hashes are retained, but
literal answer-text equivalence, device delivery and user read status remain
unknown. Config, file-ledger and pinned system-CA hashes remained unchanged;
certificate-chain and hostname verification stayed enabled.

Independent Spec and Standards maintenance reviews passed against the exact
candidate, frozen installation plan, activity reconciliation and completed state
reconciliation. Their combined review is bound to input SHA256
`cbfb25bcf594aff1fef793b77b4f189380dd6be9238aca7bbe2fb6ab8f21540f`.
Actual prepare, install and single startup receipts returned zero. Installation
reports the 12 expected changed paths and unchanged business state. Startup
observed 130.596 stable seconds, 25 socket samples and three established
connections, with unchanged business, connection bindings and sessions.
Independent readback confirmed the same process, sockets and installed controls.
Installed-manifest SHA256:
`6e9c9540b236465da41af380f547744f6e213fb2b383c8fd8779a4ba627b04ea`.
These receipts establish the runtime switch, independently of document accuracy.

Eight actual read-only capture failures remain retained: four activity, two
state and two token-stage attempts. They exposed Windows command length, the
read-only sandbox's process-inspection restriction, a legitimate legacy
connection version of -1 and supported file-ledger schema versions 1–5. The
first token failure recorded an unspecified URL error; the second established
TLS verification code 19. A subsequent probe used the existing, hash-bound system
CA in memory and succeeded without changing a trust store, configuration or TLS
verification policy. These capture failures are distinct from the two earlier
production startup failures.

Local assembly/checker/combiner failures are also preserved: an external evidence
path rejected by a relative-path assumption, line-ending conversion in an export
comparison, an assumed standalone manifest instead of the archive's manifest,
and a missing duplicated top-level freezer-hash field. Corrections used actual
file/blob hashes and the existing contracts. These local failures occurred before
the affected remote operation and are not additional service incidents.

## Real acceptance and timing

Candidate 04 failed both original-source reading cases: the single PDF and the
four-file batch. The complete printed date on page 2 was reduced to its day,
then falsely reported as missing its year/month. The error persisted in source
ledgers, actual delivered Word/PDF and Excel/PDF files and the final messages.
An independent reviewer initially repeated that visual mistake; the mistaken
review, its explicit retraction and a second independent source-image check are
all preserved. The frozen answer key was not changed to fit the responses.

Five downloaded input files and four accepted artifacts matched their recorded
hashes. All eight exported PDF pages were inspected. The original spreadsheet's
36 item rows and 38 formulas/caches match its PDF; all 80 formulas and saved
results in the delivered comparison workbook were independently checked.
The quotation total is consistent. The payment promise, later internal receipt
and remaining independent-verification limit were kept distinct. These passes
do not offset the date failures. No Excel wrong-path incident occurred naturally
in these two runs, so the recovery claim remains limited to the isolated replay.

Six simple-query samples completed. All three replies from one private entrance
omitted the estimated-table qualifier; all three from the other retained it and
the lack of final confirmation. One query overlapped the other account's batch
work for its full 19.210-second native turn. This observation is not a load test
or a causal performance claim. Independent review recomputed all six samples
from their correlated message, native-turn and numeric helper records.

| Candidate 04 sample | Core turn s | Native turn s | Business tool envelope s | Action s | Guard s | Host s | Received to reply handler s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A1 | 19.478 | 19.210 | 8.307 | 7.750 | 2.112 | 5.638 | 20.927 |
| A2 | 17.056 | 16.782 | 8.202 | 7.624 | 2.062 | 5.561 | 20.746 |
| A3 | 16.404 | 16.115 | 7.409 | 6.847 | 1.634 | 5.213 | 20.547 |
| B1 | 26.194 | 25.806 | 9.110 | 8.545 | 1.985 | 6.559 | 27.576 |
| B2 | 27.505 | 27.213 | 7.787 | 7.226 | 1.743 | 5.482 | 31.849 |
| B3 | 20.815 | 20.549 | 8.858 | 8.299 | 1.632 | 6.666 | 25.126 |

These are nested intervals, not additive components. Native medians/maxima are
16.782/19.210 s for A and 25.806/27.213 s for B. Each query made one business
execution and three distinct protocol reads, with no duplicate read or polling.
The installed Host requires those protocol reads for each turn; their occurrence
across turns is not evidence that they can safely be removed. Each measured Host
used four resource CLI calls, one fewer than the earlier five-call path.

Host resource phases took 3.525–3.951 s. B1 and B3 also waited 1.176 and 1.390 s
for a connection-file lock; the other samples waited 0.003 s or less. The lock
holder is unknown. These are not measured SQLite waits or proof of cross-user
blocking. Queue time, pure model/network/SQL time, actual HTTP request count and
platform delivery/read time remain unknown. The reply-handler interval does not
prove the message was visible to the user at that instant.

For candidate 04, the before/after fictional business record, customer record,
handoff records and five approval/write ledger snapshots are identical. That
comparison does not establish the final candidate 05 post-acceptance boundary.

The old-version baseline contains three correct queries per account. Native
turn medians are 20.197 s and 24.023 s; maxima are 23.702 s and 27.929 s.
All answers retain the difference between estimated tables and an unconfirmed
final count. Each query performed one business execution and three protocol
reads; no within-turn duplicate protocol read or business reissue was observed.

Samples are too few for a stable P95 or a causal speedup claim, and the before/
after conversations differ. No performance improvement is inferred from these
two sets of six samples alone.

Candidate 05 was then tested with the two repeated source cases, both previously
unused heldouts and six new same-text queries. Results below separate initial
answers, saved evidence and actual generated files. A later correct answer does
not erase an earlier failure.

| Case | Source reading and persisted evidence | Generated output and current limit |
| --- | --- | --- |
| A, repeated two-page PDF | Both full dates, page-specific payment evidence and qualifiers are correct in the downloaded note and DOCX. Six detail images match exact crops of their parent pages. | Accepted DOCX content and its one-page rendered preview pass independent inspection. The saved source input ID omits its final character; the source name and full SHA256 are correct. The preview PDF was not a delivered artifact. |
| D, repeated four-file batch | Three projects' source qualifications and the actual saved ledger are correct. Actual original Excel/PDF bytes and all 36 item rows, 38 formulas/caches and totals agree. The helper returned all 48 rows and 234 nonempty cells. | R1's intended formula-display text became spreadsheet formulas and produced `Err:501`/`#VALUE!`. Independent downloaded-byte checks reproduce the error-cache rejection with all 82 formulas preserved and 34 error caches. R2 contains 38 formulas with empty caches and 40 literal formula-text cells; it was not rendered or visually checked again. No accepted delivery. |
| B, heldout PDF | The initial answer incorrectly attributes an explicit event-date-pending statement to both pages; only page 2 contains it. Actual saved ledger quotations and the final answer are correct. | Downloaded accepted DOCX/PDF content and both PDF pages pass independent inspection. The initial page-attribution error remains despite the later correct files. |
| C, heldout PDF | The actual saved ledger correctly records absent printed calendar dates and preserves page-specific qualifications. A first ledger's irrelevant supporting quote was revised before authoring. | The final renderer invocation manually repeated part of the input path and failed preconditions before Office conversion. The correct Word path was subsequently reopened, but not rendered or delivered again. The assistant disclosed the incomplete result. |

The source-input read succeeds independently of the generated workbook failure
in D. No naturally occurring wrong-path retry for the original Excel source read
was exercised in this round; that recovery remains supported by the separate
actual-original replay. C's distinct final-renderer path error was not retried.
For C, a failed final render does not prove that its original PDF was unreadable.
The frozen R1/converted-R1 pair reproduces the candidate validator's first
error-cache rejection. Its current hashes do not establish R1's unfrozen
historical starting bytes. R2's empty caches describe an unrecalculated saved
workbook, not a failed R2 conversion.
Candidate 05 before/after snapshots now match in every field except capture time:
the fixed fictional business/customer/handoff records and five approval/write
ledger snapshots are unchanged. This establishes that selected read-only boundary,
not the state of unrelated business. Final post-acceptance runtime readback also
confirms the same process, epoch, three sockets and installed controls; no restart
is observed. Preservation checks found no changes to 38 original dirty files or
473 prior evidence files. The four approved test works account for seven matched
inputs and three accepted artifacts: A's DOCX and B's DOCX/PDF. D and C have no
accepted delivery. Matching runtime snapshots do not prove uninterrupted network
availability between those observations.

All six candidate 05 query answers retain the current estimated value and lack
of final confirmation. Each made one business query, with no business replay.
Five turns made three distinct protocol reads; B1 made four because it read the
same complete Skill twice. Exact tool-call and returned-text hashes establish
that duplicate, whose tool envelope was 0.511 s. It does not explain the whole
35.312-second native turn.

| Candidate 05 sample | Core turn s | Native turn s | Business tool envelope s | Action s | Received to reply handler s | Rule reads / duplicates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A1 | 18.566 | 18.319 | 8.899 | 7.489 | 19.869 | 3 / 0 |
| A2 | 17.687 | 17.403 | 7.454 | 6.897 | 21.773 | 3 / 0 |
| A3 | 17.711 | 17.494 | 7.173 | 6.611 | 22.561 | 3 / 0 |
| B1 | 35.593 | 35.312 | 8.240 | 7.677 | 36.907 | 4 / 1 |
| B2 | 22.613 | 22.346 | 7.553 | 6.996 | 26.304 | 3 / 0 |
| B3 | 20.692 | 20.404 | 7.065 | 6.496 | 24.214 | 3 / 0 |

These intervals are nested and must not be summed. Native medians/maxima are
17.494/18.319 s for A and 22.346/35.312 s for B. Four Host resource CLI calls take
3.259–3.938 s per query. Observed guard/Host file-lock waits remain below 3 ms;
they do not account for the seconds-long delay in these samples. The
0.827–4.435-second received-to-native-start interval is not an independently
measured queue wait. Model, pure network, individual SQL, SQLite lock waiting,
device delivery and user read times remain unknown. Small samples and overlapping
attachment work do not establish a causal speedup, stable P95 or absence of
concurrency effects.

## Maintenance cost and remaining work

The initial release and recovery form one continuous handling chain, with two
failed new-version starts, one successful old-version start and one successful
corrected new-version start. Candidate 05 is a later planned switch with a
successful startup and independent readback. Eight read-only capture failures,
local checker/assembly/combiner failures, review findings, candidate failures and
CI retries remain separate evidence; their counts do not measure production
incidents or focused work. Stable observation windows (about 125 seconds for
rollback/M2 and 130.596 seconds for M3) are not downtime. Human focus time,
agent focus time, waiting and total service downtime are unknown where direct
evidence is absent.

The complete candidate 05 UI log records 18 bounded actions (four session resets,
four uploads, four prompts and six queries) and two timestamped deviations: a
cancelled folder dialog and a scroll rejected before execution for a missing
argument. A separate retained note records one rejected non-target-dialog click
with an unknown exact timestamp.
They are operator-automation records, not a measured count or duration of human
work. Seven files were uploaded across four batches. The cancelled dialog and
rejected click sent no unintended file or message. Local readback-tool extensions and synthetic red tests are evidence
preparation costs, distinct from model authoring/conversion failures and service
startup incidents. No further runtime change is included in this closeout.

Priorities are judgments based on observed consequence and scope, not measured
repair-hour estimates:

| Order | Remaining work | Evidence, consequence and smallest useful next check |
| --- | --- | --- |
| 1 | Complete reliable generated-file delivery | D's formula-display/cached-result problem and C's wrong final input path leave two cases without accepted outputs. Distinguish literal formula text from executable formulas, reuse the known work/input path without manual reconstruction, then render and inspect every final page after the last change. Preserve precondition and formula checks; C's precise remote exception is not exposed. These are scoped authoring/recovery changes, with human effort unknown. |
| 2 | Keep source statements attached to their actual page | B's first answer makes one unsupported page assertion despite later correct files. Verify quotes and page associations in the first answer as well as the saved ledger; later correction is insufficient for first-pass reliability. Only one heldout instance is established here. |
| 3 | Copy provenance identifiers without transcription | A omits one input-ID character in two saved outputs. Bind the ID from work context and compare the saved value; correct filename/SHA preserve another route to the source but do not repair the ID. A narrow deterministic check should be lower scope than renderer repair. |
| 4 | Remove proven redundant reads, then measure remaining delay | One of six query turns repeats an identical rule read. Avoid that within-turn duplicate while preserving required fresh authorization and business reads. Profile existing CLI and pre-invocation intervals before changing locking or claiming speedup. |
| 5 | Reduce recurring evidence preparation work | Reuse exact-path metadata and manifest-bound readers for supported file types. Preserve the two-stage hash/request review for undelivered diagnostics; do not turn observed filename exceptions into unrestricted enumeration. No maintenance-time saving has yet been measured. |

The following local-only evidence anchors bind the conclusions and their detailed
source indexes. Raw materials, private identity mappings and source transcripts
are excluded from this report. Cost draft 08 is retained; its final addendum
supersedes the earlier pending-runtime and one-UI-deviation statements.

| Local evidence | SHA256 |
| --- | --- |
| `candidate05-independent-acceptance-final-01.json` | `bff5b3770d2168385c6a9a4dde459dd6bb87c36869e52c82a1eb58297760113f` |
| `candidate05-six-query-independent-review-01.json` | `f610037f418af3ccfe37c19655c7745c5ceb1d38369bffb0618c0f36bb4c97de` |
| `candidate05-c-renderer-diagnostic-01.json` | `3de21d027b7d1bb6a6b524c7748bc3bc3337f2d977bfa72d3ed6f15b80169a7d` |
| `candidate05-d-saved-xlsx-diagnostic-01.json` | `f3276dc18e7a24762ecf128f5f668f85e2a33c1cc775ed3c0f939439fab910c3` |
| `runtime-v3-1792076760137058300.json` | `cb666c938a1eb06250c4f4369e4197356003eb589bc374cdc8e3ce67d2383b49` |
| `candidate05-business-before-after-01.json` | `02d5d77fb7b0067ebeb3c45aa93d0fadf9c05d036cd4a431e658c48097363bcf` |
| `preservation-1792076366271355900.json` | `563b79feda94176e80af6abc83ee737b1265a0a7b9fbda0b9d190976e85ac509` |
| `maintenance-events-current-draft-08.json` | `ac0ad52907ce619e9568d017dda7b1fe5c951d8493be1427abc8c98f3855a716` |
| `maintenance-events-current-draft-08-addendum-01.json` | `f74730b631fbecc5bc182dfbdd27e97344dd84c878093608cdd6f19117739095` |

Exact-head archival review and GitHub delivery are separate remaining report
tasks; they do not reopen the completed runtime or verification stages. This
closeout does not authorize another deployment.
