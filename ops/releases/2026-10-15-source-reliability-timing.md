# Source readback and query timing

A saved source note previously omitted a visible page date. A separate Excel
read failed on a mistyped path, refreshed the host context, and stopped without
reading the corrected file. Preserve both failures when validating this change.

File reading now uses quotes before inferred ledger fields, followed by actual
saved-note readback against page images, including headers and footers. The
registered Excel reader resolves an exact current input ID through the existing
file Host, checks its immutable bytes through the existing Office validator, and
returns bounded rows with coordinates, formulas and saved caches. Resolving a
path alone never completes a read. Missing caches, uninspected rows and unreadable
source fields stay unknown. No business write or delivery command was added.

A specific banquet read can reuse the complete record returned by its own scoped
number lookup. This removes one duplicate Base call; staging, approval and other
write-sensitive callers still recheck the resolved record. Personal authorization
and version checks remain in place. Current business reads are never cached
across user turns.

Host-only timing reports count and elapsed intervals for connection CLI calls,
resource CLI calls, connection database setup and connection lock acquisition.
The companion gateway adds request stages, queue wait and final response handler
timing. Metrics do not contain arguments, identities, document text or error
messages, and do not change the stdout business protocol. CLI intervals include
startup and networking; database setup includes schema and commit work. These
are not pure network, all SQL, model inference or end-user delivery durations.
Nested intervals must not be summed as independent work.

Validation uses real workbook bytes and the public reader entry point with only
external Host/process boundaries substituted. It covers the failed path followed
by actual reading, hash/identity/scope rejection, permission failure, pagination,
formula cache uncertainty and bounded output. Native Mac CI runs the same reader
tests. The decision diagnostic adds ledger-readback and Excel-retry cases, but
does not execute tools or prove visual understanding.

Production source accuracy, saved notes, installed file permissions and timing
breakdowns require the subsequent controlled Mac/Feishu acceptance. Local model
execution or a correct draft alone is insufficient. No Docling or EvoOntology
integration, database migration or document dependency change is included.
