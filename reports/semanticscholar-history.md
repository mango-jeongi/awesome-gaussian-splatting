# Semantic Scholar dated history

Successful exact Semantic Scholar matches now write a separate
`data/signals/semanticscholar-history.json` sidecar. Custom cache paths use
`<cache-stem>-history.json` in the same directory. Latest typed observations
remain in the existing cache format; no cached value is automatically promoted
to a new dated sample. OpenAlex history is unchanged and remains separate.

Each strict sample contains canonical paper ID,40-hex provider ID, aware UTC
observation time, nonnegative integer citation count, and optional influential
citation count. Zero is a valid count. Boolean/negative counts, naive timestamps,
invalid identities, extra fields, duplicate UTC dates, out-of-order observations,
and unreviewed identity remaps are rejected. Provider IDs normalize case. The
first genuine success per paper/UTC date is retained; subsequent successful
same-day fetches may update latest values but leave that day's first sample
unchanged. Retention uses a13-calendar-month cutoff with month-end clamping.

The adapter loads history while holding its existing provider refresh lock.
Identity fencing checks both the latest cache and retained history, including
recovery after loss of the latest cache. Failed, throttled, missing, mismatched,
or remapped responses never add samples. Cache-only reads do not create a
history file. All writer workflows already stage `data/signals`, so the sidecar
is covered by their explicit generated-path allowlists.

On a successful batch, history is atomically published before the latest cache.
If the process dies between those writes, the prior cache remains valid and
retrying the due batch preserves the first UTC-day sample without duplication.
A simulated cache-publication failure verifies this ordering and recovery.
Both files remain typed, readable snapshots; no multi-file atomicity is claimed.

## Provider-selected momentum

`uv run python -m src.cli momentum --provider semanticscholar` reads only S2
history and latest identity. `--cache PATH` selects a custom cache and its history
sidecar. The default provider remains OpenAlex. Output summary and per-paper
results carry the selected provider. Mixed provider identifiers are rejected.
Both providers use the same measured window rules: nearest30-day baseline within
7–45 actual elapsed days, fractional-day normalization, freshness and identity
checks, signed raw delta, and a nonnegative ranking component for corrections.
A single observation or no observations produces an unavailable value, never0.
No provider totals, IDs, or histories are blended.

## Evidence and limits

Twelve new regressions verify zero counts, first-date deduplication,13-month
retention, crash recovery, case normalization, remap protection after cache loss,
failed/missing-source preservation, no cache-only history fabrication, strict
sample validation, provider separation, fractional negative velocity, and the
real provider-selected CLI report. These are fixture histories, not historical
production observations. The current190 active papers have no genuine Semantic
Scholar history and therefore no measured S2 velocity. A keyed live success and
a real minimum seven-day observation interval remain outstanding. The public
provider selector/ranking integration and workflow deployment also remain open.

Final validation:307 tests passed in49.51s; lint, format100 Python files, build,
canonical schema190 records, and diff whitespace checks pass. A current real
CLI report labels all190 S2 velocities `no_observations`; production history
remains absent. Canonical SHA-256 is unchanged. No push/deployment occurred.
