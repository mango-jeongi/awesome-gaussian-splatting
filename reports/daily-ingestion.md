# Daily updated-window ingestion

The `daily` command scans arXiv in descending `lastUpdatedDate` order until it
crosses the previous successful watermark minus seven days, or exhausts the
source. It replays every saved page before preparing a canonical import. Both
passes must agree on records, update timestamps, ordering, counts, and offsets.
The window uses update timestamps, so revisions to old publications are included
without changing their original publication dates.

Initialize an explicit coverage boundary once:

```sh
uv run python -m src.cli daily --since 2026-11-02 --dry-run --max-requests 20
```

Use `daily` without `--since` for later passes. A pending run retains its initial
cutoff and resumes its scan or verification cursor. A completed run starts a new
window from its successful watermark minus the overlap; a long outage never
clamps coverage to the latest week. Daily initialization does not establish
historical completeness. The workflow explicitly bootstraps only the previous
seven UTC calendar days when neither state nor a watermark exists.

Each network dispatch is charged durably before sending and uses one attempt
through the shared arXiv rate gate. Request and elapsed-time budgets are bounded.
The elapsed budget controls dispatch admission; an in-flight request can finish
after it. A killed dispatch retries its unacknowledged cursor while preserving
its previous charge. Required-source failures leave the watermark unchanged.
Source drift archives the failed run and starts a new scan on the next invocation;
immutable content-addressed page evidence remains available. `--restart` can also
abandon a pending run explicitly. Query/policy changes cannot silently reuse an
existing watermark; coverage migration is required.

Canonical publication uses the shared identity, archive, relevance, and reviewed
metadata rules. Every candidate receives a disposition. Review/exclusion outcomes
remain in the import receipt and original source-page cache. A dry run saves this
evidence but writes neither canonical records nor a watermark. Successful writes
are reloaded and hash-validated before the watermark advances. A crash between
canonical save and watermark publication safely replays through idempotent upsert.

The daily workflow persists the checkpoint, source evidence, import receipts, and
failure diagnostics on `feed` after build/validation/tests, then reports a failed
required source as a failed workflow. A budget-limited scan is resumable unfinished
work; it is not reported as complete coverage. Generated-path commits include
`data/ingestion/daily`. Other controlled arXiv executors must still coordinate:
the local rate gate is not a distributed lock.

## Current validation and rollout limits

The 2026-11-09 live dry run scanned the explicit UTC window
`[2026-11-02, 2026-11-09)` in two requests (one page and its exact replay).
It prepared 48 dispositions: 43 included and 5 requiring review, with 13 proposed
insertions, 29 updates, and one identity merge. These are proposals only. The
192-record canonical catalog and its SHA-256 remained unchanged, and no watermark
was created. The live canary is separate from production checkpoint storage.

Twelve daily regression tests cover more than 60 records, old-paper revisions,
interruption/resume, empty inventory, tampered source evidence, duplicate/short
pages, changed pages, automatic drift recovery, publication failures, a crash
after canonical save, invalid/future/regressing cutoffs, and missed-run overlap.
The local annotated relevance benchmark now passes its numeric targets, with
review and sampling limitations documented in reports/relevance. Final workflow
deployment and broader release gates remain outstanding. This local implementation is not a deployed coverage claim.

## Weekly indexing reconciliation

`weekly-reconciliation.yml` schedules a Saturday 02:00 UTC pass on `feed`,
before the Sunday release. It uses the same verified scanner with a 30-day
overlap, but stores its own cursor, page evidence, receipts, and successful
watermark in `data/ingestion/weekly`. First initialization explicitly starts
30 UTC calendar days ago. Subsequent runs use the previous weekly watermark
minus 30 days; an outage does not truncate recovery. Daily state is untouched.

Each pass admits at most 60 requests and 900 seconds by default, sharing the
repository-wide non-cancelling writer group. Incomplete scans resume on a later
scheduled or manual dispatch. Source failures retain diagnostics and checkpoint
state on `feed` after validation, then fail the workflow. This bounded second
pass catches delayed indexing within its update window; arbitrarily old delayed
records still require historical inventory reconciliation. It is not a complete
historical coverage claim.

A fixture verifies that a record with a 20-day-old update timestamp, missed by
the seven-day daily bootstrap, is recovered by weekly reconciliation after an
interrupted scan. It also verifies independent watermarks, outage recovery, and
idempotent replay. The workflow is local and has not been pushed or dispatched.

The weekly live dry run for `[2026-10-10, 2026-11-09)` used six total requests
across two invocations: three source pages and three identical verification
pages. It accounted for 231 unique candidates: 210 included and 21 requiring
review, proposing 110 insertions and 100 updates. None was applied. The catalog
remained 190 active records / five archived with the same raw SHA-256, and no
weekly watermark was created. These are query-window results, not evidence of
complete historical coverage. Full regression validation: 282 tests passed in
33.25 seconds; lint, format, workflow YAML, and all five Bash blocks passed.
