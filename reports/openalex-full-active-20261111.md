# OpenAlex full active due queue — 2026-11-11

The configured authenticated client completed the currently due queue without
errors or rate limits. Three bounded passes attempted 200, 1,000 and 2,815 papers,
using six, 28 and 74 requests respectively (108 total). Provider-reported cost
summed to $0.0108. No credential value was printed or committed. Canonical paper
bytes stayed unchanged throughout.

At final verification, all **4,102 active IDs** have an explicit cache status:
**3,793 `ok`, 277 `not_found`, 32 `ambiguous`**. All retained successful active
observations are fresh under the implemented TTLs. A cache-only replay attempted
zero papers, issued zero requests, reported zero currently due, and preserved the
exact cache bytes. This is time-specific due-queue completion, not permanent
freshness or resolution of misses/ambiguities.

The run receipts retain request budgets, observed results, before/after cache
hashes and unchanged canonical SHA. The
[full verification receipt](runs/openalex-full-active-verification-20261111.json)
binds the final cache SHA. Individual passes are
[pass 1](runs/openalex-due-20261111.json),
[pass 2](runs/openalex-due-pass2-20261111.json) and
[pass 3](runs/openalex-due-pass3-20261111.json).

There are **1,086 genuine observed zero citation counts**. They do not retroactively
validate the 4,064 legacy canonical zeros. Genuine history supports 3,690 fresh
single snapshots and 103 histories without a qualifying 7–45-day separation;
309 active IDs have no successful history. **No velocity is eligible yet.**
The account key's current presence does not establish Actions secret rollout.
Semantic Scholar and Gemini credentials are absent from the local configured
environment; neither provider was silently substituted with OpenAlex.

## Cross-canonical identity gate

An in-memory cache-only citation/graph preview failed closed before any save:
new OpenAlex publication DOI evidence would collide across `2506.21633` and the
original seed `paper:2025-b16566cdad`. The
[complete cross-record audit](runs/openalex-cross-canonical-identity-audit-20261111.json)
found one shared OpenAlex work (`W4416960543`) and one prospective DOI collision,
`10.1109/tgrs.2025.3639636`. These are SAR-GS title variants. The frozen Crossref
registry record and arXiv record both list Aobo Li, Zhengxin Lei, Jiangtao Wei and
Feng Xu, which provides a strong primary-identity review lead beyond the shared
provider match.

No merge was applied. The final `ok` count measures per-ID cache mappings, not
3,793 distinct publications or completed corpus deduplication. A reviewed merge
must retain the original seed ID, preserve the removed record and aliases, enrich
its independently verified original preprint date, and refresh seed/extraction
coverage. The archive/alias invariants and replay must pass before publication.

The public graph still uses materialized canonical references. Refreshed cache
references have not been projected into public graph artifacts, and no rebuilt
portal or deployment is claimed. Both the cross-record identity review and the
cache-to-public-graph projection remain required work. No push, release or remote
workflow dispatch was performed.
