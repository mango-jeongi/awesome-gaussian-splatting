# ICCV 2025 metadata evidence — complete frozen listing, partial edition review

All **2,701 publications in the frozen official main-proceedings listing** now
have verified metadata and author abstracts. This includes 2,700 automatic exact
listing/page matches and one explicit source-reviewed title variant. A final
zero-request replay rechecked every body hash and review binding: zero pending,
zero failed, selected metadata complete. No canonical paper import occurred.

The [completion receipt](runs/iccv2025-full-metadata-completion-20261111.json)
binds listing, policy, state, report and review hashes. This completes metadata
capture for this named listing; the edition remains **partial** pending inventory,
identity, scope, original-date and provider review.

## Frozen boundary and source evidence

The official listing `https://openaccess.thecvf.com/ICCV2025?day=all` has 2,701 rows,
SHA-256 `e684fe760c417a35c2f1e9a5acb3015a192fce10e566086e2d4bf7f78cbb97fe`.
The all-metadata epoch retains its original policy digest
`388dfe1507123d4bfb7e4bfac474e94afa84321eb5067d8a5db8f4622d8b4d0f`.
The corresponding override document is frozen under `data/venues/policies/`;
future replay must pass that file with `--overrides` and `--all-metadata`.
The later MASt3R root-policy change did not reclassify this epoch.

All 2,701 pages provide abstracts; 1,682 expose official arXiv links. Those links
are source evidence, not completed exact-ID/original-date verification. A page
without such a link does not prove the absence of a preprint. Raw bodies and
original observation times remain retained. Request/response/time ceilings,
successful-request pacing and per-page retry deadlines were enforced.

## Title screening and full-metadata policy

The original title-priority epoch captured 149 selected pages, which was not
complete abstract-based venue coverage. The separate all-metadata epoch reused
those exact bodies/timestamps and fetched every remaining listed page.

| Frozen title decision | Full metadata include | Full metadata review | Full metadata exclude |
| --- | ---: | ---: | ---: |
| Include | 108 | 0 | 0 |
| Review | 16 | 25 | 0 |
| Exclude | 49 | 62 | 2,441 |
| Total | 173 | 87 | 2,441 |

The [49 title-excluded inclusion leads](../data/venues/iccv2025-all-metadata/title-screen-rescue-evidence.json)
are automatic policy outcomes, not 49 adjudicated GS papers or a population
recall estimate. Baseline-only GS mentions and competing representations such
as Radiant Foam still require scope inspection. The separate known-catalog tail
audit found 46 policy-passing active matches excluded by title; those are also
review leads rather than independent ground truth. No policy relaxation or
automatic canonical inclusion was used to make capture complete.

## Explicit RoboTron title adjudication

The sole persistent metadata failure was reachable HTTP-200 content: the listing
and URL slug say **RoboTrom-Nav**, while page citation metadata and the independent
accepted table say **RoboTron-Nav**. All six full authors agree in order after case
normalization; year, edition and exact source/PDF path also agree.

The [review](../data/reviews/iccv2025-robotron-title-review-20261111.json) binds the
unchanged listing and exact retained response hashes plus independent accepted
row evidence. It promotes only that already captured body, without network
traffic or a retry-deadline bypass. Its observation time remains the actual fetch
time. The [application/replay receipt](runs/iccv2025-robotron-title-review-20261111.json)
shows an offline application and no-op replay.

Every other page retains strict default title matching. Author, year, edition,
PDF-path and source-hash checks also remain strict for the reviewed case. Changed
or forged review sources fail before traffic. Diagnostics retain complete bounded
invalid responses separately; invalid/oversized data is not counted as verified.
No canonical paper alias was asserted by this source-level correction.

## Independent inventory remains unresolved

The [official accepted table](https://iccv.thecvf.com/Conferences/2025/AcceptedPapers)
also has 2,701 rows at SHA-256
`b4aa86509a1c613e884f5bea41bc8952770d7754ce757431ffac73b30065331e`.
The original [comparison](../data/venues/iccv2025-main/independent-reconciliation.json)
retains 2,677 normalized-title matches, seven reviewed typography pairs and 17
unmatched rows on each source. Its evidence is preserved unchanged.

The [RoboTron review overlay](../data/venues/iccv2025-main/reviewed-identity-reconciliation-20261111.json), [eight exact-author title reviews](../data/reviews/iccv2025-eight-inventory-title-pairs-20261111.json), and [final eight explicit source reviews](../data/reviews/iccv2025-final-eight-inventory-title-pairs-20261111.json) now account for all 17 original unmatched title pairs. An independent reconstruction from both frozen primary inventories proves a [one-to-one mapping of all 2,701 rows](../data/venues/iccv2025-main/reviewed-complete-title-mapping-20261111.json): 2,677 normalized-title matches, seven typography pairs and 17 explicitly reviewed title correspondences. No title row remains unmatched.

Author reconciliation remains open for **512 rows**: 504 among normalized-title matches and eight among explicit title variants. These author sequences are preserved verbatim; name expansions, spelling differences and accepted-table institutional fragments are not silently corrected. The earlier ambiguous typography/author case is included among the eight explicitly reviewed variants. Inventory-row correspondence does not authorize a canonical paper merge or establish relevance.

For the SafetyDPO/AlignGuard title change, five additional bounded arXiv metadata captures include both versions of the same ID: v1 is SafetyDPO and v2 is AlignGuard. The other three linked arXiv records corroborate proceedings titles and full author lists. Raw bodies and hashes are retained in `data/venues/iccv2025-main/inventory-arxiv-evidence/`. The whole edition remains partial until author/source, scope, identity/date and provider gates are resolved.

## Reviewed proceedings discoveries

A later [source-reviewed import](iccv2025-reviewed-discoveries-20261111.md) added DGTalker and Hi-Gaussian using independent official author agreement and exact-title/full-author Crossref DOI evidence. All 4,101 prior active records remain exact. This does not retrospectively change the frozen capture outcomes or reconcile the whole edition. The current catalog has 4,103 active records and six archives.

## Validation and remaining gates

All 480 tests pass with one native-symlink case skipped on this Windows host;
global Ruff lint/formatting (164 files) pass. New checks cover bounded failure
body retention, default strict matching, reviewed-title replay, unchanged source
bytes, stale/tampered review refusal and preservation of author/year checks.

The final capture uses no extra inference or canonical writes. At metadata-capture completion, the catalog was
4,101 active/six archived at raw SHA-256
`bc966ff4d460b33f08a589d3fe5d1133d472c0d89de32c23fb17d6a007770dfd`.
The venue inventory still has four partial cells and 52 pending cells. Original
dates/identities, scope adjudication, proceedings-only insertion review, remaining
inventory discrepancies and DBLP evidence remain open. No watermark, push,
workflow dispatch or deployment advanced.
