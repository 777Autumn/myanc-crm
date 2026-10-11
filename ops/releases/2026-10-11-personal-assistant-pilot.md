# Personal assistant pilot acceptance

Status: the two-account pilot is installed and its core journeys passed.
The three supplementary abnormal-path tests below are complete within their
stated layers. The employee's lightweight read after the latest restart is now
verified; independent Spec and Standards reviews permit two-account pilot closeout
within these evidence boundaries.

The personal-Bot route is a pilot. The original single/public-Bot route remains
a product option; the present pilot routes common-group work to the public Bot
and redirects its old private chats. Retaining that option does not restore old
authorizations or copy private conversations between Bots.

## Installed versions and source delivery

| Component | Installed source | Delivery |
| --- | --- | --- |
| Gateway | `09fb8b95536ad9e8d9bda0f840fe27525335b9d8` | PR62, then guidance fix PR63 |
| CRM | `7c00a153296105893ca78b68d2383791c03e1eb4` | PR142 |
| Knowledge | `ada437cac33d156634b70b20948dc7abc09bec7e` | PR22 |

One Mac mini, one Gateway, three app channels and four business entries retain
the shared Codex backend. Codex is 0.157.1 with gpt-6-luna. Credentials, individual
connection versions, authorization checks and business ledgers remain protected.
The guidance candidate archive SHA256 is
`17c371ebb04f4591a9ad7ad63baf0801e31c2176555b829b7176abe4ad15aa77`;
the unchanged config SHA256 is
`402193cf2f04398ad5c144b40c69f226e447a9b6aa043b77fc92320113b295a5`.

Exact PR/merge CI and independent source review records are indexed by
`three-source-release-gate.json` and
`handoff-guidance-frozen-standards-ci.json`. Initial installation and guidance
maintenance receipts are preserved, including failed starts, their reviewed
recovery, and platform-specific test failures/skips. No failed run is relabeled
as a pass. This archive-only change installs no code and is not a new candidate.

## Accepted journeys

- Both real accounts queried authorized CRM/knowledge and received Word files.
  Actual native turns overlapped by 20.51 seconds; this is not a capacity claim.
- Manager-to-employee handoff covered publication, return, a new version and
  approved acceptance. Version 5 initially failed tool discovery and required
  assistance; that failure remains recorded. After the guidance fix, reverse
  version 6 independently read the published material and completed acceptance.
- Employee disconnect rejected the old work. Reauthorization advanced only that
  connection to version 10; a new read succeeded while old work remained blocked.
  The manager's connection stayed at version 1.
- Unreadable version 7 material refused startup. Restoring its original access
  allowed organization; duplicate clicks did not create another work.
- Personal reminders arrived once per member. The old public private-chat
  attachment route gave its fixed guide and left host state unchanged. An expired
  old card had no observed effect; that alone is not proof of every legacy guard.

## Three supplementary tests

| Test | Evidence and result | Boundary |
| --- | --- | --- |
| Started, valid notification across restart | New maintenance receipt; normal pause/start, one Gateway, three app channels and 127.0449 seconds stable. Reclicking the same version 7 notice produced `handoff_already_started`; native trace and handoff events were identical before/after. | Real Feishu click and real service restart; no new work, model turn or business write. |
| Failed/unknown delivery recovery | Existing CRM fixture with real SQLite and approval code covered before-send failure, a real send with hidden receipt, and omitted ack after a real send. Reopening did not requeue; repeat claim was refused; normal lookup and approved acceptance worked without duplicate writes. | Synthetic business identity/backend, real fixed personal-Bot sender. Not a production Engine polling/network-fault or native-crash test. |
| Manager alert and recovery | Existing alert state machine, trusted manager route and real sender emitted one warning and one recovery; another tick emitted nothing. Both were observed in the manager's personal Bot. | Synthetic health snapshot and separate alert database; not a test of detecting every real production fault. |

All synthetic messages were labeled as tests. They had no business action
buttons. Actual send runs compared four production database snapshots before
and after; these remained equal. Neither sender started a receiver or model.
Unknown/dispatching records were not silently changed to sent or blindly retried.

Two restart preparations failed before stopping service because their session
inventory assumptions were wrong. Their plans and review records were retained;
neither had a consumed start attempt. The corrected, independently reviewed
maintenance stage checked four active routes and preserved all six session files.
An early sender fixture also stopped before sending due to a test-only non-null
role assumption; the corrected fixture matched production's optional-role
semantics while retaining strict App/user/chat routing. It used a new isolated
attempt directory and retained the failed attempt.

## Maintenance end check and review

The manager's post-restart real message queried the fictional banquet read-only.
Its actual `banquet` tool returned exit code 0, `status=found`, and stage signed;
the native turn completed in 23.0569 seconds. At 21:06 local time, the employee
independently queried the same fictional banquet in their personal Bot. The
`banquet` invocation returned an execution session; polling that same session
returned exit code 0, `status=found`, and stage signed. The Gateway completed the
turn in 20.9526 seconds and the observed Feishu reply matched. Only the protocol
read and banquet read ran; earlier pre-restart reads were not substituted.

Fresh Spec and Standards reviewers independently checked exact source versions
and raw receipts. They found no new actionable runtime blocker and independently
verified the employee's final tool-result chain. Standards' archive requirement
was delivered by documentation PR143, merge
`9b76943e9a6015e2a251d2e65c3797536def54d3`, with exact merge CI38141170515 passing.
Both reviewers allow closeout of the two-account pilot at the stated validation
layers. Their reports are stored outside this documentation commit and are not
GitHub human approvals. The archive commits do not change the installed CRM.

## Evidence index and limits

The restricted local evidence bundle is `personal-assistants-evidence-20261011`.
This repository contains only the sanitized index, not raw conversations, app
credentials, private URLs, recipient IDs or production ledgers.

- `live-acceptance.md`, `abnormal-supplement.md`: prior real journeys and limits.
- `three-items-acceptance.md`: supplementary test methods and failures.
- `notification-restart-prepare-1791721206562969700.json` and
  `notification-restart-run-1791721271496616800.json`: new maintenance receipts.
- `trace-1791721452433269700.json`, `trace-1791721513043638700.json`,
  `restart-duplicate-result.json`: same valid notice across restart.
- `notification-sender-before-send-1791721950898691500.json`,
  `notification-sender-notice-lost-1791722254029722400.json`,
  `notification-sender-notice-ack-1791722291368900100.json`,
  `notification-sender-alerts-1791722327383846100.json`,
  `notification-sender-inspect-1791722364633670100.json`: isolated fault/real send.
- `trace-1791723031711313300.json`: actual manager post-restart tool result.
- `trace-1791724073556955600.json`: employee post-restart call, same-session
  poll, actual tool result and Gateway completion.
- `final-spec-clean.md`, `final-standards-clean.md`: independent closeout review.

The employee's earlier combined question obtained banquet facts but did not
answer the handoff version; that remains a partial product result. Wrong-tenant
real events cannot be generated with the current same-tenant accounts; named
logic controls do not count as that live test. No multi-employee long-term load,
general agent-to-agent chat, private-context transfer, or arbitrary material
reliability is claimed. Rollback retains connection versions, authorization guards
and business history; it does not restore old authorizations.
