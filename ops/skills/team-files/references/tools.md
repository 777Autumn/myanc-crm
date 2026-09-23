## Controlled file tools: FILE_HOST_TOOLS_V1

The installed `/usr/local/bin/cc-connect-file` accepts one command and one stdin
JSON object. The host supplies its temporary session token and the fixed, narrow
action-tools transport. These are separate from the management API. Callers never
supply a principal, project, recipient, source root, socket, token or endpoint.
Keep commands and local paths internal; employees work entirely in Feishu.

| Command | Input | Result |
|---|---|---|
| `work-context` | `{}` | `enabled`, `work_id`, selected `inputs` (`id/name/path/sha256`), `output_dir`, `latest_version`, `artifacts` |
| `file-deliver` | `work_id`, `path`, `sha256`, `expected_version` | `delivery_id`, `version`, `status`, name/path/hash and optional `message_receipt` |
| `file-status` | `work_id`, `delivery_id` | The persisted delivery state/receipt for that work |

```sh
printf '%s' '{}' | /usr/local/bin/cc-connect-file work-context
```

A successful current `work-context` with `enabled: true` establishes availability.
The presence of this skill or executable does not. Disabled, missing or failed
context leaves delivery unavailable; use no substitute transport. Ordinary safe
preparation remains available within the existing workspace permissions.

`work-context` has no create/switch argument. The trusted message/session binding
chooses the work; an ID alone grants no access. Reuse the returned work ID. The
receiver stays bound to this work's original private chat, group or thread even
when another colleague speaks. An inaccessible old work requires clarification,
not a guessed path or a different recipient.

Read each selected input from its returned path. A missing original is a real
input gap: request that file again rather than reconstructing it from memory.
Retain original documents and images; extracted Markdown/text is a working aid. Material
selected for this work is not authorization to publish a knowledge proposal.

For delivery, `path` is relative to the returned `output_dir`; absolute paths,
parent traversal and links are rejected. Read `latest_version` in this turn and
send it as `expected_version`; `sha256` is the lowercase SHA-256 of the saved file
bytes. Use a new filename for revisions and preserve earlier outputs. The host
checks scope, ownership, file format, size and hash, freezes bytes, claims a new
version and sends only that snapshot. A version conflict requires reading current
context and identifying the intended artifact before making another request.

For a revision, read the chosen artifact's relative `path` under `output_dir` and
verify its `sha256` before editing. Missing or changed bytes require locating the
matching file or requesting it again; memory does not establish the prior version.
The host's immutable snapshots remain private and are not a model file browser.

File limits: up to 4 selected input files, 20 MiB each and 40 MiB per
batch; each output is at most 20 MiB, with at most 100 MiB expanded OOXML content.
DOCX/XLSX remain available under the original configuration. The separately
enabled proposal formats add PPTX, PDF, PNG and JPEG, including directly posted
Feishu pictures saved as current work inputs. PNG/JPEG are limited to 25 million
pixels; PDF is limited to 200 pages and rejects encryption, scripts, attachments,
forms and external actions. PPTX supports editable text/shapes/tables and embedded
PNG/JPEG; charts with embedded workbooks and audio/video are unsupported.
Macros, embedded active objects, external relationships (including external
hyperlinks), and active external/DDE formulas are rejected. With proposal formats
enabled, Word fields are limited to PAGE, NUMPAGES, TOC and internal PAGEREF with
supported switches; other fields are rejected. Headers/footers and tables remain
supported. XLSX formulas such as SUM remain supported without external references.
Report the specific unsupported content and request a static source
or a separately prepared compatible file. Do not silently strip fields, remove
content or change the format.

A `file-deliver` preflight rejection returns HTTP 400 with `status: blocked` and
a specific `code`, such as `file_format_unsupported`, `file_work_scope_mismatch` or
`file_version_conflict`. This attempt did not send a file. Preserve the output
and resolve the reported cause; scope/version conflicts require fresh context
and identification of the intended work/artifact. HTTP 503 with
`status: unavailable`, `code: file_outcome_unconfirmed` may follow a send whose
receipt could not be persisted. Treat that outcome as unknown and recover status;
never rename the file or retry delivery to bypass it.
`file_delivery_requires_reconciliation` also blocks a new attempt while an earlier
delivery is uncertain; recover that earlier status, never bypass it with a new name.

Delivery states have different evidence:

- A file that was generated and locally checked is ready, not yet sent.
- `submitted`: the host recorded a send attempt; Feishu acceptance is unconfirmed.
- `accepted` with `message_receipt`: Feishu accepted the file message. Say the
  file was submitted to Feishu; employee receipt/opening still needs real feedback.
- `failed`: the transport established that no recipient-visible message was
  accepted. Preserve the generated file and report the failure.
- `unknown`: the request may have succeeded. Keep the delivery ID for an operator
  check; never resend, rename to bypass uncertainty, or repeat a business action.

After a timeout or missing response, neither success nor zero sends is proven.
Read `work-context` to recover persisted artifacts when the ID was not returned,
then `file-status` for the matching delivery. Identical requests replay the stored
result; they do not send again. Pending/unknown delivery prevents another version
from hiding the uncertain attempt. A service restart preserves unknown outcomes.
Employee receipt, ability to open, content correctness and actual waiting time
are separate acceptance observations, not facts inferred from an API receipt.
