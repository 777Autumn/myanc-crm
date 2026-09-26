# Maintenance consolidation and pinned Claude upgrade

Status: source candidate in progress; not installed and no new live-model or
Feishu acceptance is claimed here. This continues the
[recorded colloquial trial](../acceptance/2026-09-26-colloquial-trial.md).

## Change and compatibility

Reuse the existing maintenance startup, activity and candidate paths. Complete
journal parsing now rejects omitted/null messages and keeps unknown activity
blocked. Reviewed startup and clean-exit checks move out of one-time scripts;
the three historical unsolicited INFO events remain unexplained. Frozen file
inventories distinguish old/new/partial/unknown installations. Consistent updates
run with the existing receiver stopped and start only after all files match.

The Owner approved one explicit, diagnosed recovery per candidate in the
original receipt root. The [maintenance contract](../MAINTENANCE_START.md)
defines its immutable bindings, fresh reconciliation and consumed-attempt rules.
It is not an automatic retry or permission to replay business operations.

The official native CLI artifact and its hash are pinned in
[`claude-release.json`](../runtime/claude-release.json). The managed version gate
must match it. Installers preserve all other installed managed settings, including
site-specific protections; the template is not a replacement for live policy.
Only the four listed owner/test entries receive explicit model/effort settings.
The shared CLI affects all six entries. Preserve existing authentication, native
file execution and ordinary identities; no Node or other dependency upgrade.

## Evidence and remaining gates

- Base: CRM `7192143e079c6e9e9ab94cbf184b482ee0be1653`.
- Unchanged gateway: `6e7c014ed3ea200007b86a6636fc76a6b9ec5e00`.
- Unchanged knowledge: `88a60ba60a634fe3d6b0f68f91de326b19a39b30`.
- CRM [draft PR94](https://github.com/77AutumN/myanc-crm/pull/94) carries incremental
  tests and CI; final exact-head AI reviews and merge CI remain required.
- The downloaded 2.1.283 Linux x64 artifact matches its official manifest:
  241,556,664 bytes; this is download verification, not executable/model acceptance.
- The known CRM sandbox blocker, earlier file-quality limits and all previous
  maintenance failures remain in the [follow-up index](../FOLLOWUPS.md).

The installation inventory will bind the normal merged candidate, CLI artifact,
service identity and three changed live files (CLI, version pins, gateway options).
Rollback restores their paired runtime/configuration backups; it never restores
business databases, chat histories or artifacts to an older snapshot. New CLI
sessions are not presumed compatible with an older CLI after rollback.

After controlled maintenance, verify all six entries, the sole receiver and a
125-second stable window. Verify the requested model from actual invocation and
response metadata, then open the two-account fictional sales/revision and handoff
artifacts. Keep first results, corrections, timings and intervention separate.
Unavailable Opus 5.5 or a low-effort failure stays unverified/failed; do not silently
substitute another model or effort. No long-term reliability claim follows from
this bounded window and sample.
