# Gemma GPU canary — 2026-11-10

The user approved the prepared bounded GPU canary. The dedicated service was
installed, verified with `systemd-analyze --user verify`, started once, exercised
with one synthetic JSON request and stopped. It remains a static, inactive unit;
it was not enabled as a persistent model daemon. Port 8791 has no listener after
the test. The existing extraction worker runtime, queue and timer were unchanged.
Its timer remains active and its last service result is success/exit 0.

[Raw runtime receipt](runs/gemma-gpu-canary-20261110.json) and
[source/schema validation](runs/gemma-gpu-canary-validation-20261110.json) retain
the response, usage/timings, slot properties, sampled device memory and journal.
Run receipts retain exact bytes in Git so their recorded digests survive Windows
checkout conversions.

| Check | Observed result |
| --- | --- |
| Model | Official Gemma E4B QAT Q4_0, pinned weight SHA `676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee` |
| Runtime | llama.cpp b12259 / commit `351025ec5`, CUDA 12.8 distribution |
| Startup | Server log reports model loaded about 59.83 seconds after process initialization |
| Slot | One slot, `n_ctx=16384` reported by live `/slots` |
| Input/output | 168 prompt tokens / 57 completion tokens; finish reason `stop` |
| Request wall time | 39.1888 seconds, one cold synthetic request |
| Server prompt processing | 37.6275 seconds; 4.4648 tokens/second |
| Server token decoding | 1.5330 seconds; 36.5294 tokens/second |
| Device memory | 101 MiB baseline; sampled high of 3,200 MiB; 101 MiB after stop |
| Cleanup | Inactive/dead, exit 0, no port listener; extraction timer active |

The result selected word index 2 from `Ours`, `PSNR`, `32.15`, `dB`. The existing
schema/source-word validator reconstructs exact value `32.15` at the expected
synthetic box and leaves review_required=true. All contextual fields were empty.
This passes the synthetic value smoke test; it does not establish correct table
row/column/unit extraction or a successful paper-level pilot.

GPU allocation and utilization show GPU participation. The default-verbosity log
does not prove that every requested layer or attention operation was offloaded;
full-layer offload verification remains false. The configured 16K slot is proven,
but only a 168-token prompt was exercised. Device memory is sampled total GPU
usage, including baseline, rather than a continuously measured peak. The cgroup
MemoryPeak in the raw receipt is not a process RSS or total physical-model-memory
measurement. Startup tokenizer/control-token warnings are retained in the journal.

The cold prompt cost dominates this sample, so decode speed alone would misstate
latency. No warm/long-context benchmark, actual table accuracy result, Qwen
comparison or superiority conclusion is claimed. No further inference was run
after the authorized single request.

## Adapter follow-up

The worker's opt-in model configuration now explicitly defaults
`enable_thinking=false` and sends it as a chat-template argument, matching the
verified canary request. Changing that setting changes the fenced job identity.
A captured-response fixture verifies the real Gemma JSON remains consumable,
source-grounded and unreviewed. This updated adapter has not been installed into
the active remote extraction runtime. Focused adapter/evaluator/runner checks pass.

Next acceptance remains a source-reviewed real-table pilot, warm latency/VRAM
measurement, fuller offload diagnostics and headless model-service recovery.
The earlier broader Phase 2/3 requirements remain open. Canonical catalog metadata
is unchanged; no push or deployment occurred.

Final validation: all 434 tests passed in 121.92 seconds. Global Ruff lint and
formatting (146 files) pass. The canary receipt's exact indexed Git bytes match
the SHA-256 recorded by its independent source/schema validation receipt.
