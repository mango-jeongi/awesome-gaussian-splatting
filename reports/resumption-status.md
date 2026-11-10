Current checkpoint: 300 active records, 5 losslessly archived. Raw SHA256 9285cbcbbb6a0b26a773dbcd7283205840bb101da38fcddecaae874b44ec561a. Baseline ledger: 140 retained, 5 archived, 20 unresolved; all165 IDs and all140 retained hashes verified. Full suite357 passed in27.37s; lint/format/build/schema checks pass. Local checkpoint commits enabled on codex/papers-pipeline-phase2-3. Earlier entries are historical.

# Papers pipeline resumption status

Updated 2026-11-09 America/Los_Angeles (live observations use UTC).

The goal remains active. M0â€“M5 and the Phase 2/3 acceptance gates are incomplete.
Local implementation checkpoint6b4116a is committed on codex/papers-pipeline-phase2-3.
No push, deployment, canonical v2 activation, full historical import, or model download has occurred. The approved dedicated remote
extraction service and five-minute timer are installed; see the later deployment evidence.

## Current v2 relevance and foundation checkpoint (2026-11-09)

gs-topic-v2 repairs generic-Gaussian false positives and missed editing, segmentation,
simulation, robotics, restoration, spatial splatting and Gaussian scene representations.
Explicit competing non-Gaussian primitive methods enter review. Three exact arXiv
foundation overrides carry reviewed source metadata and scope justifications. The
original100 balanced candidate/annotation bytes are unchanged. Current development
precision50/50 and recall50/50 pass95% targets and all five required phenomena are
represented. Eleven known negatives still enter review rather than automatic inclusion.

Added a normalized-identity-disjoint100-record challenge:21 unused early arXiv records,
49 updated arXiv records and30 HF descriptions, selected by position/identifier hashes
without policy outputs. Agent labels were frozen before evaluation. First v2 challenge
had61/63 precision and61/68 recall; saved failure evidence drove general rule corrections.
Final challenge has68/68 precision/recall,30 correct excludes,2 correct reviews. It is
now a development challenge, not an untouched holdout. Neither sample is independently
human-adjudicated or population-representative. Only the original balanced fixture
meets all five composition requirements; the challenge supplements its numeric checks.

Development source quality:82 official arXiv/18 legacy seed descriptions. Challenge:
70 arXiv/30 provider-supplied HF paper.summary descriptions, not AI summaries and not
independently verified author abstracts. Saved daily source observation time is explicitly
local page persistence time, not an invented HTTP response timestamp or dated citation
observation. Source packets, labels, baseline/first/final reports and old policy source
snapshots remain immutable evidence. reports/relevance-review.md has the current scope.

Verified canonical import added exactly original NeRF2003.08934, mip-NeRF2103.13415,
and Instant-NGP2201.05989, preserving all192 prior record values. Current195-record SHA
is above; immutable rollback is work/canonical-before-foundation-import.json. Exact
preview/application and idempotent replay are recorded in outputs/foundation_canonical_import.json.
Original dates remain day-precision2020-03-19/2021-03-24/2022-01-16. Instant-NGP's
published DOI10.1145/3528223.3530127 and all three arXiv aliases resolve correctly.

Rebuilt public artifacts for195 records:47 referenced descriptors pass hashes/paths/sizes;
78,084-byte compact index; all three foundation lazy details/aliases valid; repeated build
preserves bytes.29 stored graph edges. Old daily-policy checkpoint refuses reuse before
network requests and remains unchanged. Output:foundation_public_verification.json.
The scaling fixture now clears source arxiv_doi when cloning synthetic identities;
production collision checks remain strict. Full suite271 passed in24.93s; lint/format
and195-record validation pass. No Git commit/push/deploy or canonical-v2 activation.

Regenerated coverage:11 processed/153 source-work queued/30 unavailable/1 unsupported;
22 accepted numeric cells remain in the reviewed ledger. Cached momentum131 single
snapshots/64 without observations, no measured velocity. Trending1 partial/194 unavailable.
No new provider sampling, PDF transfers or model downloads were performed in this step.

Remaining priority: baseline165 seed reconciliation and M0 writer/rollback/v2 rollout;
full source reconciliation and historical crawl; scheduled HF/provider integration;
remote runtime refresh, local llama/Gemini architecture, matured real observations,
and the remaining performance/release/deployment gates. The full goal remains active.

## Historical v1 relevance-evaluation checkpoint (2026-11-09)

Frozen100 actual candidate records with individual agent review annotations and three
immutable hashed source captures. Composition:47 early broad-query hits/32 early GS
hits/10 medical-sensor seeds/8 adjacent reconstruction seeds/3 exact-ID NeRF foundations.
Seven annotations identify acronym collisions.82 records have official arXiv metadata;
18 retain explicitly identified legacy seed descriptions, not verified author abstracts.
Reviewer:Codex, also the policy author; this is not blinded or independent human review.
Labels and their scope reasons were assigned before evaluating this packet. No provider
prediction was copied into a label, and no production override was added.

The unchanged gs-topic-v1 policy FAILS the required95% precision/recall targets:
gold include50/exclude37/review13;44 correct automatic includes,3 confirmed false-positive
includes,2 unresolved automatic includes,6 missed includes. Confirmed-inclusion precision
44/49=89.80%; resolved-binary-label precision44/47=93.62%; recall44/50=88.00%.
The three confirmed false positives are dust-density fitting, CT Gaussian smoothing,
and galaxy-distance inference. Missed includes are explicit anisotropic Gaussian
splatting visualization, PhysGaussian, GaussianEditor and the three NeRF foundations.
Source and label provenance limitations are reported; this is not a population estimate.

Added `src/relevance_benchmark.py` and `evaluate-relevance` CLI. Exact sample/label
inventory, normalized identity uniqueness, packet/record/source hashes, original source
field equality and aware review/capture chronology fail closed. Abstentions on gold
includes count as missed includes; unresolved automatic includes remain visible and
count against the conservative acceptance threshold. Zero denominators never pass.
Twelve focused tests exercise arithmetic, tampering and the complete frozen fixture.
Full suite255 passed in45.28s; focused12/lint/format also pass after metric terminology
was clarified. CLI report replay is deterministic. Canonical192-record SHA256 unchanged.

Evidence:tests/fixtures/relevance/{candidates,annotations}.json and sources/*.json;
reports/relevance/gs-topic-v1-sample-v1.json; reports/relevance-review.md;
outputs/relevance_evaluation_cli.json. Next action:repair general representation/context
rules and explicitly curate justified foundations; preserve these labels and baseline,
then add an independently selected challenge sample. Do not treat this failed gate as
permission for bulk import or deployment. Goal and all broader unfinished gates remain active.

## Historical daily-ingestion checkpoint (2026-11-09)

Implemented the `daily` CLI and updated-window session: descending source-update
paging to the prior watermark minus seven days, durable candidate pages and request
charges, bounded resume, exact second-pass replay, source-drift restart with retained
evidence, shared deterministic ingestion, canonical CAS, post-save hash validation,
and watermark publication only after successful import. First-run coverage requires
an explicit boundary. Outages retain the prior watermark instead of losing older gaps.
Dry runs and required-source failures do not advance coverage. Twelve new tests cover
the update window, revisions, budgets, failures, tampering, and crash recovery.

Local daily workflow now calls this command, persists its source/checkpoint/import
paths, retains failure diagnostics, and commits validated progress before reporting
a required-source failure. YAML parsing and all five Bash run-block syntax checks pass.
It has not been committed, pushed, or deployed. The annotated policy-precision gate
and production initialization remain open; daily coverage is not historical coverage.

Real two-request dry run completed one source page and its replay for the explicit
UTC window [2026-11-02,2026-11-09). It prepared48 dispositions:43 include/5 review;
proposed operations13 insert/29 update/1 merge/5 none. No proposal was applied.
Canonical192-record SHA256 remains2c7a5b5c1cab6fef9cefa5d1ff08ff5ae3c708b04fabe8e25f5835f81444b525;
no watermark was created. Evidence: outputs/daily_live_canary.json and
reports/daily-ingestion.md. Final full suite243 passed in28.01s; lint/format verified
after the test-import whitespace correction.

## Historical baseline and preservation

Local main was fast-forwarded from a235a1e to 2e98015. Canonical data/papers.json
still has 189 records, last_updated 2026-11-06T08:57:09Z, SHA256
fa50b1230e981931c5132b11b05d0daf2724cd8555a7c94fc5f32280c68c5f9f.
The original seed had 165 IDs; 24 subsequent feed additions remain present.
The in-memory graph has 189 nodes, 29 edges, and 25 connected records.
There are 441 aliases without detected collisions, 149 legacy zero counts,
189 unknown date precisions, and 84 legacy DataCite DOI slots awaiting review.

## Implemented locally

- Strict immutable monthly v2 shards, hashed alias/signal/archive artifacts,
  atomic manifest publication, validation, concurrent-writer detection, and no-op saves.
- Stable identity matching, transactional upserts, reviewed field protection,
  provenance/date contracts, seed date corrections, snapshot-bound archival review,
  merge-chain validation, resurrection prevention, and active-only public exports.
- Historical arXiv discovery with durable page acknowledgments, monthly subdivision,
  resume boundary replay, earliest-source probe, frozen policy/query contracts,
  explicit request budgets, candidate dispositions, and dry-run/import receipts.
- arXiv single-executor cross-process pacing with one connection, persisted retry
  deadlines, strict response integrity, and bounded requests. This is a local gate;
  all controlled executors must still be coordinated before bulk operation.
- Deterministic relevance policy and reviewed override support. The synthetic
  regression cases do not satisfy the required 100 manually annotated candidates.
- Compact public index, bounded lazy details/search, 50-card pagination, retry states,
  safe special identifiers, full-author BibTeX, precision labels, and preserved UI controls.
- Frozen workflow installs, shared writer concurrency, ordinary atomic ref pushes,
  explicit generated-file allowlists, dispatch validation, ISO week-year release checks.
- Literal local credential loading with environment precedence and sanitized errors.
  The ignored local OpenAlex key is active; no secret is printed or committed.
- Shared httpx OpenAlex transport, exact DOI/location-alias matching, max-40 identifier
  batches, pagination validation, request/time ceilings, provider budget exhaustion,
  bounded retries, authorization headers, and sanitized failures. Citation commands
  now delegate to the shared cache and preserve newer loaded observations.
- Separate typed OpenAlex response cache and genuine UTC daily citation history,
  rolling 13 calendar months, TTL/retry queue, cache-only mode, error preservation,
  identity remap refusal, and explicit conflicting-arXiv review.

## Evidence and limits

The latest full suite is recorded in the chat validation output. The prior suite
passed 137 tests; two new alias/conflicting-arXiv tests are included in the current
139-test validation. Ruff lint passes; formatting was corrected after the last check.
Workflow YAML and 18 shell steps parsed; ten dispatch boundary/injection cases passed.
These local checks do not constitute a deployed workflow gate.

The 5,000-record fixture index is 1,862,213 bytes (514,999 gzip), with 58 detail
artifacts and largest detail 350,814 bytes. Edge156 on Windows11/Core Ultra9 285H,
31.43GiB, 1440x1000, 4x CPU, 10Mbps/1Mbps and100ms: five cold loads median2910.9ms,
slowest2924.3ms; five warm searches median72.6ms, slowest85.1ms. These are small
samples, not p95. Mobile390x844 and pagination/filter/theme/lazy-recovery checks passed.
The older offline5000 graph/store/build timing was3.64sec and needs rerunning after
new contracts before being used as current evidence.

A real arXiv dry-run used one request, wrote no canonical records, and found4451
broad-query hits. Earliest hit: hep-th/9808009, published1998-08-03, a Gaussian-barrier
paper. This validates earliest discovery and demonstrates false positives; it is
neither the relevant corpus count nor a completed historical crawl.

The first authenticated OpenAlex snapshot was2026-11-09T05:21:28.525343Z:
3D Gaussian Splatting for Real-Time Radiance Field Rendering, DOI10.1145/3592433,
W4385318467,7238 citations,44 references. A later bounded five-request refresh
added130 successes; overall cache has131 successful papers,2 misses,18 ambiguous,
and38 errors. The errors were caused by exact alias handling of publication work
responses; location-alias support now passes tests, but those38 have not yet been
retried under the repaired adapter. One live provider work combines two arXiv IDs
and must stay ambiguous. Additional diagnostic calls were made after that refresh.
No measured velocity exists: a second real comparable snapshot at least seven days
later is required. Snapshot timestamps were not backfilled from legacy counts.

Read-only SSH to msi-raider succeeded: RTX2070 8GiB,370GiB free local SSD, uv present;
llama-server was absent from PATH. This initial probe preceded the later approved service installation.
GitHub CLI is unauthenticated. Public repository REST showed no queued/running known
workflows before the arXiv canary; the latest observed weekly release was successful.

## Work remaining

Complete M0 rollback/baseline and writer rollout before v2 activation; meet the
annotated relevance gate and validate/deploy daily scanning; review seed dispositions;
run the reconciled historical crawl; complete HF scheduling/public integration and all
venue inventories; broaden reviewed extraction coverage and update the remote runtime;
configure local llama/Gemini work; complete provider sampling, real matured velocity,
trending presentation, and release/deployment/rollback evidence. Routes, graph, and
worker implementation evidence appears in later dated sections. Keep acceptance gates
open until verified; no GitHub deployment has occurred.

## Measured momentum implementation update

The velocity module and CLI now select the baseline nearest30 days within the
inclusive7â€“45-day window, retain fractional elapsed days and negative raw deltas,
clamp only positive ranking momentum, and reject stale/future/duplicate observations
and incompatible identity segments. Nine dedicated tests cover these contracts.
The real-cache report has131 single-snapshot papers and58 without observations;
zero records have measured velocity. No historic snapshots were invented.
The latest full suite passes148 tests; Ruff lint and format checks pass.

## Trending formula implementation update

Added config/ranking.yaml, src/ranking.py, and the trending report command.
Version trending-v1 uses normalized midranks (singleton0.5), velocity/upvote weights
0.7/0.3,30-day half-life,90-day age limit, and7-day HF freshness. Partial scores
renormalize weights; complete scores sort first. Ties resolve by original date
then stable ID. Outputs include coverage, actual signal dates/windows, percentiles,
and effective weights. Unknown/coarse publication dates cannot fabricate paper age.
Four tests verify hand-calculated scores, ties, zero signals, decay, partial coverage,
freshness boundaries, age limits, and invalid configuration. Full suite passes152 tests;
Ruff lint/format pass. The real trending report marks all189 records unavailable
because their original-date precision remains unverified. Provider data maturity,
HF observations, date adjudication, and portal integration remain incomplete.

## Semantic Scholar adapter update

Added src/extractors/semanticscholar.py and refresh-semanticscholar CLI. Uses httpx,
optional SEMANTIC_SCHOLAR_API_KEY in x-api-key,40-ID batches, at most1 request/sec,
request/time ceilings, bounded retries and preserved Retry-After deadlines. Exact
returned arXiv/DOI identity is required; mismatches and identity remaps become ambiguous.
Separate typed observations preserve genuine zero citation/influential counts and
successful empty references. Reference completeness is explicit; partial returned
references do not claim full coverage and are not merged into the OpenAlex graph.
Cache-only operation and stale-success preservation use the existing SignalStore.

The current official tutorial was checked at implementation kickoff:
https://webflow.semanticscholar.org/product/api/tutorial
It documents optional x-api-key, batching, and the standard1 request/sec keyed rate.

Two bounded anonymous live canaries each received provider throttling. The first
revealed an attempt-accounting edge case, now fixed; the second persisted a real
rate_limited observation with retry deadline. No successful live Semantic Scholar
sample exists, so the M3.2 live gate remains open. Do not repeatedly retry before
the persisted deadline. No Semantic Scholar counts were copied from OpenAlex.
Full suite now passes156 tests; Ruff lint/format pass.

## Bounded graph projection update

Added src/graph.py and immutable public graph artifacts: capped overview, adjacency
pointer index, and lazy adjacency/node buckets bounded by the500KB detail limit.
The manifest binds graph artifacts to the corpus SHA and build digest. Projection
uses citing-to-referenced direction, recomputes incoming adjacency, rejects self,
duplicate, and inactive endpoints, and reports unmatched source references. Legacy
reference provenance remains explicitly unverified unless matching dated provider
reference evidence exists. The global overview selects at most300 nodes/1200 edges;
one-hop ego projections cap80/200 and two-hop150/400 with deterministic omitted counts.
Year/category filters and deterministic degree/global-count/ID priorities are supported.
Six tests cover a5000-node star, dense caps, inversion, invalid edges, filtering,
artifact parity and no-op generations. Full suite passed162 tests; subsequent
provenance-label correction passed the graph tests, Ruff lint and format checks.
Hash routes, lazy graph UI, pinned Cytoscape loading, layout cancellation, accessibility,
and browser acceptance evidence remain open; this is the projection foundation.

## Canonical paper route update

Added #/paper/<encoded-id> with lazy full authors/abstract, source link, BibTeX,
canonical alias resolution, relationship links, unknown-ID state, archival lookup,
and retry UI. Catalog hashes preserve query/year/sort/code/category/tags/page;
return navigation retains originating catalog state and stored scroll position.
Route generations invalidate stale async results. Details navigation no longer
replaces the search query or inherits filters as an accidental paper selection.

Playwright CLI/Edge verification on the5000-record fixture passed canonical deep-link
refresh, exact page2 card restoration with browser Back, arXiv alias canonicalization,
unknown encoded slash/colon ID, relationship navigation retaining page2/oldest state,
and mobile390x844 without horizontal overflow. Zero browser errors were observed;
the existing Tailwind CDN warning remains. Saved paper_route_qa.txt and
relationship_route_qa.txt contain results. Browser and temporary HTTP server closed.
The fixture index remains1,862,213 bytes/514,999 gzip; current artifact build took2.30sec.
These browser checks do not yet cover all archive dispositions/special-ID aliases,
failed detail retries, Forward state, graph routing/rendering, or project-base deployment.
Those M4 acceptance items remain open. Python implementation was unchanged this turn;
last full Python suite remains162 passing tests.

## Lazy interactive graph update

Added docs/assets/graph-view.js and #/graph routes, linked from catalog and paper
pages. Cytoscape3.33.1 loads only on graph entry. Global/ego projections enforce
300/1200,80/200,150/400 render caps; year/category and hop controls update hash state.
Deterministic ID-seeded preset positions avoid unbounded force simulation. Route
changes stop layouts and destroy the old Cytoscape instance. Directed arrows and
coverage/omitted counts are visible, with keyboard-accessible equivalent paper and
directed-relationship links. Missing graph data and failed fetches have explicit states.
The implementation kickoff consulted https://js.cytoscape.org/ for preset/layout,
stop, and destruction behavior. Cytoscape version is pinned in the asset loader.

Playwright CLI/Edge on the5000-record fixture verified no Cytoscape on catalog entry,
actual lazy library success, global300 nodes/196 edges, one-hop3/2, two-hop4/3,
old instance destruction on paper navigation, empty category filter state, and mobile
390x844 without overflow. A fresh document with the CDN request deliberately blocked
retained5 keyboard-accessible paper/relationship links; Enter opened the canonical
paper route. That injection generated the expected browser network error. Saved
outputs/graph_qa.txt and outputs/graph_fallback_qa.txt contain these results.
Browser and temporary server closed. Node syntax check passed. Last full Python
suite remains162 passing tests; no Python source changed this turn.

Remaining M4 evidence includes all archived/special aliases, failed detail retry,
Forward/scroll restoration, exact frontend/backend selection parity under deliberately
stale legacy graph counts, dense cap browser tests, visual review, project-base-path
refresh, and deployment. Broader M0â€“M5/Phase2/3 gates remain open.

## Frontend/backend graph parity update

Public graph index now includes recomputed incoming counts, provider citation counts,
year/category selection metadata, and lazy record pointers. Frontend selection uses
that index rather than potentially stale legacy compact-index counts. Extracted a
pure graph-projector.js shared by the actual renderer and Node/Python parity checks.
Two tests compare exact selected node metadata/order, directed edges, omitted counts,
and caps against Python for sparse/dense graphs,1/2-hop views, category/empty filters,
special IDs, and intentionally stale legacy in-corpus counts. CI explicitly checks
Node availability before Pytest. Full suite passes164 tests; Ruff lint/format pass.

Playwright/Edge reran against the new artifact schema on5000 papers: lazy library,
global300/196, ego3/2 and4/3, route instance destruction, empty category and mobile
checks passed with zero browser errors. outputs/graph_parity_browser_qa.txt records
results. Browser and temporary server closed. Python/browser parity is now directly
verified for those cases; the broader route/deployment/visual acceptance remains open.

## Alias and route acceptance update

Added route-identifiers.js with Python-parity DOI/arXiv/OpenAlex normalization and
safe own-key alias lookups. Arbitrary canonical IDs retain exact case/Unicode/slashes.
Archive exclusion messages include review time and receive keyboard focus. A direct
Node/Python parity test covers DOI encoding, arXiv URLs/versions/legacy IDs, OpenAlex
forms, arbitrary IDs, and inherited object property names. Full suite passes165 tests;
Ruff lint/format pass.

Playwright/Edge fixture served under /project/ passed five aliases/deep-link refreshes
including full DOI URL, arXiv legacy PDF/version URL, OpenAlex ID, merged DOI, and a
quote/slash/Unicode canonical ID. Excluded DOI alias displayed disposition and review
date; constructor was safely unknown. Query/title-sort/page2 state survived Back,
Forward restored the paper route, and a separate awaited check restored scrollY900.
An injected details network failure displayed Retry and then loaded successfully.
outputs/route_acceptance_qa.txt and route_scroll_qa.txt record evidence. The injected
failure generated the expected browser network error. Browser/server closed.
These fixture checks do not constitute GitHub Pages deployment evidence or complete
all M4 visual/dense-browser acceptance; broader goal milestones remain incomplete.

## Extraction queue protocol update

Added src/workers/queue.py with strict digest-keyed jobs, immutable configuration,
queued/leased/succeeded/failed-retryable/failed/review-required states, fenced lease
tokens, expiry recovery, bounded attempt counts, validated PDF/page/time/size limits,
and atomic locked queue/result publication. Result identity binds canonical ID,
PDF digest and extractor version. Durable output written before interrupted queue
acknowledgment is recovered without another extraction attempt. Late/expired lease
results are rejected. Acknowledged results are hash-checked when loading the queue.

Candidate contracts record source page/bbox, caption/table heading, dataset/split,
metric/unit, row/column context, source value and confidence; all parser candidates
remain review-required. Missing context never becomes a leaderboard entry. Figure
candidates can carry reuse basis but are not automatically published.
Seven protocol tests cover no-op identity, immutable limits, lease recovery/fencing,
crash-before-ack recovery, partial numeric provenance, attempt exhaustion/corrupt
state, result/source limits and acknowledged-result corruption. Full suite passed171
tests before the seventh corruption test; the final worker suite passes7 tests.
Ruff lint/format pass. This is the queue/result foundation only: optional PDF parser
dependencies, queue/pass/import CLI, bounded subprocess enforcement, remote service,
client-disconnect recovery evidence, actual PDF pilot and coverage scan remain open.
No remote install, model download or canonical import occurred this turn.

## Bounded PDF worker execution update

Added optional extraction dependency group with locked pdfplumber0.11.10 and its
resolved dependencies. src/workers CLI supports enqueue, bounded pass and validate-result.
Enqueue hashes source bytes into an explicitly configured local SSD PDF cache;
parser subprocess rechecks exact digest/signature and enforces byte/page limits.
Parent enforces per-job wall time, suppresses raw parser stderr, validates bounded
JSON output and publishes through the fenced queue. A pass processes each key at
most once, so a failure cannot consume all retries in one pass. Heavy PDFs and
parser temporary files stay off Google Drive; Windows UNC/G: cache paths are rejected.

Conservative parser captures ruled numeric table cells with page/bbox, exact raw
value, provisional row/column/header text and confidence; context and units are not
guessed. Embedded image bounds are sourced figure candidates with unavailable
captions/reuse basis pending review. Borderless tables/vector figures are explicitly
uncovered. All candidates remain review-required; no figure assets are redistributed.

Verified local RadSplat PDF first-page title/authors against the corpus record before
enqueueing. The15,059,485-byte,11-page PDF completed a60-second-budget subprocess pass,
producing39 numeric-cell and59 image candidates. Digest and extractor version are in
outputs/local_worker_sample.json. Zero cells have been manually accepted. This is one
operational sample, not the12-paper/six-category/30-reviewed-cell pilot acceptance.
Full suite passes176 tests with all dependency groups; Ruff lint/format pass.

Commands (set UV_PROJECT_ENVIRONMENT=C:\Users\mingu\.venvs\papers first):
- uv run --group extraction python -m src.workers enqueue --queue <queue-dir> --cache <local-SSD-dir> --pdf <file> --paper-id <canonical-id> --source-url <locator>
- uv run --group extraction python -m src.workers pass --queue <queue-dir> --cache <local-SSD-dir> --max-jobs 1
- uv run --group extraction python -m src.workers validate-result <result.json>

Reviewed import, richer context extraction, actual pilot review, remote service and
disconnect/kill recovery demonstration, model setup, full eligibility scan and durable
coverage remain open. No remote installation or canonical metadata change occurred.


## Reviewed extraction import update

Added src/workers/review.py and papers-worker review-import CLI. Review binds exact
canonical corpus snapshot, result-file SHA, source PDF digest, canonical active ID,
and extraction/review timestamps. It shares the canonical repository writer lock
and atomically publishes a separate typed reviewed-extraction ledger. Dry-run writes
nothing; identical replay preserves bytes/mtime; conflicting re-review requires
adjudication rather than silent replacement. Original parser candidates and corrected
accepted values are both retained. Partial reviews leave other candidates unreviewed.

Accepted numeric cells require explicitly reviewed dataset/split/metric/unit,
row/column context, accepted value, reviewer, reason and source-check assertion.
Accepted figures require sourced caption and recorded reuse basis; this importer
does not itself redistribute figure assets. Rejections remain auditable. Inputs
with changed PDF/result bytes, stale new decisions, invalid indices/timestamps or
missing accepted context fail before ledger publication. No comparable-table grouping
or leaderboard is inferred from these records.

Command: uv run --group extraction python -m src.workers review-import --data <canonical.json> --ledger <reviewed-ledger.json> --result <result.json> --pdf <source.pdf> --review <review.json> [--dry-run]
Set the mandated UV_PROJECT_ENVIRONMENT=C:\Users\mingu\.venvs\papers first.
Sixteen dedicated review tests pass. Full suite now passes192 tests; Ruff lint/format
pass. No real RadSplat decisions have been accepted:39 numeric and59 image candidates
remain unreviewed. Remote service, reviewed pilot, richer parser/context and coverage,
public benchmark integration and all broader milestone gates remain open.

## Remote worker deployment update

User explicitly approved the verified RadSplat PDF transfer and dedicated service/
timer startup after automatic review requested specific authorization. Installed
content-addressed runtime79711958ee618714 under /home/mingu/.local/share/papers-worker,
locked Python3.12.14 SSD environment at /home/mingu/.venvs/papers-worker, separate
queue/results and SSD PDF cache. No credentials/corpus/git metadata were bundled.
Service/timer templates are tracked-worktree candidates under deploy/.

Observed service activating/MainPID227946 before the submitting SSH connection
closed; fresh SSH verified success,11 pages and98 unreviewed candidates. Systemd
reported2.105sec elapsed,103.2MB memory peak. Timer enabled and active/waiting;
user lingering enabled. Re-running completed queue claimed0 jobs, preserved queue
hash and retained exactly one result. Remote result copied to workspace scratch;
no reviewed import or public asset publication occurred. Existing proxy services
were untouched. Pre-existing failed desktop portals and spice-vdagent config warning
were inspected/reported without unrelated fixes.

outputs/remote_worker_deployment.md records paths, evidence, status commands and
non-destructive stop/rollback commands. In-flight kill/recovery demonstration,
reviewed pilot and coverage remain open. Latest full suite remains192 passing tests;
this turn added deployment templates rather than changing Python behavior.

## Real killed-worker recovery evidence

Isolated recovery queue with the approved real RadSplat PDF/runtime: observed lease
06:06:04.725245Z, killed control group PID228534, preserved expiry06:07:04.725245Z.
Early restarts claimed0. Scheduled recovery completed06:07:15.455658Z on attempt2,
with exactly one durable review-required result. Further pass was a byte-preserving
no-op. Production queue hash stayed unchanged. The transient15sec test timer was
stopped; both transient units verified not-found/inactive afterward. Production
five-minute timer remains active/waiting. No fabricated timestamps or manual lease
expiry were used. outputs/remote_worker_recovery.json and remote_worker_deployment.md
record evidence and distinguish test/production retry latency. No source code changed;
last full suite remains192 passing tests. Remaining worker gates are reviewed pilot,
coverage and validated publication/import integration, alongside the broader goal.

## Twelve-paper pilot execution update

Matched local PDF filenames to active corpus titles, then verified all12 selected
titles against first-page PDF text. Selection covers exactly six current taxonomy
categories, two papers each: foundations, dynamic, generative/reconstruction, avatars,
active perception/SLAM, and2D/compression. Bounded local subprocess pass claimed12
jobs:11 review-required results and one size-limit failure (GaussianImage++,53,500,852
bytes against the unchanged50MB job limit). Source PDFs/cache stayed on local SSD;
no additional remote PDF transfers occurred.

Found merged text regions and plot annotations among parser numeric candidates.
Candidate counts explicitly do not represent accepted numeric cells. None has been
manually accepted. outputs/pdf_pilot_execution.json records source digests, title
checks, categories, pages, vector-object observations, execution states and counts.
Vector objects were observed programmatically; visual multi-column/vector-source
review and the30-cell/six-benchmark-paper acceptance remain open.

Fixed deterministic immutable input failures (invalid PDF, byte/page limit) to stop
as terminal rather than waste retries. Existing retryable records with these reasons
are classified terminal on the next queue pass, preserving their attempt count.
Three regression cases added. Full suite passes195 tests; Ruff lint/format pass.
The deployed runtime79711958ee618714 predates this failure-classification change;
it must be updated before broad remote use. Its existing completed RadSplat queue is
unaffected. Pilot source-page review, corrected/rejected numeric decisions, full
eligibility coverage and broader milestones remain incomplete.

## Rendered numeric source review update

Rendered and visually inspected source pages from RadSplat(p6), MGStream(p6),
FSGS(p10), HUGS(p7),4C4D(p6) and original3DGS(p8). Checked five numeric cells per
paper,30 total. All30 parsed values match their source cells. Corrected method,
metric, dataset/split and unit context in separate reviewed decisions; original
parser candidates remain retained. Imported22 accepted cells and8 explicit rejections
pending further unit verification. Rejections are not claims that those values were
numerically wrong. Source units/metric conventions are recorded in accepted decisions;
no missing-unit PSNR/warp value was silently promoted.

Reviewer is explicitly Codex(rendered-source inspection), not an independent human.
Dry-ran all six review packets, then applied with exact PDF/result/corpus digest
checks to data/extraction/reviewed.json through the repository writer lock. Replayed
saved packets with zero additions, preserving ledger bytes and mtime. Canonical
papers.json retains SHA fa50b1230e981931c5132b11b05d0daf2724cd8555a7c94fc5f32280c68c5f9f.
outputs/pdf_pilot_numeric_review.json contains all30 decisions and source-page render
hashes. Source render PNGs remain scratch evidence; no paper figure reuse/publication
was approved. Other extracted candidates remain unreviewed and no leaderboard or
cross-paper superiority claim is generated.

This supplies the30-cell/six-benchmark-paper numeric review evidence alongside the
12-paper/six-category execution inventory. It does not complete M2: full included
record eligibility/coverage scan, public integration, deployed runtime update and
remaining source/venue/worker requirements are open. Latest full code suite remains
195 passing tests; this turn added reviewed evidence rather than Python behavior.

## Full included-record extraction coverage update

Added workers coverage module/CLI and persisted data/extraction/coverage.json for all
189 active IDs. Dispositions:11 processed,147 queued,30 unavailable and1 unsupported
under the unchanged size limit. All147 queued records explicitly link durable source
materialization/identity-verification tasks; they are not represented as parser jobs
already executing. Local candidate locators use opaque local-inventory hashes rather
than publishing filesystem paths. The private local source index stays in scratch.
Unavailable means no configured PDF URL/local candidate in this inventory, not a
claim that no PDF exists globally. Unsupported identifies the configured parser/input
limit. Processed requires validated acknowledged result bytes, not mere job presence.

Coverage joins reviewed decisions only against matching job/PDF/result digests,
reports22 accepted cells and8 rejections, and labels remaining candidates unreviewed.
Current-version coverage is explicit and does not claim all PDF versions were parsed.
Three tests verify exact active inventory, source-work/task linkage, no-op saves,
validated result/version behavior and known failure dispositions. Full suite now
passes198 tests; Ruff lint/format pass. outputs/extraction_coverage.json mirrors the
repository coverage artifact. Canonical bibliographic metadata remains unchanged.

The scan supplies explicit included-record eligibility coverage after the pilot.
Pending source work is substantial and requires materialization/identity checks;
parser/public integration and remote runtime update remain open, as do broader
M0/M1/M2 venue/HF/curation and M3â€“M5 acceptance requirements.

## Accepted evidence public projection update

Automatic approval access recovered; confirmed the previously rejected edit never
ran. Added reviewed_public.py and optional reviewed-ledger integration in public
builder/lazy details. Only accepted numeric cells for active papers are projected,
with dataset/split/method/metric/unit, source page/bbox, parsed and accepted value,
PDF digest and review attribution. File URLs and rejected/unreviewed/figure candidates
are excluded. Builder loads the validated adjacent extraction ledger when present.
Verified actual22 cells/six papers, no local URLs, and inactive-record exclusion.
Full suite remains198 passing tests; Ruff lint passes. Frontend table rendering,
projection regression tests, final build/browser checks and deployment remain open.

## Reviewed source-table UI update

Added reviewed-benchmarks.js and paper-route tables for accepted numeric evidence.
Dataset/protocol, source method, metric, exact accepted value, unit, source page and
review attribution remain visible. Review details retain parsed value/PDF digest/bbox.
Tables explicitly describe baseline labels and protocol incomparability; no leaderboard
is inferred. All cell strings use text nodes. Non-HTTP(S) source links are excluded.

Added a projection regression test for accepted/active/numeric filtering, preservation
of original/corrected values, safe local-URL fallback and literal hostile-looking text.
Playwright CLI/Edge verified RadSplat's four accepted rows (rejected cell excluded),
method/unit context, mobile390px internal horizontal scrolling without page overflow,
and literal HTML-looking cells with no executable DOM or javascript link. Saved
outputs/reviewed_table_qa.txt. Browser/server closed. Full suite passes199 tests;
Ruff lint/format and JavaScript syntax checks pass. This used an isolated project-base
preview; production artifact rebuild/deployment and broader goal gates remain open.

## Hugging Face live contract kickoff

Checked official Hub API reference and captured one bounded successful daily_papers
request(limit10) at2026-11-09T16:15:16.289144Z. Real shape is a daily wrapper around
nested paper metadata, including repository/stars/upvotes/provider summary and source
timestamps. Spaces were absent in this sample, so no Spaces URL is inferred. Saved
raw fixture in scratch and outputs/huggingface_contract_probe.json with field inventory.
Added huggingface_contracts.py and4 focused tests for nested shape, absent versus
zero counters, versionless arXiv IDs, provider-summary separation and invalid types.
All10 live fixture entries validate; Ruff lint/format pass. Last full suite remains
199 passing tests plus4 new focused tests. The extractor is still the prior stub;
shared HTTP transport, discovery lookback/relevance import, per-paper live probe,
typed observations/TTL/retry queue and CLI integration remain open.

## HF shared transport and singleton live sample

Added HFPapersClient with httpx, bounded request/time ceilings, conservative1sec
spacing, at most3 attempts, Retry-After/backoff, auth-failure latching, sanitized
errors and explicit404 miss handling. Daily lookups use the captured nested contract;
per-paper lookup validates exact versionless arXiv identity and refuses mismatch.
A single real request to /api/papers/2308.04079 succeeded at2026-11-09T16:17:32.952999Z.
Saved normalized singleton fixture in scratch and outputs/huggingface_single_probe.json.
The report's fields list describes the typed model, not a claim every optional field
was present in the raw response. No summaries/repositories were copied into canonical
metadata. Six focused contract/client tests pass; Ruff lint/format pass. Last full
suite remains199 tests; six HF tests added since it. Discovery importer, bounded
lookback, typed observation cache/TTL and resumable enrichment queue remain open;
the old ingestion extractor stays disabled/stubbed until those safeguards are wired.

## HF persistent observation cache

Added huggingface_cache.py over the shared bounded client and typed SignalStore.
Refresh queue persists after each attempt; supports request ceilings/cache-only,
confirmed404 misses separately from failures, recent daily activity24h TTL and older
matches/misses7day TTL, retry deadlines and error preservation. No arXiv identifier
becomes ambiguous/review-required rather than a fabricated provider miss. Summaries
are attributed HF provider text; repository/project links remain provider evidence.
Absent stars/upvotes remain unavailable; genuine zero stays zero. No Spaces URL or
canonical abstract/code ownership is invented. One focused cache regression passes,
including success/error timestamp/value preservation and canonical-field preservation.
Ruff lint/format pass. Last full suite remains199 tests plus7 focused HF tests added.
CLI/discovery integration, lookback caching and relevance import remain unfinished;
no production HF observations were claimed or canonical metadata changed this turn.

## HF CLI and bounded discovery integration

Replaced the HF discovery stub with a shared-client adapter and added distinct CLI
commands discover-huggingface / refresh-huggingface. Discovery persists dated provider
snapshots,24h reusable day caches, bounded1â€“31day lookback(default7), per-day limits,
unique-ID deduplication and topic dispositions. Full pages are explicitly possibly
truncated and cannot claim a complete bounded inventory. Resume tests preserve already
cached days after request-budget interruption. Provider summary/repository fields are
not copied into author abstract or official code URL. Missing source publication date
requires review. The legacy ingest command no longer directly upserts HF candidates,
so ENABLE_HUGGINGFACE cannot bypass the separate discovery/review path.

Real seven-day run examined197 unique provider candidates, proposing2 includes and
195 exclusions under the current topic policy. Included IDs2611.08264 and2611.05593
are source candidates, not added canonical papers or human-adjudicated relevance.
All seven queried days returned fewer than100 records; complete=true applies only
to this bounded daily-endpoint contract, not exhaustive HF coverage. Saved
outputs/huggingface_discovery_report.json. Three-request real enrichment recorded1
matched observation and2 confirmed misses in data/signals/huggingface.json. Canonical
bibliographic data was unchanged. Full suite passes208 tests; Ruff lint/format pass.

Remaining HF work includes authors/Spaces field-completeness validation, explicit
canonical candidate import through identity/relevance review, broader TTL/retry edge
cases and scheduled workflow/public signal integration. The independent100-annotated
candidate relevance gate and all broader phase requirements remain open.

## HF authors, linked Spaces and import preview

Captured raw per-paper3DGS contract: ordered author name objects, ai_summary,
linkedSpaces and numTotalSpaces are present. Preserved authors in candidate records;
AI summaries remain separately attributed provider text. Linked Spaces are emitted
only from validated provider IDs, with explicit relationship provider-linked/not
verified official and completeness derived from returned versus total counts. The
real sample linked an AI timeline Space; it is not labelled an official paper demo.
Discovery cache contract upgraded to version2 so old snapshots that dropped fields
are refreshed instead of silently reused. One regression test added.

Added preview-huggingface-import using the same deterministic identity/relevance
preparation as historical ingestion. Preview is bounded to the latest report's exact
day/limit contract and records corpus/policy/source-candidate digests. No canonical
write occurs. Actual197-candidate preview:2 includes,194 excludes,1 review; includes
resolve to2 updates of existing records,0 inserts/duplicate papers. Saved
outputs/huggingface_import_preview.json. Verified unrelated malformed stale cache
file outside the report window is ignored. Refreshed discovery/preview remained
network-bounded and canonical metadata unchanged. Full suite passes209 tests; Ruff
lint/format pass. Actual reviewed candidate application, observation-cache contract
migration, workflow/public HF integration and broader gates remain open.

## HF contract migration and guarded application

HF successful observations with an outdated response contract are refresh-due despite
ordinary TTL; failures preserve the previous successful response schema version as
well as values/timestamp. Success records hf-paper-v2. A real one-request migration
refreshed the existing HF match successfully. Added exact-proposal application command:
apply-huggingface-import --cache <directory> --approved-report <preview.json> [--dry-run].
Application verifies corpus/source/policy/result digests, uses the preview's fixed
result timestamp, rejects stale/changed proposals and preserves storage CAS checks.
Identical applied-result replay is a no-op.

Inspected actual two-record proposal: date precision/evidence for unchanged dates
2611.08264 and2611.05593, plus tag-order normalization in the latter. No title/author/
abstract/code/ID/count changes. Dry-run passed; applied to an isolated database copy,
then replayed with changed=false/written=false. Canonical raw SHA remains
fa50b1230e981931c5132b11b05d0daf2724cd8555a7c94fc5f32280c68c5f9f.
Real canonical import remains unapplied. outputs/huggingface_application_verification.json
records result-digest parity and migration counts. Six new regressions cover migration,
exact apply/replay and changed corpus/source/policy/result failures. Full suite passes
215 tests; Ruff lint/format pass. Remaining provenance timestamp completeness, reviewed
canonical application, scheduled/public HF integration and wider milestone gates remain.

## First guarded canonical HF metadata application

Bound HF source-date provenance to the original discovery fetch timestamp, not preview
regeneration time, and included observation times in the source-candidate digest.
Added a regression for retaining source observation time while preserving publication
date. Full suite passed216 tests before application and again against the updated
canonical corpus; Ruff lint/format and189-record schema validation pass.

Inspected and constrained the actual diff to2611.08264 /2611.05593. Dates remain
2026-11-05 /2026-11-03 respectively; both now have day precision, observed placement,
and timestamped HF evidence. Only the latter's unchanged tag set was reordered.
No title/author/abstract/code link, paper count, or ID changes occurred. Saved exact
pre-apply rollback bytes in workspace work/canonical-before-first-hf-apply.json.
Guarded apply and exact-result no-op replay verified; no commit/push/deploy occurred.
Canonical raw SHA changed from fa50b1230e981931c5132b11b05d0daf2724cd8555a7c94fc5f32280c68c5f9f
to0511b27c7531a3c7b764f1b9c1408e8c1bed95f872814a653af237ac3f0f296f.
outputs/huggingface_canonical_apply.json records the complete field diff and receipt.

Regenerated extraction coverage against the new canonical digest; dispositions remain
11 processed/147 source-work queued/30 unavailable/1 unsupported,22 accepted numeric
cells. Refreshed real trending report now has1 partial(HF-only) score and188 unavailable;
no complete scores or measured citation velocity are claimed. Earlier SHA/unchanged
statements in this chronology describe historical checkpoints. Current corpus has
189 records,2 day-precision dates and187 unknown precision dates. Canonical v2 cutover,
writer rollout, full backfill/curation, sources/venues, models and release gates remain open.


## Proceedings inventory and venue evidence foundation

Frozen config/sources.yaml with56 cells:28 requested editions, main/workshop separate.
Implemented publication_locations over shared OpenAlex metadata: exact evidenced
identifiers plus published journal/conference location required; repository hosting
is excluded. Reported work year is retained separately, never invented as confirmed
venue year. Existing cache yielded34 provisional publication-location candidates for
34 papers; no official venue/year assignments or canonical mutations. Saved
outputs/venue_location_candidates.json.

Checked current official DBLP API/query documentation. One bounded live probe returned
HTTP202/non-publication response, so the live JSON contract remains unverified.
Implemented bounded DBLP page parser/client with source total/offset/count checks,
deduplication, strict short-page/count-drift handling, one-second pacing and request
ceiling; >1000-result queries require refinement instead of false reconciliation.
Fixture tests do not substitute for live DBLP verification. Saved probe metadata.

Official CVPR2025 all-days listing loaded HTTP200 with2871 unique paper-page links.
Saved listing scratch and outputs/cvpr2025_inventory_probe.json. Marked CVPR2025 main
crawled/partial with source evidence; individual metadata and independent inventory
reconciliation remain pending. Other55 cells remain pending. Full suite passed219
tests before this audited inventory status change; final venue tests and lint pass.
No relevant non-arXiv candidate import or confirmed proceedings attribution is claimed.
All remaining edition reconciliation/discovery/official verification and broader
M0â€“M5 gates remain open.

## CVF listing parser and verified publication sample

Resumed after explicit pause; the interrupted test handle was terminal. Parsed all
2871 CVPR2025 main listing entries with ordered authors, validated edition/track URLs,
nonempty title/author inventories and no duplicate source URLs. Policy dispositions:
99 include,2723 exclude,49 review. Listing digest and counts are recorded in
outputs/cvpr2025_topic_inventory.json; full candidate inventory remains scratch.

Fetched three bounded official paper pages: FlashGS, SpecTRe-GS and Feat2GS. Citation
metadata matches listing titles/authors,2025 publication year, main conference and
exact corresponding PDF paths. Verified links identify arXiv2408.07967 /2412.09606
for FlashGS/Feat2GS; SpecTRe-GS's page supplies no arXiv link. That absence is not a
claim that no preprint exists elsewhere. Saved outputs/cvpr2025_verified_samples.json.

Added typed official publication adapter retaining edition year separately from
original date. Regression verifies merging an official2025 venue does not move an
existing2024 arXiv date or stable ID. New-source year-only records use explicit coarse
year placement; linked-preprint original-date resolution is still required before
real canonical inclusion. Three-sample deterministic preview proposes three new
records, including the CVF-only-linked SpecTRe-GS candidate; none was applied.
Saved outputs/cvpr2025_sample_import_preview.json. Ten CVF regressions cover listing
integrity, publication identity/year/track/PDF validation and date preservation.
Full suite passes229 tests; Ruff lint/format pass. Current189-record canonical corpus
is unchanged this turn. Remaining relevant CVPR pages, exact non-arXiv reconciliation,
all other venue cells, original-date resolution and broader gates remain open.

## Exact linked-preprint lookup and first CVF canonical inclusion

Added bounded exact arXiv ID-list lookup through existing shared connection/rate gate.
It omits broad topic filtering, validates1â€“40 IDs, and rejects missing/unrelated results.
Two new regressions pass. Current official arXiv manual confirms id_list semantics.
Public repository REST reported0 in-progress/queued known workflow runs before the
one-attempt batch request. Exact lookup resolved FlashGS2408.07967 to2024-08-15 and
Feat2GS2412.09606 to2024-12-12; title/author evidence matched official CVF pages.
Their2025 proceedings years remain separate. SpecTRe-GS has no source-page arXiv
link and remains correctly year-only/2025 with explicit year-start placement, not
an asserted January1 publication day.

Applied the three verified source candidates through deterministic topic/identity
preparation with preserved old-record equality, storage CAS and rollback bytes.
Corpus189â†’192; no old IDs/records removed or changed. New stable CVF IDs retain
arXiv aliases where evidenced. Canonical raw SHA now
2c7a5b5c1cab6fef9cefa5d1ff08ff5ae3c708b04fabe8e25f5835f81444b525.
Rollback copy: workspace work/canonical-before-cvf-sample.json. Exact source replay
is unchanged for all3 records. In-memory replay of actual arXiv records adds0 papers
and preserves the192-ID set. outputs/cvpr2025_canonical_import.json records receipt,
original/venue dates and future alias-replay proof. No commit/push/deploy occurred.

Full suite passed231 tests before and after canonical inclusion; lint/format and
192-record schema validation pass. Coverage regenerated:11 processed/150 source work
queued/30 unavailable/1 unsupported. SpecTRe-GS is a real proceedings-sourced record
without an arXiv alias in current evidence, not a claim that no preprint exists anywhere.
Remaining CVPR metadata, other55 venue cells, DBLP live contract, complete source
reconciliation, M0 rollout/backfill/curation and broader phase gates remain open.


## Seed reconciliation inventory and author identity fix (2026-11-09)

Recovered repository access after the approval-review usage limit. Corrected author
surname evidence: et al. is removed before matching; comma-form names, accents,
unknown authors and organization names are handled explicitly. Different abbreviated
authors can no longer agree through the token al. Eight new regression cases cover
the observed seed-name defect. Full suite279 passed in53.05s; lint/format pass.
Canonical195-record SHA256 remainsdddcf787a0a1fcdd79f4377b9fc4857b530dd68fbbc06bc5c1238be4794eac52.

Frozen exact Git baselinea235a1e7ab94d8a7719b399e3687b7840bd6d2ab in
data/baselines/seed-a235a1e.json; raw SHA256
6bbdea4ec9fac2c3e90d39d4f6ea436089458f38b914d2a34872add69203eac8.
Verified165 records and82 without arXiv IDs. All165 current active identities are
mapped in outputs/seed_reconciliation_inventory.json. Every row remains explicitly
unresolved_review pending source-backed adjudication; this inventory is not a claim
that the seed retention/archival gate is complete. Cached OpenAlex bibliographic
fields are available for many seeds; error/missing/ambiguous evidence is retained.
No seed record was merged, archived or removed. Next: resume bounded provider-cache
repair and exact source identity verification before applying seed dispositions.

## Bounded seed provider recovery (2026-11-09)

Retried38 failed baseline OpenAlex lookups through the shared authenticated client:
one request,36 successful,1 not-found,1 ambiguous,zero errors; provider-reported
cost$0.0001. Successful responses and real current-day observations were persisted
in the shared cache. No canonical fields or source timestamps were fabricated.

Generated outputs/seed_identity_evidence.json with one row for all165 baseline IDs.
123 records satisfy normalized exact title, corrected author-surname agreement,
year difference<=1 and exact DOI-alias agreement;60 of these lack canonical arXiv IDs.
These are bibliographic support checks, not reviewed retention/archival decisions.
Every disposition stays unresolved_review pending adjudication. Evidence includes
provider work digests and actual successful fetch timestamps. Canonical195 records
remain valid and unchanged. Next: verify candidate arXiv identities from exact source
records, resolve title/author/year discrepancies, then apply snapshot-bound decisions.

## Official seed arXiv verification (2026-11-09)

Derived52 unique arXiv candidates from cached DOI/location aliases for bibliographically
supported baseline seeds lacking arXiv IDs. Two coordinated official exact-ID requests
captured all52 records in batches40+12.51 satisfy exact normalized title, corrected
author surname and year-difference<=1 checks. The remaining survey2401.03890 has the
same title and matching author evidence but original preprint2024-01-08 versus seed
2026; preserve this as an independent original-date/publication-year review case.
No canonical fields or IDs were changed. Raw captures are work/seed-arxiv-exact-batch1.json
and batch2.json; combined comparison is outputs/seed_arxiv_verification_combined.json.
These source matches enable snapshot-bound metadata corrections next; they do not
constitute completed seed retention/merge/archival adjudication. Full goal remains active.

Prepared snapshot-bound corrections for51 officially verified seeds in work/seed_metadata_prepared.json and outputs/seed_metadata_review_preview.json. Validated195 stable IDs and collision-free identity inventory. Changes cover verified arXiv identifiers, DataCite DOI separation and original day-precision dates; publication-year fields preserved. One survey date discrepancy remains deferred. Canonical source SHA remainsdddcf787a0a1fcdd79f4377b9fc4857b530dd68fbbc06bc5c1238be4794eac52. Prepared result digestb774cb9bc78c83d68cf10c78147c1fd0052be78202e358c2cd4400ec86659b03. Not yet applied; next step exact snapshot/CAS application with rollback and preservation verification.

## Applied verified seed metadata corrections (2026-11-09)

Applied exact prepared51-seed metadata snapshot after source/raw/result digest checks
and locked canonical CAS. All195 stable IDs preserved; other144 records are value-identical;
publication dates/years preserved. Original dates and verified arXiv identifiers corrected;
legacy DataCite DOI values separated from published DOI slots. Model-derived paper/PDF
URLs were allowed only when formerly empty and exactly matched verified arXiv IDs.
Initial strict verification caught these derived URL changes before any write.
Rollback:work/canonical-before-seed-metadata-review.json. Replay preserved bytes.
Current raw SHA2563dd6fcf93915bef233b08f7a50c91001fafde6a9366d224826f03cbb8cd290e5.
Receipt:outputs/seed_metadata_application.json. Local public build and schema validation
pass; no Git push/deploy. Survey date discrepancy remains deferred. Full regression
run is being verified separately; earlier195-record checksum checkpoints are historical.

Post-correction verification:279 tests passed in50.85s; lint/format pass. Synthetic5000-record fixture now clears source-specific reviewed metadata evidence when assigning synthetic IDs; production review-evidence validation remains strict. Canonical corrections and public artifacts validated.

Survey date adjudication completed using official arXiv and Crossref DOI10.1145/3807511: original2024-01-08, journal online2026-05-15, publication_year2026, ACM Computing Surveys. Same stable ID; all194 other records preserved exactly; rollback work/canonical-before-survey-date-review.json. Current195-record SHA2562879bb1619737b65b49d3d9d323c832e8a3ce8e2dc2f72dc06b424ee2bbc1114. Receipt outputs/survey_date_adjudication.json. Replay no-op; local build/schema checks and279 tests pass in47.28s. Cached identity report now recognizes both published DOI and arxiv_doi fields; remaining year-heuristic mismatches must distinguish original and publication years. Seed retention/archival adjudication and full goal remain unfinished.

## Published-only seed registry verification and title corrections (2026-11-09)

Captured10 bounded successful Crossref DOI registry responses for remaining non-arXiv
publisher-DOI seeds.9 exact/prefix title+author matches; SAR-GS singular/plural title
variation was manually adjudicated using matching DOI and authors. Restored full
Fusion3DGS title and corrected SAR-GS registered title, preserving all195 IDs and all
other193 record values. Only titles and reviewed title evidence changed. Snapshot/CAS
save, rollback work/canonical-before-verified-title-review.json. Current raw SHA256
03641caed7c5163e92ac5f53b42913b03058a44e1a08abf3d8f5e850824b4013.
Outputs:remaining_seed_crossref_evidence.json and verified_seed_title_corrections.json.
Local public rebuild/schema validation pass. These registry matches are not claims
that no arXiv versions exist or that final relevance/archival adjudication is complete.

Source-reviewed two non-GS ultrasound seeds against full captured Crossref abstracts. Exclusion preparation exposed a batch archival preservation defect: after excluding paper:2024-3a358cc95f, graph repair changes paper:2017-cdf6136dba incoming citation from1 to0 before its snapshot is archived. All pre-write checks stopped the operation; canonical193-record proposal was NOT saved and current195 records remain unchanged. Work/archive_reviewed_non_gs_seeds.py records exact diagnostic. Next: fix prepare_archive_review to retain original per-paper pre-review snapshots across a batch, add regression coverage, then reapply source-backed exclusions losslessly. Full goal remains active.

Fixed prepare_archive_review batch snapshot preservation: archived originals are restored from transaction input after sequential active-graph repairs. Regression covers both linked-record exclusion orders and replay. Applied two official-abstract-reviewed non-GS ultrasound exclusions:193 active/2 archived, all original records/aliases/observations preserved in archive; replay no-op. Raw SHA25645639f4b7760453b0a3a3a89b8fdddc079542b5ae9ff0926ca28c27e5d13dd11. Rollback work/canonical-before-two-seed-archives.json. Public rebuild/schema pass. Updated original165 ledger:2 reviewed archived,163 unresolved. Application receipt outputs/two_seed_archive_application.json. Full goal remains active.

Source-adjudicated36 direct-GS seed retentions using captured official arXiv titles/abstracts, exact titles, corrected author surnames and current canonical record hashes. Ledger data/reviews/seed-reconciliation.json now covers exact165 baseline IDs:36 retained/2 archived/127 unresolved. Two immutable official source captures are retained under data/reviews/sources by SHA256. Verified all36 current record hashes and both actual archive entries; updated current titles/arXiv identifiers in unresolved inventory rows. Retentions are agent scope review, not copied policy predictions or independent human adjudication. Adjacent methods remain unresolved pending explicit scope justification. No canonical mutation;193 active/2 archived unchanged. Output seed_reconciliation_inventory.json updated. Full goal remains active.

Reviewed official full abstracts for adjacent seed methods: retained On-the-fly Reconstruction2506.05558 and ExploreGS2508.06014 as explicit3DGS pipelines. Edge-reliability2508.15158 and LiTo2603.11047 remain unresolved; no concrete GS role established by captured abstracts. Ledger now38 retained/2 archived/125 unresolved across165 IDs. Previous ledger saved by content hash under data/reviews/history. Canonical193 active/2 archived unchanged. Full goal remains active.

Captured all83 original arXiv-backed baseline records through3 coordinated paced exact-ID requests; all83 titles and author surnames agree with current canonical records. Source captures durable under data/reviews/sources. Reviewed all83 official titles; explicit Gaussian-splatting topics retained through per-title agent source review, with evidence_basis explicit_official_title, source/record/current-canonical hashes and preserved prior ledger history. Generic/adjacent titles remain unresolved for full-abstract scope review. Current ledger summary is authoritative in outputs/seed_reconciliation_inventory.json. No canonical mutation;193 active/2 archived unchanged. Full goal remains active.

Full official abstract adjudication retained SceneAgent2610.34745, VidEdit3D2610.35756, LingGS2610.36853, GCSR-OCC2610.37149, benchmark alignment2610.38349 and MLLM-GS2610.39936. Each establishes direct Gaussian representation use or concrete GS evaluation/optimization. Honeycomb-Surfels2610.37668 remains explicitly unresolved as a competing non-Gaussian primitive method; source_scope_reviewed_at records completed inspection, preventing repeated queue selection. Ledger90 retained/2 archived/73 unresolved; all prior ledger history preserved by content hash, no canonical mutation. Next select unresolved records without source_scope_reviewed_at to inspect fresh source abstracts. Full goal remains active.

Reviewed seven more full official abstracts: retained LucidLyra2610.40495, L3G-World2610.40614, PriorGS2610.41011, trusted-autonomy thesis2611.00158 via explicit REALM Gaussian-scene component, lunar benchmark2611.00870, GSExplorer2611.01543 and Xiaomi world model2611.01677 via explicit WorldRec Gaussian scene reconstruction/rendering. Ledger97 retained/2 archived/66 unresolved across165 unique baseline IDs. Revalidated every retained current record hash against canonical193-active corpus. Source hashes and prior ledger history preserved. No canonical mutation. Next continue unresolved records without source_scope_reviewed_at. Full goal remains active.

Full official abstract review retained SCARF2611.02365, RxGS2610.25681, PhysSkin++2610.26067 via explicit Gaussian animation binding, World2HOSI2610.27725, coded-aperture design2610.28004, and SplatFlux2610.28257. OV-Foam2610.28131 remains explicitly unresolved as a competing PowerFoam primitive representation; source_scope_reviewed_at prevents repeated fresh-queue selection. Ledger103 retained/2 archived/60 unresolved; all retained record hashes validated, previous review history preserved. Canonical193 active/2 archived unchanged. Full goal remains active.

Full official abstract review retained CoGaussian2610.28530, AEON2610.28631, Real2Sem2Real2610.28880, AirPlayground2610.29699, TerraTransfer++2610.30319 via concrete GS HUGSim evaluation, and SplatLab2610.30468. AutoPhyX2610.29517 remains explicitly unresolved: general representation compatibility alone does not establish a concrete GS application/evaluation. Source-scope review timestamp/capture hash retained for pending case. Ledger109 retained/2 archived/54 unresolved; all retained current record hashes verified and prior history preserved. Canonical193 active/2 archived unchanged; full goal remains active.

Completed source-scope adjudication of all83 original arXiv-backed baseline seeds:79 retained and4 explicit unresolved scope cases (Hexels, OV-Foam, CVTSplat competing primitives; AutoPhyX compatibility-only abstract). Latest full abstracts retained GSHeadRelight2610.30619, CLIP calibration2610.30908, PixGR2610.31908, GEMS2610.33158, LegoOcc++2610.34093, RIDE-Splat2610.34632, DUET4D2610.35002 and monocular-flight planning2610.26508 via concrete GS simulation. Overall165 baseline ledger117 retained/2 archived/46 unresolved. All retained canonical hashes verified, prior history preserved, no canonical mutation. Remaining46 comprise4 explicit original-source scope cases and42 older seed cases. Full goal remains active.

Completed full-abstract scope inspection for remaining14 officially identified older seeds: retained TUM2TWIN2505.07396 for explicit GS novel-view benchmark and Lift4D2606.23688 for explicit deformable3DGS optimization. Twelve general geometry/NeRF/background cases remain explicitly unresolved with per-paper source-linked scope reasons and inspection timestamps. Ledger119 retained/2 archived/44 unresolved; previous ledger history preserved, canonical193 active/2 archived unchanged. These pending cases need specific curated-foundation or GS application evidence rather than automatic inclusion. Full goal remains active.

Reviewed eight remaining publisher-DOI seeds against captured registry records. Retained Fusion3DGS, cultural-artifact GS, SAR-GS, ThermalGS and thermal SfM/GS rendering using explicit registered GS titles plus exact DOI/title/author evidence. Ultrasound NeRF remains adjacent-scope unresolved; FisherRF and cooperative-UAV digital twins lack registry abstracts and retain explicit primary-source lookup tasks. Registry captures durable under data/reviews/crossref-sources, with paths/hashes recorded per ledger row. Ledger124 retained/2 archived/39 unresolved, all retained canonical hashes verified; previous history preserved. Canonical193 active/2 archived unchanged. Full goal remains active.

Three bounded official arXiv title lookups completed with shared pacing. FisherRF search returned original2311.17874 and primary extension2410.04680 explicitly identifying/using FisherRF for3DGS. Retained FisherRF seed using specific GS application evidence; original/journal title variation remains an explicit identifier review, no automatic arXiv binding. Cooperative digital twins and streaming-scenes title queries returned0; durable negative query captures recorded without claiming absence of preprints. Ledger125 retained/2 archived/38 unresolved; history/source evidence preserved, canonical193 active/2 archived unchanged. Full goal remains active.

Resolved streaming seed2604.02851 through exact official lookup plus official version-one metadata and DataCite. Version-one title matches original seed exactly; current title is Streaming Persistent3D Gaussian Proxies for View-Flexible Remote Rendering; same ID/DOI and matching author evidence. Retained as direct Gaussian remote-rendering method. Three immutable versioned source captures retained under data/reviews/versioned-sources. Earlier empty title search correctly superseded by exact versioned evidence. Canonical arXiv/title refresh remains separate pending work; no canonical mutation. Ledger126 retained/2 archived/37 unresolved. Full goal remains active.

Applied version-verified streaming seed metadata refresh under stable IDpaper:2026-48934263b9: arxiv2604.02851, current official title, original day-precision date and URLs; DataCite DOI moved to arxiv_doi. All192 other active records and2 archives preserved. Rollback work/canonical-before-streaming-version-refresh.json. Updated retained-review record hash and history; summary126 retained/2 archived/37 unresolved unchanged. Receipt outputs/streaming_metadata_refresh.json. Current193-active raw SHA256148617d5fc9e81fc215d89fb10291a88ea95c19f10d02fcd9aec8bde85778778. Local public rebuild completed; validation/testing verification follows separately. Full goal remains active.

Inspected six available local PDFs, hashed full originals and extracted first-page title/abstract evidence with pdfplumber. Retained GaussTwin, Cut-and-Splat,3DGStream, consistent-region active learning, continual-learning edge optimization, and InsideOut as direct GS methods. Truncated3DGStream/InsideOut seed titles resolved for scope from complete source titles; canonical bibliographic changes remain separate. Cut-and-Splat extracted author spelling flagged for rendered review, not silently altered. Durable manifests under data/reviews/local-pdf-evidence contain PDF/text hashes and opaque local locators, not private filesystem paths or published figure assets. Ledger132 retained/2 archived/31 unresolved; all retained record hashes verified. Canonical193 active/2 archived unchanged. No extra PDF downloads or remote transfers. Full goal remains active.

Inspected eight more available local PDF first pages. Retained MRI Gaussian reconstruction, AeroDGS, UAV photorealistic GS pipeline, D3DR harmonization, Asset Harvester and SHARP using direct source method evidence. AR-VIU point-cloud ultrasound and Seoul world-model synthetic data remain explicitly unresolved pending full methods inspection. Full PDF hashes, page1 text hashes and opaque source locators retained in durable manifests; no private paths/figures published. Ledger138 retained/2 archived/25 unresolved; all retained current record hashes verified, previous history preserved. Canonical193 active/2 archived unchanged; full goal remains active.

Inspected full local PDFs for AR-VIU(17 pages) and Seoul world model(32 pages). Source methods resolve both as outside current GS scope: AR-VIU native point-cloud octree renderer(p2,p12), Gaussian KDE only(p14); Seoul synthetic data uses CARLA/Unreal(p6), depth forward splatting(p10), Gaussian noise and bibliography mentions are not GS method evidence. Applied lossless reviewed exclusions with exact original archived snapshots and replay no-op. Canonical191 active/4 archived; raw SHA2563d40dd000765944d1e2dd6ae3d0a5111ed4b700654c7e5780a70f46dbe7fa3ea. All138 retained record hashes unchanged. Baseline ledger138 retained/4 archived/23 unresolved. Rollback work/canonical-before-fulltext-two-archives.json; receipt outputs/fulltext_two_seed_archive_receipt.json. Local build/schema pass; regression result follows. Full goal remains active.

Inspected remaining six local first pages: retained GS property-assessment review and academic ISR GS application paper. SyncDreamer, urban UAV optimization and cooperative UAV digital twins remain methods/foundation scope cases; local publisher PDF now supplies previously missing cooperative-UAV abstract. The pregnancy ultrasound debate has a source-backed proposed exclusion, not yet applied. Full titles, PDF/text hashes and opaque locators retained; source_scope_reviewed_at and next_source_action populated for pending cases. Ledger140 retained/4 archived/21 unresolved. Every retained record hash verified; history preserved; canonical191 active/4 archived unchanged. Full goal remains active.

Applied primary-source clinical debate exclusion with preserved original snapshot, rollback work/canonical-before-clinical-debate-archive.json and replay no-op. Receipt outputs/clinical_debate_archive_receipt.json. Audit outputs/seed_reconciliation_audit.json verifies165 unique original IDs,140 current retained record hashes and5 archives. Original arXiv subgroup79 retained/4 unresolved; original82-without-arXiv subgroup61 retained/5 archived/16 unresolved. Historical59/23 estimate not forced or claimed verified. Resolved archive tasks removed from active review queue. Broader pipeline gates and20 scope cases remain incomplete; full goal remains active.
## Weekly reconciliation checkpoint (2026-11-09)

Added local `.github/workflows/weekly-reconciliation.yml`: Saturday 02:00 UTC
feed-branch scan, independent `data/ingestion/weekly` state, 30-day updated
overlap, 60-request / 900-second default pass budgets, shared repository writer
concurrency, and checkpoint/diagnostic persistence before required-source failure.
Historical backfill remains separate. Nothing has been pushed or dispatched.

The fixture recovers a late-indexed record with a 20-day-old update timestamp
that daily ingestion missed, verifies interruption/resume, independent daily
state, outage coverage, and idempotent replay. All282 tests pass in33.25s;
lint/format and workflow YAML/Bash syntax checks pass. A live dry run verified
three pages twice in six requests over `[2026-10-10, 2026-11-09)`:231 candidates,
210 include /21 review,110 proposed inserts /100 proposed updates. No canonical
write or watermark occurred. Canonical190 active/five archive and SHA unchanged.

The previously approved remote service/timer installation is recorded above.
A fresh SSH connection timed out in this turn, so its current running state was
not reverified. No additional PDF transfer or service modification was attempted.

## Scheduled signal refresh checkpoint (2026-11-09)

Implemented `refresh-signals --provider ... --due` with bounded request/time/
paper budgets, cache-only mode, keyed-provider credential skips, explicit health
reports, and optional workflow summary output. All three adapter queues now
prioritize never-attempted then oldest-attempt IDs to avoid bounded-pass
starvation. Common citation refresh opts into daily recent/weekly older cadence;
legacy metadata refresh TTL defaults and retry clocks remain unchanged.

Added a seven-day04:00 UTC `daily-signals.yml` writer and integrated due-provider
passes into daily arXiv, midweek sync, and weekly release before build/checks.
Each provider is bounded to5 requests/90 seconds/100 due papers, with serialized
writers, cache/report persistence, explicit failures/skips, and cached-publication
fallback. Four workflow YAMLs and17 Bash blocks validate. Nothing deployed.

The live OpenAlex canary used one request and reported cost$0.0001:6 attempted,
5 successful exact matches,1 ambiguity,0 errors. HF used two requests:1 match,
1 confirmed miss,185 remaining due. Semantic Scholar skipped without a key.
Canonical190 active/five archived and raw SHA unchanged. No mature velocity
claim: the real dated interval still has not elapsed.

All295 tests passed in37.75s including13 new regressions; lint/format97 files,
build, schema, and diff whitespace checks pass. See reports/scheduled-signals.md
for exact semantics and limitations. S2 dated history/live success, HF discovery
scheduling, public provider/score integration, deployed secrets/workflows, and
the broader M0-M5 completion gates remain open.

## Semantic Scholar history checkpoint (2026-11-09)

Added strict, separately labelled S2 dated history alongside latest observations:
first successful count per paper/UTC date, optional influential count,13-month
calendar retention, exact normalized provider identity, and no samples from
failures/misses/cache-only reads. History is saved before cache publication.
A simulated failure between those writes proves idempotent retry and no lost
first-day sample. Retained history also prevents remapping after cache loss.

Extended `momentum --provider semanticscholar` and shared velocity measurement
with source-specific identity validation, labelled results,7–45 actual-day
baselines, fractional elapsed time and negative-correction handling. OpenAlex
default behavior remains intact. Provider histories/counts are never blended.

All307 tests pass in49.51s, including12 new history/consumer regressions; lint,
format100 files, build, schema190 records, and diff checks pass. The real current
S2 momentum report shows190 no_observations and no production S2 history file.
Fixture histories establish behavior, not live enrichment or measured velocity.
Canonical190 active/five archived and raw SHA unchanged; no push/deployment.

S2 keyed live success, a genuine minimum seven-day interval, public provider/
ranking UI, workflow rollout, and full M0-M5 acceptance remain incomplete.
See reports/semanticscholar-history.md for persistence and recovery semantics.

## Public provider selector checkpoint (2026-11-09 America/Los_Angeles)

Added an explicit OpenAlex/Semantic Scholar selector and source-specific
most-cited sorting, URL state, card source/status/fetch-date freshness, optional
influential counts, and unavailable handling. OpenAlex stays default. Current
provider observations project into the public index and a separate hashed lazy
signal artifact; canonical JSON is unchanged. Public artifacts contain selected
active-paper fields only, never full/private responses or archived rows.

Real Edge QA passes50 initial cards with0 signal requests, one lazy request
when selecting S2,50 honest unavailable S2 cards, source-specific sorting, URL
reload restoration, intentional network failure/retry, return to OpenAlex, and
390px mobile with no horizontal overflow. A browser-found sort insertion bug was
fixed before acceptance; the temporary QA browser/server are stopped.

All311 tests passed in21.86s, including four new provenance/identity/privacy/
zero/freshness/payload regressions and5,000 fully observed two-provider rows under
the4 MB lazy-artifact gate. Lint/format103 files, build, schema190 records, hash
verification and patch checks pass. Canonical190 active/five archived and SHA
unchanged; graph projection currently28 edges. No push or deployment occurred.

Public trending/velocity display, genuine S2 live/history maturity, full source
coverage, workflow rollout, and broader M0-M5 release gates remain open. See
reports/public-provider-selection.md and the saved mobile screenshot/evidence.

## Public trending checkpoint (2026-11-09 America/Los_Angeles)

Added deterministic lazy source-specific discovery snapshots, trending sort,
complete/partial/unavailable filters, formula/version/weights and observation
dates, signed actual-window velocity/correction presentation, URL state and
retry. Snapshots expire at the earliest supporting-signal/age boundary or24h,
with an automatic deadline rerender. No provider time series are blended.

All317 tests pass in22.77s, including six new score/payload/expiry/indexed-history
regressions. The realistic-ID5,000-paper two-provider complete fixture remains
under4 MB. Lint/format106 files, build/schema190, hashes, diff and byte-identical
no-op manifest checks pass. Real Edge coverage-filter/source/URL/retry/expiry
and390px mobile checks pass; temporary browsers/server stopped.

Real current results:0 complete /1 HF-only partial /189 unavailable for each
provider, and0 measured velocities. The displayed partial45.59 uses HF weight1.
It is not evidence of live citation velocity. Canonical190 active/five archive
and raw SHA unchanged. No push/deployment. Live S2 success, real7-day history
maturity, full historical/venue coverage and broader M0-M5 release gates remain
open. See reports/public-trending.md and saved validation/mobile evidence.

## Frozen scheduled HF discovery checkpoint (2026-11-09 America/Los_Angeles)

Added persistent frozen discovery windows with hash-bound daily evidence and
pretraffic validation, cross-day/cache-expiry resume, bounded overlapping outage
catch-up, explicit truncation status and exact import previews. Daily arXiv and
seven-day provider workflows now discover HF under10-request/120-second caps,
retain source checkpoints/reports, and prepare proposals without auto-application.

The live seven-date canary needed2+5 requests across two invocations of the same
run, retained both original response hashes, and accounted for158 candidates.
The preview has2 includes/155 excludes/1 review,2 existing-record updates,0
insertions; no changes applied. Canonical190 active/five archive and SHA unchanged.

All324 tests passed in24.42s including seven new regressions; lint/format109
files, build/schema, four workflow YAMLs and17 shell blocks pass. No deployment.
HF reviewed applications and broader completeness, S2 live/history maturity,
workflow/secret rollout, and full M0-M5 release gates remain open. See
reports/hf-scheduled-discovery.md and the saved live receipts/proposals.

## Manual operation dispatch checkpoint (2026-11-09 America/Los_Angeles)

Added preview-default manual backfill and reviewed worker-import workflows with
validated environment inputs, shared writer concurrency, frozen resume, expected
feed-parent checks before ordinary pushes, full pre-push checks and failure
reporting after valid checkpoint persistence. Reviewed-source preparation uses
only matching active canonical public PDF URLs, bounded HTTPS origin/redirect/
byte/time retrieval, and exact source/result hashes. Existing reviewed import
controls application; source PDFs remain temporary. Contributor/README generator
operator instructions updated together. No workflow deployed or dispatched.

All340 tests pass in24.01s, including16 new regressions. Both manual workflows
and10 Bash blocks pass YAML/syntax checks; lint/format112 files, build/schema
190 and diff checks pass. A narrow live backfill dry run accounted for40 records,
resumed with0 source requests plus1 comparator request, then replayed with0
requests. Proposals:37 include/3 review;6 inserts/31 updates; nothing applied.
Worker import/materialization proof uses fixtures only. Canonical190 active/
five archive and raw SHA unchanged.

Live dispatch/branch-race rehearsal, compatible rollout, real reviewed-source
workflow evidence, full historical/venue coverage, S2 live/history maturity and
broader M0-M5 release/deployment gates remain open. See reports/manual-operations.md.

## CVPR2025 metadata checkpoint (2026-11-09 America/Los_Angeles)

Resumed and verified the unfinished CVF capture code, corrected its date enum,
and added bounded CLI operation plus official author-abstract provenance. All
148 title-prioritized official pages now verify from the frozen2,871-entry main
listing:148 author abstracts,101 arXiv links,0 capture failures. Current title
screen101 include/47 review/2,723 exclude; full metadata117 include/31 review.
A0-request replay revalidates every saved hash and publication contract.

Independent current official accepted/proceedings inventories each have2,871
rows:2,861 normalized-title matches and10 reviewed title variants account for
all current rows. Two author-name differences are retained without person-alias
claims. The separate official announcement reports2,872; that one-paper aggregate
difference remains unresolved, so overall reconciliation staysfalse/partial.

All348 tests pass in24.88s, including eight new capture/provenance/pacing/CLI
regressions. Lint/format116 files, build and schema190 pass. Canonical190 active/
five archived and raw SHA unchanged. No import/push/deployment. Remaining work
includes31 scope reviews, excluded-title recall audit, exact arXiv original-date
verification,55 other venue cells and the full M0-M5 release/live-history gates.
See reports/cvpr2025-metadata-capture.md and saved evidence.

## Reviewed CVPR import and branch checkpoints

Verified101 exact arXiv links (99 direct plus two source-bound title/name-order
reviews), preserving47 year-only source dates. Corrected three comparison-only
false inclusions with policyv3; both frozen100-record fixtures retain1.00 numeric
precision/recall with their disclosed sampling/reviewer limitations. Explicit
zero-request source-evidence migration retains the old v2 capture.

Applied110 inserts and four existing-record enrichments:300 active/five archive.
All old core identifiers/original dates and archive snapshots are preserved;
186 old records unchanged. Replay:114 unchanged/34 review;0 inserts/updates/merges.
An immutable pre-import snapshot and receipt provide rollback evidence. All165
seed IDs remain mapped,140 retained hashes validate after one explicit source
refresh, and20 scope cases remain unresolved. Full357 tests pass in27.37s;
lint/format118 files, build/schema300 pass.

At user request, work now lives on codex/papers-pipeline-phase2-3 with local
validated milestone commits, separating implementation from data/evidence.
Implementation checkpoint:6b4116a. No push/deployment. Full M0-M5 requirements
remain active; see reports/cvpr2025-reviewed-import.md.
