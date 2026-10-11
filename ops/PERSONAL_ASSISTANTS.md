# Personal assistant pilot

This runbook extends the existing Mac installation. Do not run first-install
scripts, recreate personal CLI profiles, copy OAuth credentials, or initialize
business ledgers. The release requirements in [RELEASE.md](RELEASE.md) apply.

## Scope and reuse inventory

The pilot has two people (777秋 and test), two personal AppBots, and the existing
public ANC AppBot. It keeps one Gateway, one shared Codex app-server, the existing
subscription login, and four business routes: two private routes and two
sender-specific routes in the existing shared group. Employees use Feishu.

| Resource | Treatment |
| --- | --- |
| Multi-App transport and shared Codex runtime | Reuse; one receiver per App, no second Gateway |
| CLI 1.0.90 profiles, refresh, connection versions | Reuse without enrollment or credential migration |
| CRM tools, approvals, conflict checks and receipts | Reuse with trusted member resolution; model parameters unchanged |
| Banquet handoff versions, recipient and acceptance state | Reuse; verified receipts produce host-only notification events |
| File publication, immutable snapshots and import | Reuse original ledger and snapshots, retaining original physical provenance |
| Reminder and operations alert senders | Adapt fixed destination selection to canonical member |
| Knowledge host | Add complete physical-principal-to-member configuration; access remains principal scoped |
| Missing notification/start path | Add a narrow host callback and persistent claim/receipt to the existing CRM ledger |
| Tests and release | Extend existing fixtures/CUJs and exact-commit release gate |

The `anc-company-builder` and `anc-fde-reuse` packages provide methods and
operational references, not a replacement identity or notification runtime.
No OAuth service, A2A framework, scheduler platform, or new dependency is needed.

## Protected configuration delta

Freeze actual deployed hashes, configured routes, runtime versions and the
reminder store before preparing the installation delta. Use synthetic identifiers
in reports; secrets and full account mappings stay in the protected host config.

1. Retain the public App's two group routes. Add `member_id` (the original
   `allowed_actors` key), `source_tenant_key`, `legacy_private_chat` and a fixed
   `legacy_private_redirect` naming that member's assistant. Old private messages
   get the redirect before downloading attachments or starting a model. Old
   private action cards cannot execute.
2. Create two personal Apps and independently verify each App, tenant, actual
   human sender and private chat. `open_id` is App scoped: never copy the public
   App's `allow_from` into a new App. Never trust a display name or a registration
   response alone. Retain the same member identifier and CLI profile.
3. Configure each new private project with its own App credentials, exact
   `allow_from`, exact `allow_chat`, `member_id` and `source_tenant_key`. User-role
   rules use the physical sender ID. New projects have new session stores and
   work directories. Keep the existing protected model login and shared runtime.
4. In CRM `personal_connections.routes`, add the exact physical route and its
   `member_id/source_app_id/source_tenant_key`. Keep the original global source
   App/tenant anchor, `allowed_actors`, connection profile and business App fields;
   they preserve the existing connection subject and generation. The startup
   handshake verifies the full project/App/tenant/member/sender/chat mapping.
5. In Knowledge, configure all four physical principals and their existing access
   grants explicitly. Add complete `member_bindings` from each principal key to
   the same CRM member identifier. Every member has exactly two entries. Mapping
   does not merge histories, read receipts, approval cards, or knowledge scopes.
6. Keep the common file ledger and immutable snapshot location. Keep original
   publication principals, receipts, connection tombstones and native session IDs.
   New work can import an authorized published snapshot; it cannot import the
   original conversation.
7. Recheck pending/unknown reminders immediately before maintenance. The observed
   empty store permits no migration work. If it is no longer empty, stop this
   cutover and reconcile exact records; do not rewrite frozen destinations or
   replay unknown sends. Native banquet reminders keep their existing source.

Do not increase the total configured image cache above 512 MiB. Separate Bots do
not create separate model processes or additional subscription capacity.

## Handoff behavior and recovery

Only a verified submit/accept/return receipt creates a notification event, in the
same CRM transaction. The recipient is resolved by trusted member configuration.
The model cannot select an App, profile, destination or notification command.

The host claims one event, sends a non-actionable card with a fixed dispatch UUID,
saves the exact message receipt, and then enables the start button. Unknown sends
or incomplete receipts are not automatically resent. A failed card update leaves
the underlying publication intact. Inspect the host notification record and use
the existing pending-handoff view to recover.

For a delivery investigation, call the existing protected `host-handoff-events`
operation with the exact configured project, source App, source tenant and
publication event ID. It returns the recorded notification status, message ID and
start binding. If a message ID is recorded, read that exact message using the
same sending App and check its chat and card against the recorded destination.
A missing receipt cannot be replaced by a similar-looking card or a guessed ID.
Without conclusive evidence, retain `unknown`/`dispatching`, do not resend or
rewrite the receipt, and record the investigation separately. The recipient can
use My pending handoffs and the ordinary authorized handoff read/approval flow;
that flow does not depend on the notification becoming `sent` or gaining a button.

Clicking the button checks the actual callback principal, original message,
current publication/version, current personal connection, pending approvals and
published file snapshots. Busy recipients retry later. An idle recipient gets a
new work and session with a durable one-time start binding. Repeated clicks,
including after restart, do not start another model turn. A claimed start is not
proof that the model finished: follow its linked file-work and session receipts.
The assistant reads approved materials and lists gaps; accept/return still use the
existing human-approved actions. Delivery, organization and acceptance are three
different outcomes.

## Member instructions

- 777秋 uses “777秋的助手”; test uses “test的助手”. The public ANC Bot continues
  shared group work. Other people cannot use a personal assistant as its owner.
- Use the existing connection-status and reconnect commands when prompted. The
  new Bot uses the existing personal connection; a new authorization does not
  revive work bound to an expired connection.
- After materials are published, use the personal notice's “整理交接” button.
  Finish an existing task or approval first if the assistant is busy.
- Inspect the gaps and files, then explicitly request accept or return. Approve
  the specific preview. Updated materials require a new version and confirmation.
- If no notice arrives, open “我的待接手” or query the current handoff. An unknown
  notification outcome does not mean publication failed; do not republish solely
  to retry delivery.

## Acceptance and release record

Keep logic tests, real-model tests and real Feishu journeys separate. Required
normal/refusal pairs cover both users' CRM/knowledge/files, concurrent isolation,
wrong sender/App/tenant, disconnect/rebind, both directions of handoff including
return and a new version, stale/duplicate/busy clicks, missing files, send failure,
restart, shared-group scope, legacy private redirects/cards, reminders and alerts.

Use clean Spec and Standards reviews bound to exact commits, PR and merge-SHA CI,
and a pinned three-source Darwin candidate. Cut over only after tasks drain and a
new maintenance receipt has passed all current checks. Verify one Gateway, one
receiver per App, a shared model runtime and at least 125 seconds of stability.

Rollback disables new entries while retaining guards, connection versions,
business ledgers and all invalidation evidence. Never move new private histories
back into old public-Bot sessions or restore revoked authorization.

Record local implementation, GitHub delivery and online release independently.
Two-user acceptance does not establish long-term multi-employee capacity. The
single-subscription technical setup is retained for this pilot; production
customer subscription applicability remains a separate documented deployment
question, not a reason to change this pilot's backend or purchase a plan.
