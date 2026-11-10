# CVPR 2023 main-track evidence — 2026-11-10

The official [CVF proceedings listing](https://openaccess.thecvf.com/CVPR2023?day=all)
contains 2,353 records (6,273,840 captured bytes), frozen at SHA-256
`8284937abea6f8052da24f58802f619bb7b4261d80ee52305f31b428a2cfe4c5`.
The current frozen relevance policy is
`388dfe1507123d4bfb7e4bfac474e94afa84321eb5067d8a5db8f4622d8b4d0f`.
Title screening produces zero include, 90 review and 2,263 exclude dispositions.
These exclusions are title-screen results, not an independently audited recall
estimate or evidence that all relevant NeRF foundations have been reviewed.

## Publication capture

A paced, bounded pass attempted all 90 selected official publication pages and
verified 89. Their full-metadata scope dispositions are all review: inclusion as
a foundation/adjacent method needs explicit justification. No canonical record
was imported, archived or changed. All captured response bodies are hash-addressed
under [the source cache](../data/venues/cvpr2023-main/), with observation timestamps
and frozen listing/policy bindings in its state.

NeRFVS (`Yang_NeRFVS_Neural_Radiance_Fields_for_Free_View_Synthesis_via_Geometry`)
had a transport failure. Its retry deadline is recorded in `state.json`; the
failure was not bypassed or represented as an absent paper. A zero-request replay
revalidated all 89 retained captures and left the pending count at one.
`selected_metadata_complete` and `venue_inventory_reconciled` remain false.

## Independent inventory comparison

The [official accepted-papers page](https://cvpr2023.thecvf.com/Conferences/2023/AcceptedPapers)
reports 2,359 accepted papers and contains 2,359 table rows. Its frozen 3,695,645-byte
capture has SHA-256
`dcac4f4fad649809685163f58dfd69125991b64f3d8f83edf23c34056cc60a63`.
The [comparison receipt](../data/venues/cvpr2023-main/independent-reconciliation.json)
accounts for:

- 2,344 normalized-title matches, with 14 full-author-sequence differences retained.
- Nine inspected display variants (degree sign versus `deg`, or diacritics), each
  with a matching complete author sequence after punctuation/diacritic normalization.
- Six accepted-only records with no mapped proceedings counterpart:
  Clothing-Change Feature Augmentation for Person Re-Identification; DeltaEdit;
  RiDDLE; Semantic Prompt for Few-Shot Image Recognition; VideoFusion; and Vision
  Transformer With Super Token Sampling. Full source titles and authors are in
  the receipt. Their absence is not classified as withdrawal without evidence.
- No remaining proceedings-only record after the nine display correspondences.

No canonical identity or aliases were inferred from these source comparisons.
`src.venue_inventory.reconcile_inventory` supplies the reproducible UTF-8 parser
and comparison; it splits both middle-dot author separators, rejects normalized
title collisions and keeps author mismatches/unmapped records visible. Its five
offline regressions pass. The accepted listing's announced total and body agree,
but the six accepted-only cases keep the cross-source reconciliation incomplete.

## Coverage and reproduction

`config/sources.yaml` records this main-track cell as crawled/partial. Three
venue/track cells now have partial evidence; 53 remain pending. Workshop coverage,
DBLP discovery, arXiv/source identity resolution, reviewed foundation decisions,
non-arXiv import and exclusion-recall audit remain open for this edition.

Resume capture using the committed `listing.<sha>.html`, the same override policy
and `data/venues/cvpr2023-main` cache with `src.cli discover-cvf`. Use
`--max-requests 0` for offline checksum/model verification. Never clear the source
retry deadline just to force another request.

Canonical input remains 4,102 active records, five archived, raw SHA-256
`9e0da7759d593cfa4d95f50dc30383a059b32392de22f9595cfc9a638c60daca`.
No model staging, repository push, remote workflow dispatch or deployment occurred.

Validation: all 420 tests passed in 113.88 seconds. Canonical schema validation,
artifact build, Ruff lint/format and source-inventory count assertions pass. The
canonical raw digest is unchanged. The new CVPR 2023 source link is generated from
the README builder.
