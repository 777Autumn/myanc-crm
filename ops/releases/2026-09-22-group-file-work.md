# Two-account group file collaboration acceptance

Recorded 2026-09-22 (Asia/Shanghai). The existing Owner and test accounts completed
an explicit file-reference journey in the existing test group through the existing
Bot. Computer Use operated the logged-in Feishu client, opened every returned file
and downloaded it for content/hash checks. This is AI-operated acceptance, not
independent employee sign-off. Earlier [Owner private](2026-09-22-owner-file-work.md)
and [test private](2026-09-22-test-private-permissions.md) evidence is retained.

## Exact source delivery and candidate

| Repository | Installed source | Required exact merge-SHA CI |
| --- | --- | --- |
| CRM | `fa44e7e00b1f165dd17711011d27dc17b7e6d828` ([PR #51](https://github.com/77AutumN/myanc-crm/pull/51)) | [35638054868](https://github.com/77AutumN/myanc-crm/actions/runs/35638054868), passed |
| Gateway | `ee7afd38ec40dc4d95f3d02084dfb5f3b6c72523` ([PR #25](https://github.com/77AutumN/cc-connect-anc/pull/25)) | [35642199523](https://github.com/77AutumN/cc-connect-anc/actions/runs/35642199523), all five passed |
| Knowledge, unchanged | `88a60ba60a634fe3d6b0f68f91de326b19a39b30` | [34704220632](https://github.com/77AutumN/myanc-team-brain/actions/runs/34704220632), four required matrix jobs passed |

The gateway contains [PR #23](https://github.com/77AutumN/cc-connect-anc/pull/23)
(same-Bot/group accepted-file snapshot handoff),
[PR #24](https://github.com/77AutumN/cc-connect-anc/pull/24) (schema downgrade
protection), and test-only PR #25. CRM only extends the existing native workspace
guard to the two existing group accounts and adds regression coverage. Features
remain opt-in. Neither a new sender API nor a database/service/account was added.

Exact base/head AI Spec and Standards reviews are preserved on
[gateway #23](https://github.com/77AutumN/cc-connect-anc/pull/23#issuecomment-5765289146),
[CRM #51](https://github.com/77AutumN/myanc-crm/pull/51#issuecomment-5765289576),
[gateway #24](https://github.com/77AutumN/cc-connect-anc/pull/24#issuecomment-5765482558),
and [gateway #25](https://github.com/77AutumN/cc-connect-anc/pull/25#issuecomment-5765786364).
Each used the normal release gate; AI reviews are not human approvals.

PR #24's exact merge CI [35639576418](https://github.com/77AutumN/cc-connect-anc/actions/runs/35639576418)
failed an existing concurrent CUJ cleanup race despite green PR CI. Candidate
building stopped. PR #25 waits for both sessions to finish and checks persisted
user/assistant histories. The old wait reproduced 17 cleanup failures in 300 Linux
runs, and the persisted-history regression failed twice in 20 old-wait runs. The
fixed test passed 300/300 and exact merge CI. No candidate from the failed merge
was installed. Local cross-Windows coverage output paths were unsupported; full
Linux coverage evidence comes from CI, not that local attempt.

Normal `ops/build_vps_candidate.py` exported the exact three commits above, built
locked assets and Linux/amd64, and passed the four existing paired CRM/knowledge
journeys. CRM tests: 330, seven existing platform skips; spikes: 18; knowledge: 71,
two existing skips. Existing full Linux CI and ordinary-identity fixtures passed.
No broad suite was rerun just for this evidence-only commit.

- Candidate: `candidate-fa44e7e0-ee7afd38-88a60ba6.tar.gz`, 30,807,071 bytes.
- SHA256: `b8962ecb220aeeaea323c765755596706a2ca8447c1c9a2ef5a242db704f3734`.
- All 94 archive files match the manifest, with no extras.
- Toolchain: Go 1.25.6, Node 24.13.0, pnpm 10.28.1, Python 3.13.2.
- Private local manifest, build/review/maintenance evidence:
  `D:/MYANC/file-loop-evidence/group-file-20260922/`.

## Authorized installation and boundaries

One controlled stop/start installed 18 targets: gateway, guard, two workspace
instruction files, existing file/banquet Skills for both group accounts, narrow
group file configuration, and one service drop-in. Five existing files were backed
up; 13 files were new. Two work bases and the Skill directories were prepared.
The drop-in adds two existing groups to the ordinary gateway process; no account
membership, credential, network, dependency or CRM approval rule changed.

The frozen one-time maintenance script hash is
`e37d336efb2a44cac19b6127da9b70640965110aa05863310c230fa1bbc3fd28`.
Seven stores and gateway state were backed up. A scoped natural stop ended the
earlier idle Owner model before the frozen idle precheck; intake was checked again
after stopping. The shared startup helper ran once. Readiness was stable for over
130 seconds, six engines shared one receiver, with zero startup errors/restarts.
Installed gateway hash:
`859bb6efbf9930ba7c835be0343b9c96dcd8349620bb1d1f18fd7ffb5a68cec4`;
guard hash: `2508d93ca788ff3f23905791e2a06dac9aca9a1a46b9af63af6b41ce41def4b6`.

Actual ordinary-identity probes checked gateway UID 999 and model UIDs 1001/1005,
all with zero effective capabilities. Each model can read its own inputs and
write its own outputs, cannot write the inputs, and is denied all eight checked
protected paths: configuration, ledgers, knowledge configuration, management
directory and other account work bases. The gateway can read all four test works.
Real creation, model writes, host snapshots and revisions used these identities.
Different work directories within one employee account are not OS sandboxes.

## Real files and work association

Audit window: 2026-09-21 19:20:00–19:48:14 UTC. All budget data was explicitly
fictional and supplied in the initial request; this group trial did not read
company knowledge. Prior private-chat company grounding remains separate evidence.
Employees entered ordinary requests and native file replies, no commands, Skill
names or work numbers.

| Step | Actual result |
| --- | --- |
| Owner starts budget work | Excel and one-page Word: 12 tables, 120 people, total 44,400, 5,600 remaining from 50,000. |
| Test replies to Owner's Excel | 14 tables, drinks 250/table; Excel total 51,500, over budget by 1,500. |
| Test starts another task | Four-line fictional invitation copy, text only; distinct work/session, no file delivery or publication. |
| Test replies to the original Owner Excel again | Resumes the same imported budget work/session; keeps 14 tables and drinks 250, changes venue to 5,000; total 50,500, over by 500. |
| Owner replies to test's latest Excel | A new Owner work imports that exact accepted snapshot; 15 tables/150 people, drinks 250, venue 5,000; total 53,750, over by 3,750. |

All five real downloads matched accepted delivery receipts and immutable snapshot
hashes. Original outputs, inputs and old versions remain intact. The source chain
is Owner original → test's two revisions → Owner's final revision; the unrelated
copy work stayed separate. Each actor has its own model identity/session/work and
the host fixes the same group recipient. Filenames use v2/v3/v4 for the employee;
host version counters are local to each work, not a shared global sequence.

The [sanitized artifact checks](2026-09-22-group-file-artifacts.json) record the
actual hashes and numerical/formula checks. Eight formulas per workbook were
preserved and Feishu recalculated them. All five files were actually opened;
Word was one page. Formula caches are absent; desktop Excel/cache-only readers
were not tested. PAGE/TOC fields remain rejected, never silently removed, and
compatibility with a desensitized real template remains unverified.

Scoped traces contain 42 paired tool calls/results: 32 Bash, four Skill, three
Read, two Write and one ToolSearch. One script write outside the allowed workspace
was correctly blocked; Claude recovered inside its workspace. No technical
permission cards were observed and the exact gateway journal window contains zero
permission-request events. Six business/knowledge stores and prior read records
were unchanged; no new knowledge read was recorded. Earlier private file works,
installed controls and directory policies were unchanged. The gateway remained
on the same healthy process, with zero automatic restarts during acceptance.

This verifies the two named accounts' scoped file collaboration, not background
group monitoring, arbitrary cross-group sharing or every employee work type.
Existing CRM writes still require their existing business approval.

After the first group work the existing ledger is schema 2. Rollback must retain a
schema-2-aware gateway and can disable the two group file routes through controlled
maintenance. Never downgrade/rewind the ledger or delete originals/provenance.
This evidence-only commit changes no runtime and needs no build or installation.
Raw chats, credentials, business originals, runtime logs and backups are excluded.
