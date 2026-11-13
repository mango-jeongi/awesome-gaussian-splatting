# CVPR 2023 all-metadata capture: bounded progress

The separate all-metadata epoch selects all **2,353** papers in the frozen official main-track listing. It now verifies **689 pages**, with **1,664 pending including one transport failure**. Metadata coverage and edition reconciliation remain incomplete.

| Completed pass | Actual requests | New verified pages | Verified total | Failure records |
| --- | ---: | ---: | ---: | ---: |
| 1 | 200 | 200 | 290 | 0 |
| 2 | 400 | 399 | 689 | 1 |

The original 90 pages are reused without changing hashes or observation times. Pass 2 preserves all 290 prior verified entries/times. Limits were 400 paced requests and 480 seconds; the original live process was observed terminal before finalization and was not restarted because of polling timeouts. [Pass 1 receipt](runs/cvpr2023-all-metadata-pass1-20261112.json), [pass 2 terminal receipt](runs/cvpr2023-all-metadata-pass2-20261112.json).

The [second zero-request verification](runs/cvpr2023-all-metadata-pass2-verification-20261112.json) replays all 689 retained responses through the production hash/parser checks and preserves checkpoint bytes. Latest report invocation count is zero because it reflects that replay; separate terminal receipts preserve the actual cumulative 600 network requests. The earlier title-priority epoch, listing and frozen policy remain unchanged. The frozen current policy file is `data/venues/policies/ba199b2d41740722abb0dcc7aaad3f89a3f48c149dc4ff991d8929a1cefe73e9.yaml`.

One request for **Towards Accurate Image Coding: Improved Autoregressive Image Generation With Dynamic Vector Quantization** failed at transport level. No HTTP response status/body was captured, so neither an HTTP code nor paper unavailability is inferred. The recorded retry deadline is **2026-11-13T04:39:19.083315Z** and remains intact. The pending total includes this failure; other unattempted pages can continue under the same epoch without bypassing it.

Metadata outcomes are zero include, 105 review and 584 exclude. Fifteen captured title-excluded pages are automatic review leads, not source-adjudicated inclusions or population relevance accuracy. No paper was imported. The remaining 1,664 pages and earlier 90 adjacent/foundation outcomes still require appropriate capture, identity and scope work.

Only the CVPR 2023 main declaration receives updated partial evidence; all other edition entries remain semantically unchanged. Cell counts remain four crawled/partial and 52 pending. The independent accepted table still has 2,359 rows versus 2,353 proceedings rows, six unmapped accepted-only titles, nine reviewed typography mappings and 14 exact-title author differences. This metadata pass does not resolve those discrepancies or complete deferred original-date/DBLP work.

The [current coverage receipt](runs/coverage-after-cvpr2023-metadata-pass2-20261112.json) verifies consumed-input hashes and current canonical/seed/extraction bindings. Canonical paper data, provider histories and public artifacts are unchanged. No production code changed; validation uses actual zero-request hash/parser replay and preservation of prior source entries rather than repeating unchanged unit tests.

Resume with the same listing, frozen policy and `--all-metadata`, using a new receipt and bounded budgets. Preserve recorded retry deadlines and all prior observation times. No source watermark, PDF/parser result, push, dispatch, deployment or remote worker change occurred. Phase 2/3 remains active.
