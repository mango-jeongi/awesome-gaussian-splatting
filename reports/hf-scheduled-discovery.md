# Scheduled frozen HF discovery

The `discover-huggingface` CLI now uses a durable frozen-window session with
explicit request/time/lookback budgets, source response hashes, observation
timestamps, relevance dispositions, optional exact import preview, and workflow
summary output. The existing legacy extractor remains available for compatibility.
Discovery and preview never write canonical papers. Reviewed import still uses
the existing snapshot/policy/source/result-bound application command.

A pending window keeps its dates across UTC-day changes and cache expiry. Each
completed day points to an immutable response digest; every retained response is
validated before further provider traffic. The per-day mutable cache can change
without altering an active window or its preview. A changed window configuration,
regressing cutoff, corrupt hash, or future/naive observation fails safely.

The default first window explicitly samples seven recent UTC dates. After a
finished window, the next window advances by at most seven days, preserving
seven-date overlap. Thus outage recovery covers the missing dates in bounded
windows instead of jumping to the latest week; a default catch-up window has at
most14 dates. Persistent run receipts retain prior windows. Sampled dates are not
a claim of all-time HF completeness. A full100-entry day remains possibly
truncated: the window may finish sampling, but inventory_complete remains false.

The weekday arXiv workflow and seven-day provider workflow now run discovery
with at most10 requests/120 seconds, then save a reviewable proposal. Existing
signal refresh budgets remain separate (15 requests/270 seconds across three
providers), so combined HF discovery plus signal admission is at most25 requests
and390 seconds, excluding arXiv ingestion and in-flight/lock completion. Both
writers share repository concurrency, retain checkpoints/source evidence under
`data/ingestion/huggingface`, and commit run reports. Failures are visible while
checked cached publication may proceed. Neither workflow auto-applies a proposal.

## Validation and live evidence

All324 tests passed in24.42s; seven new regressions verify frozen resume beyond
UTC/cache expiry, bounded outage recovery without date gaps, hash/config fencing
before traffic, honest full-page status, immutable preview source selection, and
workflow budgets/persistence/review separation. Lint/format109 files, artifact
build, schema190 records, four workflow YAMLs and17 Bash blocks pass.

The live canary froze `[2026-11-04,2026-11-10]`: the first two requests left a
pending checkpoint with35 candidates. Five more requests completed the same
window, retaining exactly the first two response hashes and accounting for158
unique candidates. All seven daily responses were below the endpoint cap. The
preview reports2 include /155 exclude /1 review, with2 proposed existing-record
updates,0 insertions, and156 no-ops/dispositions. No proposal was applied.

Canonical190 active/five archived and raw SHA-256 remain unchanged. Source
classification uses the current relevance policy and verified provider metadata;
provider prose is not copied into canonical author abstracts. The canary cache is
local scratch, separate from deployment state. No push/dispatch/deployment occurred.
Reviewed HF applications, historical/venue completeness, S2 live access and real
citation-history maturity, workflow/secrets rollout, and broader M0-M5 acceptance
remain open.
