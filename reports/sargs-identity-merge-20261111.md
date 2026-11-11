# SAR-GS reviewed identity merge — 2026-11-11

The later backfill ID `2506.21633` is merged into the original seed ID
`paper:2025-b16566cdad`. The canonical corpus is now **4,101 active and six
archived**. The original 165-seed scope accounting remains 141 retained, 19
unresolved and five archived; the sixth archive entry is the duplicate backfill
record, not another excluded seed.

The frozen arXiv record and IEEE-deposited Crossref record have the same four
full authors in the same order, compatible 2025 dates and inspected title
variants (hyphen/case and Image/Images). The shared OpenAlex work provides
corroboration, not the sole merge basis. The reviewed publisher title and DOI
remain unchanged. The surviving seed gains its exact arXiv identity, full author
list/abstract, verified June 25, 2025 original date and year-only publication
evidence. No precise journal-publication day is invented.

[Snapshot-bound review](../data/reviews/sargs-identity-merge-20261111.json),
[preparation evidence](runs/sargs-merge-preparation-20261111.json) and
[application/replay receipt](runs/sargs-merge-application-20261111.json) retain
both source hashes, previous/current seed records and canonical digests. Only
the surviving active record changed. The removed record is preserved exactly
in the archive, with aliases redirected to the seed and its successful provider
observation retained. A repeated review is a no-op. The save used the original
canonical compare-and-swap token.

The pre-apply guard exposed stale aggregate seed-ledger metadata from the
190-record era. All 141 reviewed retained-row hashes were checked against the
current canonical snapshot before refreshing the aggregate binding. Its previous
values and entire previous ledger remain in history; no scope disposition was
silently recomputed.

Extraction coverage reconstructed byte-for-byte before the merge and was rescanned
afterward. It now covers 4,101 IDs: 11 processed, 4,080 queued, nine unavailable
in the configured inventory and one unsupported. Every other extraction record
is unchanged, and all 30 prior numeric review decisions remain untouched.
Provider cache/history entries are preserved. Public artifacts still require
rebuilding with the refreshed cache graph; no push or deployment occurred.
