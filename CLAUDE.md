# CRM development contract

For implementation, PR review/merge, candidates and completion reporting, first
read [ops/RELEASE.md](ops/RELEASE.md). Source changes never authorize deployment.

This repository develops controlled tools for a general Feishu Claude assistant.
Repository instructions are for developers, not the deployed assistant's prompt:
- Always-loaded runtime boundary: [ops/CLAUDE.vps.md](ops/CLAUDE.vps.md).
- CRM workflow and tool protocol: [team-crm](ops/skills/team-crm/SKILL.md).
- Personal reminders and linked-plan handoff: [team-reminders](ops/skills/team-reminders/SKILL.md).
- Team knowledge remains owned by the separate team-brain repository.
- Rule migration and release/rollback checks: [ops/SKILLS.md](ops/SKILLS.md).

Keep identity, access scope, approvals, persistence, idempotency, time validation
and credential isolation in the host code and protected configuration. Skills
cannot grant access or replace those controls. Preserve the controlled interfaces;
do not revive the legacy request-file/PermissionRequest path in tools mode.

After changes run:

```sh
python -m compileall -q myanc_crm ops tests
python -m unittest discover -s tests -v
```

Run the relevant spikes and paired gateway CUJs as required by the delivery
contract. Use fictional fixtures; never substitute real CRM data or credentials.
