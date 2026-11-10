# Historical arXiv source capture and reviewed application — 2026-11-10

The completed frozen query covers 340 monthly intervals from August 1998 to the
exclusive cutoff 2026-11-10T00:00:00Z. All cached pages were revalidated without
network before application. It contains 4,466 unique source candidates, matching
the initial broad-query count. The comparator query reported 3,996 under inclusive
API bounds; that count is a separate diagnostic, not an inclusion target.

The [source checkpoint](../data/ingestion/backfill/full-v3-20261110/crawl/checkpoint.json)
and original policy snapshot remain unchanged by the later relevance review.
The [application ledger](../data/ingestion/applications/historical-v3-reviewed-20261110/proposal.json)
uses a separate policy snapshot, including two previously reviewed GS applications
and 23 exact-identity review holds backed by captured author abstracts.

| Application result | Count |
| --- | ---: |
| Source candidates | 4,466 |
| Include | 4,045 |
| Exclude | 41 |
| Review pending | 380 |
| New canonical records | 3,800 |
| Updated existing source identities | 213 |
| Source identities merged into existing canonical IDs | 32 |
| Active records after application | 4,102 |
| Archived records preserved | 5 |

The [import receipt](../data/ingestion/applications/historical-v3-reviewed-20261110/import-receipt.json)
records the before/after hashes and rollback snapshot. Existing IDs, nonempty core
identities and publication fields, and protected metadata were preserved. Replay
produced zero inserts, updates or merges. The original 165-record baseline remains
140 retained, five archived and 20 unresolved. All 140 current retained-record
hashes were verified; 118 metadata refreshes retain prior review and canonical
snapshots without changing scope dispositions.

The real 4,102-record compact index is 1,619,335 bytes (430,180 bytes gzipped).
This is a payload measurement, not a browser interaction or release-performance
claim. Extraction coverage is 11 processed, 4,081 source-materialization tasks,
nine unavailable in the configured inventory and one unsupported input. Those
source tasks are not completed downloads or claimed parser jobs.

Both unchanged agent-reviewed relevance fixtures meet the specified thresholds:
development include precision 1.00 / recall 0.98, challenge precision 1.00 /
recall 1.00. These purposive fixtures and targeted abstract reviews do not establish
independent human or population accuracy. The newly held comparison-only and
ambiguous cases still require scope or full-method adjudication.

This is a local branch checkpoint. Nothing was pushed or deployed. Historical
query capture is complete; broader venue recall/reconciliation, 380 historical
reviews, 20 baseline reviews, canonical v2 rollout, provider coverage and measured
velocity, expanded worker extraction, portal performance and release/rollback
gates remain open. The graph still contains only 28 previously observed edges;
expanded citation coverage is not claimed.
