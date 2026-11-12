# Coverage snapshot — 2026-11-11 (America/Los_Angeles)

Observed at 2026-11-12T07:54:26.411907+00:00. The [current machine receipt](runs/coverage-after-foundations-20261111.json) is generated directly by `python -m src.cli coverage` and binds 394 consumed files, including verified cached historical pages. The prior [source-review snapshot](runs/coverage-after-source-reviews-20261111.json) and earlier receipts remain preserved. This report does not declare Phase 2/3 complete.

## Corpus and frozen discovery boundary

The catalog has **4,103 active papers and six archived records**. There are 4,070 active arXiv IDs and 33 records without one. Missing arXiv IDs do not prove proceedings-only discovery. The reviewed SAR-GS merge preserved the original seed ID and archived the duplicate with source evidence; see the [identity review](sargs-identity-merge-20261111.md).

All 340 frozen monthly query slices are complete, covering 1998-08-01 through the exclusive cutoff 2026-11-10T00:00:00Z. The literal query and comparator remain in the receipt. There are 4,466 unique candidates: 4,045 reviewed-application includes, 41 exclusions and 380 unresolved reviews under the frozen application policy. These counts do not establish coverage of all NeRF literature or later updates. The current source hashes were checked before retaining the historical-query results.

The original 165-seed ledger has **144 retained, five archived and 16 unresolved**. The sixth catalog archive is a later duplicate, not an extra excluded seed. Source-backed MASt3R and [Zero-1-to-3 foundation retention](zero123-seed-foundation-review-20261111.md), plus the SAR-GS identity review, preserve all original IDs without silently discarding review cases.

## Venue coverage

The declared inventory still has **56 cells: four crawled/partial and 52 pending**. No edition is fully reconciled. Title-priority captures alone do not establish abstract-based coverage.

| Full-metadata epoch | Frozen listing | Verified pages | Pending, including failures | Failed |
| --- | ---: | ---: | ---: | ---: |
| ICCV 2025 main | 2,701 | 2,701 | 0 | 0 |
| CVPR 2024 main | 2,716 | 2,713 | 3 | 3 |

ICCV has all 2,701 abstracts and a verified one-to-one title mapping between the two frozen official inventories. **512 rows retain author discrepancies**; source identity, dates, scope and provider review remain open. Of 2,552 title-excluded pages, metadata produced 49 include leads, 62 review leads and 2,441 exclusions. Those are automatic policy outcomes, not measured population relevance accuracy. See the [ICCV report](iccv2025-metadata-capture.md).

CVPR 2024 has **2,713/2,716** verified pages: 133 reused and 2,580 additional captures from 2,593 paced requests across seven bounded passes, including four source-bound offline metadata corrections. Three frozen listing URLs still return HTTP 404. A zero-request replay verified all retained response hashes without changing state. Title-excluded pages yield 15 include leads and 91 review leads, awaiting scope adjudication. The epoch retains its frozen policy. See the [CVPR checkpoint](cvpr2024-full-metadata-capture.md). CVPR 2023/2025 and the other 52 cells retain their declared gaps; DBLP access remains unresolved.

Two [source-reviewed proceedings discoveries](iccv2025-reviewed-discoveries-20261111.md), DGTalker and Hi-Gaussian, are now canonical additions with verified publication DOIs and independent official author agreement. All 4,101 previous records, existing aliases and six archives remain exact. Neither captured CVF page links arXiv; global preprint absence is not asserted. The two papers have fresh OpenAlex observations, but no eligible velocity window.

Matrix3D and fVDB now have source-backed foundation decisions, leaving **144 retained, 16 unresolved and five archived** seeds. The [review report](matrix3d-fvdb-seed-foundation-reviews-20261111.md) distinguishes full-method GS use from current software dependency evidence. Canonical bibliographic fields remain unchanged.

## Provider observations and real time windows

All denominators below are **4,103 active papers**. Latest attempt status is separate from retained successful values. Freshness is evaluated at the receipt timestamp using implemented adaptive OpenAlex/HF refresh TTLs and the seven-day Semantic Scholar TTL; it is distinct from retry eligibility and ranking availability.

| Provider | Cached active entries | Latest attempt statuses | Fresh successful values | Stale successful values | No cache entry |
| --- | ---: | --- | ---: | ---: | ---: |
| openalex | 4,103 | ok: 3,794, not_found: 277, ambiguous: 32 | 3,786 | 8 | 0 |
| semanticscholar | 41 | rate_limited: 41 | 0 | 0 | 4,062 |
| huggingface | 5 | ok: 2, not_found: 3 | 1 | 1 | 4,098 |

OpenAlex has 1,088 genuinely observed zero citation counts. The 4,065 zeros in canonical bibliographic records do not themselves carry provider observation freshness; the cache independently verifies successful observed zeros. OpenAlex has 3,691 single-snapshot histories, 95 histories without an eligible 7–45-day interval, eight stale histories and 309 without observations. **No active paper has eligible measured citation velocity.** Semantic Scholar has no successful history for any active paper. No dates or counts are fabricated to fill those gaps, and providers are never added together. HF's small sample is not full-corpus enrichment.

## Public graph and extraction

The verified public buckets have **27,343 directed internal edges**, connecting 3,464/4,103 papers; 639 are isolated in this observed graph. There are 69,512 external/unmatched source references. Canonical v1 materialized references still contain 28 edges; the public builder projects current cache evidence offline. This is partial observed lineage, not a scientific isolation or provider-recall claim. See the [graph verification](cache-backed-public-graph-20261111.md).

Extraction covers all active IDs: **11 processed, 4,082 queued for source materialization, nine unavailable in the configured inventory and one unsupported**. Queued tasks are not downloaded PDFs or completed jobs. The 12-paper pilot spans six categories. Prior agent rendered-source inspection checked 30 numeric candidates: 22 accepted cells across six papers and eight rejected/deferred cells. This is not an independent human benchmark. No figure asset is accepted for redistribution.

The [approved Gemma real-page diagnostic](gemma-radsplat-real-page-20261111.md) completed one generation, which failed source-index validation. No result or measurement was accepted; the warm repeat was omitted. The dedicated service stopped and its port closed. The existing extraction timer remained healthy. Broader Gemma accuracy, persistent model activation and worker replacement are unproven.

## Storage, release and remaining gates

Canonical storage remains v1. Full-corpus v2 parity, interrupted-write and rollback rehearsals passed locally; cutover and compatible remote writer deployment remain open. [Bounded public retention](public-artifact-retention-20261111.md) removed 316 obsolete files while retaining three verified generations. The current index is 1,717,929 bytes. Dedicated reports retain actual and 5,000-paper portal/performance evidence.

The [full cached-corpus release rehearsal](release-cache-backed-rehearsal-20261111.md) produced two byte-identical 83,681,280-byte archives, restored all 160 files and verified the earlier 393-file rollback archive. These local checks do not establish production deployment or rollback.

Remaining gates include 16 seed decisions, unresolved source/scope cases, venue inventory work, author/date/identifier adjudication, reviewed figure publication, broader extraction coverage, live Semantic Scholar access, genuine citation windows, compatible storage rollout, live competing-writer evidence and public candidate verification. Nothing in this snapshot pushes, dispatches, deploys, advances a source watermark or claims either phase complete.

## Reproducing this report

Run `uv run --all-groups python -m src.cli coverage --output reports/runs/<new-run>.json`. This performs no provider request, build or canonical update. It verifies the declared historical source pages and exact application inventory, reports seed/extraction binding gaps, and refuses input changes or report overwrite. An identical evaluation time and unchanged inputs reproduce the same JSON bytes. Public-manifest metadata is reported separately from the owned graph projection; release/deployment integrity checks remain separate. See [command validation](coverage-command-20261111.md).
