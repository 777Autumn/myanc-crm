# Document intake, PDF review and authorization repair

This batch repairs three observed failures: a read-only garbled PDF was answered
without viewing its pages; one selected attachment reached the engine after a
later upload advanced the timestamp watermark and was discarded; remote
authorization held the file Store/SQLite transaction and delayed other users.

## Source and regression evidence

- CRM PR #160: `0c67d92ad59ceb5cb97c398da97affa2c8ac2406`.
  The file Skill now loads the production reference before reading originals,
  including read-only requests. The diagnostic regression does not preload that
  reference and therefore tests discovery rather than supplied answers.
- Gateway PR #69: `31afe5c3c0a7c30a7e0e8e6018a8f30b2893c591`.
  File-only uploads retain message deduplication but no longer lose intake because
  downloads complete out of creation-time order. Old mixed/text instructions
  retain stale-message checks. A CUJ checks saved inputs, queue drain and replies.
- Publication/project authorization runs outside the Store gate and SQLite
  transaction. Reentry validates ownership, source and pending-input provenance.
  The gate observes cancellation; SQLite BEGIN uses a 50 ms busy wait before the
  existing cancellable retry. No database or schema migration is involved.

Both repositories passed independent Spec and Standards source review on exact
base/head pairs. Gateway review requested two changes: extract the added
authorization coordination from long functions and place the multistep test in
the CUJ suite with user-visible assertions. Both were addressed and re-reviewed.
The initial gateway CI staticcheck failure was an equivalent Boolean-expression
style issue; its failed run remains in local evidence.

Local CRM suite: 627 tests reported, including 18 skipped. The 13-case model routing diagnostic
passed, but is not a rendering or production acceptance test. Final gateway head
was cross-built and the file module ran successfully on an ordinary Mac identity;
the explicit timing experiments are separate. Full CUJ tests passed. Windows
full-suite failures involving platform paths, external CLI and unbuilt web assets
remain recorded; they are not relabelled as passing.

## Final-source isolated concurrency

The final test head `2752f1d870bf8878ec3ef63e3ab6983780220ae2` and gateway merge
have identical complete Git trees. The Mac timing binary, source overlay and
34 package source files were independently matched to that head. Earlier WIP
measurements remain separate and are not substituted for this final-source run.

The matrix has 18 topology/authorization-stage/delay conditions, each repeated
three times: 54 trials and 162 concurrent message/context/file-state reads.
All reads and imports succeeded; every trial authorized twice, sent the source
once and remained usable afterward. Complete raw samples, phase observations,
medians and maxima are in
[the public data](2026-10-14-document-repair-concurrency.json).

|Topology, 30-second authorization wait|Prior read range ms|Final-source read range ms|
|---|---:|---:|
|Same Store|30010.191–30013.349|0.276–1.256|
|Different Stores, shared SQLite|30044.499–30064.898|0.283–1.202|
|Independent SQLite|0.313–0.952|0.262–0.964|

Only authorization waiting was replaced in the isolated real Host/SQLite path.
These are not Feishu end-to-end latency or a stable P95. Each operation/condition
has three samples. `sqlite_begin` includes SQL work and lock waiting; retry
backoff stays in total time. Local JSON, file validation and snapshot I/O still
serialize inside the transaction.

All 18 reads in the six additional slow-authorization cancellation scenarios
finished before their deadline; they do not measure cancellation latency. Two
separate actual-lock regressions use a 100 ms deadline and a 500 ms wall-clock
return guard, then verify reuse. Authorization cancellation was measured once
per stage at 0.003458/0.001667 ms. Cancelled grants, same-message activation,
pending/source mutation and uncertain-COMMIT non-replay also passed final-head
file-module regressions. These small samples do not establish a general bound.

|Synthetic work records|Payload bytes|SQLite bytes|Median/max processing ms|
|---:|---:|---:|---:|
|100|55812|61440|1.910 / 2.115|
|1000|564412|569344|9.878 / 12.737|
|10000|5723412|5734400|50.073 / 50.165|

This is record-count growth, not three-month capacity. Attachment bytes and real
business distributions are excluded. Earlier/current payload sizes differ, so
this is not an identical-byte workload comparison. Whole-state processing remains
a possible next optimization when measured operating scale warrants it.

## Docling isolated comparison

Docling 2.138.0 with local RapidOCR and four CPU threads ran on Windows. Remote
conversion services were disabled. Four target original PDFs were converted in
default and forced OCR modes, three repetitions per mode. An initially misselected
native Word re-export is retained as a separate control; the actual delivered
garbled PDF was then tested without replacing those first results.

|Target|Default field fidelity|Forced OCR field fidelity|Default median/max seconds|Forced OCR median/max seconds|
|---|---:|---:|---:|---:|
|Scanned meeting notes|100%|100%|2.956 / 13.680|4.224 / 5.599|
|Garbled historical handoff PDF|47.6%|61.9%|3.985 / 4.275|7.253 / 8.214|
|Actual delivered garbled PDF|42.1%|84.2%|1.785 / 5.603|3.825 / 5.667|
|Multi-page quotation table|100%|100%|9.340 / 13.488|17.005 / 17.201|

Field fidelity is `(correct + accurately preserved source unknown) / selected
fields`, assessed against original pages, not current business records replacing
historical facts. Character-order corruption counts as an error without implying
that every error is an opposite business assertion. This is neither OCR character
accuracy nor assistant answer accuracy. Repetitions are not independent documents.
Only two of the four target PDFs preserved every selected field in both modes.

All conversions returned SUCCESS, but both garbled PDFs still contained damaged
key table text. Their table cells remained identical between default and forced
OCR. Forced OCR improved surrounding paragraphs; it did not repair those tables.
The separate native Word export control passed and does not replace the actual
delivery result. The quotation contained 36 rows; 216 selected row subfields were
checked in addition to totals and qualifications.

The same-machine pypdf baseline used identical source hashes. It returned no text
for the scan and damaged Chinese order for the two garbled PDFs. pypdf call
medians were about 0.001–0.031 seconds, but it does not perform equivalent OCR or
layout work. Both timing series exclude saving outputs; first-call loading is
not separately isolated. These are not Mac latency or end-to-end user measurements.

The isolated environment installed 108 packages. Environment/model logical file
sizes total 2,199,301,111 bytes, and recorded model download elapsed time was
80.232 seconds. These are not allocated disk blocks, memory usage or maintenance
labour. Installation duration, human focused effort and ongoing maintenance
cost remain unknown; no dedicated pypdf environment-size baseline was measured.

Decision: do not adopt Docling in production in this batch. Retain visual review.
Any later adoption trial must first repair the observed table-text problem and
repeat the original-file field checks, then measure deployment/maintenance cost.
EvoOntology remains deferred.

## Installed candidate and actual acceptance

Both source PRs were squash-merged. Exact merge push CI passed: CRM
[38556022933](https://github.com/777Autumn/myanc-crm/actions/runs/38556022933)
and gateway [38557813617](https://github.com/777Autumn/cc-connect-anc/actions/runs/38557813617).
The frozen Mac candidate archive SHA256 is
`5ca72dca79e677080c369f43142a0786d46f190d9fe3b1145c2ca8bb3f57f065`;
manifest SHA256 is `42b8afebfb1df9d9edc5297d175327c5a66bb1a4dce7ac17d1209b1c02c5d13e`.
Installed source versions are the two merge SHAs above; knowledge remains
`ada437cac33d156634b70b20948dc7abc09bec7e`.

Separate independent Spec and Standards maintenance reviews bound the candidate,
installer, wrapper, activity reconciliation and frozen 413-file inventory.
Exactly six files changed: gateway binary plus canonical and four workspace file
Skill entrypoints. There were no configuration, ownership, mode or directory
changes. One normal start, no recovery start, passed 129.514 seconds of stability.
The installed inventory digest is
`ed763f1c5b2af448eefca0b5f58103a39abef47c4821ae0dd7ebfafdab9b69a4`.
Post-acceptance checks matched the same process identity, three connections and
installed controls. Four entrances started; live messages in this round covered
only the two designated private assistants, not the two group entrances.

The first post-cutover attempts used the previously frozen originals. Each
message, native turn and saved work was correlated, with separate readback of
six saved originals and thirteen rendered page images. The independent reviewer
actually inspected all thirteen pages and checked twenty complete rule/reference
readbacks against their source text. Results are deliberately not all-pass:

|Case|Actual result|Remaining boundary|
|---|---|---|
|R1 historical Word/PDF read|Original garbled PDF rendered and both pages viewed before the answer; file revision R1, historical handoff 8/pending, current handoff 10/accepted and file versions 3/4 distinguished correctly|Initial nested command-tool API call failed, then direct execution recovered; the failure remains recorded|
|R2 other person's simple read|Correct current estimate, 23 tables; its 9.213-second query was entirely inside the other person's 44.929-second handoff call|Receive-to-model-final 34.217 seconds; receive-to-core-complete 35.229 seconds. These are trace timings, not employee read receipts or separately measured authorization/lock/network waits|
|R3 four selected attachments|All four saved once with exact original hashes; a file created 6 ms earlier arrived later and was still accepted; zero file deliveries|Actual watermark value was not captured; only observed out-of-order creation/arrival and successful intake are claimed|
|R3 preliminary attachment answer|FAIL: the first page's old payment-promise qualifier was attached to a later receipt record without its source/time scope|The later combined answer does not erase this first failure|
|R3 attachment interaction|Three subsequent attachment messages each triggered another clarification question without tools|No duplicate file delivery, but the batch still causes avoidable model turns and chat noise|
|R3 final combined comparison|19 selected fields correct, 5 source unknowns accurately preserved; 36 quotation rows and totals agree between saved Excel and PDF|Material-recorded receipt amounts are distinct from independent real-bank verification; this is a small fictional sample|

R1 received-to-core-complete was 138.382 seconds. The real concurrent read finished
before the handoff call returned. This supports concurrent progress for this
observed case; the 30-second isolated authorization matrix is separate evidence.
Actual final replies were also observed in the two private-chat UI views.
No new business records, approvals, staged changes, write intents/fences or handoff
events appeared: full before/after hashes and the selected fictional records
matched. The three related works had zero file deliveries. The original Excel
printout splits its subtotal column onto later pages; the final answer accurately
reported this input-layout limitation. No generated file was delivered this round.

## Maintenance cost and remaining priorities

[Recorded cost data](2026-10-14-document-repair-maintenance.json) separates CI job
spans from summed parallel compute time. Source delivery used five CI runs,
including one failed gateway attempt; CRM had one source-review round and gateway
two. The source CI job spans were 100, 121, 880, 877 and 232 seconds. They exclude
run queue time and cannot be added to infer human focused work. The later
report-only PR is outside these source-delivery counts.

|Continuous cause-handling event|Necessary work and retained retry evidence|Category|
|---|---|---|
|Read-only PDF routing|Freeze failed original/trace, discovery regression, rule entrypoint repair; incorrect first unittest invocation retained|Development repair|
|Attachment timestamp ordering|Reproduce dropped file, constrain exception to file-only messages, mixed-message negative case, visible CUJ; initial test expectation corrected|Development repair|
|Authorization lock waiting|Real Host/Mac red tests, move grants outside locks, transactional recheck, final matrix; temp group and missing testdata attempts retained|Development repair|
|Docling comparison|Isolated dependencies/models, repeated conversions, independent source/page scoring; mistaken native export retained as separate control|Acceptance preparation|
|Source delivery|Two-axis reviews, CI and gated merges; Boolean-style CI failure and review-driven cleanup retained|Planned release|
|Mac maintenance|Freeze, reconcile 344 additional activity rows, two-axis review, backup/install/start; recovery-document wording corrected before execution|Planned release|
|Real private-chat acceptance and archive|Seven business/material messages, source/page readback, state comparison and independent review; timestamp argument capture error and UI recovery observations retained|Acceptance preparation|

Shutdown and running log markers are 58.672 seconds apart. This is a lifecycle
interval, not an exact measurement of user-visible downtime. The 129.514-second
stable observation is separate. There was no failure recovery start. Human and
agent focused effort, installation effort, and separately attributed model/network
waiting remain unknown. Three repeated questions are one observed interaction
defect, not three maintenance incidents. Synthetic cases are not normal throughput.

|Priority|Consequence, recurrence and scope|Minimum next change / unresolved question|
|---|---|---|
|P1 source/time qualifiers|One preliminary scan summary reused an old-page qualifier on a newer receipt record; financial/state summaries can change meaning even after correct rendering|Freeze the exact two-page counterexample; require each temporal/uncertainty qualifier to stay with its source fact. Determine whether a targeted rule/eval suffices without a new parser|
|P2 batch clarification and latency|Four uploaded files caused four turns, including three repeated questions; simple real query still took 35.229 seconds to core completion despite lock isolation|Coalesce attachment-only clarification while preserving every receipt and dedup boundary; measure rules/model/network phases before adding caching or concurrency changes|
|P2 tool invocation and evidence transport|One nested command API error recovered; one local timestamp argument error blocked capture before reads; UI refresh/focus failures needed state recovery|Retain narrow regressions and transport metadata; use documented direct command surface and exact timezone strings, not broader permissions|
|P3 history growth and input print layout|10,000 synthetic works still require whole-state processing; supplied spreadsheet splits columns in print|Optimize only after measured operating-scale pressure; for future generated files keep full-page saved-output inspection|
|Deferred parser adoption|Docling still damaged key table text in both failed garbled PDFs and adds an isolated 108-package/model footprint|Do not deploy; require all selected source fields correct plus measured Mac timing and maintenance burden before reconsideration. EvoOntology remains deferred|

The source implementation, GitHub delivery and authorized Mac update are complete.
Live acceptance is partial: required visual review, file intake and observed
concurrent progress passed, while the preliminary semantic and repeated-question
failures remain open. Existing 38 dirty files and 13,263 historical evidence files
were rehashed unchanged. Raw documents, chats, images, identity mappings and every
failed attempt remain local; this repository carries only the sanitized report
and aggregate/raw synthetic timing data. This does not establish reliability for
all documents, real customer material, sustained production load or all entrances.
