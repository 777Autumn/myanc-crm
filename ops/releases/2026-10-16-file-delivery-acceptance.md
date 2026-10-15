# File correctness and delivery recovery acceptance

The scoped implementation and Mac update are delivered, but the overall acceptance
target remains **incomplete**: five of six cases pass; case B fails its required
pre-delivery inspection. Twelve accepted final files and all eighteen PDF pages
were independently read back. A correct post-delivery file does not erase B's
missing pre-delivery read.

## Source and installation

Implementation PR [#169](https://github.com/777Autumn/myanc-crm/pull/169) has head
`d127de0ff61b1eab31334b39f303e22b1f3d60fa`, base
`ec13741a176ac0ee96b587d864f0ab7d4e5891b1`, and merge
`b68921e002cadf205bb27bf17bc81a325c999e11`. Distinct Spec and Standards reviews
passed. PR CI `38780073632` and exact merge push CI `38780511293` passed.
Local CRM tests ran 633 cases with 18 skips; native Mac recovery tests passed all
12 cases. These deterministic checks do not establish live model behavior.

The Darwin/arm64 candidate SHA-256 is
`de27c387f50fdbb84fdb6d61b30c3bdd91b80ed80863b8e83932959d9c1ee90a`.
The reviewed maintenance updated 22 existing file contents with 419 control
checks and no new installed paths. The actual runtime uses the CRM merge above,
unchanged gateway `d4d2aa6ef2327bb343a82f139a00765a803c2134`, and unchanged
knowledge `ada437cac33d156634b70b20948dc7abc09bec7e`. Post-acceptance checks found
the same process, socket observations and installed control manifest as after
maintenance. This report-only change requires no new deployment.

## Scope and observed results

The change reuses current work context, immutable file references, render
manifests and existing delivery/status commands. It adds context-resolved input
and output references, explicit text-cell intent with formula preservation,
source identifiers copied from the host, final-byte checks before preparing a
delivery, and the exact retained failed workbook for bounded local recovery.
Permissions, Office/file validation and unknown-send checks remain in place.
No general task framework, production Docling/EvoOntology integration, database
migration or query performance refactor was introduced.

Old rules already required visual source checks, correct cell types, final
recalculation/render/readback and status-first send recovery. The old validator
correctly rejected an erroneous workbook and missing formula caches. The gap was
manual reference transcription and incomplete transitions between required steps;
removing the validator was not a valid repair. A specific repeated full Skill
read within the same turn was the only query-adjacent rule adjustment.

Four original failure-material cases and two frozen holdouts ran in six separate
work contexts across the two authorized private test chats. No source answers or
tool instructions were supplied to the tested assistant. Every case delivered
one editable file and a PDF. Raw materials, chats, screenshots, native traces,
intermediate failures and receipt identities remain in the local evidence archive.

| Case | Material | Final content/layout | Pre-delivery process | Combined |
| --- | --- | --- | --- | --- |
| A | Original scan, Word/PDF, 2 pages | Pass | Recovered wrong path and rechecked final revision | Pass |
| B | Original scan, Word/PDF, 2 pages | Pass for requested facts | Read editable source and final PDF, but not the actual final Word; claimed coverage still prepared | **Fail** |
| C | Original scan, Word/PDF, 2 pages | Pass | Recovered final-path and preparation-argument errors; final bytes checked | Pass |
| D | Four originals, Excel/PDF, 8 pages | Pass: 8 sheets, 60 formulas/caches, 36 detail rows, 4 source bindings | R3 corrected intermediate historical-version replacement, then rerendered/rechecked/delivered | Pass |
| E | Held-out scan, Word/PDF, 2 pages | Pass | Actual saved files and both pages inspected | Pass |
| F | Held-out workbook, Excel/PDF, 2 pages | Pass: 5 formulas/caches and equals-prefixed explanation remains text | Three edits followed by new renders; final changed page rechecked, identical page hash reused | Pass |

No operator stop, cancellation or diagnostic replay was sent for D: its first
turn completed naturally. Earlier incomplete snapshots remain valid only for
their observation cutoffs. All intermediate errors remain preserved. F retains
four distinct rendered versions; its editable source was revised in place.

Nonblocking observations are kept separate from the acceptance failure. B omits
two source details outside its specifically requested date/table/payment fields.
D does not repeat a source's handoff-version/no-assignee statement in the project
row, although the document explicitly says it is not a handoff. D/F narrative
amounts are snapshots: later input changes require updating prose and rechecking
the new files. Formula dependency checks do not prove automatic prose updates or
an independent interactive Office recalculation. A few no-op calls and read-only
working-directory deviations remain maintenance follow-ups.

## Timing observations, not a simple-query benchmark

| Case | Gateway receipt to final reply handler log (s) | Recorded queue (s) | Turn duration (s) | Instrumented action-host sum (s) |
| --- | ---: | ---: | ---: | ---: |
| A | 159.324 | No queue event | 158.203 | 6.050 |
| B | 178.103 | 18.762 | 157.936 | 5.994 |
| C | 248.757 | 8.237 | 239.143 | 9.379 |
| D | 1807.392 | 246.030 | 1559.976 | 9.342 |
| E | 200.445 | 27.243 | 171.858 | 6.321 |
| F | 264.762 | No queue event | 263.617 | 7.186 |

Host sums are nested within turns and cover only instrumented action-host calls,
not all shell/render/model tools. Missing queue events are not measured zeroes.
The observed project-mutex waits sum to less than two microseconds per case;
this does not measure all database locks. Pure model, network, SQLite and client
delivery times remain unknown. Do not subtract host sums and label the remainder
model time, or add nested intervals as independent work.

D had 961.175 seconds between adjacent recorded events. The cause remains unknown;
the other account completed E during that interval. This is not proof of general
concurrency isolation, an outage, or a stable P95. Further simple-query timing
requires a fixed query and record snapshot with correlated client, queue, model
tool, host and reply boundaries. That measurement is a separate batch.

## Remaining order and preservation

1. Bind actual final-file reading evidence to the final bytes in the existing
   read/prepare path. B proves caller-reported coverage alone does not enforce
   the required inspection. More prompts or unverified flags are insufficient;
   file hashes still cannot prove visual understanding or semantic truth.
2. Scope revision edits to intended cells/text. D's broad revision-label
   replacement temporarily changed source history; the same turn corrected it.
3. Remove the demonstrated manual long-ID/path transcription points using
   returned references, retaining scope and permission rejection behavior.
4. Measure unexplained waits separately before proposing a performance change.

Two fixed fictional business records, their related handoffs and five ledger
snapshots are unchanged. Counts remain approvals 53, staged changes 53,
write intents 4, write fences 0 and handoff events 12. This is not a whole-tenant
audit. The three original repositories retain all 38 dirty files; all 1580 files
in the prior frozen evidence index match their hashes.

[The sanitized evidence index](2026-10-16-file-delivery-acceptance.json) binds
results to local evidence hashes, final artifact hashes and exact source versions.
It does not contain raw customer/chat data or receipt identities. Source delivery,
runtime maintenance and behavior acceptance are separate: the unresolved B
requirement keeps overall behavioral acceptance incomplete.
