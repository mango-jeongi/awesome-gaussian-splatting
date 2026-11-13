# Coverage snapshot — 2026-11-13 (America/Los_Angeles)

Observed at 2026-11-13T20:23:43.527228+00:00. The [current machine receipt](runs/coverage-trunk-bound-20261113.json) binds 396 consumed files. Earlier receipts remain preserved. Raw source replay depends on the local NVMe cache; only metadata, state and digests are tracked.

## Catalog and trunk integration

The catalog contains **4,130 active papers**, **8 archived records**, **4,090 active arXiv IDs**, and **40 records without an arXiv ID**. The reviewed feed merge retained 14 additions and explicitly excluded one Gaussian point-spread-function paper. Every pre-existing canonical record was preserved. See [feed reconciliation](../data/reviews/trunk-feed-reconciliation-20261113.json).

The original 165 seeds remain **154 retained, five archived and six unresolved**. All 154 retained record hashes were verified before refreshing the aggregate catalog binding. Seed decisions and unresolved cases were not re-adjudicated. The seed and extraction inventories both bind the current canonical snapshot.

The 340 frozen historical arXiv slices remain complete, with 4,466 source candidates. No historical crawl or additional venue cell was opened in this pass.

## Venue metadata and reconciliation

The declared inventory remains **56 cells: four crawled/partial and 52 pending**. Full publication-page capture is separate from accepted-list reconciliation, scope review, original-date resolution and canonical import.

| Frozen full-metadata epoch | Verified | Listed | Pending, including failures |
| --- | ---: | ---: | ---: |
| CVPR 2023 main | 2,351 | 2,353 | 2 |
| CVPR 2024 main | 2,715 | 2,716 | 1 |
| CVPR 2025 main | 2,871 | 2,871 | 0 |
| ICCV 2025 main | 2,701 | 2,701 | 0 |

CVPR 2023 resumed the frozen listing and policy in bounded 200-request checkpoints. All 1,189 prior capture hashes and observation times were retained. The Sarkar face-segmentation page required an [offline author-metadata review](../data/reviews/cvpr2023-sarkar-author-variant-20261113.json): its visible author line and BibTeX retain Nikitha SR, while the citation meta tag truncates the name. The raw HTTP-200 response was promoted through the existing source-bound review contract, with zero network requests.

One bounded retry is scheduled for **2026-11-13T20:52:51Z / 12:52:51 p.m. Pacific**, after both retained transport deadlines. The two pending pages have no HTTP response; their status does not establish publication unavailability.

The independent accepted table still contains 2,359 rows versus 2,353 proceedings rows, with six unmapped accepted-only titles and 14 exact-title author differences. No withdrawal, equivalence or original publication date is invented. Adjacent/foundation leads require explicit scope justification; no automatic CVPR 2023 canonical import is claimed. Other edition evidence and the 52 pending cells remain unchanged.

## Worker and bounded model comparison

Extraction coverage records **11 processed**, **4,109 queued source tasks**, **9 unavailable**, and **1 unsupported**. Queued source materialization is not a downloaded PDF or a completed parser job. Existing processed records and source bindings were preserved while adding tasks for the 14 feed additions.

The reviewed ledger retains **22 accepted numeric cells across 6 papers**, eight rejected candidates and zero accepted figures. One acknowledged 98-candidate RadSplat result was SHA-validated and synced to the repository review queue. Neither the extraction runtime pointer nor existing accepted decisions changed.

The [bounded Gemma comparison](gemma-radsplat-comparison-20261113.md) reproduced invalid source-word indices. One generation was rejected and the service stopped cleanly; precision/recall is not scorable for an invalid generation. Deterministic extraction matched 4/4 reviewed numeric values on the selected RadSplat page, with context omissions/differences and 35 predictions outside the accepted subset unscored. Population precision and full-table recall are not established.

## Providers, graph and observation schedule

OpenAlex has **4,116 cached active records**, including **3,808 successful**, 31 ambiguous and 277 not-found statuses. The 14 retained feed additions have no OpenAlex observations yet. The owned cache projection contains **27,430 internal citation edges** across **3,474 connected records**.

Hugging Face retains 15 cached entries: eight successful and seven not found. Semantic Scholar retains 41 typed rate-limited entries; the optional key is absent, so the bounded check made zero requests and preserved the cache.

There are **zero matured seven-day velocity windows**. The oldest genuine OpenAlex sample is 2026-11-09T05:21:28.525343Z, for the original 3D Gaussian Splatting paper. Its earliest maturity is **2026-11-16T05:21:28.525343Z**. A one-shot user timer is active for **2026-11-16T05:21:29Z / November 15 at 9:21:29 p.m. Pacific**, with at most 20 requests and a 120-second request-admission budget. It uses observation sampling, and an [offline admission check](runs/openalex-maturity-admission-20261113.json) confirms the oldest paper is selected. No observations were fabricated or refreshed early, and no in-session wait for this window occurred.

## Storage and public artifacts

The active canonical writer uses the existing v1 `data/papers.json`; lossless v2 snapshot/migration support is implemented but is not activated in this checkout. This pass preserves the current writer format.

The production builder regenerated README, the public export and the manifest-selected compact index at `docs/data/index.4836e807513e8881f152f007c103ed81762ada97d49ae63e3459454ab099c6e6.json`. The index is **1,731,559 bytes**, **452,626 bytes gzip**, below the 4 MB budget. The handoff's `data/index/public-index.json` path is not used by this checkout. The current public manifest matches the canonical cache-backed projection; archive verification is a separate release gate.

All **71 previously tracked raw HTML files (101,164,307 bytes)** were removed from the current Git index while retaining their local NVMe copies. [Cache inventory and SHA-256 digests](../data/reviews/local-raw-cache-inventory-20261113.json) bind those files. Raw HTML/PDFs under `data/` are now gitignored; repository-native page code and test fixtures remain tracked.

The full trunk quality gate passed: Ruff, formatting, **577 tests**, validation of all 4,130 canonical records, and the locked CSS build check. A [tracked-only build rehearsal](runs/tracked-only-build-rehearsal-20261113.json), containing neither raw source cache nor local secrets, regenerated byte-identical README and public artifacts. Final release rehearsal and the push approval gate remain open while the scheduled metadata retry is pending. No push, deployment, workflow dispatch or production rollback has occurred.
