# Owner private file work acceptance

Recorded 2026-09-22 (Asia/Shanghai). The existing Owner private chat now uses the
same native file path as the [already verified test account](2026-09-22-test-private-permissions.md).
Computer Use operated the existing Feishu client and Bot as the authorized Owner
account. This is AI-operated acceptance, not independent employee sign-off.
Group collaboration and all employee work types are **incomplete**.

## Source and candidate

- CRM [PR #49](https://github.com/77AutumN/myanc-crm/pull/49): reviewed base
  `dcf5ea56ef2dcc1d9ab39a889d7d87063e16ae4a`, head
  `42640a277a7ea51dd9571d04fc18b0ce27bc4bcc`, squash merge
  `0db25120e68ec10b14326562238638f3a2819f70`.
  [Independent AI Spec/Standards reviews](https://github.com/77AutumN/myanc-crm/pull/49#issuecomment-5764308203)
  and [exact merge CI](https://github.com/77AutumN/myanc-crm/actions/runs/35629136774) passed.
- Gateway remains `e9634d15377d614c87334498d39e6c1e38d68c1f`,
  [exact merge CI](https://github.com/77AutumN/cc-connect-anc/actions/runs/35618391452).
- Knowledge remains `88a60ba60a634fe3d6b0f68f91de326b19a39b30`,
  [four required matrix jobs](https://github.com/77AutumN/myanc-team-brain/actions/runs/34704220632).
  No knowledge source or publication state changed.

The source patch only extends the workspace guard to the existing Owner account,
adds cross-account regression coverage and documents the opt-in rollout. The new
Owner case failed against the original guard; all seven guard tests then passed
under WSL Ubuntu. CRM tests passed (330, seven existing skips), as did 18 spike
tests and existing Linux CI. File capability remains off by default.

Normal `ops/build_vps_candidate.py` exported these exact three merged sources,
built locked assets and Linux/amd64, and actually passed the four existing paired
CRM/knowledge journeys. All 92 archive files matched the manifest, with no extras.
Toolchain: Go 1.25.6, Node 24.13.0, pnpm 10.28.1, Python 3.13.2.

- Candidate: `candidate-0db25120-e9634d15-88a60ba6.tar.gz`.
- SHA256: `d10ae93c8edb8a0608f77c3d5b6b22965d4d50ecf257afdc1dc14fff0948ebcf`.
- Private local manifest, checks and maintenance receipts:
  `D:/MYANC/file-loop-evidence/owner-file-20260922/`.
- Gateway binary already matched the candidate and was not replaced:
  `b0a2f4b824410d7e192d4579f56a25b6277d41e8767aebd5890bf016e3df0337`.

## Authorized maintenance and boundaries

One controlled stop/start installed ten file/config targets: the guard, Owner
instructions, existing file/banquet Skills, narrow Owner native-file configuration,
and a service drop-in adding the existing Owner group. The dedicated work base is
gateway-owned and group-readable by that model account; account memberships were
not changed. Only Owner private and test-private use native bypass/file work.
Other routes, managed sandbox/denies, CRM approvals, authentication, network,
dependencies and the unique Bot receiver were retained.

Seven stores and gateway state were backed up before mutation. Initial preflight
stopped before service/config changes because an earlier idle test model process
remained. The actual test chat received a natural stop command and acknowledged
it; its model exited cleanly. The reviewed idle fingerprint then included that
known stop. Earlier failure and script versions are preserved privately.
The final one-time installer SHA256 is
`fee43ee3b57dc1989ad3f45ab51076cd355acbfdd42b8478b33b3056404591ca`;
independent AI maintenance reviews include the corrected race, backup and failure
reporting checks. No ledger rollback occurred.

The existing startup receipt helper completed once. Readiness stayed true from
10.1 through 140.9 seconds, with six engines sharing one receiver, zero errors and
zero automatic restarts. Gateway UID 999 and model UID 1000 have zero effective
capabilities. Read-only probes dropped to those actual identities: both can access
the intended work, while the model cannot open protected configuration, ledgers,
the other test account's work base or the management socket directory.

## Real conversation and files

Audit window: 2026-09-21 17:21:00–17:37:00 UTC. No employee command, Skill name or
work ID was entered. The first request specified a fictional 20-table/200-person
banquet comparison with a 100,000 budget; a natural unquoted follow-up changed it
to 22 tables/220 people and retained the budget and prior files.

| Evidence | Actual result |
| --- | --- |
| Company grounding | One successful knowledge body read; the documents distinguish the company service-boundary material from fictional `DEMO-VENUE-001` v1.0. This is general scope guidance, not a real banquet price list. |
| First Word/Excel pair | Both received, opened and downloaded in Feishu; totals 81,600 / 93,600. |
| Natural revision | Same work, two new files; totals 89,560 / 102,760, with B exceeding budget by 2,760. |
| Preservation | All four download hashes match accepted receipts and host snapshots; original outputs and prior versions remain. Other file works, including test-private, are unchanged. |
| Permission experience | Zero technical permission events/cards; no manual tool approval. One attempted script write outside the workspace was correctly blocked by the existing guard; Claude recovered inside its own workspace. |
| Tool evidence | 44 calls have paired results: 3 Skill, 4 Read, 30 Bash, 5 Write, 2 Edit. The one guard denial is retained as a recovered error, not reported as zero errors. |
| Business state | Six business/knowledge stores retain their business/publication tables and prior reads; only one knowledge-read record was appended. Same healthy gateway process, no restart during acceptance. |

The [sanitized artifact checks](2026-09-22-owner-file-artifacts.json) cover ZIP/XML,
requested totals, formulas, revision text, source labels and receipt/hash binding.
The first Excel used currency formatting for table/person counts; the natural
revision corrected these to tables/people. Per-person figures display rounded
whole currency units. Excel formulas have no cached values (19 in v1, 21 in v2);
Feishu recalculated them, but desktop Excel/cache-only readers were not tested.
PAGE/TOC and real-template compatibility remain unverified. Raw chats, source
bodies, actual files and private maintenance records are not committed.

Rollback requires controlled restoration of the ten backed-up code/config
targets and startup checks; preserve all work files and business ledgers. This
evidence-only commit changes no runtime and requires no new installation.
