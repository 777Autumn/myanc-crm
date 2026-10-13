# Banquet read-only behavior follow-up

Status: source delivery, second native Mac cutover and the targeted live defect cases complete. Residual protocol adherence limits are recorded below; the first candidate's historical-version failure remains retained.

The controlled CRM protocol now preserves exec session metadata and polls a running query instead of repeating it. Banquet material checks distinguish dated source snapshots and file revision labels from current host versions. Each new turn determines read versus write intent afresh: reading a failed, expired or replan-required receipt does not stage another card. A later explicit acceptance request still uses the existing approval flow. No authorization boundary or business ledger rule changed.

A first native retest still misread the historical snapshot. Its combined seven-reference tool result was truncated before the new banquet rule, and the model did not reread that reference. The second change directs separate complete reference reads and recovery of truncated sections. This is model guidance, not a deterministic enforcement boundary.

## Source delivery and checks

CRM PR149 merged reviewed head `2f9ece612dfa3375f4ed85f73f7316e3637a9a7a` as `eefa9f0fe0ee6c3c6492316b6f89c9e30c5d4b27`; PR CI38407095950 and exact merge push CI38407537270 passed both required jobs. PR150 merged reviewed head `3730f2a9b12a6c71a0e20d5bb9f01ccc1789627d` as `c5d32f78bdc7c32a1813c0005b7d5297fd5d77ba`; PR CI38412728312 and exact merge push CI38413030645 passed both required jobs. Each pair has identical Git trees and independent exact-base/head Spec and Standards reports outside the commits. Original dirty worktrees were retained.

The final fresh candidate ran 616 CRM tests: 601 passed and 15 existing skips, plus 18 spike tests and six required paired CUJs. Five focused fixture/grader tests passed. Four observed bad decisions are retained as rejected fixtures, including missing truncated-protocol recovery. The initial simplified old-policy model diagnostic did not reproduce all original live bugs; an overly strict unknown-body grader was corrected and its old results retained. Nine final fixed-model diagnostic cases pass, but they provide the complete protocol directly and cannot establish native protocol-loading behavior.

Gateway remains `a1291efc9dc999c50d323c9537181e92c64bbf8f`; the candidate verifies its exact push CI38372532137, including both Mac jobs. Knowledge remains `ada437cac33d156634b70b20948dc7abc09bec7e`, unchanged and outside this two-source package.

## Native cutover

The second Darwin/arm64 archive SHA256 is `844b44e2d9f49540975605906ed16f0fc11e0b64f2328f8319f787f125077a17`, manifest `82fc69e592f9c6cbb8cf64bad124e2b231ccae31bf451cb2194273cd0c4233c1`. Independent maintenance reviews bind the full 413-file/84-directory inventory, existing protected prior plan/review, activity evidence and maintenance source. Only the canonical CRM Skill entry and its four entrance copies changed; the Gateway binary hash is unchanged.

The new-source candidate used a new protected maintenance root. All consumed prior roots and the first candidate's successful cutover followed by failed behavioral retest remain immutable. Prepare freshly compared the frozen live state; install verified backups, stopped the single receiver and replaced the five files. One startup passed 129.22 seconds of stability with the same process identity, three unchanged established TLS connections and four configured entrances. Complete target inventory SHA256 is `d5b6a9b78f59714f4342b67f94eb33e3f38bf7c26852e7537a068fffe2975614`. Business state, connection bindings and six sessions were unchanged through maintenance. The pinned Mac Codex0.157.1 runtime and its permissions were retained.

Before this cutover, 5652 audited log rows plus 48 new rows were reconciled, with all 116 native lifecycle prefixes preserved and one new closed read-only turn. No card callbacks or open turns were introduced. Lifecycle closure did not convert that first candidate's historical-version failure into a pass. Existing exact business exceptions and old unknown outcomes remain unchanged; three masked SDK startup messages retain the classifier's unenumerated-query-key limitation.

## Live fictional acceptance

Nine native turns across both personal and both group entrances completed between 14:44 and 15:10 UTC. Each has a unique SDK message, gateway receive/completion pair and native start/completion; no captured tool call lacks a result. The earlier first-candidate failure is a separate tenth intake in the wider collection window.

- The repeated ordinary read-only request initially concatenated references again, then repaired the truncated load with separate reads. A complete standalone banquet protocol reached the model before domain queries. It actually read Word paragraphs/tables and both PDF pages' text, then requested both rendered page images. Its reply correctly treated the 16:22 version-8 snapshot as historical relative to version 9 published at 16:31 and accepted at 17:53. R1 stayed a file revision label; historical 20 tables did not replace current 23. No approval was created.
- An explicitly requested submit card republished the same verified R1 file hashes to the designated fictional recipient as version 10 pending, keeping 23 tables and the other business facts. The operator approved only that card; the host recorded verified write/readback and delivered its private notification.
- During the explicitly requested version 10 acceptance preview, the actual handoff import exceeded 30 seconds and returned session 57507. The model called `write_stdin` for that same session and read its successful completion, without repeating the handoff command. It read the imported bodies before creating the requested card. The operator cancelled it; the host recorded cancelled/no write.
- The next user turn explicitly requested only the cancelled and earlier failed operation receipts plus current facts. The model read both receipts and one current context, answered cancelled/replan-required and version 10 pending, and did not call any stage operation. Full approval rows were identical before and after: two existing records, zero additions.
- A later explicit request produced one new acceptance card. After operator approval, its host receipt was verified. Fresh recipient and submitter reads independently returned version 10 accepted, 23 tables and acceptance at 23:03 China time; the submitter also read sent submission/acceptance notifications. The old cancelled card stayed cancelled.
- Both group entries performed read-only current-context queries. They returned shared customer/banquet/follow-up facts and the host's private-required handoff boundary, without exposing private material/version/notification metadata or staging a card.

The final approval window contains exactly three authorized proposals: verified submit, cancelled acceptance, verified acceptance. Success-result and group readbacks added none. No repeated CRM read command was observed within these nine turns; the two `result` calls in the failure-check turn concern different operations. This is observed behavioral coverage, not a universal model-compliance claim.

## Evidence and limitations

Restricted evidence is retained in `banquet-behavior-evidence-20261013`. Public native traces include user messages, visible replies and tool calls/results; hidden reasoning is excluded and image payloads are deliberately omitted. Recorded document text/hash reads and image-view requests do not constitute an independent pixel-level certification of omitted images. Raw chats, private links, recipient identifiers, credentials and ledgers are not committed.

Some later completed-read wrappers still emitted only `output`, despite the protocol requiring the complete exec result. Those calls finished and did not repeat; the separate real running-session case above retained metadata and polled correctly. This residual protocol adherence risk is retained explicitly. The owner submit turn also read the complete banquet rule in a combined, untruncated result rather than a standalone one. Do not report every wrapper or reference load as fully compliant. Broader timeout, expired-receipt, quoted-intent and true-current-conflict cases remain automated/diagnostic coverage, not additional live runs.

| Restricted evidence | SHA256 |
| --- | --- |
| First candidate failed public trace | `89fa101d2b8258f37215aa6f187884cca94b87ce9ce195847cba4ccb52736598` |
| Second candidate final four-entrance trace | `2294b7d22ccc61ae34b71af088567c5ee642514ac46cb3d9b8c8c120d37df019` |
| Intake metadata | `8c4f499c7f9fa91c92fb9c47e31444700a7a80d94d00b7ddb025952eb44648ac` |
| Message/turn and approval associations | `8d1216a8c2efe4d90f17978771745c15ee5d502737d8ee806e49c2eacb8b6029` |
| Final approval readback | `68fdde6eb036becf2b76f8ebfdd6b89df57aba3fb17f8626e98958893a068610` |
| Final canonical maintenance freeze | `7a1ac3c2469023246d2fb5d02ecb702a45a684e1e989c3eb9862537a5bc88428` |
| Independent Spec maintenance review | `4d7b874ae2c73dd452c7430ab402a7e1c9baf6fd9e54de60728cb205498b4dbb` |
| Independent Standards maintenance review | `46d1fd6dc5382332259971a8638347fafeca5e505152f6cbc2c065bdf9da01e0` |

This archive commit is documentation only and does not replace the installed CRM source SHA. The earlier release archive and all original failure evidence remain unchanged.
