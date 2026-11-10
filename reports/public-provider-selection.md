# Public citation provider selection

The catalog now offers an explicit OpenAlex / Semantic Scholar selector while
retaining OpenAlex as the default. Most-cited sorting uses the selected
provider's counts; unavailable observations follow valid zero counts. Fresh
observations precede stale ones. Corpus graph counts remain separately labelled
and continue to use their existing source-labelled projection.

The builder reads typed provider caches alongside canonical data, falling back
to v2 loaded signal stores when conventional cache files are absent. It publishes
only active-paper count/status/fetch-date fields into a content-addressed
`signals.<hash>.json` artifact declared in the manifest. Full responses, private
fields, provider request credentials, references, and archived rows are excluded.
The compact index projects current OpenAlex counts/status/fetch dates, including
successful zero, without modifying canonical metadata. Signal artifacts are
written before the manifest and retained like other immutable generations.

The initial default catalog loads no provider artifact. Selecting Semantic
Scholar lazily requests the separate artifact once and caches it. Missing S2
counts and influential counts remain unavailable instead of borrowing OpenAlex
values or summing providers. Card tooltips expose source, successful fetch date,
latest status, freshness, and S2 influential count/unavailability. Failed refresh
observations may retain prior successful values and their original date; missing,
ambiguous, or unknown identities are unavailable. Freshness is computed in the
browser from dates and the provider policy rather than frozen at build time.

Provider state is encoded in catalog URLs, restored on reload and route return,
and included in sort/filter cache keys. Failed lazy fetches expose a retry action
and retain no rejected promise. Reset restores OpenAlex. The existing filters,
pagination, layout, and50-card page boundary are preserved.

## Validation

Four new regressions cover source-labelled counts, zero vs missing, optional
influential zero, private-field/archived-row exclusion, deterministic hash-bound
manifest publication, v2 signal-store fallback, stale-on-error preservation,
ambiguity exclusion, browser selection/sorting logic, and a5,000-paper fully
observed two-provider artifact below4 MB. Existing5,000-record public index/detail
checks continue to pass. A browser-discovered sort-helper insertion defect was
corrected before acceptance; one pre-existing Windows-encoded ellipsis was
converted to the document's declared UTF-8 and line endings were normalized.

Real Edge QA verifies50 initial cards and zero initial signal requests; selecting
S2 issues one signal request and shows50 unavailable S2 cards without falling
back to OpenAlex. Most-cited sorting, provider URL restoration after reload,
intentional failed-request recovery, switching back to OpenAlex, and390px mobile
layout all pass. Mobile scrollWidth equals viewport width390px. The network error
from the intentional abort is expected; the existing Tailwind CDN warning is
unrelated. A mobile screenshot is saved with the validation artifact. The
isolated browser and temporary8765 loopback server were stopped after QA.

This is local implementation evidence. S2 successful live observations and a
real minimum seven-day velocity interval are still absent. Public trending-score
and measured-velocity presentation, repository workflow/secret rollout, release
and deployment verification, and the broader M0-M5 acceptance gates remain open.
No canonical paper was inserted, archived, or changed by this UI work.

Final suite:311 passed in21.86s; lint and format103 Python files pass. The190-row
provider artifact is49483 bytes (1873 gzip);
its SHA-256 is verified against the current public manifest. Canonical raw hash
remains unchanged. No push or deployment occurred.
