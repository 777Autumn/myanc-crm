# PDF visual fallback after unreadable extraction

The source fix, reviewed Mac update and two scoped live Feishu private turns are complete. This documentation-only archive requires its own exact-head independent reviews, PR CI, squash merge and exact merge-SHA push CI; it does not change the installed runtime source.

## Defect and source delivery

The owner-private turn in the [previous acceptance](2026-10-14-auxiliary-skills-cleanup.md) extracted garbled Chinese from a two-page PDF and disclosed the limitation, but stopped without using the available renderer. Before changing policy, the original public tool trace was fixed as a regression case: it has no matching render manifest or returned page images and fails the visual-coverage check. The original failure remains unchanged.

The shared file-production reference now requires rendering and visually reading affected pages when PDF extraction is garbled, misordered, missing or otherwise unreadable, including read-only questions. Unknown affected-page coverage requires all pages. Rendering alone is insufficient. Inspection previews stay in the current work without creating a business delivery or approval. Actual permission denial or rendering/reading failure retains the existing stop rule, with affected pages and uncertainty reported.

[PR157](https://github.com/777Autumn/myanc-crm/pull/157) reviewed head `59963b903a58b899327e61e9076caf64d6bb82f9` against base `abccdceaa296b9aee82d5f51d1df467602b8906f` independently on Spec and Standards, then squash-merged as `1c69695c3ee11a60f404abaae8f454a2bb4cbb8f`. Head push CI38519102730, PR CI38519133232 and exact merge push [CI38519384687](https://github.com/777Autumn/myanc-crm/actions/runs/38519384687) passed the required test and mac-maintenance jobs.

Local validation ran 626 tests: 608 passed and 18 platform-specific tests skipped. The existing behavior grader's five tests passed, and all 12 model-decision cases passed, including unreadable extraction, rendered-but-uninspected pages and permission denial. The diagnostic used local CLI 0.159.0 and does not execute the actual PDF tools; production acceptance below used the pinned native Mac CLI 0.157.1. The standard candidate build also passed its 18 spike tests and six required paired CRM/Gateway CUJs. No new dependency or rendering implementation was added.

## Reviewed Mac update

The standard Darwin/arm64 builder verified exact source CI before and after packaging. Candidate SHA256 is `bde9f1d009dd076428821fe4922b4f6cc5c170efd7f5e2796b497f10cb4642f8`; manifest SHA256 is `69d281a8834f1dff7473f9c8c4ed420f63c0e210b02b923bbc9343937bd51c0f`. Gateway remains `f28d9f479d55b70e08bdfc4ba36caa49e46ec7a9`. Knowledge remains `ada437cac33d156634b70b20948dc7abc09bec7e`, unchanged and outside this two-source package.

Two independent maintenance reviews bound the source, wrapper, frozen candidate, activity reconciliation and complete 413-file/84-directory inventory. Exactly five files changed: the canonical file-production reference and its copies in the four active workspaces. Each new policy copy hashes to `81fac94247896acd57944de0aa5a16fc9e13aeb4b1af274de2f7a43aeab67831`. File ownership and modes, gateway binary, native CLI/configuration, identity bindings and historical workspaces were unchanged. Prior activity reconciliation accounted for 70 appended records, with no unclosed native turns or unexplained new events.

The new maintenance root completed prepare, install and one normal start. No previous start attempt or recovery marker was reused. The new process passed a 129.84-second stable window with 25 samples, three unchanged established connections, one receiver and all four entrance routes. Business state, connection bindings and sessions were unchanged at the installation boundary. Installed inventory SHA256 is `8db6e0328b1115b7589fc4970c230612e3939fd9d1d8b923b866a4d3abca8ff2`. A post-acceptance read-only probe confirmed the same process identity/start time, exact three socket tuples and installation inventory.

## Real Feishu acceptance

Between October 14 14:16 and 14:19 Beijing time, the owner and recipient each sent one fictional read-only private request to read the current handoff PDF and distinguish its historical facts from current CRM records. Neither request named the renderer, page-image tool or Skills. Both final replies were observed in the desktop client.

| Entrance | Observed execution and result |
| --- | --- |
| Owner private | Loaded the new production reference, rendered the original PDF directly after the earlier known extraction failure, read its manifest and actually viewed both page images. Correctly reported historical handoff version 8/pending at October 13 16:22 versus current version 10/accepted, estimated 23 tables and historical consideration of 20 tables. |
| Recipient private | Extracted garbled text during this turn, then rendered the selected current-handoff PDF, read its manifest and actually viewed both page images. Correctly separated file revision R1 from CRM handoff versions and preserved the distinction between estimated and final table counts. |

Both manifests bind the same two-page original SHA256 `e6319034b87a85493b22d0abb39fed1954ab2f60adb8feeb85382d5547d34827`. Page hashes match across the two accounts. The owner's already-created page images were fetched read-only, verified against those hashes and visually inspected again: page 1 clearly distinguishes the historical snapshot and table estimates; page 2 lists unresolved matters and repeats that final tables are unconfirmed. No OCR or text extraction was treated as a substitute for image inspection.

The bounded public trace reconciles to two SDK intakes, two host receives and two completed native turns. All 32 tool calls have complete matching results. Each turn loaded applicable Skills and required references separately before domain calls and queried current banquet-context exactly once. The owner used work-context once; the recipient obtained the selected PDF from the authorized handoff read. Additional case reads/listing were distinct context reads.

No turn staged a change, requested approval, delivered a new file or wrote a business record. The same three approval rows are field-for-field unchanged, and fixture handoff events match the previous acceptance capture. Rendering created local inspection previews only.

These two turns close the observed failure for this original two-page fixture. The policy remains cooperative model guidance, not deterministic enforcement. This batch did not repeat group or business-write acceptance; unchanged group routes were checked at startup. The initial partial capture is retained separately and is not used as completed-turn evidence.

## Evidence preservation

Raw chats, documents, page images, identity mappings, credentials and protected ledgers remain outside Git in `pdf-visual-fallback-evidence-20261014`. Prior failure archives remain intact; all 101 indexed files from the immediately previous batch and all 38 original dirty CRM/Gateway files were rehashed unchanged. Local operator failures, including a copied probe self-check timestamp outside its narrowed window and its corrected UTF-8 update, remain documented without altering the earlier evidence.

| Evidence | SHA256 |
| --- | --- |
| Original failing visual-coverage result | `02beb90a8f2e4164050075b73c589897e7a3c9bd696c56637529a1e12db6768b` |
| Independent maintenance review bindings | `2caf00daa2c5222bafee919063e2eded661f38600351557b51b3d1162fc329d8` |
| Stable startup receipt | `25281ca42b8c7cf7832b2554169e697fad5728dca8f92de3567e103464aaeae3` |
| Completed two-turn public trace | `a6fbd19f38b2506f3863b52310030c86bb3cbb898a28df1203d0e6d2ce51ab81` |
| SDK/host association | `62cbfb44da4292ea1b9f731e32a4c26914765244f6b71b5761b5c70ce79fe87a` |
| Post-test approval rows | `76476c74eb07e4fce374f7483e0f0a55b3226f59dca9ceb23a964623d45e303a` |
| Acceptance reconciliation | `ce0abd369161840bc2d365974bd0cf7de95bbdb5f580f0102a655e09c9075d89` |
