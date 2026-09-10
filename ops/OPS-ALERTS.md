# Host operations alerts — candidate, not enabled

Follow [RELEASE.md](RELEASE.md). This module adds no model command, receiver,
listener, credential or native timer access. It observes reminder health through
committed state and uses the existing authorized private Feishu sender.

## Semantics

Storage failure, changed identity/destination and permission-paused work are
reported immediately. Ordinary unknown acceptance starts a durable incident;
an independent one-second loop checks its 15-minute deadline even while reminder
retry is waiting. Same-category/person observations are aggregated; counts refer
to affected reminder items or standalone private-list pages. No body, raw private
ID, credential or raw upstream error is included in an alert or ordinary log.

An incident binds the verified Owner route when first observed. Each send freezes
its text, UUID and route in a separate SQLite outbox before networking. Unknown
results retry with that UUID inside one hour; later attempts explicitly warn of
possible duplication. Permission rejection pauses that send. A changed/revoked
Owner route never redirects queued alerts; reconcile via protected operations.
Unsent hourly warnings coalesce instead of building a notification flood. A
recovery notice cannot overtake its warning, and requires a complete, successful
reminder-state check with that fault absent. Alert acceptance alone is not recovery.

Alert initialization precedes opening the reminder database. A missing/corrupt
alert DB is never recreated automatically: logging and at most three best-effort
notices per process (at least an hour apart) are the fallback. This fallback does
not preserve backlog across restart. CRM/knowledge keep their existing lifecycle.
There is no recursive alerting. A Feishu-channel failure delays notifications;
VPS-wide failure cannot be reported immediately through this same VPS.

## Separately authorized maintenance

1. Pass exact-head review/CI/merge and build one clean dual-SHA candidate. Inspect
   current identities, running versions, pending operations and backups first.
2. Preserve all existing configuration. Create `/var/lib/myanc-ops-alerts` owned
   by the existing supervisor `ccconnect`, mode 0700. As that user, invoke the
   reviewed binary's `ops-alerts-init /var/lib/myanc-ops-alerts/alerts.sqlite`
   exactly once. Existing files are refused, including damaged ones.
3. Merge `runtime/ops-alerts.service.conf`, replacing its project placeholder with
   the already verified Owner **private** project; never put a free-form user/chat
   ID there. This is a drop-in for the existing service, not a new service.
4. Merge the reviewed model policy, command guard and managed deny rules without
   removing knowledge instructions or existing ACLs. Verify the actual database
   is 0600 and all six model Unix users receive EACCES when attempting to read it;
   a nonexistent path is not evidence. Do not expose queue/receipt inspection to
   any model or general-purpose Feishu CLI.
5. Merge `runtime/business-display.toml`, then run the read-only Python 3.11+
   `runtime/verify-business-display.py <protected-config> --project <name> ...`
   with all six verified project names. It checks project overrides as well as
   global defaults and emits no identity values. Retain protected diagnostics.
6. Count one receiver/listener, check six environments and existing ledger hashes,
   run Owner/test independent task acceptance, and record exact installed hashes.
   Fault-injection tests run only with synthetic stores/clocks, never against
   production databases. No automatic resume or resend of paused work is added.

## Recovery and rollback

Pause relevant scheduling before restoring reviewed code/configuration. Retain
both reminder and alert databases, pending messages and receipts. Never restore
an old business ledger over live data, clear a queue, or initialize an empty DB
to mask missing data. Determine actual send outcomes before re-enabling. Missing
bindings require operator reconciliation, not a new recipient selected by a model.
