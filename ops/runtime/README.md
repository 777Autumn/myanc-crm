# Runtime templates

These selected templates were backfilled from the existing local operations
assets on 2026-09-09. They are inputs for a separately authorized maintenance
workflow, not an installer. The base service and partner drop-in are used
together; production identity mapping, auth, config and ledgers remain external.

The guard tests use synthetic commands/paths. `test_partner_boundary.py` needs
Linux root only to exercise temporary numeric UIDs; it creates no user accounts
or services and must never be repurposed as a production fault injector.

Historical one-time deployment/recovery scripts remain outside this repository.
Their fixed PID assumptions and maintenance context make them **non-reusable**.
The supported future candidate entrance is described in [../RELEASE.md](../RELEASE.md).
