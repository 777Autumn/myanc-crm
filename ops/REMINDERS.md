# Reminder delivery runbook

Status: implementation under validation; **not deployed or enabled**.
Follow [the shared release contract](RELEASE.md). Current code and templates do
not establish live acceptance. Default: no `MYANC_REMINDER_DB`, no scheduler.

## Candidate and maintenance

Use the dual-SHA candidate builder, with explicit `MYANC_SPIKE_CRM_ROOT` paired
tests. Keep exact source SHAs, independent review, PR/main CI and artifact hashes.
Initialization and installation below require a separate approved maintenance.

Before installation, reconcile live hashes and outstanding writes, back up the
service configuration and data, and freeze the knowledge/CRM files to preserve.
The deployed knowledge client/protocol may be newer than old CRM templates:
**do not replace whole runtime workspaces or managed settings from a template**.
Apply only the reviewed reminder client/policy additions, preserving knowledge
commands and current proxy behavior. `CLAUDE.vps.md`'s reminder section is the
single authoritative model contract; copy that section without erasing existing
knowledge instructions.

Create `/var/lib/myanc-reminders` owned by `ccconnect:ccconnect`, mode 0700,
then run the new binary's `reminders-init /var/lib/myanc-reminders/reminders.sqlite`
as **ccconnect**, once, before enabling the service override. Existing files are
refused. Never initialize during startup/recovery or replace a missing database
with an empty one. The service needs the existing six verified routes and one
private sender per person; no credentials, identity IDs or database enter git.
Verify with the host that the file exists, is mode 0600 and is unreadable by
all six model Unix users; permission-denied is evidence, missing-file is not.

Merge the managed deny rules and command-guard literals for the reminder state
directory. No new sudo permission or model-readable socket is needed. Activate
only the reminder override; do not enable knowledge implicitly. Count exactly
one receiving connection and one tool listener after restart.

## Acceptance and incidents

Owner/test: group create → private receipt; list/update/cancel; restart overdue
catch-up. Test only fictitious content. Record partner's unexecuted acceptance
as unexecuted, not inferred. Recheck CRM cards, knowledge tools/cards, image,
`/new`, `/stop`, and six isolated environments. No actual reminder has been
created by this implementation task.

The host logs only error categories: `storage_unavailable`,
`identity_route_changed`, `permission_or_route`, `acceptance_unconfirmed`.
Inspect protected state through the existing admin channel; do not paste full
reminder bodies/private IDs into logs or issue trackers. A paused record needs
an operator to check identity/permissions and reconcile delivery receipts; there
is intentionally no automatic reroute or blind unpause command.

Feishu acceptance is not proof of reading. Unknown acceptance retries with the
same frozen UUID/body within one hour; later attempts may duplicate and say so.
Cancelled in-flight reminders may already have reached Feishu; no recall promise.

## Rollback

Stop reminder scheduling before changing versions. Preserve the independent
database, all pending records, frozen batches and receipts. Remove only the
reminder enable override and restore reviewed code/configuration. Never restore
an empty reminder database or overwrite CRM/knowledge business ledgers. Reconcile
unknown sends before a later restart so delayed retries remain truthful.
