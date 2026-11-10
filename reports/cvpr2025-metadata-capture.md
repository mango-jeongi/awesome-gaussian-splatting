# CVPR2025 official metadata capture

Completed the title-prioritized set of148 official CVF paper pages from a frozen
2,871-entry main-proceedings listing. The current policy screens101 include /47
review /2,723 exclude at title level. All148 pages verified title, complete
listing author sequence, venue/year/track, matching PDF URL and optional exact
external identifiers. Every selected page supplies an official author abstract;
101 pages provide arXiv links and none supplies a citation DOI. Full-source scope
classification now yields117 include /31 review. No canonical import occurred.

`discover-cvf` exposes the reusable bounded path. It validates saved response
hashes and timestamps before traffic, retains listing/policy/edition binding,
checks2 MB response and elapsed/request budgets, paces one second after each
response, and saves each page before advancing. Failures retain retry deadlines;
full-source identity conflicts cannot silently become verified. Official abstract
text is kept with source evidence; absent abstracts are not fabricated.
Publication-year precision stays independent of original preprint dates.

The live pass used148 paced requests with0 failures. A subsequent CLI run with
request budget0 revalidated all148 sources and publication contracts without
network traffic. Eight new regressions cover resume/replay, hash/policy fencing,
retry deferral, abstract provenance/absence/ambiguity, explicit pacing, and the
actual CLI's zero-budget report. All348 tests pass in24.88s; lint/format116 files,
artifact build and schema190 records pass.

## Independent inventory comparison

The current [official accepted-paper table](https://cvpr.thecvf.com/Conferences/2025/AcceptedPapers)
and CVF proceedings listing each contain2,871 unique titles.2,861 normalized
titles match directly, all with shared author-surname evidence. Ten visible
title variants were paired one-to-one using complete or all-but-one full-author
name agreement and explicit title review. Eight have equal normalized complete
author-name sets. Two retain source author-name differences (a middle initial;
and one first-name change among17 authors) without asserting person aliases.
Author order and punctuation/title differences remain source observations.
This accounts for every row in both current inventories.

The separate [official technical-program announcement](https://cvpr.thecvf.com/Conferences/2025/News/Technical_Program)
reports2,872 accepted papers. The one-paper difference is unresolved; no withdrawal,
publication omission or administrative cause is inferred. Accordingly the overall
venue inventory remains `reconciled:false`, with partial coverage in the source
configuration. Raw accepted-table HTML, its SHA-256, paired differences and
comparison evidence are retained beside the proceedings capture.

## Limits and next work

Selected metadata completion does not prove recall for the2,723 title-screened
exclusions, resolve the31 scope cases, establish all-time GS coverage, or complete
the other55 venue/year/track cells. The101 arXiv links still need exact original
preprint metadata and identity/date review before bulk canonical application.
No title variant or author difference was used to rewrite canonical records.
Canonical190 active/five archived and raw SHA-256 remain unchanged. No commit,
push or deployment occurred. Full M0-M5 and real citation-history maturation
requirements remain open.
