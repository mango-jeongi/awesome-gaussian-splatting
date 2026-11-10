# Gemma staging and comparison readiness — 2026-11-10

The user explicitly approved Gemma/runtime staging after the earlier Qwen proposal
was held for model review. The authorized staging operation completed on
`msi-raider` in `/home/mingu/.local/share/papers-llama/staging-gemma-b12259`.
The [remote staging receipt](runs/gemma-staging-20261110.json) matches the committed
Gemma pin manifest and records these verified downloads:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| CUDA 12.8 runtime archive | 594,371,481 | `745c840cfec4c46460cd2769dc3adba856a561e449de74113659798c18b56231` |
| llama.cpp b12259 CUDA archive | 188,342,236 | `7c25180a39ec72ed0acbe74e9d91e466cebf13b9995660b593fa7406bb42acc3` |
| Gemma E4B QAT Q4_0 weights | 5,154,941,280 | `676c35070db6dbe52f93e9c864ee0fba4eddea94b9c875d9cb10daff453fbaee` |

Both runtime archives were extracted only after size/hash verification. The model
is from the official Google repository revision
`4b4a2c1d584be7264f87aac328a1bc739ce81b6c`. The multimodal projector and Qwen
weights were not downloaded. These artifacts do not establish which model is best.

With the staged runtime library paths, `llama-server --version` exits successfully:
`0.9.0-dev`, build 12259, commit `351025ec5`, GNU 13.3.0, Linux x86_64. Its help
lists the planned context/parallel/GPU-layer/quantized-KV/FlashAttention flags.
This is binary/dependency verification, not a model load or CUDA offload test.
The existing extraction timer remained active and the GPU still reported
7,686 MiB free. No model service or inference request was started.

## Next reviewable canary

The prepared `scripts/worker/papers-llama-canary.service` binds only
`127.0.0.1:8791`, requests one slot and 16K context with q8_0 KV caches, and uses
an explicit model alias. It has no restart, a 15-minute runtime limit, a 10 GiB
RAM limit and 300% CPU quota. Port 8791 had no listener during preparation.
It is not installed or enabled. Its small companion request tests one synthetic
source-grounded numeric cell with JSON-schema output and thinking disabled.

Starting that GPU canary requires authorization beyond the staging-only approval.
If authorized, check health, logs, actual layer offload, peak VRAM and the response,
then stop the canary. Failure to fit or unsupported kernels must be reported;
do not claim the planning document's 16K/Turing performance assertions are proven.
The active extraction worker's runtime and timer must remain unchanged during it.

## Quality comparison harness

The optional `src.workers.evaluation` command now scores an explicitly selected
accepted numeric-cell subset, bound to paper and PDF hashes, with source-box/page
matching. It refuses ambiguous/duplicate coordinate matches and reports values
separately from row/column/dataset/split/metric/unit context. Unit case is preserved
so `mW` cannot receive credit for `MW`. Extra candidates outside the accepted
reference subset remain unscored; no population precision is reported.

The [baseline receipt](runs/extraction-reviewed-subset-baseline-20261110.json)
checks self-consistency of the earlier deterministic parser: 22 accepted reference
cells across six papers all match their reviewed values, while 729 additional
numeric candidates are outside this positive subset. Review labels were produced
by Codex's rendered-source inspection; this is not an independent human benchmark.
No local-model quality, latency or VRAM result is inferred from that baseline.
See [operator instructions](../CONTRIBUTING.md#extraction-model-comparison-scorer).

All 431 tests passed in 127.02 seconds before the final unit-case regression was
added; all six evaluator tests then passed with the final case-sensitive behavior.
The 4,102-record canonical catalog is unchanged. No push or deployment occurred.

The [subsequent authorized GPU canary](gemma-gpu-canary-20261110.md) has now run and
stopped. This staging report remains the earlier download/binary-verification
snapshot; use the canary report for the later runtime evidence.
