# Knowledge catalog candidate — recorded September 11, 2026

## Scope and source baseline

This is a candidate-development record, not an online deployment receipt.
Clean worktrees started from live main:

| Repository | Base |
| --- | --- |
| myanc-crm | c736bfac52b07482c8f6586898a5820d247ee01a |
| cc-connect-anc | 148a2fe51ec3553d52aed4277d5b14518739c7ea |
| myanc-team-brain | 0d75a2d4dcfc0fb45717e308ca6e6edfea8d240b |

The user observed a generic meeting-preparation query miss, followed by a
successful exact-title answer and an accessible source link. That establishes
the symptom and the working read path; it does not prove a Feishu platform bug or
that the entire knowledge space lacked the requested information.

The candidate adds read-only catalog lookup over the existing published registry,
then explicit source reading. Feishu stays canonical. No knowledge-body cache,
new database/schema, search service, vector store, scope, credential, or customer
record change. Native search remains for customer/detail queries. The client,
gateway command maps and skill/protocol must travel as one version set.

## Verification and pending gates

- Knowledge Python suite: 62 tests, two POSIX-only checks skipped on local Windows;
  the four required knowledge CI matrix jobs remain the cross-platform gate.
- CRM Python suite: 246 tests, six platform/integration skips; spike suite: 17 tests.
- Added real Engine/HTTP/Python Brain/SQLite catalog-read-follow-up-scope journey
  passed locally with the explicit knowledge checkout. Model intentions and
  Feishu I/O were synthetic; this is not real-model or colleague acceptance.
- Three-domain command dispatch regression failed before the allowlist fix and
  passed afterward. An existing cross-repo fixture selected the Windows Python
  Store alias; it now follows the existing platform-specific executable pattern.
- Full local Go suite was attempted and is not a pass: existing Unix path,
  shell, PTY and filesystem-permission assumptions fail on Windows. Do not weaken
  or relabel those checks; require the unchanged full Linux GitHub workflow.
- Web resources were rebuilt with the frozen lockfile; bundle-size/Browserslist
  notices are informational, not a dependency-upgrade task in this change.
- Release tests cover exact four-job knowledge CI, explicit two/three source maps,
  three-source incident closure, required non-skipped knowledge CUJ, fresh exports,
  runtime/skill/template hashes, and removal of ambient live-model flags.
- The `knowledge-catalog` real-model case covers a question without a document
  title, a source-preserving follow-up and quoted-command rejection. Execution and
  semantic review evidence must be recorded separately; test existence is not pass.

GitHub delivery and candidate completion remain **incomplete** until each exact
reviewed PR head is merged, its precise main push CI passes, and the supported
builder records all three merge SHAs and product hashes. Preserve external
SHA-bound independent Spec/Standards evidence; it is not GitHub human approval.
The generated candidate manifest and handoff reference those immutable results,
without rebuilding just to embed a package's own digest into its source.

## Maintenance and colleague trial

Online acceptance is **incomplete**. No production change, restart, permission
change, selected-source ingestion, or business-ledger migration is authorized by
this record. Follow [the shared release contract](../RELEASE.md) and obtain a
separate maintenance window. Reconcile actual host-wrapper/runtime/client/skill
hashes and historical compatibility patches before replacing anything. Preserve
the existing journal; never rerun installation/bootstrap to upgrade.

After deployment, Owner/test should ask naturally, without supplied document
titles, then follow up and open sources. Do not reuse the previous exact-title
success as acceptance of this generic-query fix. Wang's waiver remains a waiver.

## Explicitly deferred

Miaoji transcripts: later use only individually selected, shareable material to
draft a filtered team version, compare existing sources, and obtain approval.
Keep raw recordings/transcripts at their original permissions. No automatic
Miaoji acquisition, chat scan, full-transcript import, CRM/reminder writes or new
permissions in this candidate; link-based Miaoji ingestion remains unverified.
Original dirty worktrees, runtime upgrades and unrelated historical cleanup remain
outside this release.
