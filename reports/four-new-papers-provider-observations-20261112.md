# Provider observations for four recently added papers

One bounded OpenAlex request enriched all four previously unobserved active papers, costing $0.0001. All lookups succeeded with no misses, ambiguities, errors or rate limits. The [actual request receipt](runs/four-new-papers-openalex-20261112.json) records limits of four requests and 45 seconds; only one request was consumed.

| Paper | OpenAlex work | Observed citations | Returned references |
| --- | --- | ---: | ---: |
| FreeSim | W4413147368 | 25 | 20 |
| Sketch and Patch | W4408938892 | 7 | 33 |
| GPAvatar | W4413145248 | 4 | 0 |
| GPVK-VL | W4413146292 | 0 | 0 |

All observations are genuine at **2026-11-13T02:43:15.696594Z** (November 12 local time). GPVK-VL's zero is an observed value, not an unavailable count. Empty returned reference arrays do not prove absent bibliographies. Each new identity has exactly one sample and no eligible citation velocity. Provider counts remain provider-owned rather than copied into canonical bibliographic fields.

The [preservation verification](runs/four-new-papers-observations-verification-20261112.json) checks every old observation and history sample: 4,115 prior observations and 3,906 prior samples remain exact. Four new samples yield 3,910 total. New work identities are distinct from each other and every prior successful identity; no histories are spliced or reassigned. Canonical bytes remain unchanged at `68feccef30c3dad4f245a90e2fa8e9cc629de88608fe341cf3c5f1e9b9a6747c`.

Build succeeded. [Public verification](runs/four-new-papers-public-verification-20261112.json) checks all 81 descriptors, original metadata/date precisions, all four actual counts/timestamps and the genuine zero. Corrected Sketch/Lapis DOI ownership remains intact. The projected graph now has 27,428 directed edges. No new browser QA, performance benchmark or live deployment is claimed. The [current coverage receipt](runs/coverage-after-four-new-observations-20261112.json) verifies all consumed-input hashes and source bindings.

No production code changed; the prior full suite passed 576 tests with one skip. Actual old/new cache comparisons, canonical byte checks and rebuilt public integrity checks validate this provider-only change. No PDF/parser/remote-worker action, push, dispatch or deployment occurred. The catalog remains 4,112 active records and eight archives. All remaining Phase 2/3 scope and gates remain active.
