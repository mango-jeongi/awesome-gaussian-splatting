# Coverage snapshot — 2026-11-12 (America/Los_Angeles)

Observed at 2026-11-12T22:11:26.377174+00:00. The [current machine receipt](runs/coverage-after-cvpr2025-three-discoveries-20261112.json) is generated directly by `python -m src.cli coverage` and binds 395 consumed files, including verified cached historical pages. Earlier snapshots remain preserved. This report does not declare Phase 2/3 complete.

## Corpus and frozen discovery boundary

The catalog has **4,107 active papers and six archived records**. There are 4,071 active arXiv IDs and 36 records without one. Missing arXiv IDs do not prove proceedings-only discovery. The reviewed SAR-GS merge preserved the original seed ID and archived the duplicate with source evidence; see the [identity review](sargs-identity-merge-20261111.md).

All 340 frozen monthly query slices are complete, covering 1998-08-01 through the exclusive cutoff 2026-11-10T00:00:00Z. The literal query and comparator remain in the receipt. There are 4,466 unique candidates: 4,045 reviewed-application includes, 41 exclusions and 380 review outcomes under the frozen application policy; later independent resolutions, including PhysConvex, are recorded separately. These counts do not establish coverage of all NeRF literature or later updates. The current source hashes were checked before retaining the historical-query results.

The original 165-seed ledger has **154 retained, five archived and six unresolved**. The sixth catalog archive is a later duplicate, not an extra excluded seed. Source-backed MASt3R and [Zero-1-to-3 foundation retention](zero123-seed-foundation-review-20261111.md), plus the SAR-GS identity review, preserve all original IDs without silently discarding review cases.

## Venue coverage

The declared inventory still has **56 cells: four crawled/partial and 52 pending**. No edition is fully reconciled. Title-priority captures alone do not establish abstract-based coverage.

| Full-metadata epoch | Frozen listing | Verified pages | Pending, including failures | Failed |
| --- | ---: | ---: | ---: | ---: |
| ICCV 2025 main | 2,701 | 2,701 | 0 | 0 |
| CVPR 2024 main | 2,716 | 2,715 | 1 | 1 |
| CVPR 2025 main | 2,871 | 2,871 | 0 | 0 |

ICCV has all 2,701 abstracts and a verified one-to-one title mapping between the two frozen official inventories. **512 rows retain author discrepancies**; source identity, dates, scope and provider review remain open. Of 2,552 title-excluded pages, metadata produced 49 include leads, 62 review leads and 2,441 exclusions. Those are automatic policy outcomes, not measured population relevance accuracy. See the [ICCV report](iccv2025-metadata-capture.md).

CVPR 2024 now has **2,715/2,716** verified pages. Two [source-bound URL reviews](cvpr2024-url-reviews-20261112.md) resolve GenHowTo and DePT using previously retained official HTTP-200 responses; application and identical replays made zero requests. A full cache replay preserved state bytes, and a subsequent one-request retry confirms SportsSloMo still returns HTTP 404. Four earlier title/author corrections remain intact, as do all 2,713 prior verified captures and original observation times. Title-excluded pages yield 15 include leads and 91 review leads for scope adjudication. The epoch retains its frozen policy. The [accepted-table cross-edition title conflict](cvpr2024-cross-edition-title-diagnostic-20261112.md), announcement count gap and remaining metadata/scope work remain unresolved. CVPR 2023 and the other 52 cells retain their declared gaps; DBLP access remains unresolved.

CVPR 2025 now has **2,871/2,871** full-metadata pages verified, with zero pending pages and zero failures: 148 reused responses and 2,723 additional verified pages. Four completed passes reported 1,936 requests; the user-paused fifth pass retained 488 further verified pages but produced no terminal request receipt, so its exact request count remains unknown. Zero-request recovery verified 2,563 retained pages, and a separate 308-request resume finished the queue. The final zero-request hash/parser replay preserves state bytes, all response timestamps and the frozen policy. All 2,723 title-excluded pages yield 73 include leads and 74 review leads awaiting current-scope adjudication. Metadata completeness does not settle source identity, authors, original dates, the accepted-table count gap or scope. [Complete capture and recovery evidence](cvpr2025-full-metadata-capture.md).

Two [source-reviewed proceedings discoveries](iccv2025-reviewed-discoveries-20261111.md), DGTalker and Hi-Gaussian, are now canonical additions with verified publication DOIs and independent official author agreement. All 4,101 previous records, existing aliases and six archives remain exact. Neither captured CVF page links arXiv; global preprint absence is not asserted. The two papers have fresh OpenAlex observations, but no eligible velocity window.

Three further [CVPR discoveries and a title-variant review](cvpr2025-three-reviewed-discoveries-20261112.md) add GeoAvatar (multi-person reconstruction), LOD-GS (Scalable Gaussian Soup) and GBC-Splat using primary CVF/Crossref evidence. The existing same-acronym GeoAvatar and LOD-GS records remain distinct. FreeTimeGS gains a verified CVF alias and publication year without changing its original title, authors or date. All 165 seed rows remain unchanged. The post-application audit has 179 matched and 116 unmatched non-excluded leads, including 12 unmatched automatic includes; 59 matched records still lack or differ in venue/publication year. Those leads remain subject to source and scope review.

AutoPhyX and LiTo have [direct GS method decisions](autophyx-lito-method-scope-reviews-20261112.md); [SyncDreamer](syncdreamer-foundation-review-20261112.md), Matrix3D, fVDB and the newly reviewed [Bayes’ Rays and Domain Randomization foundations](uncertainty-randomization-foundation-reviews-20261112.md) leave **154 retained, six unresolved and five archived** seeds. The [review report](matrix3d-fvdb-seed-foundation-reviews-20261111.md) distinguishes full-method GS use from current software dependency evidence. Canonical bibliographic fields remain unchanged.

[VGGT-Ω retention](vggt-omega-foundation-review-20261112.md) adds a concrete GS geometry foundation: two inspected primary GS methods explicitly use its features/depth or pretrained encoder. All 154 retained seed hashes verify. D4RT and the drone NeRF method remain under review; Gaussian blur augmentation and a proposed future GS extension are not treated as implemented splatting. Canonical bytes remain unchanged.

The user's [adjacent-work preference](../data/reviews/adjacent-splatting-user-scope-20261112.json) now retains verified non-Gaussian splatting competitors as explicitly labelled adjacent work. Hexels, CVTSplat and OV-Foam display `Adjacent Work` and `Non-Gaussian Splatting` tags; Hexels' misleading `2DGS` tag was removed. Digital Twin AI is retained for substantive GS survey coverage. In that earlier 4,103-record application, only those three tag/provenance records changed; all other 4,100 records, titles/authors/dates/identifiers, aliases and archives remain unchanged. [Four reviews and validation](adjacent-splatting-scope-and-seed-reviews-20261112.md). The frozen challenge packet counts Hexels conservatively against its older review gold label: precision/recall 0.9855/1.00, with no gold relabelling or population-accuracy claim.

The [generalized and convex reviews](generalized-and-convex-adjacent-reviews-20261112.md) extend this preference to existing GES and DyGASR (`Generalized Splatting`) and newly added PhysConvex (`Non-Gaussian Splatting`). Gaussian members of the generalized families are preserved accurately. GES publication year/precision is source-backed; original dates and authors remain unchanged. PhysConvex has one genuine OpenAlex sample and one queued PDF task, with no claimed completed extraction or eligible velocity. At that checkpoint the original relevance packets and annotations remained unchanged; the suite passed 531 tests with one skip. The later source-bound review version is reported separately below.

The [versioned relevance review](relevance-review-versioning-20261112.md) preserves the original limited-evidence development score of **94.23% precision / 98% recall**, which fails its precision gate under the current policy. A separately named, source-bound review version resolves the three previously adjudicated foundations and scores **100% / 98.11%** on the same 100 candidates, meeting the unchanged thresholds. These post-evaluation agent judgments are not independent holdout validation; all original annotations and both scores remain visible. The final implementation passed **551 tests with one skip**, plus lint/format checks; [validation](runs/foundation-review-validation-20261112.json) includes 20 additional evidence-contract regressions.

## Provider observations and real time windows

All denominators below are **4,107 active papers**. Latest attempt status is separate from retained successful values. Freshness is evaluated at the receipt timestamp using implemented adaptive OpenAlex/HF refresh TTLs and the seven-day Semantic Scholar TTL; it is distinct from retry eligibility and ranking availability.

| Provider | Cached active entries | Latest attempt statuses | Fresh successful values | Stale successful values | No cache entry |
| --- | ---: | --- | ---: | ---: | ---: |
| openalex | 4,107 | ambiguous: 32, not_found: 277, ok: 3,798 | 3,790 | 8 | 0 |
| semanticscholar | 41 | rate_limited: 41 | 0 | 0 | 4,066 |
| huggingface | 15 | not_found: 7, ok: 8 | 7 | 1 | 4,092 |

OpenAlex has 1,089 genuinely observed zero citation counts. The 4,069 zeros in canonical bibliographic records do not themselves carry provider observation freshness; the cache independently verifies successful observed zeros. OpenAlex has 3,695 single-snapshot histories, 95 histories without an eligible 7–45-day interval, 8 stale histories and 309 without observations. **No active paper has eligible measured citation velocity.** Semantic Scholar has no successful history for any active paper. No dates or counts are fabricated to fill those gaps, and providers are never added together. HF's small sample is not full-corpus enrichment.

The [HF detail delivery](huggingface-detail-delivery-20261112.md) now exposes attributed provider summaries, returned upvotes/stars, repository evidence and recorded Spaces through lazy paper details. Ten bounded requests produced six exact-ID matches and four misses, preserving all five older observations. All 15 cached observations have corresponding details; 4,092 papers remain unobserved. Valid zeros, unavailable values, stale retained successes and confirmed misses stay distinct. No provider text replaces the author abstract or reviewed code URL, and repository ownership remains unverified.

## Public graph and extraction

The verified public buckets have **27,361 directed internal edges**, connecting 3,467/4,107 papers; 640 are isolated in this observed graph. There are 69,548 external/unmatched source references. Canonical v1 materialized references still contain 28 edges; the public builder projects current cache evidence offline. This is partial observed lineage, not a scientific isolation or provider-recall claim. See the [graph verification](cache-backed-public-graph-20261111.md).

Extraction covers all active IDs: **11 processed, 4,086 queued for source materialization, nine unavailable in the configured inventory and one unsupported**. Queued tasks are not downloaded PDFs or completed jobs. The 12-paper pilot spans six categories. Prior agent rendered-source inspection checked 30 numeric candidates: 22 accepted cells across six papers and eight rejected/deferred cells. This is not an independent human benchmark. No figure asset is accepted for redistribution.

The [approved Gemma real-page diagnostic](gemma-radsplat-real-page-20261111.md) completed one generation, which failed source-index validation. No result or measurement was accepted; the warm repeat was omitted. The dedicated service stopped and its port closed. The existing extraction timer remained healthy. Broader Gemma accuracy, persistent model activation and worker replacement are unproven.

## Storage, release and remaining gates

Canonical storage remains v1. Full-corpus v2 parity, interrupted-write and rollback rehearsals passed locally; cutover and compatible remote writer deployment remain open. [Bounded public retention](public-artifact-retention-20261111.md) removed 316 obsolete files while retaining three verified generations. The current index is 1,721,108 bytes (450,351 gzip), and the largest detail shard is 492,412 bytes. All 81 referenced descriptors and the 15 HF detail projections pass [current integrity checks](runs/cvpr2025-three-publications-public-verification-20261112.json); prior adjacent-label evidence remains preserved. The README retains its existing latest-60-per-category window. The new HF section passed [actual browser QA](runs/hf-detail-browser-verification-20261112.json), including mobile layout, themes, BibTeX, the 50-card catalog, safe text/links and the search shortcut, with zero page/console errors. The full suite passed 564 tests with one skip plus lint/format checks. Earlier actual/5,000-paper performance evidence is preserved; this is not a fresh five-cold-load performance measurement.

The [full cached-corpus release rehearsal](release-cache-backed-rehearsal-20261111.md) produced two byte-identical 83,681,280-byte archives, restored all 160 files and verified the earlier 393-file rollback archive. These local checks do not establish production deployment or rollback.

Remaining gates include six seed decisions, unresolved source/scope cases, venue inventory work, author/date/identifier adjudication, reviewed figure publication, broader extraction coverage, live Semantic Scholar access, genuine citation windows, compatible storage rollout, live competing-writer evidence and public candidate verification. Nothing in this snapshot pushes, dispatches, deploys, advances a source watermark or claims either phase complete.

## Reproducing this report

Run `uv run --all-groups python -m src.cli coverage --output reports/runs/<new-run>.json`. This performs no provider request, build or canonical update. It verifies the declared historical source pages and exact application inventory, reports seed/extraction binding gaps, and refuses input changes or report overwrite. An identical evaluation time and unchanged inputs reproduce the same JSON bytes. Public-manifest metadata is reported separately from the owned graph projection; release/deployment integrity checks remain separate. See [command validation](coverage-command-20261111.md).
