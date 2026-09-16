# CRM daily follow-up v1

Source implementation and regression tests are present. Exact-head reviews, CI,
model evidence and merge status are tracked in [CRM PR #34](https://github.com/77AutumN/myanc-crm/pull/34)
and [gateway PR #15](https://github.com/77AutumN/cc-connect-anc/pull/15).
Online enablement and host checks completed in the authorized September 16 window;
new shared-plan live approval/delivery acceptance remains incomplete. See the
[actual release record](releases/2026-09-16-crm-skills-live.md) and follow [RELEASE.md](RELEASE.md).
The model contract lives in [team-crm](skills/team-crm/SKILL.md).

## Scope and invariants

Customer discovery uses bounded native filters, stable sorting and live pages;
history pages remain separate from current customer fields. Number lookup is exact.
No Base table, business field, service, listener, identity or permission is added.
The CLI does not document sorting by its system record ID. History therefore
fetches only the resolved customer's filtered history, checks complete retrieval,
then sorts by communication time and real record ID before returning ten rows.
This costs O(that customer's history); timeout/failure reports unavailable rather
than returning a partial list as complete. It is not a frozen cross-page snapshot.

Customer next action/date may change independently through the existing approval.
One shared plan is keyed by host-configured Base/customer table and real record ID,
not by chat or model input. Only a verified CRM receipt advances its revision and
outbox in the same CRM-ledger transaction. Historical backfills do not schedule.
The approving sender's frozen private route receives the notification. The reminder
store consumes revisions atomically and preserves cancellation tombstones, so replay,
out-of-order events and A→B→A cannot restore an obsolete notification. Personal
reminders and the knowledge publication journal remain independent.

Before sending or retrying, recheck revision, actual CRM plan, authorization and
the frozen route. Unavailable/mismatched evidence pauses only the linked item and
uses existing operations alerts; it must not strand ordinary reminders. API
acceptance is not user reading, and in-flight messages cannot be guaranteed recalled.
The CRM receipt may report pending synchronization, never pretend that is delivery.

## Authorized maintenance only

Both controls default off: protected CRM config `crm_plan_reminders_enabled=false`
and gateway `MYANC_CRM_PLAN_REMINDERS` unset. Enable both only in a separately
authorized window after exact-SHA review/CI and paired candidate verification.

1. Reconcile installed CRM/gateway/knowledge hashes and pending releases. Record
   preserved knowledge changes separately; do not attribute them to this CRM work.
2. Back up existing protected configuration and both stores. Use additive schema
   upgrades against copies first, then existing stores as the service owner; never
   initialize over a missing/corrupt business store or copy back an old ledger.
3. Confirm six model users cannot read/write the stores, current customer schema
   supports the query contract, and existing Feishu permissions suffice. Do not
   add production IDs/secrets to git. The model receives no host outbox commands.
4. Enable the reviewed pair; retain exactly one receiving connection and one tool
   listener. Old customer dates are listable but are not bulk scheduled or replayed.
5. Use fictional approved data for list/history paging, independent planning,
   replacement by a second actor, no-reminder/restart and delivery reconciliation.
   Historical waived trials are not reopened. Record actual tests separately from
   automated evidence; code merge does not establish live acceptance.

Rollback disables linked consumption and sending first, retaining plan revisions,
outbox, notifications, tombstones and receipts. Do not restore old business DBs.
If an older binary cannot safely read the additive schema, keep compatible reviewed
code and disable the new entry points instead. Ordinary reminders, CRM approvals
and knowledge remain within their existing boundaries.
The first consumed CRM plan upgrades reminder state from schema 1 to 2. The new
binary reads both; old binaries deliberately reject schema 2 instead of treating
linked reminders as personal ones or discarding links. Never downgrade that state
or overwrite it with a pre-upgrade backup to make an old binary start.

## Required evidence

Run Python and Go suites plus real-Engine paired CUJs with `MYANC_SPIKE_CRM_ROOT`.
Cover paging/sort changes, time defaults/expiry, no fabricated history, owner and
chat isolation, disabled notification persistence, outbox interruption, readback
failure, changed table data/routes/authorization, mixed batches and sending races.
Use a fixed candidate for a small fictional real-model multi-turn positive/negative
sample; report unavailable real-model evidence rather than substituting mocks.
Independent spec/standards review and exact head/main CI precede candidate build.
