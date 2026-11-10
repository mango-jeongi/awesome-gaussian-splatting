# Pinned local-model staging

`llama-qwen-pins.json` freezes llama.cpp `b12259` CUDA 12.8 x86_64 binaries,
the companion CUDA runtime, and the official Qwen Q5_K_M split GGUF at repository
revision `bb5d59e06d9551d752d08b292a50eb208b07ab1f`. The four files total
**6,227,545,077 bytes**; the model files account for 5,444,831,360 bytes.
Checksums come from the GitHub release asset digests and Hugging Face LFS metadata.

Preview locally without creating output directories or contacting providers:

```sh
uv run python scripts/worker/stage_llama.py --pins scripts/worker/llama-qwen-pins.json --root <dedicated-staging-directory> --dry-run
```

After remote staging is authorized, copy the script/pins to a dedicated directory
and invoke it using the remote worker virtual environment's Python. Do not use
system Python for workspace extraction/metadata operations. The script requires
15 GB free, validates the entire pin inventory before traffic, admits at most
8 GB of downloads, resumes `.part` files, limits curl to 25 MiB/s, and checks
exact byte sizes and SHA-256 before publishing files. Each transfer has a
30-minute curl timeout and at most two retries. A subprocess has a 5,500-second
outer bound. Bad existing artifacts are refused, never silently replaced.

Runtime archives are extracted only after checksum verification, using Python's
`data` tar filter. No service definition, active runtime pointer, model symlink,
worker queue or repository state is changed by this staging command. The receipt
explicitly leaves model inference unverified. Staging is not a CUDA/VRAM or model
quality test. Verify the receipt against current artifact hashes when resuming.

Sources: [llama.cpp release](https://github.com/ggml-org/llama.cpp/releases/tag/b12259),
[official Qwen model](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/tree/bb5d59e06d9551d752d08b292a50eb208b07ab1f).

On 2026-11-10, automatic approval review rejected remote execution because prior
approval covered only the 15 MB PDF transfer/extraction service. Remote model
staging therefore awaits explicit approval. No transfer or installation occurred.
Ten offline checks pass, covering exact pin inventory, unsafe names, unexpected
URLs, invalid sizes/checksums, duplicates/missing artifacts and a no-network,
no-output-directory preview. Ruff lint and formatting pass.

## Gemma alternative (prepared, not installed)

Following the model-choice review, `llama-gemma-pins.json` prepares the official
`google/gemma-4-E4B-it-qat-q4_0-gguf` text-only inference weights at revision
`4b4a2c1d584be7264f87aac328a1bc739ce81b6c`. The weight file is 5,154,941,280 bytes;
with the same CUDA/runtime archives the download is 5,937,654,997 bytes. The
991,552,256-byte multimodal projector is not included, because the current table
adapter sends extracted words rather than page images. Image-input support would
require a separately verified projector/runtime path and VRAM measurement.

Neither model has been benchmarked on the extraction pilot. Qwen was the earlier
plan's baseline, not a demonstrated winner. Gemma E4B is a plausible first test on
the 8 GB GPU; actual peak VRAM, context fit, latency and row/column/metric/unit
accuracy must be measured. Use the same source pages, schema, acceptance rules
and output budget for a comparison, with one model resident at a time. General
chat or reasoning benchmarks do not establish table-extraction superiority.

The user's model question did not approve remote staging. Both pin sets remain
local preparation only; no remote download or installation has run.
Sources: [official Gemma GGUF](https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf),
[Google memory-planning notes](https://ai.google.dev/gemma/docs/core).

## Approved Gemma staging completed

The subsequent explicit Gemma staging approval supersedes the earlier hold for
that manifest. All three files (5,937,654,997 bytes) were downloaded, size/hash
verified and the two runtime archives extracted on `msi-raider`. The
[receipt and binary check](../../reports/gemma-staging-20261110.md) record the
result. Qwen weights remain unstaged. No model service or inference was started.
The prepared canary service/request files are review artifacts, not an installed
service; startup remains a separate authorization step.

## Approved GPU canary completed

The subsequently approved 15-minute canary ran one synthetic request and was
stopped. Its static unit is inactive, no port listener remains, and the existing
extraction timer is still active. See the
[canary evidence and limitations](../../reports/gemma-gpu-canary-20261110.md).
A live 16K slot and exact source-word value were observed; full-length context,
full-layer offload, real-table quality, warm performance and persistent daemon
operation remain unverified. The canary is not a production model deployment.
