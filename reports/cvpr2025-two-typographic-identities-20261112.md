# AuraFusion360 and BG-Triangle: explicit CVPR identity application

Two source-bound title variants now resolve to existing stable IDs, without importing duplicates or broadening automatic matching rules:

| CVF title variation | Existing ID | Explicit substitution |
| --- | --- | --- |
| AuraFusion360 | 2502.05176 | `360deg` → `360°` |
| BG-Triangle | 2503.13961 | `Bezier` → `Bézier` |

The [source review packet](../data/reviews/cvpr2025-two-typographic-identity-reviews-20261112.json) replays both retained official pages through the production parser, checks response hashes, verifies every ordered author and verifies the complete abstract after only the stated substitution. This is agent source review, not independent human validation. Zero new HTTP requests were made.

The application adds two explicit CVF aliases and reviewed CVPR 2025 publication year/precision evidence. BG-Triangle also gains its missing venue. Original titles, abstracts, ordered authors, stable IDs, original exact dates, links, tags and identifiers remain unchanged. No exact proceedings day or canonical DOI is established by this review. AuraFusion360's existing provider-owned public DOI remains projected from its cached OpenAlex observation; it was not newly verified or written to canonical metadata here.

The [application receipt](runs/cvpr2025-two-typographic-identity-application-20261112.json) records recoverable baseline Git revision, input/output hashes and exact changed fields. All other 4,105 records, six archives and previous alias targets remain exact. All 165 seed rows and 154 retained hashes verify unchanged. Extraction records/tasks are unchanged; seed/extraction aggregate source bindings were refreshed. A fresh save preserves bytes and mtime. Provider observations were not refreshed or altered.

The [new gap audit](../data/reviews/cvpr2025-after-typographic-identities-gap-audit-20261112.json) has 181 matched and 114 unmatched non-excluded leads; 10 unmatched automatic includes still need source/scope adjudication. The 59 matched venue/year gaps remain because these two previously unmatched sources enter the matched set with their year fields resolved. Frozen source captures, timestamps, policy and prior audit reports remain intact. CVPR 2025 inventory reconciliation is not complete.

Build succeeded. [Production public-artifact integrity verification](runs/cvpr2025-two-typographic-public-verification-20261112.json) checks all referenced descriptors, both aliases, original bibliography and reviewed publication fields, all canonical tags and unchanged provider cache bytes. An initial helper assertion incorrectly expected public DOI to equal canonical DOI; inspection confirmed the existing cache-owned build projection, and the corrected verifier checks that projection explicitly. No production code changed. The prior full suite passed 564 tests with one skip; it was not rerun for this data-only application. No new browser QA, deployment or performance benchmark is claimed.

The [current coverage receipt](runs/coverage-after-cvpr2025-typographic-identities-20261112.json) verifies consumed-input hashes with current canonical/seed/extraction bindings. The catalog remains 4,107 active records. All remaining Phase 2/3 gates remain open as listed in the coverage report.
