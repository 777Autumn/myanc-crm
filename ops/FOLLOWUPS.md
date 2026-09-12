# Tracked delivery and experience follow-ups

Updated 2026-09-12. This ledger distinguishes implemented source, GitHub delivery
and online acceptance under [RELEASE.md](RELEASE.md); it is not a deployment receipt.
The current model acceptance scope is defined once in the
[candidate record](acceptance/2026-09-10-bot-ux-candidate.md#当前验收口径2026-09-10-用户调整):
the Owner changed the gate to practical task completion on September 10.
Post-merge version and CI evidence is in the
[September 11 delivery record](releases/2026-09-11-bot-ux-delivery.md). The subsequent
authorized deployment and actual checks are in the
[live maintenance record](releases/2026-09-11-bot-ux-live.md); earlier evidence is
not retrospectively relabelled as live acceptance.
The later knowledge catalog cutover is recorded separately in the
[catalog live record](releases/2026-09-11-knowledge-catalog-live.md); source discovery
is deployed. The untitled-question trial is partial: test's new-session lookup and
both source links passed; Owner's old session and controlled new-session retest
both skipped retrieval. Owner's later explicitly guided follow-up retrieved and
cited a page (screenshot and native trace), without a separately confirmed link
click. Test's follow-up reused its previously read source; its UI/click result is
not separately confirmed. These do not close the first-query trigger defect.
The scoped follow-up is [implicit knowledge intent](acceptance/2026-09-11-knowledge-intent.md).
The subsequent [answer-policy live record](releases/2026-09-11-knowledge-answer-live.md)
records the authorized 23:02 policy/Skill cutover and host checks. Subsequent
[source-display acceptance](acceptance/2026-09-11-source-display.md) records the
Owner's changed requirement and bounded live audit: both uncoached first queries
retrieved/read sources and gave grounded answers. Test's missing unsolicited URL
is no longer a blocker. Subsequent same-session follow-ups and requested-source
answers passed for both accounts in the bounded 23:45–23:57 audit. Platform
receipts, mobile rendering and clicks are not inferred from gateway history.
Historical failures and guided successes above remain unchanged. This source
revision is not a new deployment or a new live-model run.

The subsequent [September 12 maintenance](releases/2026-09-12-approval-expiry-live.md)
installed the optional-source rules and approval elapsed-time fix. A startup HTTPS
count check caused a protective pause; one separately authorized recovery corrected
the check and passed the stable-window, control-file, isolation and store checks.
No new live-model or colleague acceptance is inferred from that maintenance.

The [September 12 transcript-intake record](acceptance/2026-09-12-transcript-intake.md)
records the first three selected, de-identified trial suggestions published through
the Owner's real private-chat approval card and verified readback. Two subsequent
Owner-authorized, operator-sent questions in the same old session received visible
replies but failed overall acceptance: the model did not read the newly published
body and carried forward an obsolete pending-approval claim. This is not an
uncoached Owner trial or a runtime deployment. The intake turn also exposed a
source-interpretation defect: the model called existing templates empty despite
three successful, nonempty reads. A minimal Skill candidate is in
[knowledge PR #16](https://github.com/77AutumN/myanc-team-brain/pull/16), merged as
`b093670c0c3f7dab8ba923a2869e1284db628152` after exact-head independent source review
and PR CI. Its four required exact-merge push CI jobs also passed, verified by the
release gate. It is not installed. Its first isolated real-model regression has now
run once and failed after 77.15 seconds: template interpretation was usable, but
the later answer searched without rereading the changed body and inferred that
the collected suggestion was not yet included from old pending evidence. The synthetic
proposal itself remained pending; this was not a verified fixture-ledger result.
Gateway PR #12 (`009244cfdbb3bd7400ea58cec2b3ba0207093be2`) adds the bounded
regression; knowledge PR #17 (`8f5c53f794b615b492305f599c4e7777c23ba7c3`) makes
the reread step explicit. The second isolated trial on that knowledge head ran
once in 135.95 seconds: all four code-gated turns passed and independent semantic
review accepted the core functional scope under the Owner's practical gate. It
read the changed body and used the new hypothesis without stale pending or
non-inclusion assertions. This is bounded acceptance, not full semantic or
per-turn reread compliance; residual content-boundary defects remain below.
Both PRs completed independent source review, head-matched squash merge and exact
main push CI: gateway `3269160359ec5c5cae004dceea86cc1f004aeb94` (five jobs, run
[34676142562](https://github.com/77AutumN/cc-connect-anc/actions/runs/34676142562)) and
knowledge `89d7ed11df3005328be2c4a6feb97e2ee196de53` (four matrix jobs, run
[34676117445](https://github.com/77AutumN/myanc-team-brain/actions/runs/34676117445)).
Reviewed and merged trees match in each repository. The prior PR #16 candidate is
superseded and must not be installed. The supported replacement was built from
these sources and CRM #31 merge `eb93c3f00c1296e2b0950834e0fa288335ab7601`;
its exact CI, three-source gate, paired tests and manifest verification passed.
The later authorized 12-rule installation and independent host observation are
recorded in [knowledge-rule maintenance](releases/2026-09-12-knowledge-evidence-live.md):
14 samples over 131.6 seconds, 71 control files, six unchanged stores and isolation
checks passed. That maintenance preserves its initial startup-check failure and is not a new
real-model or colleague trial. Both isolated trials passed temporary-token cleanup and
production service/config preservation checks; neither is real-colleague
acceptance. The Owner has
explicitly waived the new Sandbox profile/follow-up trial; it is not a required
remaining task and is not recorded as passed.

| Item | State / evidence | Next action and acceptance condition |
| --- | --- | --- |
| Historical GitHub reconciliation / release gate | Complete, `releases/2026-09-09-backfill.md` and exact merge evidence | Keep gate in supported candidate path; no automatic VPS deploy |
| One-shot reminders and agreed Owner/test acceptance | Complete within documented scope, `releases/2026-09-10-reminders.md` | Preserve historical evidence; Wang live acceptance waived, not substituted |
| Business reply wording, shown-ID continuity, date edits, pagination | Representative native tasks passed once on the September 11 recorded pair; minor English/internal-field narration remains nonblocking | Keep practical gate; zero wrong-object, invented-fact, false-success or cross-user actions; separate live trial remains |
| Trusted exact roster names | First-use exact name passed; ambiguity found a stale-read defect, policy d5c67095 fixed it and native retest passed | Preserve actor-scoped live identity verification; do not treat fixture tests as live-member acceptance |
| Independent operations alerts | Enabled in authorized September 11 maintenance; protected DB initialized, six real EACCES checks passed; no fault pending | Synthetic failure tests passed; actual fault-notice delivery not injected in production; preserve queue/receipts |
| Six-environment final-only replies and footer removal | All six live overrides verified after restart; default upstream display unchanged | Colleague trial remains; native questions/errors and host cards must remain visible |
| Native reminder acceptance defects found September 10 | Historical counts unchanged: later fixed-pair run 17 code passes, 3 quota-blocked, 1 not run; wording-only findings are nonblocking; September 11 representative native scope completed | Retain actual messages/questions and tool results; repeat functional failures only as needed, not style-only cases |
| Native representative model coverage | CRM/reminder/image 12 passes on d5c67095/2a798f53, two earlier-pair passes, knowledge three-turn pass and four historical cases on c9310282 are recorded separately | Representative scope complete; stop further quota use absent functional changes; no fake-agent or live-acceptance substitution |
| Knowledge canary installer permissions | First attempt blocked before tools by workspace/skill directory permissions; private fixture corrected, one three-turn native rerun passed | Retain failed evidence and test-only Agent/Task budget guard; do not apply these temporary permissions to production |
| Natural knowledge discovery without exact titles | Historical catalog-version Owner failures and coached follow-up remain in their release record. After the 23:02 policy/Skill cutover, both uncoached live first queries retrieved/read sources and answered from them; Owner four reads, test two. Later same-session follow-ups and requested-source answers also passed | This bounded first-query/follow-up task is complete for both accounts. No more resets or style-only retests; no universal reliability claim or inferred mobile click |
| Knowledge trigger diagnosis and English narration | Owner new-session native trace confirms no retrieval, ruling out old context alone; test new session retrieved sources but showed one English process sentence | Do not repeat /new as a fix or count coached follow-up as original-query acceptance. No silent reset/live prompt patch; English wording alone remains nonblocking under practical acceptance scope |
| Implicit knowledge entry follow-up | CRM #22, knowledge #13 and gateway #10 merged; updated policy deployed in the authorized 23:02 cutover. Bounded Owner/test first-query and later natural follow-up audits show grounded answers and actual requested sources | Recorded first-query/follow-up scope complete. Current acceptance decision: `acceptance/2026-09-11-source-display.md`; optional-link revision subsequently installed in the September 12 maintenance, not a new behavioral run |
| Knowledge coverage claim (P2) | Prior failures retained; knowledge #14 passed one original native three-turn case and installed c8b9f77 in all six environments. Later Owner/test first replies and follow-ups show grounded advice without false whole-library claims | Native regression and two live first-query/follow-up samples passed within their scope. No statistical reliability claim or additional style-only model runs |
| Optional knowledge source display | Owner approved grounded answers with on-demand sources. `KB-ANSWER-SOURCE-LINK-20260911` is closed by requirement change: test had read sources and was not asked for links. Merged revisions installed in all six environments in the September 12 maintenance | Retain actual source reads, scope, conflict/uncertainty and requested-source checks; no citation database, privacy expansion or style-only rerun |
| Rewrite temporal fidelity (P3) | Positive rewrite procedure passed one prior combined-candidate sample, with no tool calls; earlier failures remain recorded. CRM #23 policy included in this installed candidate | Rewrite not retested in the P2 three-turn trial or this maintenance; source equivalence and deployment are not new behavioral evidence |
| Knowledge example assumptions / redundant execution question | Latest passing native visit trial includes a suggested “three or four revisions” confirmation and asks whether to execute after explicit analysis-only intent; no customer fact assertion or tool operation occurred | Nonblocking UX follow-up: use the customer's actual number in examples, and finish after explicit analysis. Retain observations without more style-only model trials or weakening authorization |
| Catalog maintenance umask regression | Independent script review found root-only new directory access before execution; explicit root:root/0755 and seven real-account import checks fixed it; 14 Linux synthetic checks passed | Preserve this one-time release evidence; do not rerun historical installation scripts |
| Selected recordings / Miaoji transcript curation | First selected batch published through the Owner's real private-chat approval card on September 12: three de-identified, unverified trial suggestions; host readback `verified`, revision 2 to 3, original 57 non-root blocks retained, one append and unchanged 9-page/8-team-page counts. [Intake record](acceptance/2026-09-12-transcript-intake.md) | Publication is complete for this batch only. Two authorized operator-sent post-publication questions were partly useful but failed overall: no new-body read and an obsolete pending claim. This was not an uncoached Owner trial or a candidate regression. Remaining recordings are not implicitly reviewed or published |
| Existing-template emptiness claim | September 12 intake turn described existing templates as empty, but the three successful tool results contained 452, 397 and 468 body characters without truncation. Both isolated trials recognized existing guidance and an unparsed table; they read bodies containing unfilled fields without calling the templates empty. The first whole trial failed; the second knowledge PR #17 trial passed the bounded core task but later still reduced template guidance to fields | Preserve original failure and bounded improvement. PR #17 rules are installed in all six environments; new live-answer acceptance remains unexecuted. The remaining template/content-boundary overstatement is a nonblocking follow-up under the practical gate, not full semantic compliance or a formatting-only issue |
| Obsolete pending-approval claim after publication | At 12:58:47 the authorized operator-sent trial completed both catalog pages but did not read a body, then called the already-verified batch pending; the 13:02:09 follow-up searched with zero results and no body read, and did not correct the status. Both UI replies and complete native traces were observed; no CRM/reminder/proposal calls. The first isolated candidate also inferred non-inclusion from old pending evidence; the second read the changed body and no longer asserted historical pending or non-inclusion | The second isolated trial passed this bounded core check. Its synthetic proposal actually remained pending throughout, so current body inclusion is not proof of a verified proposal or callback synchronization. Do not infer current proposal state from old receipts or page similarity. Rules are installed, but live-answer acceptance remains open; full proposal-status query capability is separate scope |
| Isolated template/current-body regression | First native trial on knowledge `b093670`, gateway test `009244cf` failed after 77.15 seconds at turn 3; turn 4 was not run. Second trial on knowledge `8f5c53f` with the same CRM/test/model completed all four code-gated turns in 135.95 seconds and passed bounded core semantic review: current revision 3 read, new unverified advice used, only one real temporary-Brain proposal with a bound synthetic card, no CRM/reminder/quoted-command/extra-proposal action. Both trials preserved production service/config and cleaned temporary authentication | Retain both results separately. Gateway PR #12 and knowledge PR #17 completed independent review, merge and exact main CI; reviewed/merged trees match. Supported replacement candidate and later 12-rule installation are documented separately. Isolated fixture results do not replace real-colleague acceptance or prove a terminal proposal state |
| Knowledge reread and content-boundary residuals | In the second trial, turn 4 searched twice then reused turn 3's newly read revision 3 rather than rereading each turn as the Skill directs; the fixture did not change after turn 3, so this sample had no stale body. Turn 3 still said the template only specifies fields, and both later answers overgeneralized absence of dedicated documents without retaining unparsed-table limits | Nonblocking under the Owner's practical task gate, but these are instruction/content-boundary defects, not merely formatting. Preserve them without claiming full semantic compliance or universal/per-turn freshness; do not expand the model matrix just to polish these outputs |
| Isolated tool transport interruption | One September 11 retest stopped on transport_unavailable before the original failing turn; no recurrence in the bounded diagnostic batch, cause unknown | Preserve failed attempt; do not claim root-cause resolution or weaken sandbox; investigate if it recurs |
| Initial three-source candidate build failure | Previous full builder failed in paired Go tests without preserving the failed subprocess stdout. A separate paired diagnostic and one unchanged full-builder retry passed; initial cause remains unknown | Keep failed evidence separate from the native transport issue. On recurrence capture full subprocess output; do not attribute it to path/load or declare a root-cause fix |
| 2026-09-08 expression candidate | Failed acceptance, never published; new policy passed selected factual regressions and exact fixed-stage replies | Keep original failures; new results are not retroactive approval of the old candidate |
| Old-policy native session restoration | Historical 37a70b2f policy resumed into d5c67095; cancelled/pending pair passed with fresh original-operation receipts | Preserve actual native resume evidence; do not infer approval status from history absence |
| Owner/test unguided daily tasks | New-version knowledge first queries, natural follow-ups and requested-source answers passed within the recorded scope. Original September 10 reminder acceptance remains complete, not relabelled as a new run. New Sandbox profile/follow-up trial explicitly waived by the Owner on September 12, not passed | Remaining unwaived new-version daily-task evidence gaps: CRM entry and ordinary reminder management. Record actual account/version and any coaching; do not re-add the waived Sandbox trial or replay the entire old test matrix |
| New-version Sandbox profile/follow-up trial | Waived by explicit Owner decision on September 12 after the guarded test stopped before a create approval. This is a scope change, not successful Sandbox acceptance | No mandatory retest or environment switch. Any later business action keeps its normal environment, authorization and approval checks; historical Sandbox/core acceptance remains unchanged |
| Pre-write approval expiry and contention-test timing | [Issue #27](https://github.com/77AutumN/myanc-crm/issues/27): the [elapsed-time fix and synchronized regression](acceptance/2026-09-12-approval-expiry.md) passed red/green and Linux contention checks. PR #28 merged with exact main CI, frozen candidate installed and host recovery verified September 12 | This scoped source/GitHub/installation work is complete. No production expired-write fault injection or misuse established; preserve zero-write tests and original failing evidence, and do not substitute host recovery for new-version daily-task acceptance |
| Maintenance startup connection classifier | The September 12 first start was protectively paused because a health check counted all HTTPS sockets as WebSocket receivers. Separately authorized recovery used SDK WebSocket lifecycle evidence, passed 13 samples over 131 seconds, and HTTPS count settled from two to one | Keep failed and recovered receipts. Unique process/receiver/listener checks remain; do not revive the HTTPS-total-equals-one startup rule or reuse the historical one-time installer |
| Knowledge-rule maintenance startup readiness | Historical immediate start check and protective-pause failure remain recorded; exact failure-time process details were not captured, so that incident's precise cause is not proven. The shared [maintenance startup helper](MAINTENANCE_START.md) now implements bounded identity polling, two ready samples, consumed-request protection, unit-bound pre-exec stop and sanitized failure evidence. Delayed-exec regression failed with the immediate check and passes with the fix | Code and isolated regression are implemented; this commit's independent review / merge / exact CI evidence belongs on its PR. Future authorized cutovers must integrate the frozen helper and still run the existing stable application-health and ledger checks. No production restart or real race reproduction in this task; historical one-time scripts are unchanged and non-reusable |
| CI runtime upgrade | Deferred, not a current failed CI claim | Separate compatibility PR and complete workflow tests |
| Login repair later evidence reconciliation | Deferred; repair alone does not prove root cause | Reconcile sanitized post-repair evidence without changing credentials |
| Original dirty worktree cleanup | Deferred | Inventory user-owned edits; obtain scope before moving/removing; never bundle research or runtime data |

For the September 11 Bot UX release, CRM #17 and gateway #8 are merged; exact main CI completion is recorded
in the linked delivery record. Deployment and post-start checks are complete;
**online colleague acceptance remains incomplete**. Owner/test independent trial
evidence is still missing for new-version CRM entry and ordinary reminder management;
the newly waived Sandbox profile/follow-up item is excluded. Installed hashes and
protected-store preservation are recorded separately from model/synthetic/historical
human evidence. The first transcript batch is published, while the two authorized
operator-sent answer trials failed overall. The merged PR #16 candidate's first
isolated real-model trial failed. Further knowledge PR #17 passed the second
trial's bounded core functional scope, with per-turn reread and content-boundary
limitations retained as nonblocking follow-ups; it is not full semantic
compliance. PR #17 and gateway regression PR #12 completed exact main CI delivery
verification with merge mappings in the intake record. The superseded candidate
remains preserved but ineligible for installation. The supported replacement was
built, and its 12 knowledge-rule files were installed in the authorized maintenance;
see the separate live record for startup failure and host reconciliation evidence.
No new real-colleague answer acceptance has occurred. Source/GitHub delivery and
host installation do not close that remaining evidence gap.
