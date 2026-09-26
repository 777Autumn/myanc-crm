# myanc-crm

One small workflow inside a general Feishu Claude assistant:

1. read customer facts/history and clarify missing details;
2. stage a factual preview through a controlled host tool;
3. bind the real sender/session and emitted card to that preview;
4. let the host execute the original approved proposal once;
5. read back, show the actual result, and continue discussing it with Claude.

Current delivery, acceptance and remaining limitations are indexed in
[ops/FOLLOWUPS.md](ops/FOLLOWUPS.md). The latest
[two-account simulated work record](ops/releases/2026-09-26-natural-work-live.md)
separates completed journeys and feedback repairs from failed autonomous review.
[The original customer-trial gate](docs/real-crm-trial.md) preserves the earlier
development-only checkpoint; its deployment pause is not the current global status.
New CRM creation/selection and deployment still require the authorization and
checks in [ops/RELEASE.md](ops/RELEASE.md).
The current Agent contract is in [CLAUDE.md](CLAUDE.md). The older request-file /
PermissionRequest route remains legacy code, not the selected tools workflow.
This package does not replace other Feishu skills, implement general Base CRUD,
or add a Python service, MCP server, SDK, second model, or workflow framework.

## Controlled model tools

The thin `ops/crm_tool.py` client accepts one command and one stdin JSON object:

| Command | Fields | Result |
|---|---|---|
| `customer` | `customer_query` | Current facts and bounded recent history; ambiguous matches require selection |
| `stage` | `customer_query`, `content`, `occurred_at`; optional `channel`, `next_action`, `next_followup_at` | Canonical preview plus host-owned approval card; no Feishu write |
| `result` | Returned opaque `change_id` | Pending/terminal state and recorded receipt, without restaging |
| `assignee` | Exact phone/user email or previously verified name in `query` | Verified name and opaque `owner_ref`, no approval authority |
| `stage-customer-create` | `name`, at least one contact detail, `stage`, `owner_ref`; optional `allow_same_name`, `followup` | Customer-only preview; optional follow-up needs a second independent approval |
| `stage-customer-update` | `customer_query`, only changed fields in `changes`; optional `allow_same_name`, `followup` | Profile-only preview; no direct customer-number/history changes |

Communication time requires an explicit timezone. Ask instead of guessing it.
Customer numbers take precedence over normalized exact names. Never choose the
first of several matches or create a missing customer from a query. Explicit
customer creation uses its own command and approval. An unavailable history
read is not an empty history. Omitted next-action fields leave those customer
fields unchanged.

The host resolves the client bearer to a live transport-derived Principal and
calls privileged `crm-followup host-tool` with `command`, `request`, and that
Principal. The model cannot supply identity, profile, Base/table/record IDs,
endpoint overrides or approval flags. Public `crm-followup stage/apply` remain
blocked; the thin client's stage is a different, host-authenticated entry point.

The client uses the native sandbox proxy to reach one fixed loopback endpoint,
`http://127.0.0.1:18743/tool`. It clears localhost proxy bypass only in its own
short-lived process, rejects remote proxies and redirects, and never falls back
to a direct connection or retries. The fixed Claude 2.1.259 transport probe passed
all 16 checks, including rejection of other ports, Unix connects and outside
workspace writes. This is isolated acceptance, not a production switch.
The bearer is a session binding, not a Feishu credential or write approval.
There is one client/listener transport, not a Unix/HTTP runtime selection. No
`allowAllUnixSockets` or unsandboxed-command exception is required by this route.

## Approval and result contract

The gateway sends a non-actionable placeholder, binds the real card message ID
with `host-bind-card`, then activates its approve/modify/cancel buttons. A publish,
bind or activation failure does not expose approval buttons. Canonical facts
returned to Claude and rendered in the card come from the same staged result.

The real callback sender/chat and bound message ID are checked by `host-claim`.
Only the approved CAS produces a continuation for `host-execute`. Card routing
fields do not supply identity. No callback wakes Claude, restages the proposal,
or converts chat text into approval. Modification invalidates the old card and
waits for revised input; cancellation makes no CRM write. Claude remains in the
same session and uses result/customer when the user asks what happened.

For combined customer+follow-up requests, the host freezes both drafts, executes
only the first approved customer operation, then offers one separate follow-up
card against the verified record. A child cancellation or delivery failure does
not undo the customer operation. Linked results preserve both states. No newer
write intent may be superseded by the automatic child. No callback wakes Claude.

States: `pending → executing → verified|partial|verification_unknown|failed`,
or `cancelled|superseded|expired`. A new stage supersedes older pending plans for
the same trusted sender/chat/session/project, including after token rotation.
Read-only customer/result calls do not supersede anything. Repeated decisions
return the existing state/receipt rather than repeating the write.

Apply re-reads schema and preview fields before writing. A changed snapshot
requires a new preview and approval. It appends one follow-up, reads it back, then
updates and reads back only the customer's latest-contact summary. Older events
can enter history without moving that summary backwards. Verification polling
is read-only and bounded to 30 seconds per effect. The execution lease is fifteen
minutes, longer than the bounded worker call budget.

A successful first effect is retained if the second fails: report partial, not
all-failed or verified. Unknown outcomes stop for human inspection. Existing
explicit repair helpers can reconcile by operation ID and propose only an
unfinished summary update; they are administrative compatibility code, not
automatic recovery or a model-visible API. Never restore an old ledger to undo
already verified Feishu writes.

## Sandbox bootstrap — separately authorized administration only

`ops/bootstrap_base.py` creates and retains `ANC CRM Sandbox`, the two tables
`客户` / `跟进记录`, and three fictional customers (including duplicate names).
It requires absolute pinned CLI/wrapper paths and an enterprise profile; it
verifies bot/user belong to the same application. User identity searches Drive
for an existing Base; all creates/writes use bot. It never starts a login.

Supply the owner sender ID and a random host secret through the protected
environment, not command arguments. First inspect the offline dry run:

```powershell
python ops/bootstrap_base.py --lark-cli 'C:\absolute\lark-cli.exe' --profile '<enterprise-profile>' --wrapper-path 'C:\absolute\lark-enterprise.ps1' --dry-run
```

Removing dry-run requires current authorization. The script verifies each schema
and fixture and checkpoints only into ignored `config.local.json`. A failure
retains real resources for inspection, not automatic deletion. Fictional owner
cells are intentionally empty; approved actors still appear in follow-up rows.
Never put credentials or actual identity/resource values in Git.

### Future empty real CRM (do not run before separate confirmation)

`--mode empty-real` reads `--source-config` without modifying it, re-verifies the
same bot application and the single Owner, then creates an empty `ANC CRM` only
with `--confirm-empty-real`. It requires explicit new absolute `--config-output`
and `--ledger-path`, rejects existing targets/the old ledger, creates no fixtures
and does not copy or initialize a ledger. Customer numbering uses native `CRM-`
auto-number rules and a separate internal creation-operation ID field.

First provision private target parent directories and inspect `--dry-run` with
the existing pinned CLI/profile. It makes no Feishu calls or local writes. The
real-mode source must have the verified app ID (or supply `--expected-app-id`);
a matching profile name alone is not proof of the application. Checkpoints stay
at the new config path after any uncertainty; stop and reconcile them manually,
never delete them to blindly retry Base creation. This script does not switch
the running gateway or deploy a policy.

The reviewed `ops/lark-crm-writer-customer-trial.sh` is an **uninstalled template**
for the existing protected bot wrapper, not an extra public CLI. Personnel reads
allow only exact `batch_get_id` and `get-user` shapes. Before installation verify
the real app's visibility and required name/status permissions:
`is_activated`, `is_frozen` and `is_resigned` must be explicitly readable.
Unknown status is a blocked lookup, not evidence of an active colleague. No
live personnel permission or real Base verification is claimed by offline tests.

## Deployment boundary

No deployment occurs from these instructions alone. Code/configuration must be
root-managed and read-only to Claude. Production selects
`/etc/myanc-crm/config.json` without an environment override. The authenticated
gateway/helper, not Claude, owns the enterprise profile, host secret and ledger.
The absolute ledger path is outside the model workspace: parent 0700, file 0600.
The secret is passed only to short-lived helpers; configuration stores its digest.

Tools mode is explicitly enabled with host setting `MYANC_CRM_TOOLS=1`; unset
preserves the legacy path. An invalid value or a missing host configuration fails
startup. The main process owns the independent loopback listener and shuts it
down with the gateway. It never exposes the privileged management API; an occupied
port fails startup rather than selecting a different port/interface.

Tools mode and legacy marker mode are mutually exclusive. Runtime-user
permissions, real card delivery/callbacks, protected
CRM resource isolation and unrelated Feishu capabilities need production
acceptance. Existing Linux fake-Feishu canaries are not proof of those boundaries.

Migration is additive (token binding and approvals). Old unbound staged rows must
be staged again. Back up protected settings and SQLite before migration. Preserve
actual receipts on rollback and disable the new entry point instead of guessing
which external writes to reverse.

Do not add automatic cleanup/recovery in this phase. Future manual retention may
keep terminal receipts 30 days and expired/superseded changes 7 days. Never prune
partial/applying operations before inspection. Any cleanup requires its own
protected backup and authorization; report counts without CRM payloads.

## Develop and test

```powershell
python -m compileall -q myanc_crm ops tests
python -m unittest discover -s tests -v
```

CI validates the placeholder configuration, standard-library-only code, offline
tests and common credential patterns. No live Feishu, deployment, automatic
merge or sandbox deletion occurs. Real-model tests are explicitly opt-in.
