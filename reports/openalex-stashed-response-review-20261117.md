# Review of 18 stashed OpenAlex responses — November 17, 2026

**Reject all 18 edits as stale metadata reversions.** They are not new provider
observations. Every stashed response exactly matches older upstream `6b39ff6`;
every accepted response exactly matches both the preserved pre-integration local
source and current upstream `8fe82af`. No API request was needed for this review.

The complete stash cache is SHA-256
`a048df7af6318085da3f8321e22fc55d5fc40975778b762f24c29171a8f73bd1`.
Its parent is `491eac5`. The differences are within 18 existing work responses: authorship/affiliation/ORCID
and location/license/publisher metadata, plus EvoGS DOI, publication type and raw
reference-list changes. Citation history, signal observations, citation counts,
titles and OpenAlex work identities are identical to the parent. The per-work
report lists every changed path and both values.

For EvoGS (`W7206155217`), the stash would revert the journal DOI
`10.1111/cgf.70602` to the arXiv DOI, change `article` back to `preprint`, and
replace the accepted raw reference list with an empty list. Those are stale
source reversions too; they are not merely formatting changes. No canonical or
provider response was modified during this review.

## Provenance and reproduction

The original ad hoc merge routine reread the live cache once per work. An
interrupt was requested at 19:09:01 UTC and returned exit 130, then a corrected
routine ran against the same file. That exit code does not independently prove
every descendant process stopped. The corrected routine freezes its comparison
snapshot instead of rereading a file another writer can replace.

Offline reconstruction from the retained inputs proves two facts:

- The corrected merge reproduces accepted checkpoint `400202a` byte for byte
  (SHA-256 `ca9daad2c33433b199e3ef8a0ce734534ed82a0322deabfb2ad3f72da7a5b247`).
- The original routine's per-work disk-read behavior, with a modeled transition
  from the old disk snapshot to the corrected snapshot, reproduces the complete
  stashed cache byte for byte. The transition is a simulation, not an observed
  execution schedule. A replay using only the merged snapshot does not match.

The content lineage is established. A late write from the abandoned ad hoc merge
is a supported explanation for the appearance of these bytes, but the precise
writer/process timing is not independently proven. This distinction does not
change disposition: all 18 edits restore older source payloads, introduce no new
observation evidence, and would undo the source-preserving accepted result.

## Disposition and preservation

The resolved stash entry was removed from the pending stash list only after its
exact commit was preserved under the **local-only** ref
`refs/archive/openalex-stale-responses-20261117`, pointing to
`6cf09b3a3246422f96d99dd9c3172779b76e928c`. The original SHA-verified standalone
backup remains under `Documents/Codex/2026-11-17/reconciliation/`.

The original routine, offline replay program and receipts are retained locally
under `Documents/Codex/2026-11-17/openalex-stash-review/`. No routine was installed
or scheduled, no live provider/canonical file was edited, and no stale value was
accepted. This is a review disposition, not new metadata enrichment.

[All 18 responses and field differences](runs/openalex-stashed-responses-review-20261117.json) ·
[Replay hashes and limitations](runs/openalex-stash-merge-replay-20261117.json)
