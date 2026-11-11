# Prepared RadSplat real-page Gemma pilot — 2026-11-11

Status: prepared locally; no additional inference or service startup authorized or executed.

The approved synthetic canary completed and stopped. This follow-up reuses the
already staged weights/runtime and already transferred RadSplat PDF. It proposes
one bounded service run and at most two identical requests for physical page 6:
first request after startup, then a warm repeat if time remains. No download,
worker replacement, queue change, publication or persistent daemon is included.

## Exact input and scoring

`scripts/worker/gemma-radsplat-page6-request.json` was captured directly from the
current `parse_page` adapter using all 498 pdfplumber source words on page 6.
The preparation receipt binds its exact bytes, PDF SHA and reviewed ledger SHA.
It contains no accepted answers, reference labels or reviewer annotations. This
is a fixed-page diagnostic, not a test of automatic page selection: page 6 was
chosen because it has four accepted cells, all of RadSplat's current references.

The current adapter sends indices and text without layout coordinates. That
limitation is deliberately retained for this baseline. Response fields select
source words only; boxes must be reconstructed locally and all predictions
remain unreviewed. Compare each completed repetition separately with the four
accepted cells using the existing evaluator: exact values, row/column labels,
dataset, split, metric and unit. Report other predictions as outside the reviewed
subset, not false positives. The ledger is prior agent source inspection, not an
independent human benchmark. This one-paper diagnostic cannot establish model
superiority or corpus-level accuracy.

## Proposed execution bound

The prepared `papers-llama-table-pilot.service` copies the successful canary's
loopback 127.0.0.1:8791, one slot, 16K context, 10 GiB RAM and 300% CPU limits;
only the description and RuntimeMaxSec change (35 minutes). It is a separate
static unit, never enabled. The existing extraction timer/runtime stay unchanged.

Before generation, check live model alias, slot context and `/tokenize` for the
exact rendered prompt using the server's chat-template endpoint. Refuse a prompt
that cannot fit with 2,048 output tokens and a 256-token safety allowance. Capture
the template/tokenization receipts rather than estimating tokens from bytes.
At most two generation POSTs are permitted, with 900-second request timeouts and
an overall 32-minute client deadline. Do not retry failed or truncated requests.
The server's 35-minute RuntimeMax remains an independent outer bound. A warm
repeat may be omitted if the first request consumes the remaining deadline.
The harness transport timeout is distinct from the worker's existing 30-second
configuration, which is not changed by this diagnostic.

Record startup, both request timings/usage/finish reasons, schema validation,
GPU memory/utilization samples and journal offload messages. Stop the unit in a
finally/cleanup path, verify no listener remains, and check extraction timer
health. Timeout, context rejection or failed validation is a diagnostic result;
it must not silently trigger another model, context reduction or cropped input.

Execution requires approval beyond the completed single-synthetic-request canary.
