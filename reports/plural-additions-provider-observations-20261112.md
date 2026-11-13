# Genuine OpenAlex observations for the two recovered GS papers

One actual bounded OpenAlex request enriched Wonderland `2412.12091` and Particle-Grid Neural Dynamics `2506.15680`, costing $0.0001. Both lookups succeeded; no miss, ambiguity, error or rate limit occurred. The request was not repeated when an approval-service usage-limit error temporarily prevented inspecting the completed receipt. Read-only inspection succeeded after continuation.

| Paper | Provider work | Observed citations | Returned references |
| --- | --- | ---: | ---: |
| Wonderland | W4413146758 | 80 | 63 |
| Particle-Grid Neural Dynamics | W4414079057 | 25 | 20 |

Both genuine observations are dated **2026-11-12T22:48:50.194068Z**. Each has one sample and no eligible citation velocity. Returned reference counts describe provider evidence, not verified full bibliography completeness. Provider counts remain separate from default canonical citation fields.

The [observation verification](runs/plural-additions-observations-verification-20261112.json) proves all 4,113 prior cache observations and 3,904 prior history samples are preserved exactly. Two new samples yield 3,906 total. No series was reassigned or spliced. Canonical bytes remain unchanged at SHA256 `7b9171117e22cdf03e8a09613d638e29adf946167046243a7db120e4a63f92bb`; seed and extraction source bindings remain current. The [actual request receipt](runs/plural-additions-openalex-20261112.json) retains the bounded request outcome and cost.

Build succeeded. [Public verification](runs/plural-additions-enriched-public-verification-20261112.json) checks all 81 descriptors, original bibliographies, tags, Wonderland alias, both actual citation counts and exact observation timestamps. The projected graph now has 27,401 directed edges. No new browser QA, performance benchmark or live deployment is claimed. The [current coverage receipt](runs/coverage-after-plural-observations-20261112.json) verifies every consumed input and reports current active denominators separately from seven archived identities retained in cache.

No production code changed and the preceding full suite passed 568 tests with one skip. This provider-data change used actual old/new observation/history comparisons, canonical byte checks and rebuilt-artifact verification rather than repeating unchanged unit tests. No PDF, extraction job, push, workflow dispatch or deployment occurred. Catalog size remains 4,108 active and seven archived; remaining Phase 2/3 gates stay open.
