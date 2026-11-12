# Gemma RadSplat real-page diagnostic — 2026-11-11

The user approved the prepared bounded pilot. One real-page request completed,
but its source-word selections were invalid. The harness rejected the response,
omitted the warm repeat under the stop-on-failure rule, and stopped the dedicated
service. Independent SSH checks confirm inactive/dead, exit 0, static/not enabled,
no listener on port 8791, and the existing extraction timer active with its last
service result success/exit 0. The default worker was unchanged.

[Raw receipt](runs/gemma-radsplat-real-page-20261111.json) and
[independent worker validation](runs/gemma-radsplat-real-page-validation-20261111.json)
retain the input/response hashes, timings, tokenization, GPU samples, rejection
and cleanup evidence. Remote model, PDF and payload checksums matched the prepared
pins before startup. Executed harness and installed unit hashes also match the
local reviewed files.

| Observation | Result |
| --- | --- |
| Input | RadSplat physical page 6, all 498 source words, unchanged prepared request |
| Context | One 16K slot; 8,278 preflight and actual prompt tokens, exact count agreement |
| Prompt cache | Zero cached tokens for this request |
| Readiness | 3.095 seconds in this fresh service run |
| Request wall time | 12.541 seconds |
| Server prompt processing | 4.973 seconds; 1,664.68 tokens/second |
| Server decoding | 404 tokens, 7.546 seconds; 53.40 tokens/second |
| Finish reason | `stop` |
| Returned selections | One cell, selecting source word 0 (`0.25`) |
| GPU total usage | Sampled maximum 3,212 MiB; 101 MiB after stop |
| Entire client run | 15.941 seconds including startup and cleanup |

The metric field repeated and reordered indices; the unit field repeated index
0 ten times. All indices were in range, but they violated the required unique,
reading-order selections. The actual worker's `PageSelections` parser plus
`candidates_from_selection` independently reproduces the rejection. A captured
response fixture now guards this boundary; focused adapter/evaluator checks pass
(28 tests). Invalid output was not silently sorted or deduplicated into an
accepted result.

There are **zero valid extraction results and zero accepted/published predictions**
from this diagnostic. The four accepted reference cells are not scored against
an invalid generation. The existing six-paper/22-cell reviewed ledger is intact.
The prior representability audit also remains relevant: only six of 24 editorial
context fields are exactly selectable from whole page words. This one-page result
measures the current model/prompt/index contract, not population table accuracy
or Gemma-versus-Qwen superiority.

The first generation had an uncached prompt, but the model file had just been read
for checksum verification; readiness is not a disk-cold startup benchmark. The
request exercised about half the configured context, not the full 16K limit.
GPU participation is observed; available journal output contains no layer-offload
messages, so full-layer offload remains unproven. No warm-generation latency or
persistent-daemon recovery result is claimed.

The next design step is offline improvement of table/layout grounding and the
selection contract before another approved inference run. The optional Gemma
backend remains a diagnostic path. No further inference, worker replacement,
canonical import, figure publication, push or deployment occurred.
