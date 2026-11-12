# Complete frozen non-include audit

The reviewed historical application contains 4,466 candidates: 4,045 includes, 380 reviews and 41 exclusions. This audit covers **all 421 original non-includes** against current canonical identities and current policy, without altering the frozen decisions. The earlier automatic-import packet has a different policy and counts (4,066/359/41); it is a separate epoch and is not substituted for the coverage-bound reviewed application.

The [machine audit](../data/reviews/frozen-noninclude-candidate-audit-20261112.json) binds the application, canonical and policy hashes, retains complete candidate abstracts/authors and source locations, verifies 366 cached page hashes and preserves 18 identical repeated-record captures. Conflicting repeated payloads would fail the audit. All 421 unique source identities were recovered; no HTTP requests occurred.

Current policy yields 41 exclusions, 375 reviews and five includes. Twelve candidates match current canonical records. Of the five current includes, three match existing records and two raise explicit identity conflicts; there are **zero unambiguous unmatched current includes**. Automatic relevance still does not establish a merge or import decision.

Two source-backed false negatives use the plural phrase `Gaussian Splattings`, which the current word-boundary pattern does not recognize:

- **Wonderland, 2412.12091** remains under review despite explicitly predicting Gaussian scene representations from video-diffusion latents in a feed-forward reconstruction model. It was fetched, not lost during pagination. Its official CVF abstract independently describes Gaussian splatting use.
- **Particle-Grid Neural Dynamics, 2506.15680** remains excluded despite explicitly coupling its dynamics framework with Gaussian splatting for visual rendering and generating action-conditioned videos from RGB-D object interactions.

Both are reviewed as direct GS scope from the retained primary abstracts, pending policy regression evaluation and canonical application. No performance claims were accepted. The old review/exclusion outcomes remain visible; no annotation or frozen policy was rewritten to conceal them. A future plural-pattern change must preserve context and competing-method checks, quantify candidate/benchmark effects, and keep frozen capture policies distinct.

**Sketch and Patch, 2501.13045** currently raises `Contradictory identifiers for 2408.14823`. **DynFOA, 2604.02781** raises a title-match review. Neither was imported or forcibly matched; primary identifier/author review is required. These are separate from the plural-pattern misses.

Canonical data, provider observations, source captures and policy are unchanged. This is complete coverage of the declared non-include inventory, not independent relevance accuracy or exhaustive literature coverage. No tests were needed for this read-only source audit. The two missed methods and two identity conflicts are concrete remaining actions; Phase 2/3 remains unfinished.