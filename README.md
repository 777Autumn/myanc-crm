# myanc-crm

One deliberately small CRM workflow for the existing Claude Code → cc-connect →
Feishu gateway:

1. resolve exactly one customer;
2. stage a read-only follow-up preview;
3. let the existing Feishu conversation collect approval;
4. apply that exact preview once; and
5. read the Base again and return a verified receipt.

This repository is not a general CRM, a generic Base wrapper, or a production
deployment system. The sandbox contains only `客户` and `跟进记录`. No credential or
real identifier belongs in Git.

## Bootstrap the sandbox

An administrator runs `ops/bootstrap_base.py` once. It creates `ANC CRM Sandbox`,
the two fixed tables, and three fictional customers (one unique name and two rows
with the same name).

The script requires one absolute `lark-cli` executable, one enterprise profile,
and the absolute production wrapper path. It verifies that the profile has both a
user and bot identity for the same application. The user identity is used only to
search Drive for an existing Base with the same title; every create and write uses
the bot identity. It never starts an interactive login.

Set the cc-connect sender ID for the owner without putting it on the command line:

```powershell
$env:MYANC_CRM_OWNER_SENDER_ID = '<owner-sender-id>'
```

Inspect the plan first; a dry run makes no Feishu request and writes no file:

```powershell
python ops/bootstrap_base.py `
  --lark-cli 'C:\absolute\path\to\lark-cli.exe' `
  --profile '<enterprise-profile>' `
  --wrapper-path 'C:\absolute\path\to\lark-enterprise.ps1' `
  --dry-run
```

Then run the same command without `--dry-run`. The script verifies every created
schema and fixture before continuing. It writes tokens, table IDs, immutable field
IDs, the owner mapping, and a bot/user identity summary only to the gitignored
`config.local.json`; none of those values are printed. Do not share that file.

If a step fails, the script stops and does not automatically delete the Base.
`config.local.json` records the latest successful checkpoint after Base creation.
Inspect the retained resources before deciding whether to resume manually or
delete them. Fixtures intentionally leave `负责人` empty because user-cell writes
vary across supported CLI builds; normal follow-ups still record the approved
actor as `跟进人`.

## Stage

The command boundary is one JSON object on stdin and one JSON object on stdout.
Neither command accepts profile, identity, Base, table, or field overrides.

```powershell
@'
{
  "actor": {
    "sender_id": "<cc-connect-sender-id>",
    "chat_id": "<cc-connect-chat-id>"
  },
  "customer_query": "演示客户·青岚科技（唯一）",
  "followup": {
    "occurred_at": "2026-09-03T14:30:00+08:00",
    "channel": "电话",
    "content": "确认了测试需求。",
    "next_action": "发送虚构方案。",
    "next_followup_at": "2026-09-05T10:00:00+08:00"
  }
}
'@ | python -m myanc_crm stage
```

`stage` reads Feishu and the local ledger but never writes Feishu. A successful
response has `status: "staged"`, a short-lived `change_id`, the selected customer,
the proposed follow-up, the exact customer-field changes, and the untouched
fields. Other expected results are `needs_time`, `not_found`, `needs_selection`,
or `blocked`. If `next_action` or `next_followup_at` is omitted, that customer
field is deliberately left unchanged rather than guessed or cleared.

## Approve, then apply

Present the full staged effects to the sender. Use the gateway's existing private
`AskUserQuestion` flow or its same-sender group approval flow. Only an explicit
approval should pass the returned `change_id` to `apply`:

```powershell
@'
{
  "actor": {
    "sender_id": "<same-cc-connect-sender-id>",
    "chat_id": "<same-cc-connect-chat-id>"
  },
  "change_id": "<staged-change-id>"
}
'@ | python -m myanc_crm apply
```

This approval is a cooperative soft gate, not a tamper-proof host authorization
boundary. `apply` still requires the same configured sender and chat, rechecks the
schema and customer snapshot, writes once, and polls read-only verification for up
to 30 seconds after each write. It never repeats a write inside that apply attempt.
If the preview expired or data drifted, stage a new plan instead of reusing it.

Only `status: "verified"` is success. `replan_required`, `partial`,
`verification_unknown`, and `failed` require inspection or a new plan. Replaying a
finished `change_id` returns its saved receipt and does not create a second
follow-up.

## Deployment boundary

Deploy only the five files in `myanc_crm/`; no package installation or extra
service is required. Production selects `/etc/myanc-crm/config.json` directly and
does not accept an environment-variable override. The code, launcher, and
configuration must be owned by `root` and read-only to the service account. Grant
that account only the configuration read access it needs. Its writable state
directory must have mode `0700`, and the SQLite ledger must have mode `0600`.

The deployment runbook must also schedule receipt cleanup. Retain terminal
receipts (`verified`, `replan_required`, `verification_unknown`, and `failed`) for
30 days so retries remain idempotent and incidents can be inspected; retain
`expired` and `superseded` changes for 7 days. Never automatically delete
`partial` or `applying` changes: resolve them first. Run cleanup under the service
identity in a single SQLite transaction after a protected backup, and record the
deleted counts without logging CRM payloads.

## Develop and test

Copy `config.example.json` only when you need to understand the local shape; never
replace its placeholders with real values in a tracked file.

```powershell
python -m compileall -q myanc_crm ops tests
python -m unittest discover -s tests -v
```

CI validates the template, compiles the standard-library-only code, exercises the
offline bootstrap plan, runs the tests, and rejects common credential-shaped
values. It does not deploy, mutate Feishu, or clean up the sandbox. The test Base
is retained until an administrator explicitly deletes it after inspection.
