# Coverage snapshot — 2026-11-11

Observed at 2026-11-11T04:44:29.927040+00:00. This is a read-only repository snapshot, not a live provider refresh or a Phase 2/3 completion claim. The [machine receipt](runs/coverage-20261111.json) binds all consumed input bytes and retains the literal query, cell inventory, source statuses and unresolved seed IDs.

## Corpus, discovery and scope review

| Measure | Evidence |
| --- | --- |
| Canonical records | 4,102 active; 5 archived |
| arXiv identifiers | 4,070 active records have an arXiv ID; 32 lack one |
| Historical query | 340/340 monthly slices complete, 1998-08-01 through the exclusive cutoff 2026-11-10T00:00:00Z |
| Unique frozen-query candidates | 4,466 |
| Reviewed application dispositions | 4,045 include; 41 exclude; 380 unresolved review |
| Original 165 seed decisions | 141 retained; five archived; 19 unresolved |

Query completeness applies only to the literal broad query and cutoff recorded in the receipt. It does not establish coverage of all NeRF literature, later submissions or the current update window. The narrower comparator is retained separately. Application dispositions belong to their frozen policy; they have not been silently rerun under the later MASt3R foundation override. The 380 review candidates remain unresolved, not discarded. See the [seed review](mast3r-seed-foundation-review-20261111.md) and the receipt for the 19 baseline IDs still awaiting adjudication.

The 32 records lacking an arXiv ID are not 32 proven non-arXiv discoveries. Identity checks, actual proceedings-only insertions and later preprint aliases require source evidence. Publication DOI, venue/year and original dates cannot be inferred from this count.

## Venue/year coverage

The declared inventory has 56 main/workshop cells: 52 pending and four crawled/partial. No cell is claimed fully reconciled. The four partial cells are CVPR 2023/2024/2025 main and ICCV 2025 main. The receipt lists every edition/track and status; `config/sources.yaml` retains cell-specific evidence and gaps.

At this snapshot, the committed ICCV full-metadata checkpoint is 806/2,701 pages; a separate capped pass is in flight and is not counted until verified. Title-priority captures are not full abstract-based coverage. Independent inventory/title/author discrepancies, identity/date resolution, topic review and DBLP access remain open. See the [ICCV report](iccv2025-metadata-capture.md).

## Provider observations and freshness

Every row below uses **4,102 active papers** as its denominator. Archived/cache-only entries are excluded. Latest attempt status and retained successful values are separate: a failed refresh can retain useful old data. Freshness uses the implemented provider TTLs, not retry eligibility.

| Provider | Cached active entries | Latest `ok` | Fresh successful values | Stale successful values | No cache entry |
| --- | ---: | ---: | ---: | ---: | ---: |
| huggingface | 5 | 2 | 1 | 1 | 4097 |
| openalex | 190 | 170 | 155 | 15 | 3912 |
| semanticscholar | 1 | 0 | 0 | 0 | 4101 |

OpenAlex also has 17 ambiguous matches and three confirmed misses; five archived cache entries are excluded from the active denominator. Successful observed counts include 108 actual zeros. The **4,064 canonical legacy zeros have unknown observational freshness** and must not be relabelled as verified provider zeros. Successful OpenAlex observations are 1.25–1.98 days old; young/unmapped entries can already be stale under the one-day TTL. HF has three confirmed misses. Semantic Scholar has one rate-limited attempt and no successful active observation; its history file is absent. A missing provider entry conveys unknown coverage, not zero influence.

Citation velocity currently has **zero eligible active papers** from either provider. OpenAlex has 155 fresh single snapshots and 15 stale snapshots; 3,932 have no history. Semantic Scholar has no observations for all 4,102. Genuine observations spanning the required 7–45-day window are not available yet. Annual provider aggregates and synthetic dates cannot fill that gap. Counts are never summed across providers.

## Graph and extraction coverage

The materialized internal graph has 28 directed edges with active endpoints, connecting 23/4,102 papers; 4,079 are isolated in that observed graph. This measures stored `db_references`, not total citation relationships, provider recall or scientific isolation. Unmapped or unobserved citations remain unknown.

| Extraction state | Active papers |
| --- | ---: |
| Processed | 11 |
| Queued for source materialization | 4,081 |
| Unavailable in configured local inventory | 9 |
| Unsupported | 1 |

These states cover all 4,102 active IDs. A materialization task is not a downloaded PDF or a completed parser job. The pilot has 12 papers across six categories, including the unsupported/size-limit case. Thirty numeric candidates were manually checked in prior agent rendered-source inspection: 22 accepted cells across six papers and eight rejected/deferred candidates. This is not an independent human benchmark; accepted values require exact source evidence. No figure asset is accepted for redistribution. Unreviewed table candidates remain unreviewed.

The approved Gemma test was one synthetic request followed by cleanup. The [real-page diagnostic](gemma-radsplat-pilot-plan-20261111.md) is prepared, awaiting its separate approval. It is not counted as completed extraction quality evidence.

## Remaining release gates

Canonical storage is still v1; full-corpus v2 migration/rollback rehearsals passed locally, but cutover and compatible remote writer rollout remain open. Local portal performance and immutable release-artifact rehearsals have dedicated reports; they do not prove public deployment. No push, remote workflow dispatch, production Pages deployment or production rollback has occurred. Live writer-race/dispatch evidence, provider rollout, source review/completeness, reviewed figure publication, full worker coverage and real citation observation windows remain outstanding.

This snapshot does not advance any source watermark, modify canonical/provider data or declare a phase complete. Later reports must recompute denominators and observation ages against their own bound inputs.
