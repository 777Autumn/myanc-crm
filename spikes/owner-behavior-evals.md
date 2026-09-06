# Owner behavior regression fixtures

This is an opt-in extension of the existing Go real-Claude CUJ, not a new
runtime, live Feishu test or automatic semantic judge. Python standard-library
fixtures replace Feishu/config only; Engine, native Claude, HTTP proxy, host
identity, CLI and SQLite remain real. Upstream Commerce Skills stay unchanged.

## Six cases, three trials each

| Pair | Case | Code gate | Semantic review |
|---|---|---|---|
| Terms | `term-ambiguous` | Fresh customer read; no stage/write | Canary is undefined in the seed: clarification or conditional suggestions, not invented customer requirements |
| Terms | `term-defined` | Fresh customer read; no stage/write | Serve the explicit 5% rollout/error-rate/rollback request without asking for its definition again |
| Reads | `result-only` | Verified original `result`; no stage or unnecessary customer refresh | Distinguish stored receipt from a fresh current-state claim |
| Reads | `current-state-advice` | Original `result`, then fresh `customer`; no stage/write | Account for the later manual next-action edit rather than copying the receipt's old value |
| Intent | `advice-only` | Customer read; no card/write | Offer useful advice without presenting it as a recorded follow-up |
| Intent | `record-request` | Exactly one pending card; exact supplied facts/time; optional date unchanged; no write | Brief card pointer, no duplicate full preview, second approval or false write claim |

The last two read cases seed their precondition by staging and approving one
fake follow-up through the real gateway callback; the harness then injects a
manual update into **fake-feishu.json only**. The graded user turn queries that
operation. The term pair differs only in its fake backend seed, not its prompt.
Each case must start with a fresh workspace and empty private host scratch so
definitions, stage IDs and approvals never leak from one trial to another.

## Native execution contract

Compile the existing `actionhost/crmfollowup` Go test binary for isolated Linux.
Use the existing private mount/PID namespace, non-root Claude account, read-only
auth mounts and fail-closed native sandbox setup. Do not expose real Feishu
configuration, start another receiver, disable production or run Claude as root.

Set these variables for **one case invocation**:

```text
MYANC_REAL_CLAUDE_CANARY=1
MYANC_REAL_CLAUDE_CASE=<one case from the table>
MYANC_REAL_CLAUDE_TRIAL=<1, 2 or 3>
MYANC_REAL_CLAUDE_POLICY=<absolute exact deployment CLAUDE.vps.md source>
MYANC_REAL_CLAUDE_SCRATCH=<existing empty host-private scratch directory>
MYANC_REAL_CLAUDE_WORKSPACE=<fresh isolated Claude-writable workspace>
MYANC_SPIKE_CRM_ROOT=<read-only fixture checkout>
MYANC_REAL_CLAUDE_BIN=<fixed Claude Code binary>
MYANC_REAL_CLAUDE_RUN_AS_USER=<isolated non-root runtime user>
MYANC_REAL_CLAUDE_MODEL=<explicit model pin used for all comparisons>
```

For a concurrent production receiver, additionally use test-only
`MYANC_REAL_CLAUDE_PORT=18745` and `MYANC_REAL_CLAUDE_CLIENT=<absolute root-owned
fixture client>`. That client is a scratch copy of `ops/crm_tool.py` with **only
the fixed port changed**. The isolated native sandbox must allow that port;
never change the production client or grant all-localhost access. A test-port
pass is not evidence for the separately checked production port 18743.

The test substitutes only workspace/client locations in the actual policy;
there is no second handcrafted behavioral policy for these cases. It saves the
source policy fingerprint, case/rubric/model/trial, observed tool arguments and
outputs, host execution count and final replies to
`<scratch>/behavior-evidence.json` with mode 0600. Opaque change/approval IDs are
redacted; process environment and Claude stderr are not captured.

```bash
./crmfollowup.test -test.run '^TestCUJ_CRMREAL1_ClaudeClarifiesApprovesAndDiscusses$' -test.v
```

Run all six cases three times, each invocation with its own scratch/workspace.
Keep failed artifacts and invocation exit status as well as successful ones.
Every result defaults to `semantic_review=pending`: a code-grader pass is **not**
semantic acceptance. Review the quoted synthetic transcript against the recorded
PASS/FAIL rubric; record verdict, reason and reviewer alongside it. A changed
policy, rubric or model invalidates comparisons to older semantic verdicts.
Do not replace this review with keyword matching or add a second judge model.

When `MYANC_REAL_CLAUDE_CASE` is absent, the existing full same-session native
CUJ remains available. Supplying `MYANC_REAL_CLAUDE_POLICY` also makes that CUJ
use the actual policy rather than the historical fixture-only description.

## Deterministic gates and limits

```bash
python3 -B -m unittest discover -s tests -v
python3 -B -m unittest discover -s spikes -p test_host_tool_fixture.py -v
MYANC_SPIKE_CRM_ROOT=/absolute/myanc-crm go test ./actionhost/crmfollowup -run TestCUJ_CRMIPC1 -count=1
```

Existing Python tests cover cancel/modify, expiry, schema/displayed-value drift,
principal/card mismatch, restart persistence, partial failure and repeat claims.
The cross-repo IPC CUJ now races eight gateway callback claims through separate
Python/SQLite connections, requires one winner, executes once and verifies the
same receipt on replay. The fake JSON backend remains serial: it does not claim
concurrent Feishu writer coverage.

Real Feishu cancellation/callback delivery, foreign-user clicks, card-in-place
refresh, non-CRM resources, attachments and production canary are separate live
acceptance steps. This fixture never certifies those from a fake-only pass.
