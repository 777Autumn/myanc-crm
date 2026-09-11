# Tracked delivery and experience follow-ups

Updated 2026-09-11. This ledger distinguishes implemented source, GitHub delivery
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
| Natural knowledge discovery without exact titles | Catalog/read/scoped-cursor implementation merged in knowledge #12, gateway #9 and CRM #20; exact main CI and three-source CUJs passed; authorized catalog deployment and live isolation checks completed; test new-session lookup called catalog and two reads without errors, both sources opened | Owner old session AND user-started new-session same-question retest called no tool. First-query triggering remains a functional defect. Later coached Owner answer has screenshot plus successful reads/citation; test follow-up reused its read source. Neither follow-up's link/UI evidence closes original-query acceptance. Repair entry/skill selection and validate ordinary, uncoached questions |
| Knowledge trigger diagnosis and English narration | Owner new-session native trace confirms no retrieval, ruling out old context alone; test new session retrieved sources but showed one English process sentence | Do not repeat /new as a fix or count coached follow-up as original-query acceptance. No silent reset/live prompt patch; English wording alone remains nonblocking under practical acceptance scope |
| Implicit knowledge entry follow-up | CRM #22, knowledge #13 and gateway #10 merged; exact main CI and prior three-source engineering candidate passed, not deployed. Two uncoached native questions retrieved/read sources; quoted commands and explicit no-lookup requests respected | GitHub-only delivery until separate maintenance; single trials do not prove reliability or replace Owner/test live acceptance. Mapping: `releases/2026-09-11-knowledge-grounding-candidate.md` |
| Knowledge coverage claim (P2) | Two prior batches failed. New combined candidate again asserted “逐字话术模板团队库里暂未收录” after only one page was read. Native trace confirms the Skill and new evidence protocol were loaded successfully | Still incomplete. Knowledge #14 remains draft; CRM knowledge-rule changes withdrawn from #23. Retain failures; no further model retry or production release from this result |
| Rewrite temporal fidelity (P3) | Prior batches changed timing and/or necessity. The new positive rewrite procedure passed one sample on the recorded combined candidate: “第一次去见客户，得先摸清楚对方的业务流程。” No tool calls | CRM #23 narrowed to that unchanged rewrite paragraph plus records. Its final context restores old knowledge rules, so the new combined pair is not native-tested. Source delivery may proceed; deployment and overall semantic acceptance remain incomplete |
| Catalog maintenance umask regression | Independent script review found root-only new directory access before execution; explicit root:root/0755 and seven real-account import checks fixed it; 14 Linux synthetic checks passed | Preserve this one-time release evidence; do not rerun historical installation scripts |
| Selected recordings / Miaoji transcript curation | Later phase, not implemented or ingested in catalog release | Select authorized material first; filter and draft for human review before publication; no automatic scan or wholesale transcript ingestion |
| Isolated tool transport interruption | One September 11 retest stopped on transport_unavailable before the original failing turn; no recurrence in the bounded diagnostic batch, cause unknown | Preserve failed attempt; do not claim root-cause resolution or weaken sandbox; investigate if it recurs |
| Initial three-source candidate build failure | Previous full builder failed in paired Go tests without preserving the failed subprocess stdout. A separate paired diagnostic and one unchanged full-builder retry passed; initial cause remains unknown | Keep failed evidence separate from the native transport issue. On recurrence capture full subprocess output; do not attribute it to path/load or declare a root-cause fix |
| 2026-09-08 expression candidate | Failed acceptance, never published; new policy passed selected factual regressions and exact fixed-stage replies | Keep original failures; new results are not retroactive approval of the old candidate |
| Old-policy native session restoration | Historical 37a70b2f policy resumed into d5c67095; cancelled/pending pair passed with fresh original-operation receipts | Preserve actual native resume evidence; do not infer approval status from history absence |
| Owner/test unguided daily tasks | Prior Owner knowledge screenshots showed an untitled-query miss then an exact-title answer with an openable source; that is symptom/partial-use evidence, not acceptance of the new catalog version | Remaining task goals: CRM entry, Sandbox profile/follow-up with approvals, reminder management, new untitled knowledge query; record actual account/version and any needed coaching |
| CI runtime upgrade | Deferred, not a current failed CI claim | Separate compatibility PR and complete workflow tests |
| Login repair later evidence reconciliation | Deferred; repair alone does not prove root cause | Reconcile sanitized post-repair evidence without changing credentials |
| Original dirty worktree cleanup | Deferred | Inventory user-owned edits; obtain scope before moving/removing; never bundle research or runtime data |

For the September 11 Bot UX release, CRM #17 and gateway #8 are merged; exact main CI completion is recorded
in the linked delivery record. Deployment and post-start checks are complete;
**online colleague acceptance remains incomplete**. Owner/test independent trial
is still required. Installed hashes and protected-store preservation are recorded
separately from model/synthetic/historical human evidence.
