# Scoped simulated wedding progress

Default off. This is a small extension to the existing authenticated `crm-tool`
channel and protected TEST SQLite, not a CRM table, knowledge publisher, message
listener or scheduler. Gateway and CRM must be built from the recorded paired
commits. Follow `ops/RELEASE.md`; draft PRs are not installable releases.

Protected CRM configuration, fictional values only:

```json
{
  "shared_cases": {
    "enabled": true,
    "ledger_path": "/var/lib/myanc-crm/test-existing.sqlite3",
    "namespace": "mock-banquet",
    "group_chat_id": "fictional-test-group",
    "members": [
      {"platform":"feishu","user_id":"fictional-sales","chat_id":"fictional-test-group","project":"sales-group"},
      {"platform":"feishu","user_id":"fictional-operations","chat_id":"fictional-test-group","project":"operations-group"},
      {"platform":"feishu","user_id":"fictional-sales","chat_id":"fictional-private","project":"maintenance-private"}
    ]
  }
}
```

Substitute only the already verified test identities/entries. Each actor must
already exist in `allowed_actors`. `ledger_path` must differ from the formal CRM
ledger, already exist, and use the existing service-owned 0700 directory / 0600
file protection. The model never receives its path or direct database access.

In the normal approved maintenance window, as the existing host service UID,
from the installed CRM directory run `python -m myanc_crm.shared_cases --initialize`.
This reads the same protected configuration as the host helper and only creates
the three `shared_case_*` tables. It does not create directories or an absent DB.
Record the exact source combination and scoped before/after configuration hashes
in protected deployment evidence; do not commit the actual configuration or data.

For the three selected gateway entries set `file_work.shared_cases = true` only
with `file_work.enabled = true`, `runtime = "native"`. Group entries also retain
their existing `group_references = true`. Keep the unique receiver, existing
accounts, cwd, runtime permissions and network/identity configuration unchanged.
Update the installed CRM helper package, fixed `crm-tool` client and the selected
`team-banquet` Skill/reference through the normal candidate manifest. Wiki and
knowledge binaries remain pinned; no Python or system dependency is added.

Host protocol: agent commands are only `case-list`, `case-read`, `case-update`.
The gateway injects `case_context` from an original authenticated message and
work binding. One work retains one case association. A queued supplement keeps
its work and sharing grant. A `case-read` refreshes the read revision, never
grants private sharing. Model-selected sources are limited to the original
saved grants during explicit recovery.

Before file delivery, internal `case-artifact` prepare fixes the case revision
for that exact delivery request; finish records only its accepted receipt.
Neither `case-artifact` nor `host-case-import` is a public tool. Older deliveries
without a prepared basis stay unshared. A failed registration can be reconciled
against the same request/receipt; do not send under a new filename or request key.
Unknown sends remain unknown. Read returns at most 20 recent artifact entries and
imports at most four through the existing snapshot activation path; `remaining`
states the limit. A stale file remains historical even if it was delivered later.

Enablement evidence must include initialization, config/client/Skill versions,
one-service maintenance check and the two-account Feishu journey. Source CI does
not prove these. Disable shared cases through the same gate, preserving all mock
tables, versions and file snapshots. Restore previous runtime files only if they
can read the recorded file-ledger version: project-group to private imports mark
version 3 and older gateways refuse that whole ledger. Keep a compatible gateway
with the new entry points off; if a binary replacement is necessary, pause file
processing until a compatible build is available. Never downgrade or restore old
business snapshots to make a binary start. See `project-context.md` for this opt-in.
