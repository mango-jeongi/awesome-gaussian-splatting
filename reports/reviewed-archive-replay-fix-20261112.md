# Exact replay of reviewed merged archive sources

A reviewed merged archive can represent an accidental submission with a different arXiv identifier from its surviving paper. Previously, replaying the archived source still reached ordinary identity matching and failed the differing-identifier guard, even though public alias lookup resolved correctly.

`PaperDatabase.upsert` now recognizes an exact archived source record only after archive validation and exclusion-endpoint checks. When its reviewed disposition is merged, its chain resolves to an active paper and its complete record equals the reviewed archived payload, ingestion is a no-op. It never merges the duplicate's identifiers, dates, citation fields or source metadata into the survivor. General `IdentityIndex` compatibility rules remain unchanged.

Changed archived payloads require explicit review, including altered titles, abstracts, DOI/arXiv identifiers or citation counts. Unreviewed aliases do not bypass contradictory identifiers. Exact duplicate replay does not prevent unrelated valid batch insertions. Excluded archive endpoints remain subject to the existing explicit-review guard.

Eight added regressions exercise these behaviors, including save bytes/mtime preservation. Forty targeted archive/identity/venue tests passed in 1.83 seconds. The full offline suite passed **576 tests with one skip in 49.62 seconds**. Repository-wide lint passed and formatting verified 201 Python files.

The [real DynFOA source replay verification](runs/dynfoa-reviewed-archive-replay-verification-20261112.json) checks both retained primary response hashes, simulates the author-declared accidental-duplicate archive, then verifies zero replay insertions, identical model bytes and all 4,109 active records unchanged. The [source review](../data/reviews/dynfoa-accidental-duplicate-review-20261112.json) remains frozen with the original pre-fix failure evidence.

Canonical data and all provider/public artifacts remain unchanged. Applying the DynFOA archive/aliases, refreshing source-bound aggregate bindings and rebuilding public routes is still pending. No HTTP request, remote action, push, workflow dispatch or deployment occurred. Phase 2/3 remains active.