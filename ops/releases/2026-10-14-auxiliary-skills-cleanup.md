# Auxiliary skill loading and native fixture cleanup

Runtime source delivery, the authorized Mac update and four scoped live Feishu turns are complete. This documentation-only archive requires its own independent exact-head reviews, PR CI, squash merge and exact merge-SHA push CI. It does not change the installed source version.

## Defects and source delivery

The previous [native-query acceptance](2026-10-14-native-query-results.md) retained a real group-turn deviation: multiple Skills were combined into one tool result and file work-context ran without first loading its Skill. The new policy requires all applicable Skills and required references in the current turn, one complete file per result, before domain tools, including auxiliary read-only calls. The file Skill explicitly includes work-context and status. A replay of the original public tool trace still fails the new acceptance check; the original failure is retained.

The intermittent CI cleanup failure left a native CLI plugin directory nonempty after its parent process exited. A real Mac regression first demonstrated the underlying process-lifetime hazard: a child survived its parent and could write after parent-only cleanup. Both native CLI fixtures now start a separate session and share process-group cleanup before temporary-directory deletion, including when communication times out. Cleanup waits for non-zombie members of that group to exit. This covers the fixtures' process group, not descendants that actively detach into another group.

The first proposed cleanup used killpg with signal zero to observe group exit. [CI38514590983](https://github.com/777Autumn/myanc-crm/actions/runs/38514590983) failed on macOS with PermissionError after termination. That failure was retained and fixed by bounded process-table observation; it was not erased by rerunning the old head. The original nonempty-directory failure and the child-writer regression establish related evidence, not a deterministic replay of the original errno at the same directory.

[CRM PR155](https://github.com/777Autumn/myanc-crm/pull/155) independently reviewed final head `d8cd83a30c8d31e04d5a7b9f8550bf6520ae7532` against base `de9a5fd40a63162960fdc42efce39ac1b2dbde24` and squash-merged as `7c9a14c5c3c61ad5ac7eac6f2cd45ece2b118dcc`. Both Spec and Standards passed. Final-head push CI38514727761, PR CI38514731475 and exact merge push [CI38515351501](https://github.com/777Autumn/myanc-crm/actions/runs/38515351501) passed the required test and mac-maintenance jobs.

Local validation ran 626 tests (608 passed, 18 platform skips), 18 spike tests, and 69 runtime tests (45 passed, 24 platform skips). The actual pinned Mac Codex 0.157.1 CLI passed all eight integrated tests, including the real child-writer and timeout cleanup cases and the existing 32-second native HTTP query/exit-code regressions. These are finite checks, not a claim that CI can never fail again.

## Reviewed Mac update

The standard Darwin/arm64 builder verified exact source CI before and after packaging. Candidate SHA256 is `59308ad3e0aeef586b4f461dce7a5d458fb56b1681abbf51596b0f56d7c89982`; manifest SHA256 is `13842c4be304cd84cbb488d3ba166b68434ebafba58a763d7ac8ba554b9e0011`. Gateway remains `f28d9f479d55b70e08bdfc4ba36caa49e46ec7a9`; knowledge remains `ada437cac33d156634b70b20948dc7abc09bec7e`, unchanged and outside this two-source package.

Independent Spec and Standards reviews bound the complete 413-file/84-directory installation inventory and maintenance scripts. Exactly ten files changed: the canonical host policy and file Skill, plus each one's copies in the four active entrance workspaces. Ownership and modes remain unchanged. Historical inactive workspaces were preserved. The Gateway binary, native CLI/configuration, identity bindings, business ledgers and sessions were unchanged at the installation boundary.

The first read-only freeze failed before service or installed-file mutation. Its wrapper retained the stderr digest but suppressed the underlying detail; the cause remains unknown. A later fresh full freeze passed, followed by reviewed prepare, install and the normal one-time start. Neither failed receipts nor previous maintenance roots were reused or overwritten. Earlier staging/self-check/operator failures remain in the local evidence archive.

The new process passed a 131.18-second stable window with 25 samples, three unchanged established connections, one receiver and all four entrances. The installed inventory SHA256 is `68638624c15c9e598f35db307dae5f2458352dc29d2c33b9b4d3b1292096516b`. A post-acceptance read-only check confirmed the same process identity/start time and exact three socket tuples. The startup-only log classifier rejected later ordinary SDK data frames, so that later classifier result is retained as inapplicable to a second startup acceptance; the original stable-window receipt remains the startup evidence.

## Four live Feishu turns

Between October 14 13:29 and 13:36 Beijing time, the two authorized test identities sent one fictional read-only request through each private assistant and each group entrance. Both group messages selected the real bot mention. The requests naturally asked for available work materials and current banquet facts, without naming Skills or tools. All four final replies were observed in the desktop client.

Bounded public native traces reconcile to four SDK intakes, four host receives and four completed turns. Every call has its result; no captured output is truncated. Each turn individually loaded the file, CRM and relevant banquet Skills/references before its domain calls, with one file per complete result. Each queried current banquet-context once and work-context once. Optional case reads/listing and the recipient's handoff read were distinct additional reads, not duplicate banquet queries.

| Entrance | Observed result |
| --- | --- |
| Recipient private | Opened actual Word paragraphs/tables and both PDF pages, then rendered and viewed both PDF pages. Correctly distinguished R1 file revision and historical version 8/pending from current version 10/accepted, with estimate 23 and final table count unconfirmed. |
| Owner private | Read Word and extracted both PDF pages; explicitly reported garbled Chinese extraction and did not claim complete PDF-detail verification. Fresh CRM and Word supported the historical/current distinction and current estimate 23, version 10/accepted. No rendered-PDF verification is claimed for this turn. |
| Recipient group | Loaded file and shared-case protocols, found no current-work files, and did not treat an unrelated selected shared case as the requested banquet. Reported shared CRM estimate 23 and the private handoff restriction. |
| Owner group | Loaded applicable protocols, found no current-work files, queried the shared estimate once and explicitly left private handoff version/status unconfirmed. |

No turn staged a change, requested approval, delivered a new file or wrote a business record. All three existing approval rows are field-for-field unchanged before and after. Captured handoff events also stayed unchanged during acceptance. Local PDF rendering in the recipient turn produced inspection previews only, with no business delivery.

This closes the previously observed auxiliary loading deviation for these four turns. Skill policy remains cooperative model guidance, not a deterministic enforcement boundary. The owner PDF extraction limitation is retained; the separate recipient turn supplies actual two-page visual inspection. No new business-write acceptance was performed in this read-only batch.

## Evidence preservation

Raw chats, source documents, identity mappings, credentials and protected ledgers remain outside Git. Local evidence is in `aux-skills-cleanup-evidence-20261014`; all prior failure records remain in their original archives. All 38 pre-existing dirty files in the original CRM/Gateway worktrees match their baseline SHA256 values.

| Evidence | SHA256 |
| --- | --- |
| Independent maintenance reviews | `45f741060bcecbacdee53bf0f0626248abf83fc8f96f113688c3d9e4ea1200cd` |
| Stable startup receipt | `28a65dc5e65fbe77cba0665ef9cfb8b3e1e39c4670556ebac3ee05085faff099` |
| Four-turn public tool/reply capture | `f6dfae36b70442eb3752359da73db3477306b021b23f5d1e0800341a4594b4d2` |
| SDK/host association | `2cd990ee7f5aee9b38338cfc839ef71b973a538c726c5270f45aa9c798a69e1c` |
| Post-test approval rows | `4272ca66967d80a139227071995182d2be1008b94e4815ecac45b261e49fbb88` |
| Acceptance reconciliation | `fd800f1c2d52e7e0c6a66b1a062e1b66f342e7c29864a22129ce1247db0d512d` |
| Original dirty-file preservation | `69b407df3dc8644df19761ec0890b1ef14edc250a5d249f71c65f273e3bc58a3` |
