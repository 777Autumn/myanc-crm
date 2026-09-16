# Runtime skill layering

This is a rules-only refactor of CRM main
`c4f8a3ce6f6bf88832a76ff62693a2c9f533138d`. The previously frozen daily-followup
candidate remains a separate release; this document is not a deployment receipt.
Follow [RELEASE.md](RELEASE.md) for review, CI, merge and candidate gates.

Both releases were installed sequentially in the Owner-authorized September 16
window. See [installed hashes and acceptance limits](releases/2026-09-16-crm-skills-live.md).
Six-environment file/access checks passed; production model auto-trigger evidence
is still distinct from the prior isolated native-model validation.

## Rule migration map

The source below means `ops/CLAUDE.vps.md` at that exact base commit. Domain
sections moved verbatim, including their headings; no tool schema, approval,
identity, database, timing or notification behavior changes.

| Previous section | Single current authority |
|---|---|
| Introduction, BOT_CONVERSATION_V1, natural references and quoted rewrites | [CLAUDE.vps.md](CLAUDE.vps.md), same section |
| Knowledge-intent trigger and scope limits within conversation experience | Same policy entry; existing separately versioned team-brain skill unchanged |
| REMOTE_WORKSPACE_BOUNDARY_V3, Partner conversation boundary | Same policy sections; host/OS enforcement unchanged |
| REMOTE_SIDE_EFFECT_APPROVAL_V3 | Same policy section, CRM exception points to team-crm |
| REMINDER_HOST_TOOLS_V1 (commands, fresh versions, time, receipt, pagination, privacy, uncertainty) | [team-reminders protocol](skills/team-reminders/references/tools.md) |
| CRM_HOST_TOOLS_V1 (queries, pagination, assignees, staging, plans, child approvals, results) | [team-crm protocol](skills/team-crm/references/tools.md) |
| CRM read and receipt rules (facts/suggestions, current state, partial writes, visibility) | Same team-crm protocol, retained section |
| Image input and conversation continuity; General Feishu identity | Same policy sections |
| Root repository CLAUDE.md duplicated business rules | Developer-only entry links to the above; release contract stays authoritative for developers |

New skill entrypoints route to these protocols, not a second copy of the rules.
The always-loaded policy adds automatic intent routing and a missing-skill stop.
No `allowed-tools`, forked context, wrapper/API grants or generic scheduling tool.
Cross-skill handoff keeps the current sender/session; CRM-linked reminder edits
still call the existing linked-reminder update once and await its CRM card.

## Packaging and future maintenance

The existing fresh dual-SHA builder already packages all `ops/` files and hashes
them. It now tests that both entrypoints and both references are present. Do not
add a knowledge SHA merely to package this refactor: preserve the installed
knowledge version and record its actual hashes separately.

Deploy only after the daily CRM feature release and its separately authorized
maintenance. For this later rules-only window, use the existing maintenance
entry; inventory and back up these exact destinations in all six workspaces:

- `CLAUDE.md` from `ops/CLAUDE.vps.md`.
- `.claude/skills/team-crm/{SKILL.md,references/tools.md}`.
- `.claude/skills/team-reminders/{SKILL.md,references/tools.md}`.

Workspaces are `/home/{claude,claude-owner-group,claude-partner-private,
claude-partner-group,claude-test-private,claude-test-group}/ClaudeRemote`.
Reject symlinks and unexpected owners before replacing anything. Skill files
and policy remain root:root/0444; instruction directories root:root/0755.
Check parent ownership, effective model read/no-write access, exact manifest
hashes and existing managed hooks/sandbox for every account. Do not replace
whole `.claude` directories, settings, team-brain skills, credentials or ledgers.
No database migration or new permission is part of this release.

## Evidence required

- Compare the moved sections against the base Git blob before review; retain the
  byte-equivalence result (LF-normalized) outside the candidate commit.
- Run Python suites, six-account Linux guard checks and paired Go CUJs. Existing
  approval, reminders, knowledge, image, `/new` and `/stop` behavior remains.
- Use the opt-in gateway real-Claude Engine fixture with this policy and the
  exact CRM checkout. It places files under isolated `.claude/skills/`, records
  source/installed hashes and successful native reads before domain calls.
  Only the fixture client path may be substituted; skill bodies are never
  appended to prompts. The legacy no-tools decision eval proves no discovery.
- Small fictional multi-turn cases cover CRM search/stable selection/plan/
  receipt, personal reminder changes/cancel, quoted instructions and existing
  knowledge discovery. Record misses, wrong triggers, repeat reads, reply quality
  and semantic review separately from code-grader outcomes.
- Real six-environment installed hashes/access passed in the recorded window;
  subsequent releases must repeat those checks. Current production model behavior
  acceptance remains incomplete; local fixtures do not certify production loading.

If loading or behavior regresses, restore the matching prior rules/skills from
the same business version's backup. Do not downgrade application state or
restore an old ledger. Preserve skill-loading evidence and explain incomplete
local, GitHub and online stages separately.
