# Worker/SSH and local model adapter — 2026-11-10

SSH access to `msi-raider` was restored and verified live. The existing
`papers-extraction.timer` is active on its five-minute cadence. Its latest service
passes completed successfully with no queued jobs. The service is a oneshot, so
`inactive/dead` between successful timer invocations is expected. Its runtime is
`runtime-79711958ee618714`; this is not the current local branch runtime.

The host reports an NVIDIA GeForce RTX 2070 with 7,686 MiB free, driver 595.99.02,
x86_64, and 369 GB free on its home NVMe filesystem. `cmake` and `git` are installed;
`llama-server` and `nvcc` were not found on PATH, and the usual CUDA toolkit paths
were absent. No model or toolkit was installed, no PDFs were transferred, and no
existing service definition was changed during these checks.

The new opt-in `src.workers.llama_parser` backend is connected to enqueue/pass via
`--llama-config`. It uses the same lease-fenced, timeout-bounded subprocess path.
Configuration and prompt are bound to job identity. The local model may select
only source-word indices; candidate values, context and boxes are reconstructed
from the PDF. The result remains unreviewed and uses the existing review schema.
Request/word/output budgets, reported page omissions, literal-loopback transport,
no proxies/redirects, exact model-alias checking and incomplete-output refusal
are implemented. The model hash remains explicitly operator-declared.

Nineteen new offline regressions and the existing runner/queue checks passed
(33 focused tests). These verify transport/response contracts and queue behavior;
they are not evidence of live local-model quality, GPU offload or installed model
identity. See [operator instructions](../CONTRIBUTING.md#optional-local-llama-server-table-candidates).

Live llama-server installation, model/hash verification, source-reviewed table
pilot expansion and headless model-service recovery remain open. The active
extraction timer still runs the earlier deterministic runtime. The broader Phase
2/3 goal remains incomplete.

Full suite: 404 tests passed in 100.05 seconds. After tightening numeric values to
one exact source word, all 33 affected adapter/runner/queue tests passed again.
Ruff lint and formatting pass. Multiword numeric expressions are intentionally
left for source review rather than assembled into a potentially invented value.
