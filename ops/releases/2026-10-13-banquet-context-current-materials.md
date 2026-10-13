# Banquet context and current-material handoff

Status: source delivery and native Mac cutover complete; the fictional two-account handoff journey and post-cutover concurrent intake are verified. The model-behavior limitations below remain open and are not reported as acceptance passes.

The read-only banquet context joins the authorized customer, banquet, last ten follow-ups and handoff metadata, with source and missing-data information. Group conversations receive shared business facts; private handoff metadata stays in the participant's personal entrance. The context result never claims to have read document contents.

Handoff material use compares the verified publication's original business basis with current records. Stale, unknown and unavailable bases block new acceptance. The original submitter can import the latest stale publication as a durable revision reference; this does not grant current-material use. Renaming known stale bytes or assigning a new delivery does not permit republication. A changed hash alone does not establish that the document is correct.

## Source delivery

| Component | Target source | Delivery |
| --- | --- | --- |
| CRM | `f640fbb4e27c9cf8bc95fc064c4a5fe237e7f3f3` | PR145, audience fix PR146, client read budget PR147 |
| Gateway | `a1291efc9dc999c50d323c9537181e92c64bbf8f` | PR64, paired read budget PR65, shared-ledger contention PR66 |
| Knowledge | `ada437cac33d156634b70b20948dc7abc09bec7e` | Retained; not changed or packaged by this two-source release |

Exact-head Spec and Standards reviews are external to the candidate commits. Original dirty working trees were retained. Local CRM ran 611 tests: 596 passed and 15 existing tests skipped, plus paired host journeys. The latest Gateway fix has real dual-Store regressions that fail on its base and pass after the fix. Its combined Linux coverage is 49 passing packages and six without tests: the first full run retained a core CRLF-export failure, then all exact-LF core tests passed. This is not described as a single all-green local run. Exact GitHub CI is the separate source-delivery gate. CRM merge `f640fbb` push run `38355604987` passed both required jobs; Gateway merge `a1291ef` push run `38372532137` passed all seven, including both Mac jobs and race checks. The documentation-only archive commit does not replace either installed runtime SHA.

The read-budget repair covers the authenticated multi-file handoff path. The ledger repair retries only typed SQLITE_BUSY before a transaction callback begins; it never replays callbacks or commits. Shared operations remain serialized, and SQLite's existing busy handler can delay cancellation by about five seconds. Historical production SQL error codes were not logged: the contention diagnosis is supported by matching runtime state and a real reproduction, not a recovered historical SQL code.

## Native maintenance

The normal Darwin/arm64 candidate is bound to archive SHA256 `b39f68d12deca5f1ab937531e11896b5760d99107e137ba92a71246c9f1ab1be` and manifest `7a99af3089f6e2b7d990a4312fb8bd45b7755f344674a8efecf31957ee49f2a6`. Both final independent maintenance reviews passed. The frozen inventory has 413 files and 84 directories; only the Gateway binary changes. Installation completed with protected database/session backups and unchanged business state. Native startup completed on the fixed new process identity with 128.35 seconds of stability, 25 samples, four configured entrances and three unchanged established connections. The full installed inventory matched the frozen target manifest; logical business state, connection bindings and all six sessions matched the pre-cutover state. Real application-route acceptance is recorded separately below.

The first attempt to freeze the third maintenance stopped on the completed race-refusal record. Its exact full row and approval hashes were independently reconciled as one additional fixed exception; no production ledger or original four exceptions were rewritten. The extra pending card was not exempted and left the active set through normal expiry before the successful freeze.

The two earlier maintenance roots remain consumed, immutable historical receipts. The third candidate uses a separate root because it contains a new source version; it is not a retry of a consumed start. No database downgrade or old authorization snapshot is restored.

## Real fictional acceptance

Before the final contention cutover, the two personal entrances read current banquet facts. The corrected employee private scope and two-file imports worked. The shared employee entrance returned business facts without file metadata. The manager's shared entrance failed during concurrent file work; that failure prompted PR66. After cutover, a new manager-group message arrived during the employee's 47-second two-file import, waited and completed successfully. Both had distinct native tasks and no intake rejection. Both group entrances returned shared business facts and directed file metadata requests to the requester's private entrance.

The real fictional handoff progressed from a 20-table publication to a 23-table current record. The recipient's new acceptance stage was rejected; the wrong account could not obtain revision access. The original submitter imported both stale files as revision references. Actual saved stale Word/PDF bytes, renamed and delivered with new identifiers, were rejected at publication stage. Corrected files were independently read back and published as version 9 with the expected hashes and missing items.

A version-9 acceptance card was staged while the record said 23 tables. The manager approved 24 tables and received a verified write receipt. Clicking the earlier card before its expiry stopped before the acceptance write. A subsequent result query confirmed durable `replan_required / handoff_changed`; the existing full approval snapshot guard produced this outcome, so it is not attributed specifically to the new basis-comparison branch. Following the manager's restoration request and UI verified readback, a fresh employee query read 23 tables and returned version 9 pending with a current basis. An earlier version-8 attempt expired; that attempt is retained as an invalid race test.

The final runtime served both personal entrances and both group entrances. Group host results were shared/partial with private-required handoff scope; replies exposed no file names, versions or notification metadata. The unchanged logical file ledger and session snapshots preserve the existing revision-reference provenance across cutover; the real post-cutover import of current materials into a new employee work returned both exact publication hashes. The version-9 acceptance card was explicitly approved and displayed a verified write/readback receipt. The submitter's private assistant displayed the acceptance notification. A fresh submitter-side query at 17:55 China time read version 9 accepted at 17:53, estimated tables 23, publication basis current with no differences, and both submission/acceptance notifications sent. The protected event ledger independently records the acceptance notification sent to the submitter's private entrance. All six model turns in the final capture have matched starts/completions and no unmatched captured tool calls.

## Evidence boundaries

The restricted bundle is `banquet-phase1-evidence-20261013`; raw chats, recipient identifiers, private URLs, credentials and ledgers are not committed. Source delivery, native maintenance and real Feishu evidence remain separate. Automated cases cover the broader field/null/history, authorization, queue/restart and corruption matrix; two real accounts do not simulate every tenant or failure mode.

One model turn issued a fresh pending acceptance card despite an explicit read-only/no-new-card instruction. The card was not approved and no acceptance write was established; this turn is not a complete instruction-following pass. Another earlier turn performed aggregate reading and material import concurrently. After cutover, a model call discarded its running-session metadata and repeated a read-only aggregate request; a later handoff call retained and polled its running session correctly. These protocol deviations remain in the evidence. The recipient also described the document's explicitly dated pre-publication version-8 snapshot as inconsistent with current version 9; the saved text distinguishes its R1 document revision from CRM publication numbering and does not prefill a future publication number. This interpretive limitation is retained. PDF page-view calls are recorded, but the large captured image response was truncated; the independent review establishes actual document text/hash reads and page-view requests, not an independent visual certification of that truncated response.

Historical closed activity retains its prior limits: 59 old received outcomes and five queued deliveries remain unproven, 25 completion-only intake origins are not reconstructed, four guarded business exceptions remain, and three old SDK failures have unknown root causes. Closed lifecycle records are not relabelled successful business operations.

## Restricted evidence index

The following hashes identify the retained local bundle; no raw evidence is committed here.

| Evidence | SHA256 |
| --- | --- |
| Final canonical maintenance freeze | `8e57b2e141a78a6230f7821b20db4efa1869c133f74075a4450ade4c7cd4bcce` |
| Installed complete inventory | `e5832b95bab5055866c33958d1fe916821bb40f345426df883fda22f6b49a49a` |
| Final Spec maintenance review | `9a388090ece26f0204f61bc07a1ed12c61719e78d4176b189ffa986091ae160e` |
| Final Standards maintenance review | `bdd8ae1005ed99b9ed14333cc6777184709cfc800d2c3e825380bccf1bd99759` |
| Independent native-cutover review | `91311bd358db6be5a184075df5b3982f34a91a34e917257cbc4a59d2c6f4577d` |
| Final four-entrance public trace | `41f8909f0e6d4a38d97fba51b67735f3f079144dd39e4786bcf99e2a9496f573` |
| Concurrent intake metadata | `85c840decb5f6e1cfb0f6c46187b10a043004dcb28e19659391d2a55f969afa7` |

The real journey proves stale-stage refusal, before-expiry snapshot-race refusal, authorized revision import, stale-byte republication refusal, corrected two-file publication and normal acceptance. Old-version return, other changed fields, null/missing distinctions and broader queue/restart/corruption cases are automated evidence, not additional live Feishu runs. Native cutover checks prove logical provenance preservation; they do not claim a new live queue/reimport matrix.
