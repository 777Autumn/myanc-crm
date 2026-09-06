# Single-Owner customer trial — implementation and release gate

Status: development only. No real CRM Base has been created or selected by this
change. The approved target is 3–5 real customers and 10 follow-ups after a
separate real-cutover confirmation. Sandbox remains independent and is retained.

## Fixed baseline

The 2026-09-05 Owner canary used the ongoing-session controlled tool path, not
the legacy request-file/permission-marker handoff. Its approved journey was
read → clarify → stage → modify/cancel/approve → read result → discuss.

- CRM baseline commit: `972a8b2e400ee1e6f9204502eb221ac16e3c0c4a`.
- CRM baseline source tree: `a40b0e63c970aaf80726d21af4154ccbe3ff45a5`;
  the exact exported tree passed 94 offline tests on 2026-09-06.
- Gateway task-start source tree: `1a03caa898c510b9a8c3725169f2b17ad5cd72aa`,
  baseline commit `d72a34665faec9f38c26035ad4b1ea704c639edf`;
  parent commit `17c61062c2f9ce9bcdd45a2082e491f9743a2770`.
- This baseline preserves existing in-scope source before the new trial work.
  Generated gateway test-session files and unrelated workspace files are excluded.
  No credentials, live identifiers, private configuration or ledger is committed.

## Scope and data rules

One company and one primary contact per customer. Company plus one of contact
name/phone/email are required; stage and verified assignee must be specified.
Stages: 新线索、已联系、沟通中、已成交、暂缓. Updates touch only named fields;
explicit clearing must preserve those invariants. Customer number, system
fields and historic follow-ups cannot be edited. Duplicate company names need
explicit selection or a knowingly distinct same-name company; no auto merge.

New assignees are resolved by exact phone/user email through the same bot app,
then re-read by ID to verify the name and availability. Previously verified
names may be reused within the trusted sender/session scope. Choosing an
assignee does not modify `allowed_actors`. No user OAuth or arbitrary API route.

## Two approvals, one narrow continuation

The host freezes any first follow-up draft in the customer operation's approved
fingerprint. Customer create/update has its own claim, drift check, one write
and readback. Creation includes an operation ID and persists the actual created
record binding separately; the approved body never changes retroactively.

After a verified parent, the existing follow-up planner reads that bound record,
not its old/new name. One SQLite transaction checks the parent's write-intent
generation and creates at most one child + independent 10-minute approval.
New controlled write-tool requests advance the generation before backend reads; reads and
discussion do not. Thus automatic continuation cannot displace a newer request,
even if the later request is still reading. The existing placeholder → bind →
activate card publisher handles the child. Claude is not resumed by callbacks.

The first approval never approves the follow-up. Cancelling the child preserves
the successful customer operation. `result` exposes both linked operations, and
`customer` pairs current facts with the latest durable operation rather than
guessing from old conversation. Preparing or publishing a child is not itself a
CRM write. A pending/unpublished repair card may follow earlier partial writes;
describe actual effects from the durable receipt, not from card state alone.

Unknown writes stop for inspection. A verified parent survives child generation
or delivery failure. If generation stopped before publishing, report the first
operation's success and the unsubmitted new follow-up. An activation response
failure does not prove non-delivery or zero writes: inspect linked durable
receipts before manual recovery, since the independently approved child could
already be running. Preserve earlier partial writes when a repair card fails.
There is no automatic retry worker, general
workflow framework, MCP migration, SDK switch or second model.

## Release gates

1. Offline compilation, old regression suite and new customer/ledger/host tests.
2. Cross-repo real Engine/CLI/SQLite journey with only external Feishu faked.
3. Paired model-behavior cases and independent semantic review: record execution
   status honestly; deterministic tests are not model-behavior evidence.
4. Separate standards/spec code review, complexity review, independent senior
   review; required CI green before squash merge. Keep failed evidence.
5. Real switching remains paused after merge. First obtain explicit confirmation,
   verify same-app bot permissions/visibility, back up service assets and ledgers,
   then use a new empty `ANC CRM` with `CRM-` numbers and a distinct ledger/config.
   Do not copy Sandbox rows, replace its ledger or introduce multi-Base routing.
6. Fictional/new-release acceptance and non-CRM document/Base/calendar reads,
   Quiet, continuation and single receiver are explicit checks, not inferred from
   last night's canary. Real user writes remain per-card approvals.

Rollback disables the new customer entry points and restores compatible code
and configuration. Keep real writes, current ledger and receipts. Never restore
an old ledger over completed business work or blindly delete created customers.

## Usage review (no real customer data)

For each trial journey record only a local anonymous sequence number, outcome,
clarification count, repeated-explanation count, manual-recovery count and user
feedback category. Do not copy company names, contact details, message text or
payment information into Git, fixtures or research notes. Review usability after
3–5 customers / 10 follow-ups; correctness alone does not establish usefulness.

## Review basis

The implementation reuses this repo's `core.py`, `lark.py`, SQLite and controlled
client, plus the gateway's existing action host and card binding. The official
Commerce Merchant Operations, Trust & Safety and Evals Skills guide approval,
grounding and paired acceptance; Ponytail constrains additions to these two
customer branches and one child-card continuation. Official Skills and upstream
reference source are not modified.
