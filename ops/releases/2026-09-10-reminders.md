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
- At this checkpoint the reminder database contains no reminders or send batches.
  The authorized desktop send was not performed: Feishu required human login.

**Incomplete:** Owner/test live group creation to own private delivery, list,
update, cancel and controlled restart/overdue catch-up; post-upgrade live CRM and
knowledge interaction regression, image, `/new` and `/stop`. Existing CI/CUJ and
historical live tests do not replace these checks. Wang remains authorized;
his live acceptance is explicitly unexecuted. User login or a phone-originated
fictional test message is the next step; no screenshot's real reminder was made.

## Recovery

First inspect current message/approval activity and reminder sends, then pause
scheduling through a safe service stop. Restore only recorded code/policies and
settings; move the reminder enable override out of the service directory. Keep
the reminder database, pending items, batches and receipts. Keep CRM/knowledge
ledgers and their current state. Reconcile unknown sends before re-enabling.
Never restore these DB snapshots over live business state to undo a deployment.
