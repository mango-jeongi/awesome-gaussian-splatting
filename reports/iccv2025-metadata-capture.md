# ICCV 2025 main-track capture and title-screen recall gap — 2026-11-10 Pacific

The official [CVF listing](https://openaccess.thecvf.com/ICCV2025?day=all) contains
2,701 records (7,692,642 frozen bytes), SHA-256
`e684fe760c417a35c2f1e9a5acb3015a192fce10e566086e2d4bf7f78cbb97fe`.
The unchanged topic-policy digest is
`388dfe1507123d4bfb7e4bfac474e94afa84321eb5067d8a5db8f4622d8b4d0f`.

## Original title-priority epoch

The frozen title screen yields 108 include, 41 review and 2,552 exclude decisions.
All 149 selected publication pages were fetched, hash-verified and parsed with
matching title/authors/edition/track/PDF URL. Their full-abstract policy decisions
are 124 include and 25 review. One hundred pages link arXiv IDs; this is link
coverage, not independent preprint identity/date verification. Source state and
responses are retained in `data/venues/iccv2025-main`. No paper was imported.

A catalog cross-check found 150 normalized-title matches in the full listing.
Forty-six active catalog papers whose full stored text passes the policy had
been excluded by title alone. They are review leads, not 46 independently verified
false negatives: source abstracts/revisions and actual scope still require checks.
The [tail audit](../data/venues/iccv2025-main/known-catalog-title-exclusion-review.json)
retains titles, source URLs and canonical IDs. It demonstrates why title-priority
fetch completion cannot be used as complete abstract-based venue coverage.

## Separate full-metadata epoch

`discover-cvf --all-metadata` now selects every listed publication, while retaining
request/time/response budgets, pacing, per-page hashes and retry deadlines. The
mode is frozen before traffic, even for zero-request runs and legacy inventory-only
checkpoints. Existing title-priority caches cannot silently switch modes. Their
original listing/policy evidence is preserved.

A new epoch, `data/venues/iccv2025-all-metadata`, reuses all 149 verified bodies
with exact hashes and original observation timestamps. A seed receipt binds the
original state. Two bounded passes (40 then 120 requests) brought it to:

- 309 verified pages, 2,392 pending, zero fetch failures.
- Full-metadata policy dispositions: 125 include, 29 review, 155 exclude.
- One directly observed title-screen rescue: SpatialSplat (`2505.23044`). Its
  official abstract passes the unchanged policy despite its excluded title.
  [Source evidence](../data/venues/iccv2025-all-metadata/title-screen-rescue-evidence.json)
  retains the publication and capture hashes. This is not a population recall
  estimate, manual scope adjudication or an automatic canonical inclusion.

The all-metadata checkpoint is incomplete and must be resumed with the explicit
mode and same frozen listing/policy. No source watermark or corpus import advanced.
The original title-only decisions remain labelled as such in the inventory; full
abstract dispositions are separate.

## Independent inventory comparison

The [official accepted table](https://iccv.thecvf.com/Conferences/2025/AcceptedPapers)
also has 2,701 rows, frozen at SHA-256
`b4aa86509a1c613e884f5bea41bc8952770d7754ce757431ffac73b30065331e`.
The [comparison](../data/venues/iccv2025-main/independent-reconciliation.json)
retains 2,677 normalized-title matches, seven inspected subscript/degree/diacritic
display correspondences with matching full author sequences, and 17 unmatched
rows on each source. One candidate typography match has different authors and
remains ambiguous. The exact-title set has 504 author-list differences, including
name expansion, order and other source variations; they are not silently repaired.
No canonical alias or identity is asserted from this comparison. Equal aggregate
counts therefore do not establish reconciliation.

## Verification and remaining work

All 455 tests passed in 35.57 seconds after the mode/checkpoint changes; global
Ruff lint/formatting (150 files) pass. Four new regressions cover opaque-title
recovery, mode fencing in both directions and a legacy zero-request epoch.
Canonical 4,102 active/five archived stays unchanged at raw SHA-256
`9e0da7759d593cfa4d95f50dc30383a059b32392de22f9595cfc9a638c60daca`.

The inventory now has four partial cells and 52 pending cells. ICCV 2025 remains
partial: complete the 2,392-page backlog, reconcile unmatched/author variants,
verify identities/original dates, review scope and actual new proceedings
candidates, and obtain DBLP source evidence. A page without an arXiv link is not
proof of a paper without a preprint. No model service, push or deployment was
performed by this work.

## Follow-up full-metadata checkpoint — 2026-11-11

A further invocation capped at 500 requests added 497 verified responses. The
completed epoch now has **806 verified pages, 1,895 pending, and three failed
fetches** (the failures are included in pending). Each transport failure has a
one-hour retry deadline in state; none was retried immediately. A subsequent CLI
replay used zero requests and reverified every retained body against its hash.
The original invocation's terminal output was unavailable; the retained
[checkpoint receipt](runs/iccv2025-full-metadata-pass-20261111.json) explicitly
records that limitation rather than presenting the cap as a measured request log.

Current automatic full-metadata dispositions are 137 include, 41 review and 628
exclude. Thirteen title-excluded records now pass the full-text policy. These
are **policy rescue leads**, not thirteen adjudicated GS papers: papers can
mention GS as a baseline, and Radiant Foam in particular requires review of its
competing representation. Their full abstracts and response hashes remain in
the rescue evidence. No policy relaxation, identity assertion or canonical import
was performed. The 309-page figures above describe the previous checkpoint.

The configured source inventory now points to this partial 806-page checkpoint.
Canonical 4,102 active/five archived remains byte-identical. The remaining
1,895 pages, retry-deferred failures, independent inventory discrepancies,
identity/original-date resolution, source scope review and DBLP evidence remain
open. The prepared Gemma real-page diagnostic is a separate, unexecuted activity.

## Second capped follow-up — 2026-11-11

The next live invocation completed all 500 permitted requests: 497 additional
responses verified and three additional transport failures deferred. Its original
invocation summary is retained this time. A zero-request replay using the frozen
policy file verified **1,303/2,701 pages**, with **1,398 pending** (including six
retry-deferred failures). No retry deadline was bypassed.

The [second-pass receipt](runs/iccv2025-full-metadata-pass2-20261111.json) binds the
state/report hashes, complete invocation summary and retry deadlines. Current
automatic dispositions are 150 include, 51 review and 1,102 exclude; 26
previously title-excluded records pass the abstract policy. They remain scope
review leads, not 26 newly accepted papers. The canonical catalog stays unchanged.
The earlier 806-page figures describe the preceding checkpoint.

A later MASt3R foundation adjudication changed the root policy. The existing ICCV
epoch retains digest `388dfe1507123d4bfb7e4bfac474e94afa84321eb5067d8a5db8f4622d8b4d0f`;
resumption must pass its recorded frozen override file explicitly. The final
zero-request replay proved that frozen policy still matches the epoch. No source
coverage watermark, corpus import, push or deployment advanced.
