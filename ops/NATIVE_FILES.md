# Native employee file loop (candidate only)

Pairs with gateway PR #18, `FILE_HOST_TOOLS_V1`, and the unchanged knowledge
commit `88a60ba60a634fe3d6b0f68f91de326b19a39b30`. Only the existing test-private
account is included. No new receiver, provider credentials or business writes.

After exact-source merge, merge CI and the normal candidate build, request a
separate installation/maintenance authorization. Re-read the actual service,
selected Bot/chat/account and protected settings first; old inventory is not a
current-state check. Never deploy this draft branch.

The authorized installation would add only:

- The candidate gateway and `/usr/local/bin/cc-connect-file` client, plus this
  workspace guard at its existing managed location. Keep the managed sandbox.
- Root-owned/read-only `team-files` Skill and its reference in the test employee's
  existing workspace, together with the already-merged `ops/CLAUDE.vps.md` policy
  as that workspace's `CLAUDE.md` (includes the file-return approval exception).
  Keep existing team-brain/CRM Skills and authentication.
- A root-owned `/opt/team-files` virtual environment, using system Python and
  the exact packages in `runtime/team-files-requirements.txt`. Do not upgrade
  system Python or Claude. No automatic package installation by the model.
- Native file configuration, initially disabled, with work base
  `/srv/cc-file-work/claude-test-private`; omit `tools_socket`. Use the existing
  employee cwd and absolute Claude command. This path is outside host-secret
  paths denied by the managed policy, not an exception for those paths.
- Work-base gateway ownership and model primary group, mode 0750, with the
  gateway's explicitly authorized group membership. Reuse the existing file
  host's protected ledger/snapshot layout and initialization rules. Grant only
  `CC_FILE_ACTION_TOKEN` through the existing sudoers env_keep mechanism.

The native adapter passes only the selected work as an additional Claude
directory. Inputs remain read-only; the model writes outputs, and the existing
client publishes selected files to the gateway group. The guard permits Read on
inputs and file tools on outputs only for the test account's fixed work base.
Other accounts retain their existing rules. Same-employee works share an OS
identity; this candidate does not claim protection from hostile same-UID code.

Offline tests use fictional Office files, ordinary temporary identities and
fake external interfaces. They do not establish actual Claude sandbox behavior,
live company retrieval, document rendering or Feishu delivery. PAGE/TOC fields
remain rejected without deletion; real template compatibility is unverified.

The authorized live journey is one existing private chat: upload a fictional
spreadsheet, name a real company source accessible through team-brain, receive
an XLSX and DOCX citing that read, reply with a change, then receive revisions.
If the company source is inaccessible, report it and leave this criterion
unverified. Stop on wrong work/recipient, inaccessible originals, a boundary
failure or uncertain delivery; do not automatically resend.

Enable only in the approved single-service window. Rollback disables file work
and restores the matching code/rules as authorized, preserving originals,
outputs, snapshots and receipts. Never restore business ledgers or replay sends.
