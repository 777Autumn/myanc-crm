# ANC query, file delivery and waiting experience

Status: source and Mac delivery completed; acceptance is partial with the
limitations below. This record does not replace the prior
capacity findings or claim arbitrary file latency, eight-user access or long-term
reliability. Two existing test identities and fictional records are used.

## Source delivery

| Component | Merge | Delivery |
| --- | --- | --- |
| CRM query/file guidance and compact render receipt | b574f3168889b4c187ccbab2ad6c8fae3a2d33e1 | PR137; exact-head Spec/Standards; merge CI37908329322 attempt2 passed |
| Gateway safe per-turn progress | d1764ca9c7e0e4fba6ce3573f2b85e9e20d8fbfe | PR59; exact-head Spec/Standards; merge CI37911081022 passed including race and native matrix |
| Office PDF prerequisite clarification | 2f57fe70ee105e8b332640aa213da6c4ed9bd89d | PR138; clean Spec/Standards on3370574; identical merge tree; CI37917699591 passed |
| Knowledge | de936941d80d064a6860289676129a2dd67dfb2f | Unchanged, exact four-job CI retained |

The CRM change scopes current-state queries by business object. Known banquet IDs
go directly to the banquet read. Host-selected identity, schemas, approvals and
permission checks do not change. File guidance sets initial layout and requires
defect-specific repair. Only renderer CLI stdout is compacted; internal render()
and full render.json are retained. Office companion PDFs use the existing
LibreOffice path, not an optional reportlab import.

Progress is off by default and enabled in the four existing ANC project display
blocks. After30 seconds, one message may show fixed host-confirmed states. Phase
edits are coalesced at least5 seconds apart; terminal updates are handled promptly.
It does not expose reasoning, commands, arguments, paths or filenames. A completed
turn is not a business-success or delivery assertion. API failure stops progress
updates for that turn without retrying creation or blocking the work. Final replies
and existing stop behavior remain unchanged; no persistence platform was added.

## Candidate and maintenance

Initial Darwin candidate SHA256:
`af61ef985677f0a76c29ed0c88296d4b24b84cb1f51476276e06e784a130aedd`.
23 existing code/Skill files and one config were installed; sole receiver and
127.187-second stability verified. Business, connection binding and session checks
were unchanged across maintenance.

Skill follow-up candidate SHA256:
`d320973842b407353db203534161bfd7a36dd231d6d32263c04eed13781fd199`.
Only ten existing Skill copies change. Config and binaries remain identical.
Candidate-only SOURCE.json commit metadata is not installed. One historical /opt
Skill copy additionally receives the already-released final-saved-byte hash
clarification; four active workspace copies already had it. This difference was
matched to the prior complete installed inventory and explicitly reviewed.
The follow-up installed successfully and passed a 126.839-second stability
window with one receiver. Business, connection-binding and session checks stayed
unchanged. Installed inventory SHA256 is
`6f811166c115431846b4176bad9779773c526b3961e38828eaae35070f3555e2`.

All maintenance uses new protected receipts and existing idle, exact historical
exception, process, lock, backup and stability checks. Initial staging rejected an
inline-TOML assumption before runtime change; the existing serializer and complete
parsed equality resolved it. An omitted pre-existing negative-test approval was
reconciled by exact row/approval hashes and read-only no-write evidence, not by
changing the ledger or terminal-state allowlist. A follow-up preparation stopped
on a transient extra Python process before pause/install; after it exited,
unchanged guards passed. Original failed attempts remain retained.

## Verification so far

- Native Office: two Mac tests actually executed, zero skipped; 500 rows,
  1,084 formulas and19 PDF pages checked. Platform-skipped local tests are not
  counted as native acceptance.
- Known banquet queries: both accounts actually invoked the banquet tool and
  answered from its current result. Model turns18.219 and21.089 seconds.
- Employee budget: accepted Excel/PDF receipts; model finished202.306 seconds
  after sending. Independent500-row,20-category arithmetic and1,084 cached formulas
  passed. Final15 pages visually checked. One consolidated pagination revision
  changed27 pages to15. All final previews were read by the model before delivery.
- Manager's concurrent queries: actual distinct native-thread overlap with that
  budget;18.870/21.319/20.190 seconds, median20.190. Correct results, below the
  inherited45.086-second threshold. These are model-turn times, not precise
  client-arrival latency percentiles.
- Safe activity and ended states were observed in the original employee private
  chat; the original state message updated and retained the separate final reply
  and delivery receipts. Short baseline queries had no extra status message.
- Ordinary customer lookup and nonexistent banquet lookup passed with scoped
  answers and actual controlled reads.

## Retained limitations

The first manager budget failed before generation: an optional reportlab import
failed and the model incorrectly declared PDF capability absent without running
the supported converter. Its failure is retained; PR138 addresses the guidance.
The post-update manager retry delivered both accepted files within274.102 seconds;
the model finished276.261 seconds after send. Independent checks passed for500
rows,20 categories,1,064 numeric formula caches and all17 PDF pages. Four actual
render invocations mean the single-consolidated-revision goal is not consistently
met. Two employee queries actually overlapped that retry (20.707/20.553 seconds);
the third was sent too late and is not concurrency evidence. A same-input
confirmation round A_BUDGET_1_CONFIRM completed in193.222 seconds from send to
model end, with both accepted files before that end. Independent arithmetic,
1,064 numeric formula caches and all18 PDF pages passed. Its two renders changed
21 pages to18. Three employee queries actually overlapped that same native turn:
20.628/19.650/22.080 seconds (median20.628, maximum22.080), each with the correct
controlled banquet result. This supplements the missing reverse-direction
concurrency evidence without rewriting the earlier two-overlap result.

Customer-to-banquet lookup remains unaccepted: the model queried banquet keywords
using customer number/name, but the backend keyword filter covers banquet
name/number/venue/source rather than the customer relationship. Empty keyword
results do not establish absence of associated banquets. No automatic cross-object
fallback or new parameter was added. Real ambiguous-name and denied-resource
controls remain incomplete; existing permission tests are not substituted for
new real-account evidence. Existing release records do not establish applicable
current fixtures: a historical private project was subsequently shared, while
historical duplicate-name cases tested view formulas, not customer selection.
No permissions or records were changed to manufacture those controls.

Creation/edit failure, late events, queued-turn switching, waiting, cancel, timeout
and interruption have isolated lifecycle/HTTP tests; only scenarios actually
observed in Feishu are described as live acceptance. Force-terminating the host
can leave a remote status without its terminal update; recovery infrastructure
is outside this change. No model switch, scheduler, dependency, permissions change
or4/8-tier load test was performed.

Raw, local evidence index: `D:/MYANC/experience-evidence-20261009/STATUS.md`,
`live-metrics.json`, `live-file-review.md`, `resource-summary.json`, both independent
source-review pairs, candidate manifests and immutable maintenance receipts.
No credentials or production customer content are included in this release note.
