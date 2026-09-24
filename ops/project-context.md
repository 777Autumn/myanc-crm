# Mock project context — implementation contract

This opt-in pairs the CRM and gateway changes. It keeps the existing Bot,
ordinary identities, native workspaces, company Wiki, SQLite, file snapshots and
receipts. It does not enable production CRM permissions or import platform code.
Follow [RELEASE.md](RELEASE.md); a draft PR is not an installable release.

## Trusted project policy

The existing `shared_cases` config may contain this fictional example:

```json
"project_context": {
  "enabled": true,
  "group_case": "林陈婚宴",
  "managers": []
}
```

Use a fresh `mock-project-` namespace in the same protected TEST store. Existing
namespaces and files stay intact. Omission or `{"enabled": false}` preserves
legacy behavior. Registered entries still require the exact transport account,
chat and workspace, and an existing `allowed_actors` entry. Display names are
looked up from that protected configuration, never supplied as new identities.

The creator becomes the project owner. The configured group project's frozen
group audience is pre-authorized to read; a private-only second project initially
belongs only to its creator. A group cannot display another project's records.
An owner's invitation gives a registered colleague a responsibility without
transferring ownership. A business fact named “负责人” is not an access grant.
There is no removal, ownership-transfer or rename operation in this increment.

Existing `case-list/read/update` retain their payloads. `case-member-add` accepts
`case_name`, `expected_revision`, `member_name`, `responsibility` and optionally
the original `source_message_id`. The owner or configured manager must explicitly
request the named colleague's participation in the authorized original message;
ambiguous names, quoted instructions and hypothetical invitations fail closed.
This mock rollout accepts only the documented sales/operations duty phrases,
so a model-supplied responsibility cannot absorb a quoted or negated suffix.
The gateway persists the complete `original_text` separately from a selected
sharing paragraph. Member grants require that complete text; older queued sources
without it are refused. Business updates still use only the selected paragraph.
Member changes reuse the same atomic version history, separately deduplicated
from business changes in the same incoming message.

`case-access` is host-only: receipt lookup, project permission and target-work
binding must all succeed before a shared snapshot can enter a private work.
The agent client cannot call it or provide identities. Explicit references and
automatic imports must share this check; group-only legacy access is not a grant
to cross chats. Sending stays bound to the original work conversation.

## Context and acceptance

Company facts come from the published Wiki; sales/operations methods from the
department references; current progress from the selected project; personal
conversation stays private. A private project read is not permission to publish.
Only explicitly selected private business facts may be synchronized. Private
files are not automatically published or sent to the project group.

Acceptance must cover the two existing accounts in group and private entries,
actual opened group snapshots imported into the correct private project, a
private unsynchronized discussion, explicit fact synchronization, 22/23-table
totals of 103720/107980 using Wiki v2, and refusal of a private second project to
a nonmember. Additional manager/forgery/failure cases use fictional offline data.
No upstream tests or live journey have been executed merely by adding this doc.

## Reference decisions

- Cloudflare OS `1e8b190977efec5c6174c1bf3da6da85e8561b99`: bounded catalogs,
  on-demand bodies and authorization at read boundaries. Its TypeScript/Workers
  implementation is not imported. Root LICENSE is Apache-2.0.
- Multica `1c908ea52c19f193d301ca9460fc1d7d100a1b3d`: workspace/project/task context
  separation and retaining the original human actor. No source/package is copied;
  its Multica License includes conditions beyond Apache-2.0.
- Neither reference supplies our department/project member model. The reviewed
  upstream tests were read, not executed. Reuse our existing transport and stores.

Deployment is incomplete until exact-head AI reviews, existing CI, merge-SHA CI,
the normal paired candidate, scoped maintenance and actual acceptance are recorded.
