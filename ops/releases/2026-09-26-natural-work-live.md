# Natural wording and project continuity: simulated acceptance

Scope: the existing two test accounts, one Bot, existing private/group entries,
and fictional banquet materials. This extends the [project-context record](2026-09-25-project-context-live.md).
It does not establish real hotel integration, arbitrary-language understanding,
or documents that never need human review. Earlier first-attempt failures remain
evidence; successful retries are recorded separately.

## Source delivery and candidate

| Repository | Exact runtime source | PR / exact merge CI |
| --- | --- | --- |
| Gateway | `7bc3e8b9cba91586926cfe1d60f388b5acd955a3` | [PR37](https://github.com/77AutumN/cc-connect-anc/pull/37), [CI](https://github.com/77AutumN/cc-connect-anc/actions/runs/36192628195) |
| CRM | `98ce59012e5e9adfe662d5e5c20e545943beaf3b` | [PR90](https://github.com/77AutumN/myanc-crm/pull/90), [CI](https://github.com/77AutumN/myanc-crm/actions/runs/36196669117) |
| Knowledge, unchanged | `88a60ba60a634fe3d6b0f68f91de326b19a39b30` | [CI](https://github.com/77AutumN/myanc-team-brain/actions/runs/34704220632) |

The exact heads/bases passed separate Spec and Standards AI reviews and the
existing merge gate. AI review is not an independent human GitHub approval.
All required exact merge-SHA jobs passed. The normal candidate builder exported
these commits freshly from GitHub; no old worktree supplied runtime files.

The earlier [PR35](https://github.com/77AutumN/cc-connect-anc/pull/35) checkpoint
used gateway `3f52085eb2201d683d094f32ecc50aa1f870b2e5` with CRM
`1f59510377eb9e17fec10c58e8b258714af74cac` and the fixed knowledge above,
after its [exact merge CI](https://github.com/77AutumN/cc-connect-anc/actions/runs/36181489777).
Initial candidate `candidate-reference-refresh.tgz`, 139 hashed files, SHA-256
`616a62bfe27e4c397408a2757009ad36b0380529bd0fb6030267e98917c132fa`.
Toolchain: Go 1.25.6, Python 3.13.2, Node 24.13.0, pnpm 10.28.1.
CRM: 394 tests, 8 platform skips; 18 spikes passed. Knowledge: 71 tests,
2 platform skips. All seven mandatory paired journeys executed and passed:
natural confirmation/continuation, project membership, shared progress/private
grant, CRM daily planning, customer approval, profile follow-up, knowledge scope.
Windows skips do not replace the required Linux CI.

That initial maintenance targeted only the gateway binary and four copies each of
`team-banquet/SKILL.md` and `team-banquet/references/shared-cases.md`.
Accounts, configuration, dependencies, CRM runtime and published Wiki stay fixed.
The package's generated Wiki SOURCE metadata names its fresh CRM export; that
metadata is not installed, and the existing published Wiki v2 remains authoritative.
The nine-file update completed through the reviewed maintenance entrance, one
stop/start and one receiver, over 130 seconds continuously ready, no application
errors and unchanged business/session state. Healthy receipt SHA-256:
`65fadb9f7928d33976ee49c099c01071d4181a9e8ae4555db3ba873cb01102df`.
Independent installation review matched all nine file receipts, backups and
permissions, 133 protected files, seven stores and six saved sessions.
Confirmation and current-record refresh retries passed. The new private budget
passed amount, source and scope checks but still failed three content checks;
that checkpoint did not close the file-quality work.

## Previously completed real journeys

- Fresh vague material request: the Bot read the fictional input and clarified
  its purpose before producing customer-facing Word and Excel. Two additions
  received while processing were saved and produced v2/v3. Six actual outputs
  were opened in Feishu. They retain the original and versions, Wiki v2 sources,
  total 103720, surplus 6280, and correctly rounded meal share 86.5%. Word
  render/readback and 39 valid Excel formulas were independently checked.
- A second owner-only fictional project initially returned no accessible result
  to the other account. A real, specifically bound owner invitation added the
  registered operations collaborator; ownership did not transfer. An attempted
  redundant invitation was rejected by the stale-version check, then reread.
- The operations account imported four confirmed group originals and prepared a
  private Excel revision. Only the private note sheet changed; the seven original
  sheets and four formulas remained. The other account's later artifact lookup
  returned authorized shared artifacts, not the private revision. Shared original
  hashes were unchanged. Private artifact SHA-256:
  `4a1617a29a6ca0ae579d50f47f2727e6916e81e3146adba1e80857fd6d2548e1`.
- A natural topic switch created the correct new work. An ambiguous relative
  change naming both fictional projects prompted one business clarification;
  the employee's subsequent instruction to wait produced no write or file.
  A busy new-work request was rejected without entering the other work's queue.

## Retained failures and targeted repair

The first material-only run made a file before clarifying its purpose. A later
Word displayed 86.6% while its Excel formula implied 86.5%; source versions and
rendering were also incomplete. The fresh journey above passed after Skill fixes,
not retroactively on the first attempt. An earlier confirmation callback failed
to resume; its binding was repaired and a new explicit confirmation was exercised.

A private synchronization request ending with an instruction to leave other
conditions unchanged was initially rejected. The scoped repair subsequently
saved only the confirmed company/price basis, exactly once. The Bot's pre-answer
claim that it had already saved was still wrong and motivated the final wording fix.

After changing projects, quoting the old second-project file restored its correct
work but did not reread current shared progress. Only an extra employee reminder
caused the read. The resulting private v2 correctly calculated a 17-table base
total of 82420, but misstated the decoration option difference, omitted the exact
budget overrun and inferred a sales-production status without evidence. Its
SHA-256 remains `b3795d2a1cf600b9bc06986771b8b313703872a81e05ad7b06ba73114ca995b8`.
The model did catch and repair two explanation cells mistakenly stored as formulas
before delivery; that successful check does not erase the content defects.

The final patch reminds an explicitly quoted project revision to reread current
progress, preserves original work/source/private scope, uses ordinary wording for
busy new-work rejection, and strengthens existing Skill readback and cost checks.
The real confirmation retry preserved project revision 3 until the actual card
answer. The pre-answer response explicitly said the operation was not yet done.
One bound answer then added only a proposed 11:00 welcome time as revision 4;
all other facts, ownership, members, shared artifacts and the other project were
unchanged. Only after that write did the Bot report synchronization.

After a fresh switch to the other project, the employee quoted the original v1
file and repeated the earlier 17-table request without a reread reminder. The
actual `case-read` returned revision 4, including the newly proposed welcome
time, in the original work. Claude reused the existing v2 reference instead of
producing another file. This proves refreshed project context; it is not evidence
that v2's retained content defects were repaired. The employee next requested an
18-table private Excel explicitly. Its v3 SHA-256 is
`079fc71f4eff395bac9c1f88fdbddda984e6a12279b409238fb5569969287de3`.
The actual run reread revision 4, generated and checked the workbook, reread the
saved cells and delivered once. Base/upgrade totals 86680/92680 and five valid
formulas are correct; original v1/v2 bytes remain unchanged. All three sheets
were opened in Feishu. Nevertheless, a retained note still says the decoration
difference is 5000 rather than 6000; the workbook omits budget overruns 6680/12680;
and it still asserts that sales has not produced a handoff without evidence.
The saved-cell readback already contained these errors. The run did not reload
the updated Skill body; whether that explains the missed instructions is under
investigation, not an established complete diagnosis.

The concurrent new-work request received an ordinary-language rejection saying
that the new work had not started. It entered neither the saved queue nor the
model conversation. Both shared project bodies and shared artifact records
remained unchanged during this private revision. The direct turn's in-memory
sharing flag was not separately persisted; this conclusion rests on the actual
private route, bound source/work and observed unchanged shared records.

## Current Skill guidance in resumed file work

The visible original session loaded the earlier business Skill and shared-case
reference before their update. Later quoted turns received the new host reminder
and reread project state, but did not visibly reload the updated Skill bodies.
Correct installation alone did not demonstrate that the old work used current
guidance. This is evidence for a missing refresh step, not proof of a model's
internal state or the only possible cause of the content errors.

[Gateway PR36](https://github.com/77AutumN/cc-connect-anc/pull/36) adds one sentence
to the existing file-work prompt: before each creation or revision, reread the
current applicable file/domain Skills and required references, then perform their
checks. New and resumed file processes receive it; already-running processes are
not hot-reloaded. No business rules, dependencies or validation platform were added.
The actual-spawn regression failed on old source and passed after the change for
native new/resumed, isolated resumed and the unaffected ordinary-session control.
The first CI attempt caught an unchecked cleanup error in the new test; that
failure is retained and was corrected before final reviews and CI.

Reviewed base `3f52085eb2201d683d094f32ecc50aa1f870b2e5`, head
`4d94ed599d36f84262d07b48b8507b2c6b4fd80c`; independent Spec and Standards AI
reviews and all five [PR checks](https://github.com/77AutumN/cc-connect-anc/actions/runs/36186765152)
passed. Gated squash merge produced `f587d60a580fef441cda8b79f940bc8a934475a8`.
All five [merge CI](https://github.com/77AutumN/cc-connect-anc/actions/runs/36187900440)
jobs passed. The normal candidate `candidate-skill-refresh.tgz` has SHA-256
`55877ccb94f87983e27fc1f81a3bb80193ea04ab5fe7299ae97b285127d8066a`.
Its 139 file hashes were verified; only the gateway binary differs from the
initial candidate. All seven mandatory paired journeys passed with the exact
gateway f587d60, CRM `1f59510377eb9e17fec10c58e8b258714af74cac` and fixed
knowledge `88a60ba60a634fe3d6b0f68f91de326b19a39b30`, using the same toolchain.

The separately frozen, reviewed gateway-only maintenance completed with one
stop/start, one receiver, ordinary UID/capabilities unchanged, no failure receipt
and 130.8 seconds continuously healthy. New binary SHA-256:
`f343c6f318bb6af057961e3841347ccf96e3251bafa333004f91b3b0a37ebe2b`.
Healthy receipt SHA-256:
`59d63e8972d63c29f2a28b9e1dd2bf1609b2a88cba9df803b209581584998307`.
Independent verification matched backups and all 141 protected file entries.
Seven stores and six saved sessions were unchanged at the healthy checkpoint;
later model activity is separate acceptance activity, not an installation change.
The real 19-table private revision completed, but **file-quality acceptance still
fails**. The employee quoted the actual v3 file, requested 19 tables with the
budget unchanged, and explicitly kept it private. The actual process had the new
append-system-prompt instruction. It reread project revision 4 and its proposed
11:00 welcome time, but the nine matched tool calls did not reread current Skills
or their references. This establishes an observed failure to follow the refresh
instruction, not a claim about hidden model state.

The resulting v4 was accepted once in the original private work; SHA-256:
`8d7727c588b9df2c7f16f23487a4d949c81c5f81036e8267306b3d4403af0453`.
The host snapshot, saved output and downloaded workbook bytes match. Original
v1/v2/v3 snapshots and outputs remain unchanged. Shared project bodies and shared
artifact records also remain unchanged; the private revision did not synchronize
its 19-table assumption into the shared project.

All three actual worksheets were opened in Feishu: basic information, budget and
execution checklist. Independent inspection of the saved file preserved all five
valid formulas and found no explanation cells stored as formulas or error cells.
The 19-table meal cost is 77520, wine 3420, fixed service 2000 and host 3000.
Totals excluding decoration / with basic / with upgraded decoration are correctly
85940 / 90940 / 96940 against the unchanged 80000 budget. Source labels still
identify project revision 4 and Wiki v2. The shared 16-table proposal and private
19-table draft remain distinct, with the welcome time explicitly unconfirmed.

Nevertheless, all three retained defects are present in the actual file and
Feishu display: the execution checklist says the decoration option difference is
5000 instead of 6000; the budget omits explicit overruns of 10940 and 16940; and
the checklist still claims sales has not produced a formal handoff without an
adequate source. The saved-file readback covered only the budget worksheet, not
the execution checklist, and did not establish that all required checks passed.
Appending the instruction and successfully delivering v4 therefore do not close
the earlier quality failures. The reviewer did not repair the model's artifact.

Separate sanitized AI evidence, retained by the operator:

| Evidence | SHA-256 |
| --- | --- |
| `skill-refresh-installed-standards.md` | `ee085a9441a3d249932c94d69b3030ad5b0d2927e1c7d238ffedbe1cb737caaf` |
| `skill-refresh-real-spec.md` | `18758216d7cb434396bbeca1d5ef1f9d332960e162b35ff7c49228fb097ca2a3` |
| `skill-refresh-real-standards.md` | `1a4c97aebb47d401179c548e8e9a07118f3a442af031de1fa6cfbaf674f1c2d9` |

## Per-turn refresh and the remaining saved-content gap

[PR37](https://github.com/77AutumN/cc-connect-anc/pull/37) moves the existing
reminder into the actual file-turn payload, after recovery-intent parsing and
before model delivery. It covers new/resumed turns, live follow-ups and saved
supplements without changing the original sharing source. Base
`f587d60a580fef441cda8b79f940bc8a934475a8`, reviewed head
`ceadc7370969d8f9dc342f2282607e06e51774dc`; independent Spec and Standards AI
reviews and all five [PR jobs](https://github.com/77AutumN/cc-connect-anc/actions/runs/36191657744)
passed. The exact merge is the gateway in the runtime table; all five merge jobs
passed. The existing POSIX-mode test has a Windows-only limitation, retained in
the PR; the required full Linux CI passed.

The normal `candidate-per-turn.tgz` contains 139 verified files, SHA-256
`ec76cc4c3e77bff8e83282311a27b3d3ac06489125ebdb287dc5e32d39b081c7`.
All seven paired journeys passed with gateway 7bc3e8b, CRM
`1f59510377eb9e17fec10c58e8b258714af74cac`, fixed knowledge 88a60ba and the same
toolchain. Only the gateway binary changed. The frozen one-window update passed
with one receiver, unchanged ordinary identity/capabilities, 141 protected file
controls, seven stores and six saved sessions. It remained continuously healthy
for 130.9 seconds, with no application errors. Installed binary SHA-256:
`820c49cbe4ef02d4d1e339582ca45e10e9ca0c227132616956eacee93ae45610`;
healthy receipt SHA-256:
`855852da958f12777bede919f17cfc8947738043c035fccd1d253582489f0634`.

The next natural private revision requested 20 tables while retaining the budget.
The actual payload contained the reminder, and Claude invoked and fully loaded
the current `team-banquet` body. The v5 workbook was accepted once in the correct
work; snapshot, output and download SHA-256:
`536d53e8f20217b8124bb5727a23511d05f77b330eed05109620fdf3eca9e1e0`.
All three worksheets were opened in Feishu. Correct totals are 90200 excluding
decoration, 95200 with basic and 101200 with upgraded decoration. Two new valid
formulas explicitly show budget overruns 15200 and 21200. Existing formulas,
revision 4/Wiki v2 sources, proposed 11:00 welcome time, private scope, shared
16-table conditions and all v1-v4 originals remain intact.

Two defects still fail: the execution checklist says decoration differs by 5000
instead of 6000, and it infers that sales has not produced a handoff. Both rules
were present in the loaded Skill. The actual checker returned no targeted lint
findings, and the subsequent readback covered only the budget sheet. This fixes
the earlier Skill-loading gap but does not demonstrate complete content review.
The artifact was not repaired by the operator or reviewers.

A separate natural typo question in the same bound work successfully read the
current authorized project revision 4 and answered that welcome is proposed for
11:00, still unconfirmed. No new artifact or shared write occurred, and the other
project and private 20-table draft were unchanged. This covers a typo in a known
project context, not unrestricted fuzzy project search.

| Separate AI evidence | SHA-256 |
| --- | --- |
| `per-turn-installed-standards.md` | `7930e46b44912efd9731d835b9079778d2259445006eb42c96cdc4183780f6c5` |
| `per-turn-real-spec.md` | `c22f35efb4229ebcb5ef8d50a37b85d84ed0b0c6dd9ba360d008672292aa40e6` |
| `per-turn-real-standards.md` | `82a3a9ae56eddd2513d9863f92a8456f4b867dce81060295326a86d9f493851f` |
| `typo-real-spec.md` | `3178579b521df26e29c8faa1989be2ee12dfa910d175246b4bb2372c0239b915` |

## Complete saved-content readback

[CRM PR90](https://github.com/77AutumN/myanc-crm/pull/90) extends the existing
read-only checker to return saved worksheet rows and Word body/table content,
with locations, formulas and uncalculated caches. It retains existing lint and
does not modify artifacts. A shared output limit and unsupported nested Word
tables explicitly report incomplete inspection. No semantic rule engine,
delivery gate, dependency or new tool was added. The Skill requires reviewing
all returned sheets, including retained narrative, against actual amounts and
sources; missing evidence is not evidence that another employee did no work.

Reviewed base `1f59510377eb9e17fec10c58e8b258714af74cac`, head
`3a259044b2bd66d9099403b8e7ff6fe6964c9372`; separate Spec and Standards AI
reviews passed. Two new readback checks failed on the old source; all nine final
handoff checks and four runtime-Skill checks passed. The Standards finding on
nested tables was reproduced and fixed before final review.
[PR CI](https://github.com/77AutumN/myanc-crm/actions/runs/36196398586) and the
exact merge CI in the runtime table passed. The normal candidate at that table's
three exact sources is `candidate-handoff-readback.tgz`, SHA-256
`81ade17422d1bf493fdd65d2943f63e3d362a88c62abd23c93e5662076ae31cc`.
All 139 file hashes and seven paired journeys passed. The existing toolchain is
unchanged; CRM ran 398 tests with eight Windows skips and 18 passing spikes,
knowledge 71 tests with two Windows skips. Required Linux CI passed.

Only four copies each of the checker and Skill were installed. Independent
readback matched candidate bytes, backups, receipts, original ownership/modes
and ordinary-account read-only access. No configuration, identity, dependency,
gateway binary or published Wiki changed, and no service restart occurred.

The original installer wrote all eight files but failed its stable window when
one INFO event changed the complete journal hash. Its failure is retained and
its healthy receipt remains absent. The event's underlying type remains unknown;
it is not proof of an external send. Bounded reconciliation found no new employee
message, delivery, native-session record or business-state change in that window.

Two independent AI reviews then approved a separate read-only observation using
the entire reconciled journal, excluding no entries. All 145 protected paths,
seven stores, six saved-session files and service/activity state stayed equal
for 131.8 seconds over 18 samples. Original failure and absent healthy were
rechecked. This is new post-install stability evidence, not a retroactive pass
or a retry of the consumed installer. New local observation receipt SHA-256:
`328464fd69c93d18816b6ce9ab3bd2db41c8b717273ceea06fc4c22fba638e36`.

The natural private v6 regression requested 21 tables with the budget unchanged,
replying to the actual v5 file without a checking reminder or expected answers.
The new checker returned all three saved sheets (39 nonempty rows, 6694 characters,
no truncation). Claude then computed the hash and delivered without correcting
the two retained narrative defects. The current per-turn reminder was present,
but this turn did not explicitly reload the Skill body. These are observed
actions, not a claim about hidden model reasoning.

The accepted v6 output, snapshot and local copy share SHA-256
`e26dd3c5022e1da0ad95f19cae1b425cd375cc1671c9beba2175c6c578800c2c`.
All three sheets were actually opened in Feishu. Seven valid formulas are
preserved; meal 85680, wine 3780, subtotal 94460, basic/upgrade totals 99460/105460
and overruns 19460/25460 are correct. Saved formula caches remain empty; actual
Feishu display and independent arithmetic, not cached values, verify these sums.
The correct work received one accepted delivery. Shared project bodies and five
shared artifact records stayed unchanged; private scope and v1-v5 originals remain.

File-quality acceptance still **fails**: the execution checklist retains a 5000
decoration difference instead of 6000, and unsupported claims that sales has not
produced a handoff. Both statements were present in the complete checker result,
so absence of sheet content no longer explains this attempt. Independent Spec
and Standards inspections retain this as a partial result. Neither the operator
nor reviewers repaired the model's artifact. Overall closeout remains incomplete.

## Evidence and boundaries

Private operational evidence, original failures, exact review inputs, package
manifest, installation receipts and artifact copies are retained by the operator.
Raw chats, identities, configuration, native logs and databases are not published.
Recovery, save failures, conflicting versions, forged/repeated answers and unknown
delivery results use isolated tests; live fault restarts were not used as tests.
No claim is made that Excel structure checks equal visual rendering. Actual Feishu
display checks cover only the opened outputs. Complex real templates remain unverified.
Rollback requires a compatible prior runtime/configuration while retaining project
versions, ledgers, sessions, original files and all delivered artifacts.
