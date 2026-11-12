# Semantic Scholar access probe — 2026-11-11

A single anonymous batch request attempted 40 due papers after the earlier retry
window. All 40 received rate-limited states; there were no successful observations,
confirmed misses or invented zero counts. The client made exactly one request and
retained per-paper retry deadlines. Existing successful data, if any, is preserved
by the adapter; this cache currently has none.

The active cache now contains 41 rate-limited entries, including the previous
one-paper probe, against 4,101 active papers. The remaining 4,060 have no cache
entry. This is source-access degradation, not evidence that those papers lack
Semantic Scholar records or influential citations. No authenticated key is
configured locally, and authenticated rollout remains open.

[Probe receipt](runs/semanticscholar-anonymous-probe-20261111.json) binds the exact
before/after cache hashes and unchanged canonical source. The
[offline public status build](runs/semanticscholar-status-public-build-20261111.json)
updated signal/trending availability while preserving graph artifacts and the
projected model hash. No OpenAlex observations were substituted for this provider,
no retry loop was launched, and no public deployment occurred.
