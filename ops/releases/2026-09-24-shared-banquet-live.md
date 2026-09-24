# Shared mock wedding progress — scoped acceptance

This record covers two existing test accounts, their existing test group and the
sales-maintenance private entry. All named weddings and business facts below are
fictional. It does not establish production hotel integration or broader employee
readiness. Formal CRM tables, published Wiki v2 and knowledge source are unchanged.

## Exact delivered sources

| Repository / change | PR | Reviewed base → head | Squash merge | Exact merge CI |
| --- | --- | --- | --- | --- |
| Gateway shared context | [30](https://github.com/77AutumN/cc-connect-anc/pull/30) | `e453ecf34b5a576796a699a6cdc26330d2ecd3a3` → `93b0ccf9d5a68051344485615ff52a1e1f851854` | `02ea0a9e629ffcfa04b52cd569ac73c548461a31` | [PASS](https://github.com/77AutumN/cc-connect-anc/actions/runs/35994762093) |
| CRM shared records | [73](https://github.com/77AutumN/myanc-crm/pull/73) | `a95a6149ba5b89dd28fd4d27779b4ed5a4decfdc` → `a1c0cb233f8ae59aa333562c65a83bfe2b693604` | `4e9d9517d472d6597ce268f21cca34ad324aed9e` | [PASS](https://github.com/77AutumN/myanc-crm/actions/runs/35994723730) |
| Literal-source validation feedback | [74](https://github.com/77AutumN/myanc-crm/pull/74) | `4e9d9517d472d6597ce268f21cca34ad324aed9e` → `56e7455b3256e41428cf4e9dfa8164a53a5c3d14` | `e876f7fb6987c46a0d98d902ecb19d5d9d9a97ca` | [PASS](https://github.com/77AutumN/myanc-crm/actions/runs/35998228001) |
| Whole-batch diagnostics | [75](https://github.com/77AutumN/myanc-crm/pull/75) | `e876f7fb6987c46a0d98d902ecb19d5d9d9a97ca` → `54f56f416b8a0526735e5a88f06e52942ef2019d` | `40093d3245188c8426e9ae61b52c2a006ae09353` | [PASS](https://github.com/77AutumN/myanc-crm/actions/runs/36000232688) |
| Read imported budget before answering | [76](https://github.com/77AutumN/myanc-crm/pull/76) | `40093d3245188c8426e9ae61b52c2a006ae09353` → `4560842eb9fa5c2d879853004351f60bba1ad6ad` | `7edf3f32a0f12533bdd80b9b7aaf0fa751753efc` | [PASS](https://github.com/77AutumN/myanc-crm/actions/runs/36003474652) |
| Conversation routing | [77](https://github.com/77AutumN/myanc-crm/pull/77) | `7edf3f32a0f12533bdd80b9b7aaf0fa751753efc` → `4267c17f47b77e787217887a27d5e8d6b6a78af6` | `17b57f2027e324bd603e70389bd98631c576dde9` | [PASS](https://github.com/77AutumN/myanc-crm/actions/runs/36006235427) |
| Persist unverified conflict reports | [78](https://github.com/77AutumN/myanc-crm/pull/78) | `17b57f2027e324bd603e70389bd98631c576dde9` → `3338b942b3383cc9a64b07279953c47fd6f45ba4` | `3048915c6e0699cc8cb2525c14bca8d37512e262` | [PASS](https://github.com/77AutumN/myanc-crm/actions/runs/36007833180) |

Every changed head received separate Spec and Standards AI reviews, release-gate
checks and exact merge-SHA push CI. AI reviews are not human GitHub approvals.
The final installed/tested runtime source combination is CRM `3048915c6e0699cc8cb2525c14bca8d37512e262`,
gateway `02ea0a9e629ffcfa04b52cd569ac73c548461a31`, knowledge
`88a60ba60a634fe3d6b0f68f91de326b19a39b30`.

## Candidate and installation

Normal `ops/build_vps_candidate.py` exported clean merged sources. The final bundle
`candidate-conflict-3048915c-02ea0a9e.tgz` contains 135 manifest-listed files,
all checked against actual bytes. SHA256:
`f8285af767b0d99a676dcd8a842694d21471ff136d31132db18df387a231dc1a`.
Its private candidate manifest retains the full file list and toolchain:
Python 3.13.2, Go 1.25.6, Node 24.13.0, pnpm 10.28.1.

Build checks: 375 CRM tests (8 Windows-specific skips), 18 spike checks,
71 knowledge tests (2 skips), and five actually executed paired gateway journeys:
shared-case/private-grant/revision; daily list/plan approval; customer approval
and continued discussion; independent follow-up; catalog read/follow-up/scope.
These use the exact exported CRM/gateway/knowledge combination. Exact Linux CI
covers the platform checks omitted locally; no skipped local check is called a pass.

The initial scoped installation changed 12 files, initialized three mock-case
tables in the existing protected TEST store and retained the unique receiver.
Ordinary model users can read their Skill but cannot modify protected knowledge
or read the host configuration/database. Other entry configurations remain intact.
Two subsequent feedback patches each changed one module and three references;
the fee-read patch changed only the three shared-case Skill references while idle.
It did not restart the service or change configuration, databases, dependencies,
accounts, permissions, model, or Wiki. Candidate-generated Wiki provenance was
not installed. All three actual final reference hashes matched the frozen manifest.

Fee-read Skill installation receipt SHA256:
`93cf4f39718cfb176225560164fc4bf6e29fdf52e74fa33a1cb8517cfc25dc8f`.
The subsequent routing patch replaced only the wedding paragraph in three project
guides, preserving each entry's role and all other content. Each protected old
file matched its frozen baseline; resulting bytes and metadata were verified.
Service, Wiki, configuration, business and session state were unchanged during
that idle update. Routing installation receipt SHA256:
`6422fa2566cda30c6d7f029549867ef52bf8baaf8c580d9286c142026f40c827`.
The final conflict-recording patch also changed only three references. Its final
check failed on one new journal notice; a separately reviewed read-only
reconciliation used two identical full snapshots at least 120 seconds apart and
checked the entire journal against the exact old prefix plus that single notice.
It passed without retrying installation, changing runtime, or overwriting the
failure. Reconciliation receipt SHA256:
`d706e73c5a10d763f75138443abc01751f5b80c28aed28ba7c2a0878f78d7274`.
Private manifests, backups, target paths and operational receipts remain in the
restricted evidence store; this document contains no raw logs, chat identifiers,
credentials, protected configuration or business originals.

## Actual employee-side journey (2026-09-24 UTC)

All requests used the existing Feishu desktop client and natural language, without
Skill names, commands, internal IDs or supplied numeric answers. Returned files
were actually opened in the client, not inferred from delivery receipts alone.

| Time | Observation | Result |
| --- | --- | --- |
| 12:43 | Sales created 韩周婚宴: 22 tables / 220 people, A/basic decor, budget 110000. Shared revision 1 retained proposed/unverified states. | Word and budget Excel opened: Wiki v2 price 4080/table; complete total **103720**, budget remainder 6280; photography excluded explicitly. |
| 12:51 | Operations started a new work using only 韩周婚宴's natural name. Host imported two accepted same-group snapshots into that account's own work. | Execution Excel opened: 22/220, complete **103720**, welcome 12:00/start 12:30, date and contract pending. No forwarding or private-history access. |
| 12:52 | Sales privately considered welcome 11:30 and a separate private-only note, explicitly without sharing. | No case tool call; shared record and operations file stayed at 12:00; private-only note absent from shared content. |
| 12:57 | Sales changed to 23 tables / 230 people, retaining other conditions. | Revision 3; budget v2 opened: **107980** = 93840 + 2000 + 3000 + 5000 + 4140, remainder 2020. Optional LED separate; old files retained. |
| 13:01 | Fresh operations work read revision 3 and four imported artifacts. | Correct 23/230 and stale-file labels, but incorrectly reported missing complete cost without opening the imported budget. **FAIL**, fixed by PR76; see retest below. |
| 13:07 | Sales explicitly shared only welcome 11:30 as a pending proposal. | Revision 4 changed that field only; private-only note absent. Private entry could read the case but could not import group-only artifacts. |
| 13:10 | Sales created separate 顾唐婚宴: 16/160, budget 80000, provisional B/basic decor, date pending. | Separate record; no files or formal action. Bot calculated 86160 and flagged 6160 over budget; 韩周 remained separate. |
| 13:18–13:20 | After PR76's Skill update, operations repeated the natural cost/status question in a fresh work without file-reading hints. | Trace shows `case-read` revision 4, four imported artifacts and two actual spreadsheet reads. Reply correctly gives **107980**, 23/230, welcome **11:30 pending**, start 12:30; identifies all older file bases and the budget v2's obsolete 12:00 time. No new file or case update. **PASS**. |
| 13:21–13:23 | In the same work, operations reported an unverified recollection of 24 tables and asked to record the discrepancy without executing it. | Claude routed through CRM/customer and Wiki checks, skipped the shared-case protocol and incorrectly claimed no case record. No shared update. **FAIL**, requiring project-level routing repair in PR77. |
| 13:37–13:38 | After PR77, the same conversation continued naturally. | Shared protocol read and actual `case-read` revision 4 restored the 23-table basis and differentiated the venue's 24-table capacity. Routing retest **PASS**; no conflict save claimed. |
| 13:40 | The original explicit request to record an unverified 24-table discrepancy was repeated. | Correct record read, but reply said it was tentatively noted without any `case-update`. Persistence **FAIL**; PR78 clarifies saving an authorized new unverified report before clarification. |
| 14:01 | After PR78 and its read-only installation reconciliation, the same original natural request was repeated. | Actual `case-read` revision 4 followed by `case-update` **recorded**, revision 5. Read-only store assertions verify original 23 tables retained as a conflict with a 24-table unverified alternative and distinct sources. Other facts stayed unchanged; no files or execution arrangement created. Reply truthfully reported the saved discrepancy and requested clarification. **PASS**. |
| 14:08 | Operations started another work and asked only for 顾唐婚宴's progress by name, without a file reference. | Actual `case-read` revision 1, zero artifacts/imports and no update. Reply correctly gives 16 tables / 160 people, provisional B/basic decor, budget 80000 and date pending. No 韩周 conditions, conflict or files entered this work. **PASS**. |

The scoped two-account fictional collaboration journey passes after the recorded
fixes and affected retests. This does not erase the earlier failures or establish
universal model reliability. The intentional 23/24-table conflict remains pending
clarification; no operator edited the database to make the result pass.
This evidence-only change does not rebuild or reinstall runtime: the tested source
combination and candidate above remain the deployed basis.

### Opened artifact hashes

| Actual delivered artifact | Case basis | SHA256 |
| --- | --- | --- |
| 韩周婚宴_销售方案_v1.docx | 1 | `5ac523661decf2575fb87474cccf7a3061fa4267b6275799045deba3ef290892` |
| 韩周婚宴_预算交接表_v1.xlsx | 1 | `9066f89a1deac203f9e1d98b54b1d4a53ee76a85ee75e5d26f40b58ee14ce092` |
| 韩周婚宴_执行交接表_v1.xlsx | 2 | `b0b59215d8713bd0748ef03c2f017e3be798267dacb3b7df53e6e33810859b00` |
| 韩周婚宴_预算交接表_v2.xlsx | 3 | `4faa69212ec5a743169b67fafe89326ab92431b4125c0dcf586053bb36c0b41d` |

After the time-only update to revision 4, all four files remain available with
older-basis markers. Recording progress does not silently revise those files.

## Preserved failures and verification limits

- Initial maintenance stopped the receiver, then a historical helper rejected the
  inactive unit's empty ControlGroup before any file/database write. A separately
  reviewed continuation checked the stopped process state and frozen baseline,
  completed installation and started once; stable health passed for 130 seconds.
  The original failure, helper and backups were retained, not overwritten.
- First live case 林陈婚宴 failed literal-source validation; a single-field probe
  consumed the message. Correct files did not make its incomplete shared record
  pass. PR74 adds actionable feedback and whole-batch retry guidance.
- Second live case 沈许婚宴 failed on duplicate customer-needs fields; no revision
  was stored. PR75 explains the exact duplicate/state/source failure while keeping
  the batch atomic. Both failed cases and artifacts remain, without database repair.
- The fee-read omission above is a separate real failure. PR76 changes four Skill
  lines; import success alone is not evidence of actual document reading.
- The subsequent conversation-routing omission is also preserved. Loading the
  banquet Skill did not itself ensure the shared protocol was read. PR77 replaces
  three project-guide lines with four to prioritize that protocol on follow-ups.
  Its first CI failed the existing policy-length ceiling; the text was shortened
  to 199 lines without weakening the check. The rejected attempt remains visible.
- Correct conflict discussion still did not guarantee persistence: the 13:40
  response only noted the discrepancy in chat. PR78 distinguishes saving a new
  authorized unverified report from merely reading an existing conflict. It uses
  the existing atomic update and receipt, without adding another workflow layer.
- PR78's three-file update reached its final check, which failed because the
  journal changed. All three candidate bytes and metadata matched their receipts;
  service, activity, business-store and session snapshots were unchanged. The old
  journal prefix matched exactly, with one new unsolicited-event notice from the
  test entry. Its underlying event type was not recorded. Installation was not
  retried and the failure receipt remains. The scoped read-only reconciliation
  above passed. This is not a retroactive pass of the original check, proof of
  the notification's cause, or proof that it had no unobserved platform effects.
- Targeted offline tests cover duplicate/retry, concurrent CAS, save failure,
  denial/hypothesis/forged permission, ambiguous cases, queue/recovery source
  persistence, cross-account import, unknown receipts and late stale delivery.
  Unknown-send and recovery faults were not induced by restarting live service.
- New capability remains default-off outside explicitly configured test entries.
  No department lookup, automatic colleague notification, automatic file rebuild,
  production contract/collection/booking write, or customer communication was added.
- Some model replies still expose technical status labels such as `revision` or
  `proposed`. Plain-language consistency is a remaining presentation limitation;
  the scoped business/state checks above do not claim that all wording is polished.

Rollback disables the added shared-case entrances and restores the prior runtime
under the normal maintenance gate. Preserve mock-case history, delivery receipts,
old artifacts and published Wiki; do not roll business records back.
