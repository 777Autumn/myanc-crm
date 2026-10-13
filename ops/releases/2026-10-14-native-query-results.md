# Native query results and slow-query acceptance

Status: runtime source delivery, native cutover and the scoped five-turn live acceptance are complete. Broader skill-loading compliance remains incomplete as detailed below. This documentation-only archive needs its own exact-head reviews, PR CI, squash merge and exact merge-SHA push CI.

The pinned Codex 0.157.1 runtime now exposes the `functions` namespace directly using `features.code_mode.direct_only_tool_namespaces = ["functions"]`. The same native tools are unavailable inside nested JavaScript. This removes the `text(r.output)` path that discarded a running command's session handle, status and eventual exit code. CRM and file-production references describe the native call path. No model catalog, business rule, authorization boundary, Gateway binary or dependency was changed.

## Source delivery and regression

[CRM PR152](https://github.com/777Autumn/myanc-crm/pull/152) reviewed head `653eb8763f7281910533dc736b2fc89ab703f8f7` against base `ee0668c76b7413d2a5c97403e7fa1b640616d6d9`, then merged as `2997d5fff14df3f609801d4e664134e815c622a9`. Independent Spec and Standards source reviews passed. PR CI38438259156 and exact merge push [CI38438710567](https://github.com/777Autumn/myanc-crm/actions/runs/38438710567) passed the required test and mac-maintenance jobs.

The defect was first reproduced with the actual pinned native Mac CLI and a scripted local Responses API: a real loopback HTTP GET took 32 seconds, outlasting the initial 30-second command wait. The old output-only wrapper reported an empty completed script while the read remained active, without its running handle. Under the new configuration, the command returned its session handle, polling returned the full body and exit 0, and the server observed exactly one GET. A second real request returned partial output and then exit 7; polling preserved both. Attempts to use the old nested execution and polling wrappers failed before invoking those tools. Both native regression tests passed; the non-Mac local run is not counted as native coverage.

The fresh Darwin/arm64 candidate ran 618 CRM tests (602 passed, 16 existing/platform skips), 18 spike tests and six required paired CUJs. Candidate checks verified exact merged-SHA CI before and after building. Gateway remains `f28d9f479d55b70e08bdfc4ba36caa49e46ec7a9`; knowledge remains `ada437cac33d156634b70b20948dc7abc09bec7e` and is unchanged/outside this two-source package. Candidate SHA256 is `9285ee40899347a78ef3cd4571db6813cbe7abef7b121cb95f3afa3058de605c`, manifest `176688deb9f263e6d0e8ec4ee3d999ba2e60297034e932642b08e379b0176ae5`.

## Native maintenance and retained failures

The full 413-file/84-directory inventory was independently reviewed. Eleven paths change: the canonical CRM/file references and their four entrance copies, plus the shared native Codex configuration. The native configuration keeps all existing permissions and other settings; only the direct-tool feature is added. Gateway binary SHA256 remains `761d2774258e63db8840fd4610285c9eac96486bce1c70e695678d2a07bb1c3a`.

An initial preflight rejected an unknown physical process before any attempt, stop or installation. A subsequent observation found a transient background read process chain, but does not prove which executable caused the earlier rejection. The prepared baseline expired; its root remains untouched. A renewed full freeze matched every live baseline field except observation time and received new independent reviews.

The renewed attempt stopped the service at 17:59:47Z on October 13, then rejected an extra `handoff notices unavailable` shutdown warning. All old files, business ledgers, connections and sessions remained unchanged; no backup or installation had begun. Gateway source emits this warning when its read-only notification query fails or returns non-ok. Cancellation during shutdown is plausible, but the unlogged underlying error is unknown. No general warning allowlist was widened.

A separately reviewed continuation bound the exact failure receipt, six-file failed root, stopped process state and four shutdown log fields. It retained both failed roots, used a new exclusive recovery root, and reused the reviewed backup/install and one-shot startup/stability helpers. Independent review first blocked a missing TERM/HUP handler in that continuation. The corrected source and eight passing Mac tests include actual TERM/HUP signals to the test process, with a fake service backend, confirming protective pause and failure recording. Both blocked reviews and their exact source are retained. The real recovery then passed fresh prepare and installation, with all business state unchanged.

Its first start established three SDK connections, then one TCP read timed out and reconnected. The strict stability check rejected that epoch and successfully stopped the service. A proposed new-directory restart was blocked by Standards review because the contract requires the original receipt directory and `recover_once`; its initial Spec pass was withdrawn. That proposed restart was never prepared or executed.

The operator's continuation script had omitted the three candidate digests from its immutable attempt receipt. This defect was also missed in the earlier maintenance review; it prevented the existing `recover_once` from accepting the original receipt. Rather than patching evidence or bypassing the helper, [PR153](https://github.com/777Autumn/myanc-crm/pull/153) added reviewed, append-only supplemental bindings. Reviewed head `2ee56b4ec9ca5295a1d2998dd8b6c588a4591af0` against base `2997d5fff14df3f609801d4e664134e815c622a9` merged as `f608fa23da5863f5c1c1e4fcaf9c5c6db9127f29`. Independent Spec/Standards reviews, PR CI38446977079 and exact merge push [CI38447327948](https://github.com/777Autumn/myanc-crm/actions/runs/38447327948) passed. Local maintenance regression ran 101 tests, with 96 passing and five platform skips.

The separately staged released helper SHA256 is `7e51d60fa6cef77813b5e3b8e69a472e6e65e9728eaa043ffd57a9728d86b194`. The recovery binds an exact byte copy of the pre-existing complete installation attempt, retains the original incomplete attempt and startup failure, and uses the original one-time recovery marker. It does not reinstall or relabel the runtime candidate. Neither the 125-second network stability requirement nor the protective-stop behavior is relaxed.

Initial staging-format failures, a prototype stdin timeout, read-only collector/fixture failures and the original red regression remain local evidence. None is represented as a passing production check. Original dirty worktrees remain preserved. Credentials, raw chats, recipient identifiers, private document links and business ledgers are excluded from this archive.

The same-root recovery passed its independent Spec and Standards reviews and completed successfully. The observed launchd process remained stable for 130.4 seconds across 25 samples, with three unchanged established TCP connections, one receiver, no restart, and all four configured entrances. Installed inventory SHA256 remained `52f4a78f068d3a2e6a836814e262d24ac0bc21ce33ef1575eaa828ac419c98ca`; business ledgers, identity bindings and sessions were unchanged at the maintenance boundary. This proves startup stability only; Feishu routing is checked separately below.

## Live acceptance

Five real Feishu messages were sent through the desktop client between October 14 02:52 and 03:03 Beijing time, using the two authorized test identities, their private assistants and actual bot mentions in the designated test group. Host intake, public native-tool transcripts and completed reply records reconcile to exactly five SDK intakes, five received messages and five completed turns across four entrances. No native call is unmatched, no captured result is truncated, and each turn has one banquet-context execution. Hidden reasoning and image payloads were excluded from the capture.

| Check | Observed result |
| --- | --- |
| Controlled slow private query | One command waited 35 seconds before one real CRM query. At 30 seconds it returned a live session handle; two direct polls used that same handle and returned the complete body plus exit 0. Total command-to-result wall time was about 47.8 seconds. |
| Historical material reading | The recipient reopened the actual delivered Word paragraphs/tables and both PDF pages, then viewed both rendered PDF pages. R1 is the file revision; version 8/pending is the timestamped historical handoff snapshot, while fresh CRM reports version 10/accepted. The files distinguish historical consideration of 20 tables from the current estimate of 23; the final table count remains unconfirmed. |
| Owner private current facts | Fresh CRM reports expected May 2027, no exact date, venue pending, estimate 23 and final count unconfirmed; current handoff is version 10/accepted. |
| Owner and recipient group reads | Each reports the shared CRM estimate of 23 and explicitly declines to infer private handoff version/status. Neither reads or forwards private material. |
| Read-only behavior | No staging, approval submission or file-delivery call occurs. The three existing approval rows are byte-for-field identical before and after; no new approval card is created. |

Two obsolete JavaScript wrappers were attempted while loading the first skill, failed with `tools.exec_command is not a function` before executing a shell command, and were followed by direct native calls. These failed attempts are retained, not presented as successful calls. All actual execution/polling results use the native return format. The optional private case-read/case-list lookups remain distinct extra reads; they do not repeat the banquet query.

The owner-group turn combined two skill files into one result, omitted the team-banquet shared-cases reference, and invoked file work-context without loading the file skill. The CRM tool and banquet references were each loaded completely in separate results, and the returned answer respected the group restriction. This is a retained instruction-loading deviation: the scoped metadata, duplicate-query, historical-state and approval checks pass, but this run does not establish full skill-loading compliance. No broader compliance fix is claimed here.

A read-only process check after the five turns still found the same service PID and start time. All 38 recorded pre-existing dirty files in the original CRM and Gateway worktrees retain their original SHA256 values. No original working-tree change or failed maintenance receipt was removed.

The slow-query exercise uses a deliberate delay before a real read; it is not a measurement of naturally slow upstream CRM behavior. The earlier native regression independently exercises a genuinely slow loopback HTTP response and delayed nonzero exit.

This archive is documentation only and does not replace the installed CRM source SHA. Finite live checks cannot establish all model behavior; the namespace restriction specifically removes nested native-tool calls that could discard command metadata.

## Local evidence anchors

Raw evidence stays in the local `banquet-slow-query-evidence-20261014` archive. These digests bind the reviewed copies without publishing raw chats or protected state.

| Evidence | SHA256 |
| --- | --- |
| Same-root maintenance reviews | `eb149554c33c31069db81567b59fbf4b6b939d2c593fb62ddc9eec9abeaa6d01` |
| Stable startup | `a7deb3a04c8b7910c0d64ef881c19a228b0af32b0c63b23863b95cad12d07a69` |
| Five-turn tool and reply capture | `69f24adad9f0ab56fa8baee8e91a6bb4b37fb38952b6a0ca1870df6ed3dea8e8` |
| Host intake and completion association | `cbbb6eaa4246155200eaa0ab8b9c1d9b540b2553ed9b86a831d52f04de7866a4` |
| Post-test approval rows | `ed5d407dcce41e6046bc53ac7a8975f372080e02892e8a012eed2952dae90a73` |
| Acceptance reconciliation | `13f2fda1eb0ebccfbde7674f4531f53ceb11f62b1dd3d6fe96814728bf535083` |
| Original dirty-file preservation | `aafe3e3dcf311e74658f4952b4dfb745b4d8691d9d83229d92b956d8e53fe8f3` |
