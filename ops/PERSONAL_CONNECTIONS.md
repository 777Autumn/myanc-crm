# Personal Feishu connections (Mac pilot)

The gateway binds the authenticated Feishu sender to the existing protected
`allowed_actors` mapping. CRM reads use that person's official CLI login. The
model still calls `customer` / `customers`; it cannot choose a profile, application,
Base, token or execution identity. Missing authorization never falls back to bot.

## Member experience

In a private conversation with the same bot:

1. Send **连接我的飞书**. Open the returned link or scan its QR code with your own
   account. Send **连接状态** after authorization.
2. Continue assigning ordinary work. CLI refresh runs in the background.
3. Send **重新连接** if authorization has been revoked or needs renewal. An incorrectly
   scanned account is rejected; reconnect with the intended account.
4. Send **断开连接** to stop ANC using the connection. This invalidates old private
   work; it does not revoke the application's authorization on Feishu's servers.

Group messages direct enrollment to private chat. Group CRM calls use only the
fixed resource explicitly approved for that group; the boss's presence or wording
does not select the boss's personal identity. Network failures are retried and do
not automatically demand a new scan. Feishu can still require reauthorization;
this is not a promise of permanent authorization.

## Protected configuration

Omitting `personal_connections` preserves the previous behavior. Enable only with
the matching gateway build, native file-work isolation, and complete trusted routes.
Add `connection_profile` to each permitted actor, for example `anc-user-owner` or
`anc-user-test`. Profiles must be unique. Each actor's `feishu_user_id` remains the
target CRM application's verified open ID, not a display name or the bot's open ID.

Example block to merge into the protected CRM configuration:

```json
{
  "personal_connections": {
    "app_id": "fixture-crm-app",
    "tenant_key": "fixture-tenant",
    "source_app_id": "fixture-bot-app",
    "source_tenant_key": "fixture-tenant",
    "cli_path": "/usr/local/libexec/lark-cli-1.0.90",
    "cli_home_root": "/private/var/lib/cc-connect/personal-cli",
    "database_path": "/private/var/lib/cc-connect/personal-state/connections.sqlite3",
    "resource_mode": "shared",
    "routes": [
      {"platform":"feishu","user_id":"fixture-sender","chat_id":"fixture-private","project":"fixture-private-project","audience":"private"},
      {"platform":"feishu","user_id":"fixture-sender","chat_id":"fixture-group","project":"fixture-group-project","audience":"shared"}
    ]
  }
}
```

Enumerate each sender/group/project combination. `shared` is an operator assertion
that the whole fixed CRM resource is approved for **every configured shared route**.
Use `restricted` for a private fixture: only personal customer reads are available;
CRM approval previews, receipts, assignee lookups and reminder-plan adapters are
blocked before backend construction. Clean shared projects and ordinary reminders
remain available. Do not point shared mode at a mixed-permission CRM.

Provision one service-owned 0700 directory at `cli_home_root/<connection_profile>`.
Run official CLI 1.0.90 `config init` in that exact HOME with that exact profile and
the intended CRM app, passing the application secret through stdin. Do not copy
Windows credential-store references or user tokens. On this pinned Darwin CLI,
credential ciphertext and refresh locks are native files under each HOME. The OS
keychain may hold a common encryption master key; separate HOME is file namespace
isolation, not separate OS users. This does not claim equivalent Windows isolation.

The host clears CLI environment overrides and always supplies HOME and profile.
It validates the user branch of auth status, app, tenant and open ID. A first-use
native login provisioned by the operator can be adopted only after this verification.
Enrollment requests `base:field:read base:record:read offline_access`, matching
the pinned CLI's field and record read commands. Legacy `bitable:app:readonly`
alone does not satisfy those commands. Missing scopes reject adoption and require
reconnection; losing a required scope invalidates existing private work. Existing
application grants can be cumulative, so inspect actual scopes rather than claiming
that a narrow request reduced a previously broader grant. Native resource denial
91403 returns `personal_read_permission_denied` without exposing upstream error text
or using another identity; the same connection remains usable for permitted data.
Wrong-account recovery invokes native logout for the failed flow's isolated store:
CLI attempts remote token revocation before clearing that store. Verify the other
account's real API and refresh still work; file isolation alone does not prove the
platform's revocation scope. External profile replacement fails closed for operator investigation.

The protected SQLite registry stores mappings, connection state, generation,
expiry metadata, short-lived device-flow code and work/session bindings. Access
and refresh tokens remain exclusively in the CLI's store. Protect registry, WAL/
journal files and CLI directories from the model UID and actual model sandbox.

## Data scope and lifecycle

Restricted customer reads mark the existing work private before any data reaches
the model. Non-`team` knowledge reads receive the same private work restriction;
the knowledge host must also enable its complete `subject_access` policy. Non-team
knowledge is unavailable from shared conversations. The existing `team` subject
continues to represent universally shared knowledge.

The mark persists through restart, fresh action tokens and later configuration
changes. Private files may be delivered to the original private chat. Publishing
that work into a shared project, shared knowledge, reminders or CRM writes is
blocked, including delayed confirmation callbacks. Ordinary unmarked work keeps
the existing project handoff and approval paths. To start an unrelated shared task,
start a new work using the existing **换个事** command.

Every personal customer read binds its host work to the connection generation,
including reads of shared CRM. The binding does not by itself make shared data
private; restricted CRM and non-team knowledge only increase the work's privacy.
Old four-column bindings without a scope record remain private. Shared owner-ref
queries may use the existing app for principal-scoped personnel verification;
customer data still uses the person's CLI, never an application fallback.

Disconnect/rebind increments the generation. Old dependent work cannot resume or
publish; dependent active sessions are cancelled. Expired host sessions retain
their native IDs as tombstones, so deletion, switching or a new token cannot
reattach the old context. New work and previously authorized shared publications
keep their existing behavior. Lock contention is temporary: block the current
operation but preserve the connection generation and queued work.
Per-person maintenance is due at
access expiry minus four minutes, uses `auth status --verify --json`, and rereads
metadata because CLI 1.0.90 can report the pre-refresh expiry. Transient failures
back off. Current generations, including successful reconnects, are repeatably
delivered, so killing a host process cannot lose cancellation of stale work in other
private sessions. A completed device-code exchange is reconciled from the native
login and a persisted verifying state instead of consuming the same code again.

## Release and verification

Follow [RELEASE.md](RELEASE.md) and [MAINTENANCE_START.md](MAINTENANCE_START.md).
Keep business ledgers, connection registry and rotated native credentials during
code rollback. Preserve the fixed connection/session guards and expiration marks;
otherwise stop the affected private entrances before restoring code. Do not remove
the connection policy or restore an old registry/session/token snapshot. Registry
versions are local implementation state, not
customer organizational policy.

Required evidence remains separate: permission logic, real model, real Feishu and
Mac refresh/restart/sandbox. Use fictitious private/shared two-table CRM fixtures.
Test wrong scan and correction without changing the other user's native store;
search/all/exact ID and role-claim bypasses; group/summary/file/handoff containment;
per-account refresh, revocation, offline retries and restart; and paired normal
CRM, knowledge, files and shared project journeys. Simulated annual time is not a
year of observed operation. Resource ACL results do not establish row/column ACLs.

## Historical work closeout

`personal_connection_migration.py` contains offline planning/registry primitives,
not an automatic startup migration. The reviewed maintenance caller must stop and
drain the gateway, verify protected route/session mappings and frozen input hashes,
back up state, apply the registry transaction, then atomically install the planned
session snapshots with original ownership/modes. Do not start after partial failure.
Retries require the original frozen plan: only matching existing tombstones are
idempotent; changed identities/generations are conflicts.

The approved two-account closeout preserves existing bindings, permanently expires
unbound work whose authority cannot be established, and marks context-bearing
private sessions without a file work as expired. Positively attributed orphan
native IDs become expired Session placeholders, never new file work. Keep the
old current/past native IDs and business history. Remove only expired active-session
pointers so the next new request starts clean; explicit old-message recovery is
rejected. No files, approvals, publications, business ledgers or CLI tokens are deleted.

Knowledge supports two to five members with exactly two protected entrances each.
Check the full gateway principal/session/project mapping and complete subject
policy for every entrant. Five-person synthetic tests do not establish five live
authorizations; actual acceptance uses the manager and test accounts. Each future
member needs their own mapping, first authorization and real normal/denied checks.
