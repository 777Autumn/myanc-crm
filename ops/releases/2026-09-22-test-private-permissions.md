# Test-private file work without technical approval cards

Recorded 2026-09-22 (Asia/Shanghai). The earlier
[three natural-work journeys](2026-09-21-natural-file-work.md) remain evidence for
sales, execution and operations. This follow-up verifies the technical-permission
fix in the existing Bot, `test-private` and one authorized test account. It is
AI-operated Computer Use acceptance, not independent employee sign-off.

## Delivered source combination

| Repository / PR | Reviewed base → head | Squash merge / exact push CI |
| --- | --- | --- |
| [cc-connect-anc #22](https://github.com/77AutumN/cc-connect-anc/pull/22) | `1445820137b1689f8d7eefe6ed48b3e90bc6cc62` → `c6bec7123645629d43d68c8dfdb201e273cf746b` | `e9634d15377d614c87334498d39e6c1e38d68c1f` / [five required jobs passed](https://github.com/77AutumN/cc-connect-anc/actions/runs/35618391452) |
| [myanc-crm #47](https://github.com/77AutumN/myanc-crm/pull/47) | `4adae1715d1468c56931d6af8376505b3ed5f9f7` → `5e0efa2c4bdb317cbcc948e64da0084d2db4d126` | `f8c93b02b81d30e9f128d2ce684ff158754045f5` / [required test passed](https://github.com/77AutumN/myanc-crm/actions/runs/35618443373) |

Knowledge remains `88a60ba60a634fe3d6b0f68f91de326b19a39b30`, with the existing
[four required matrix jobs](https://github.com/77AutumN/myanc-team-brain/actions/runs/34704220632).
No knowledge source or publication record changed.
Independent AI Spec and Standards reviews are bound to the final exact pairs:
[gateway](https://github.com/77AutumN/cc-connect-anc/pull/22#issuecomment-5762813317),
[CRM](https://github.com/77AutumN/myanc-crm/pull/47#issuecomment-5762733718).
Earlier failed reviews and the test-cleanup lint failure remain in PR history;
only the corrected final head passed. These are not human GitHub approvals.

The adapter preserves `AskUserQuestion` in native `bypassPermissions` and
`dontAsk`, before technical permission decisions. Residual technical requests in
bypass mode are denied without showing shell approval cards. If writing that
denial fails, the session is cancelled even with a full event queue; foreground,
background and compression paths use the existing localized interruption message.
Entering or leaving native bypass restarts the Claude session instead of claiming
an unsupported live-mode change. Offline regressions cover these cases; actual
Linux CI, not the full Windows suite, is the platform-wide test evidence.

## Candidate and controlled maintenance

`ops/build_vps_candidate.py` exported the exact three merged sources above,
built locked Web assets and a Linux/amd64 gateway, and passed the existing paired
CRM daily-plan/customer/profile and knowledge-catalog Journey/CUJ tests. The
90-file manifest and every archive entry were checked. Toolchain: Go 1.25.6
(Windows/amd64 build host), Node 24.13.0, pnpm 10.28.1, Python 3.13.2.

- Archive: `candidate-f8c93b02-e9634d15-88a60ba6.tar.gz`.
- Archive SHA256: `0fefb98eda8e6c28971b539dec723d4e83363321d74bcc7cc036fcde72651670`.
- Installed gateway SHA256: `b0a2f4b824410d7e192d4579f56a25b6277d41e8767aebd5890bf016e3df0337`.
- Local archive/manifest: `D:/MYANC/file-loop-evidence/bypass-work-20260921/`.

Owner's full authorization covered this controlled rollout and real test. Four
targets changed: the candidate gateway binary, candidate test-account instructions,
the existing test-private mode, and removal of the managed native-bypass ban.
The protected configuration was transformed narrowly, not replaced with a template.
Only `test-private` is configured as `bypassPermissions`; five other entrypoints
and the managed default remain `auto`. Deny rules, hooks, enabled sandbox,
existing CRM approvals and file-host boundaries remain. Native process arguments
confirmed bypass mode with the permission-question channel still connected.
Gateway/model use their existing different ordinary accounts with zero effective
capabilities. No account, group, ACL, authentication, network, dependency or
service-definition change was made. Existing conversation-only routing prevents
employee `/mode` changes. No second receiver was started.

Two maintenance preflights failed on a transient existing read-only
`host-plan-events` polling child. Both stopped before the actual service stop;
the second had already recorded stop intent. The failures and original intent
were retained. The reviewed recovery waited at most five seconds for a genuinely
empty child set, rechecked activity and original process identity, and consumed
that same unexecuted intent once. No child whitelist, removed receipt or alternate
receipt root was used. Original script SHA256:
`2f0ea4355e142d5e43d0d63f984d01b199a6ac8b7d636ee69db6726dde86606b`;
recovery SHA256:
`1f44ee5d577ad4b6fcc80c05ef372186c9379586de3d68f63d7e52bac38eecd2`.
Both had independent AI Spec/Standards inspection; scripts/receipts remain private.

One actual stop/start used the existing `maintenance_start.start_once` helper.
Readiness was initially false, then true from 10.1 through 141.0 seconds: a
130-second stable interval, six engines sharing one receiver, zero automatic
restarts. Backups and installed hashes are retained privately. Final read-only
comparison of six business/knowledge stores found unchanged business/publication
tables and no added knowledge reads; policy/control files matched the frozen or
installed state. The same gateway process remained healthy through acceptance.

## Actual employee-facing result

Audit window: 2026-09-21 15:49:50–16:04:30 UTC. Using the existing Feishu client,
the operator requested a fictional wedding budget Word/Excel pair with ambiguous
18/20-table input, selected **18 tables** in Claude's actual business question,
then sent an unquoted natural request to change to **22 tables**, retaining the
100,000 budget and old files. No employee command, Skill name or work ID was used.

| Check | Observed result |
| --- | --- |
| Business clarification | One `AskUserQuestion`; 18-table selection reached Claude and the first files. |
| Technical approvals | Zero technical permission requests/cards; no manual tool approval. Journal has the same one business question at adapter and engine layers. |
| Source grounding | Actual Read of installed fictional `DEMO-VENUE-001` v1.0; output identifies it. `team-banquet`, `team-brain` and `team-files` were selected internally. No new live company-knowledge read is claimed. |
| First Word / Excel | Both returned to the original conversation and opened: totals 73,640 / 84,440, remaining budget 26,360 / 15,560. |
| Unquoted revision | Both new files returned in the same work: totals 89,560 / 102,760; B explicitly exceeds budget by 2,760. Word's warning and Excel preview agree. |
| Preservation / receipts | Four UI-downloaded file hashes match accepted work-bound receipts and host snapshots. Earlier versions/original outputs and other works remain unchanged; no pending input. |
| Tool result coverage | 26 calls with paired results: 1 question, 3 Skills, 2 Reads, 18 Bash, 2 Writes; no reported tool errors or missing/malformed trace events. |

All four files passed ZIP/XML and targeted source/text/value/formula checks;
their hashes and check scope are in the
[sanitized artifact manifest](2026-09-22-test-private-artifacts.json).
Raw conversations, identifiers, source bodies, maintenance state and backups stay
outside GitHub. No business write, external quotation or commitment occurred.

Each workbook contains ten uncached formulas. Known expressions/inputs were
checked and Feishu preview recalculated correctly; cache-only readers and desktop
Excel were not tested. The first files retained a redundant 18/20-table
confirmation note after the 18-table answer; revision replaces it with the
requested 22-table basis. This is a draft-quality limitation, not a wrong-work
delivery. Real templates including PAGE/TOC fields, multi-employee rollout and
all employee work types remain unverified. No field support was changed.

Rollback would restore the backed-up four code/config targets in another
controlled maintenance window, verify hashes and use the existing startup gate;
never rewind business ledgers. No rollback occurred. This documentation-only
follow-up does not rebuild or reinstall the runtime candidate.
