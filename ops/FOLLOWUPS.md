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
| Implicit knowledge entry follow-up | CRM #22, knowledge #13 and gateway #10 merged; updated policy deployed in the authorized 23:02 cutover. Bounded Owner/test first-query and later natural follow-up audits show grounded answers and actual requested sources | Recorded first-query/follow-up scope complete. Current acceptance decision: `acceptance/2026-09-11-source-display.md`; installed hashes remain in the live release record. New optional-link source revision is not deployed |
| Knowledge coverage claim (P2) | Prior failures retained; knowledge #14 passed one original native three-turn case and installed c8b9f77 in all six environments. Later Owner/test first replies and follow-ups show grounded advice without false whole-library claims | Native regression and two live first-query/follow-up samples passed within their scope. No statistical reliability claim or additional style-only model runs |
| Optional knowledge source display | Owner approved grounded answers with on-demand sources. `KB-ANSWER-SOURCE-LINK-20260911` is closed by requirement change: test had read sources and was not asked for links | Source/Skill/acceptance revisions follow the new rule; separate GitHub and deployment status. Retain actual source reads, scope, conflict/uncertainty and requested-source checks; no citation database or privacy expansion |
| Rewrite temporal fidelity (P3) | Positive rewrite procedure passed one prior combined-candidate sample, with no tool calls; earlier failures remain recorded. CRM #23 policy included in this installed candidate | Rewrite not retested in the P2 three-turn trial or this maintenance; source equivalence and deployment are not new behavioral evidence |
| Knowledge example assumptions / redundant execution question | Latest passing native visit trial includes a suggested “three or four revisions” confirmation and asks whether to execute after explicit analysis-only intent; no customer fact assertion or tool operation occurred | Nonblocking UX follow-up: use the customer's actual number in examples, and finish after explicit analysis. Retain observations without more style-only model trials or weakening authorization |
| Catalog maintenance umask regression | Independent script review found root-only new directory access before execution; explicit root:root/0755 and seven real-account import checks fixed it; 14 Linux synthetic checks passed | Preserve this one-time release evidence; do not rerun historical installation scripts |
| Selected recordings / Miaoji transcript curation | Later phase, not implemented or ingested in catalog release | Select authorized material first; filter and draft for human review before publication; no automatic scan or wholesale transcript ingestion |
| Isolated tool transport interruption | One September 11 retest stopped on transport_unavailable before the original failing turn; no recurrence in the bounded diagnostic batch, cause unknown | Preserve failed attempt; do not claim root-cause resolution or weaken sandbox; investigate if it recurs |
| Initial three-source candidate build failure | Previous full builder failed in paired Go tests without preserving the failed subprocess stdout. A separate paired diagnostic and one unchanged full-builder retry passed; initial cause remains unknown | Keep failed evidence separate from the native transport issue. On recurrence capture full subprocess output; do not attribute it to path/load or declare a root-cause fix |
| 2026-09-08 expression candidate | Failed acceptance, never published; new policy passed selected factual regressions and exact fixed-stage replies | Keep original failures; new results are not retroactive approval of the old candidate |
| Old-policy native session restoration | Historical 37a70b2f policy resumed into d5c67095; cancelled/pending pair passed with fresh original-operation receipts | Preserve actual native resume evidence; do not infer approval status from history absence |
| Owner/test unguided daily tasks | New-version knowledge first queries, natural follow-ups and requested-source answers now passed within the recorded scope. Original September 10 reminder acceptance remains complete, not relabelled as a new run | Remaining new-version task goals: CRM entry, Sandbox profile/follow-up with approvals and ordinary reminder management. Local evidence reconciliation found no completed record for those new-version daily tasks; record actual account/version and any coaching, without replaying the entire old test matrix |
| Pre-write approval expiry and contention-test timing | [Issue #27](https://github.com/77AutumN/myanc-crm/issues/27): local isolated real-clock/SQLite/fake-backend experiment reproduced an old pre-guard elapsed-time gap. Separately, early Timer scheduling reproduced the CI expiry-test failure. Relevant runtime/test code is unchanged in the source-display revision; an unchanged CI retry passing does not fix either finding | Prioritize a separate expiry fix and synchronized regression. No production misuse established, no hotfix performed; hold a future runtime release until independent review, full CI and authorized maintenance. Do not waive expiry/zero-write checks or mix this into a wording-only deployment |
| CI runtime upgrade | Deferred, not a current failed CI claim | Separate compatibility PR and complete workflow tests |
| Login repair later evidence reconciliation | Deferred; repair alone does not prove root cause | Reconcile sanitized post-repair evidence without changing credentials |
| Original dirty worktree cleanup | Deferred | Inventory user-owned edits; obtain scope before moving/removing; never bundle research or runtime data |

For the September 11 Bot UX release, CRM #17 and gateway #8 are merged; exact main CI completion is recorded
in the linked delivery record. Deployment and post-start checks are complete;
**online colleague acceptance remains incomplete**. Owner/test independent trial
is still required. Installed hashes and protected-store preservation are recorded
separately from model/synthetic/historical human evidence.
