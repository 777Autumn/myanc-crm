# One-shot reminders: deployed, live acceptance incomplete

Recorded 2026-09-10. Owner explicitly authorized the reminder maintenance window,
backup, enabling and fictional Owner/test acceptance. The service was started
with the new candidate at 07:04 UTC (15:04 Beijing). This record is not an
authorization for further deployments and does not claim human acceptance.

## Source delivery and installed version

| Repository | Merged source | PR | Exact push CI |
|---|---|---|---|
| myanc-crm | `37a70b2f3b53c3d0083a8bf7c4757e0d2c312f8b` | [#12](https://github.com/77AutumN/myanc-crm/pull/12) | [34444655225](https://github.com/77AutumN/myanc-crm/actions/runs/34444655225) |
| cc-connect-anc | `fe9e12a4cea9f818a380ea6a839d39a030cb48ca` | [#7](https://github.com/77AutumN/cc-connect-anc/pull/7) | [34444656596](https://github.com/77AutumN/cc-connect-anc/actions/runs/34444656596) |

Both final heads had independent Spec/Standards source review and passed full
CI. Subagent review is not a GitHub human approval. The dual-SHA release gate was
repeated successfully before this maintenance. The supported builder exported
these exact sources, rebuilt locked Web assets and ran explicit paired tests.
The binary is Linux/amd64, CGO disabled, `-trimpath -buildvcs=false`; the manifest
records Go 1.25.6, Node 24.13.0, pnpm 10.28.1 and Python 3.13.2.

| Artifact | SHA256 |
|---|---|
| Formal candidate archive | `564c84fd501b017e21b507ecce1f8452beb7de93d32b3b200f94a289426f9425` |
| Installed gateway | `a18c764ec34fe2ea48e07fb1cd23aa534784bfdec4c8392788ea5e26728a0128` |
| Installed controlled client | `23e78e0fcd3fdb06f2c8236e5846634ea042c3e4e309d731fb028f490495f418` |
| Six installed policies | `6062df4fbd64f4c6c9c77ee2175506bf0b38016232ddd5c22ea391b8de9802e2` |
| Installed command guard | `d6bde6c9b9d94e50367f3085be4e23eba692447ed055cf131d8671981655bcbb` |
| Merged managed settings | `3e4f22b48e5971c666de2c7aaf60b781cbe4af99a730562c280b7822b9a6211a` |
| Reminder enable override | `6508a9dc2fd6de69146e722ab70ff204cb5965f3e2f908c7820dea3e463436f4` |

The old live gateway hash was
`65f1cdd2407565235b069537178e354730b491084115101244ce0b319af510d9`.
It matched the knowledge deployment's own manifest and subsequent patch
receipts. The older generic DEPLOYED_COMMIT/SHA256 files were stale and were not
used as proof of the running version; this record plus the maintenance receipts
supersedes them for this release. No historical binary was relabeled as a clean
build from the new merges.

## Controlled cutover

Preflight reconciled all 55 knowledge release/preservation hashes. The previous
receiver had 15 received and 15 completed messages, a complete startup journal,
and over 120 seconds of quiet. CRM had no write fences or unresolved writes;
knowledge had no publication locks. An old Sandbox staged preview and a
knowledge needs-revision proposal were preserved, not cleared.

The one-time operator script was independently reviewed on both axes after
fixing policy-hash slicing, service configuration backup coverage, and strict
control-file owner/path checks. Its reviewed SHA256 is
`11a0809e7e2017a9a0be78fcaf60eb660c3b113328760759a2164be5c6690bb2`.
Four local transformation tests and a read-only live check passed before stop.
The script is historical evidence only, not a reusable installation command.

Backups under `/root/reminder-maintenance-20260910/backup` retain changed files'
ownership/modes, service configuration and four consistent business DB snapshots.
Private `prepared.json`, `installed.json` and `started.json` bind preflight,
installed hashes and service transition. None of these private snapshots,
configurations or raw traces is included in this repository.

Ten existing files changed: gateway, controlled client, command guard, managed
settings and six policies. Only the reminder protocol section was inserted;
knowledge instructions, current proxy behavior, skills and runtime were retained.
The new service override enables an explicitly initialized independent reminder
database. No routes, credentials, sudoers, CRM code, CRM selection, knowledge
configuration or business data were changed. All 46 retained file hashes and
all four business DB logical snapshots matched after cutover.

## Verification and remaining acceptance

- Active service, no automatic restart, six ready engines, one receiver process,
  one successful Feishu WebSocket connection with five shared reusers, and one
  loopback tool listener; no startup error categories.
- Reminder directory 0700, database 0600, owned by the host account; integrity
  check passed. The host first confirmed the file existed; each of the six model
  Unix users then received EACCES opening it.
- Owner/test native Claude auto-mode sandbox each ran one exact Bash command to
  create, read and clean a fictional workspace canary. No host token was supplied.
- An earlier combined probe was refused by the model because it obscured a
  protected path; it made zero tool calls. Its failed probe result is retained,
  not counted as a successful native filesystem-denial test. The EACCES evidence
  above comes from separate OS-user checks.
- Before deployment, 48/48 no-tools model decision cases passed on the existing
  VPS Claude and were independently reviewed. Those are model behavior evidence,
  not proof of the new live message/tool/delivery chain.
- At the initial deployment checkpoint the reminder database contained no
  reminders or send batches and Feishu required human login. The Owner later
  completed login. The following live evidence supersedes that initial blocker.

## Live acceptance checkpoint — 2026-09-10

All times below are Beijing time. Only fictional acceptance messages were used;
the screenshot's real customer-contact reminder was not created. Owner desktop
messages had action-time user confirmation. Protected state was read back without
exporting identity values, private chat IDs, credentials or delivery receipts.

| Case | Observed result | Evidence boundary |
|---|---|---|
| Owner group create, private delivery | `OWNER-0910`, due 15:34:48; sent with one attempt and saved item/batch receipts; visible in Owner private chat | Actor/source/destination matched pinned configuration; not sent to group |
| Owner private create and list | `OWNER-MANAGE-0910`, created 15:42, due 15:52:29, pending v1 | List showed the new item and distinguished the earlier sent group-created item |
| Owner update time/content | Same item updated at 15:46 to 16:30, revised fictional text, pending v2 | Protected state and visible updated list agreed |
| Owner cancel and list | At 15:54, same item cancelled v3, no batch or in-flight receipt; pending list empty | Cancellation preserved the historical item; it did not delete data |
| test group create, private delivery | `TEST-0910`, due 16:01:29; sent with one attempt and saved item/batch receipts | User phone screenshots matched the stored reminder; destination was test private chat, not Owner, partner or group |

A separate earlier Owner reminder also used the `TEST-0910` text and was sent to
Owner at 15:58:35. These are distinct actors and items, not duplicate delivery of
test's reminder. Identical marker text alone is not an identity or deduplication
key. Client visibility establishes delivery to the client, not human reading.

After these cases all 56 tracked runtime hashes, four CRM/knowledge DB logical
snapshots and the single receiver/listener checks remained unchanged. Reminder
integrity and six model-user EACCES checks passed. Before the next recovery test,
state held three sent reminders and one cancelled reminder, with no uncertain
or outstanding send batches.

### Controlled overdue recovery

The Owner separately confirmed one private five-minute fictional reminder plus
approximately four minutes of shared-gateway maintenance. `OWNER-RESTART-0910`
was created through the actual bot at 16:20, with due time 16:25:54. It was the
only outstanding reminder and the current turn had completed with at least
120 seconds of quiet before stopping.

Five fresh, integrity-checked SQLite backups (reminders plus four business DBs)
were kept under the root-private
`/root/reminder-restart-acceptance-20260910/backup`. Private phase records bind
the item, backup hashes and service transitions; raw files are not in GitHub.
The one-off operator script's SHA256 was
`38c4461720d411616de8d234fdce68ca0764d4fe4e6f0035de9ab45420ee1e9a`.
It is historical evidence, not a reusable deployment or restart command.

At 16:24:02 the service was stopped, receiver and listener absent, reminder still
pending and all business snapshots unchanged. A one-shot transient systemd timer
was armed beforehand to start the same `cc-connect.service` at due+90 seconds.
The intended manual resume target was due+65 seconds; the actual service start
was 16:27:24, when the recovery timer also ran successfully. The operator's start
call converged on that same active unit and PID. Do not claim the earlier manual
target was achieved or attribute the service start exclusively to that call.
The timer completed and was unloaded; no recurring recovery job remains.

The saved first send attempt was 16:27:26, 92 seconds late, with a single attempt,
fixed UUID, sent item/batch and saved receipts. The same reminder ID and fictional
content appeared in Owner private chat with `延迟补发；原定时间` and the original
date/time. No model turn was received or run after startup to cause that send.
The recorded stop-to-start-confirmation interval was approximately 203 seconds.

Post-recovery checks passed: all five backup hashes, unchanged prior reminders
and batches (including cancelled v3), all 56 tracked runtime hashes and reminder
override, four unchanged business DB logical snapshots, six ready engines, one
receiver, five shared WebSocket reusers, one tool listener, no ERROR logs or
automatic restarts, intact reminder DB and six model-user EACCES results.
No code/configuration, credential, permission or business-data change occurred.
Backups preserve evidence only; no database restore or reinitialization happened.

### Additional test management and privacy acceptance

Recorded on 2026-09-10 after the preceding recovery checkpoint. These cases use
only the user's fictional acceptance requests. No additional deployment, restart,
identity change or business-data operation was performed for these checks.

| Case | Observed result | Evidence boundary |
|---|---|---|
| test private management, 16:47–16:50 | One `TEST-MANAGE-0910` item: create v1 for September 11 09:00; list; update v2 to 10:00 with revised text; list; cancel v3 without batch/receipt | Bounded actual test-private turn has exactly five successful tool calls and two matching list results; persisted results agree. No third list or new phone-rendering claim |
| test cross-user refusal, 16:53 | Request to cancel Owner's fictional management item was refused; only test's two items were listed, Owner's ID excluded | Actual turn made only reminder-list, not reminder-cancel. This proves live model refusal and scoped listing, not a live host not_found rejection |
| Group full list to private, 17:00 | Group returned private_list_queued without reminder bodies; complete two-item list appeared in test private chat | User phone screenshots, actual group tool result and persisted one-attempt sent list batch with receipt agree; fixed recipient is test private, not the group |

For the group full-list case, the actual group tool result contained no reminders
array and no private `TEST-MANAGE-0910` content or identifier. The group assistant
reply also excluded that private canary. The group-created `TEST-0910` item was
already present in group history; it is not used as a private-content canary.
This evidence concerns the inspected turn, not every historical model context.

The list batch contains exactly the two known test items: sent v1 and cancelled
v3. It has no associated reminder items, so sending the list did not schedule a
reminder again. The cancelled management item still has no send batch or receipt.
Earlier items and batches remain unchanged, allowing the separately documented
restart delivery and test management transitions. At 17:07, all 56 tracked runtime
hashes and four business DB logical snapshots matched; the same healthy service
had six engines, one receiver/listener, zero restarts/errors, reminder integrity
ok and six model-user EACCES results.

Operator-local redacted evidence: `test-manage-live-20260910.md`,
`test-cross-user-live-20260910.md`, `test-private-list-live-20260910.md`, with
read-only reconciliation helpers. Raw screenshots, transcripts, private identity
values, delivery receipts and databases are not uploaded to this repository.

### Focused automated regression recheck

At 17:10 Beijing the unchanged gateway feature worktree was checked tree-identical
to the installed source `fe9e12a4cea9f818a380ea6a839d39a030cb48ca`.
Using Go 1.25.6 on Windows, ten selected tests passed without skips:
CUSTOMER1, KNOWLEDGE1, REMINDER1, both A3 image CUJs, B1 new-session, C5 stop,
PARTNER1 restricted commands, single-image dispatch and fixed-group private-image
quote denial. Packages: `core` and `platform/feishu`, `-count=1`.
These use fixture model/platform boundaries; they do not query or write live
CRM/knowledge data, call live Feishu, or replace the remaining live checks.
The earlier full Linux CI and paired candidate tests remain separate evidence.

**Incomplete:** post-upgrade live CRM/knowledge
interaction regression, image, `/new` and `/stop`. Earlier session-transition text
in a screenshot does not establish a fresh command regression test. Existing
CI/CUJ and historical tests do not replace these checks. Wang remains authorized;
his live reminder acceptance is explicitly unexecuted, as requested by the user.

UX observation: creation replies show date/weekday/time/content/ID but do not
consistently say delivery is private, and some include a generic delivery caveat.
Successful private delivery does not erase that wording follow-up. This evidence
update changes no runtime code, permissions, credentials or business data.

## Recovery

First inspect current message/approval activity and reminder sends, then pause
scheduling through a safe service stop. Restore only recorded code/policies and
settings; move the reminder enable override out of the service directory. Keep
the reminder database, pending items, batches and receipts. Keep CRM/knowledge
ledgers and their current state. Reconcile unknown sends before re-enabling.
Never restore these DB snapshots over live business state to undo a deployment.
