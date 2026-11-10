# Scheduled provider refresh

`refresh-signals --provider openalex|semanticscholar|huggingface --due` runs one
bounded provider pass. Adapter caches are the durable queue: successful and
missing observations stop being due; failed attempts retain successful values
and respect `next_retry_at`; unattempted work stays due. Due papers are selected
by oldest attempt, with never-attempted IDs first and canonical ID as a stable
tiebreaker. This prevents a bounded recurring queue from always selecting the
front of the catalog. Each adapter saves progress after individual papers or
batches. Process loss can replay a batch without inventing historical samples.

The command accepts request/time/paper ceilings, cache-only mode, a cache path,
`--require-key`, and an optional Markdown `--summary-file`. Limits are validated
before constructing a client. OpenAlex and Semantic Scholar use their existing
header-based environment credentials. Scheduled keyed providers report
`skipped / missing_credential` without network traffic when their key is absent.
HF needs no key. The local ignored environment loader is used by the CLI; no
credential values appear in reports or workflow summaries.

Reports distinguish `complete`, `deferred`, `degraded`, `cache_only`, and `skipped`.
`complete` means this due pass was drained, not that every identity was resolved:
ambiguity, misses, errors, request counts, and remaining due counts are explicit.
Provider identity ambiguity remains a review outcome. Provider failures do not
become zero counts, erase successful observations, or advance source watermarks.

## Cadence and budgets

The common command opts into citation sampling: successful recent papers
(original-date age at most90 days) become due daily, and older successful papers
weekly. This is separate from the default metadata-cache TTLs of the individual
legacy refresh commands, which are unchanged. Missing results keep their normal
retry TTL; error retry clocks remain authoritative. OpenAlex's existing dated
history retains only genuine successful observations, one per paper/UTC date,
for13 months. The command does not synthesize a historical observation from a
cache-only read. Semantic Scholar now also saves a separate dated sidecar on successful exact
matches; see reports/semanticscholar-history.md. Public provider/velocity UI
integration remains incomplete.

`daily-signals.yml` schedules every UTC day at04:00, including weekends. The
daily arXiv writer, midweek merge, and weekly release also refresh due queues
before building. All four workflows use `repository-writer` concurrency with
cancellation disabled, fetch branch heads inside the job, and retain ordinary
pushes. Each provider admits at most5 requests /90 seconds /100 due papers per
pass: at most15 admitted requests and270 seconds across three providers.
An in-flight HTTP request or file-lock acquisition may finish outside the
admission budget. HF's larger backlog can require many bounded passes.

Every provider's JSON and error diagnostics are retained under `reports/runs`,
with health in the workflow summary. An unexpected refresh-command failure is
visible as a warning while a checked cached build may proceed. Typed provider
failures report `degraded`; absent keys report `skipped`. Generated commit
allowlists include signals and run reports. No workflow was pushed or dispatched,
and repository Actions secrets have not been configured or verified remotely.

## Local evidence (2026-11-09)

A one-request authenticated OpenAlex canary accounted for six due records:
five successful exact matches and one ambiguous identity, with no errors and
reported cost$0.0001. A two-request HF canary returned one match and one confirmed
miss, leaving185 due. Semantic Scholar's keyed-only canary explicitly skipped
because no key is configured. These are current run observations, not a mature
citation-velocity result. The190-record canonical JSON retained SHA-256
`be5d48511084a81c1b7faa74d4ae052e75b7cc6b38e73f0c4b97254911d3b774`.

Thirteen new tests exercise zero budgets/cache-only behavior for all three
providers, missing-key suppression, oldest-attempt fairness under bounded HF
passes, daily/weekly sampling, retry separation, preservation of successful
values after a failed response, secret-free reports, and scheduled writer
budgets/concurrency/health/persistence. All four workflow YAML documents and
17 Bash script blocks pass syntax validation. Public provider/score integration,
HF discovery scheduling, successful live Semantic Scholar enrichment, and
actual deployment remain separate outstanding gates.

Final validation: all295 tests passed in37.75s; Ruff lint and format97 files,
canonical schema validation190 records, artifact build, and `git diff --check`
passed. Line-ending conversion notices are Git configuration warnings.
