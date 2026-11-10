# Contributing to Awesome 3D Gaussian Splatting

Thank you for your interest in contributing! This project is an open-source, community-driven living aggregate of **3D/4D Gaussian Splatting** literature and neural rendering tools.

---

## How to Add Your Paper or Project

We welcome authors and researchers to submit new papers, official code repositories, and interactive project demos.

### Option 1: GitHub Issue Submission (Fastest)
1. Open a new issue using our **[Paper Submission Template](https://github.com/mango-jeongi/awesome-gaussian-splatting/issues/new?template=paper_submission.yml)**.
2. Provide your arXiv ID (or paper URL), title, primary author, and official code/project links.
3. Our automated pipeline or maintainers will verify and merge it into `data/papers.json`.

### Option 2: Pull Request (Direct Contribution)
1. Fork the repository and clone it locally.
2. Ensure you have `uv` installed (`pip install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`).
3. Set up the environment:
   ```bash
   uv sync --all-groups
   ```
4. If your paper is on arXiv, you can run the CLI ingest command or append the record to `data/papers.json`:
   ```bash
   # Validate schema adherence
   uv run python -m src.cli validate

   # Rebuild README and web portal artifacts
   uv run python -m src.cli build
   ```
5. Run the test suite:
   ```bash
   uv run pytest -v
   uv run ruff check .
   uv run ruff format --check .
   ```
6. Submit a pull request against the `feed` branch (or `main`).

---

## Proposing New Taxonomy Categories or Technical Tags

If a new subdomain is emerging in Gaussian Splatting (e.g., *Optical Flow Splatting*, *SDF Hybrids*, *Edge Robotics*):
1. Open an issue or edit [`config/taxonomy.yaml`](config/taxonomy.yaml).
2. Add keyword triggers under `categories` or `technical_tags`.
3. Test retroactive tagging:
   ```bash
   uv run python -m src.cli retag
   uv run python -m src.cli build
   ```
4. Submit a PR with the updated taxonomy and regenerated artifacts.

---

## Community Guidelines
- Respect the work of original authors and researchers.
- Maintain accurate venue attribution and code links.
- Keep the database neutral, factual, and comprehensive.


### Storage migration preview (M0 foundation)

Use the SSD environment above, then run `uv run python -m src.cli migrate --dry-run`.
This checks exact record parity and reports the proposed snapshot digest without
writing a store. To write a separate snapshot, use `migrate --manifest <path>`;
validate it with `validate --manifest <path>`.

The full-corpus [migration rehearsal](reports/storage-migration-4102.md) verifies
record and generated-byte parity, rollback, no-op behavior and failure fencing.
It can be reproduced with `uv run python -m scripts.qa.storage_rehearsal --workdir
<isolated-directory> --report <report-path>`. Provider caches and reviewed extraction
sidecars must remain alongside the active canonical store; metadata parity alone
does not prove their preservation.

This is an additive compatibility stage. All database callers accept either a
legacy file or manifest through `--data`. Defaults and current remote workflows
still use `data/papers.json`; the canonical cutover remains pending. The snapshot preserves legacy fields and record order.
Legacy citation values have unknown observation freshness, including zero counts.

Monthly shards have immutable SHA-256 filenames. A validated manifest is replaced
only after every referenced shard exists and passes parity validation. Prior
shards remain available after a month correction or interrupted write. Do not
remove previous generations while a manifest can still reference them. Rollback
of an activated snapshot requires restoring its matching previous manifest and
retained shards; the legacy store remains the current operational rollback path.

Identity aliases, typed observations, compatible database adapters, local workflow
coordination changes, and compact browser artifacts are implemented. Remaining M0
work includes provenance/date-precision/archive contracts, remote writer rollout,
canonical cutover, and remaining browser acceptance cases. Migration preview alone does not
satisfy the M0 exit gate.

The builder also writes `docs/data/manifest.json`, a compact index, bounded detail
shards, a complete lazy search corpus, and aliases. Existing public artifact
generations are retained. The portal mounts at most 50 cards; abstracts, full
authors, relationships, and BibTeX load on demand. A failed full-search download
shows a retry state rather than silently searching an incomplete corpus.

Use `migrate --dry-run --report <path>` to save all source IDs, the raw source
SHA-256, legacy-zero count, edge count, and parity result. Unknown input fields or
normalization that changes existing raw field values block migration for review.
Provider failures preserve successful values and their original fetch time.

## Manual backfill and reviewed worker imports

The manual workflow definitions use the same `repository-writer` concurrency
group as scheduled writers. They operate on `feed`, re-fetch after acquiring the
job slot, remember the expected parent, and refuse to push if the branch advances
unexpectedly. Both run build, schema validation, Ruff lint/format and the full
fixture suite before persisting changes. Preview is the default; an operator
must explicitly choose apply. No manual workflow deploys Pages.

For historical ingestion, use `manual-backfill.yml` with a stable lowercase run
key, an exclusive UTC cutoff, the same optional lower boundary on every resume,
and1–100 requests per pass. Query, policy and date changes require a new run key.
The equivalent bounded preview is:

```sh
uv run python -m src.cli backfill --since 2026-11-01 --until 2026-11-09 --run-dir data/ingestion/backfill/example --resume --dry-run --max-requests 20
```

Choose the intended interval instead of treating these example dates as a
coverage target. Removing `--dry-run` permits deterministic canonical import
through existing identity, relevance, archive and storage validation. A request
ceiling or saved checkpoint is not completed historical coverage: inspect source
and comparator status, unresolved dispositions and import receipts. Source
failures are reported after a valid checkpoint/diagnostic commit. A runner lost
before that commit can replay its uncommitted work from the last saved checkpoint;
no uncommitted prefix is claimed durable.

Source-backed relevance overrides may use `include`, `exclude`, or `review`.
A `review` override holds an exact candidate identity out of automatic import
without archiving an active record. Include the captured source hash, scope
reason, reviewer and aware review time. Reclassification after a completed crawl
uses a separate application ledger and policy snapshot; retain the original
query, source pages and disposition epoch.

For reviewed extraction, commit JSON inputs under
`data/extraction/review-inputs/<key>.result.json` and `<key>.review.json`, then
dispatch `manual-worker-import.yml` with that key. The result must validate against
the extraction schema; the review must identify its exact bytes, original PDF
digest, canonical snapshot, reviewer/time and accepted cell context. Unreviewed
results are never inferred to be accepted. The runner materializes only the
active paper's canonical public PDF from arxiv.org, export.arxiv.org, or official
CVF HTTPS URLs. It allows at most four requests/three approved-host redirects,
50 MB and120 seconds, then checks PDF signature and exact SHA-256. Unsupported
sources or revised PDF bytes fail; update source evidence/review explicitly.

The PDF lives in runner temporary storage and is excluded from generated commit
paths. Preparation changes no canonical records or review ledger. The subsequent
`uv run python -m src.workers review-import` command uses the existing source/
result/canonical guards and accepted-context/reuse rules. Preview validates
without writing; apply writes only the reviewed ledger and checked public output.
Existing identical decisions replay without duplication. Figure asset publication
requires its separate review/materialization path; this dispatch does not copy
source PDFs or unreviewed crops into public assets.

These definitions must be rolled out with compatible code on both branches.
Live GitHub dispatch, branch-race rehearsal and deployment evidence are separate
release gates; local fixture/YAML/Bash checks do not establish a successful live
workflow. No extra private-file transfer or secret setup is performed by adding
these definitions.

## Official CVF metadata capture

`uv run python -m src.cli discover-cvf --listing <saved-official-listing.html> --venue CVPR --year 2025 --max-requests 10 --max-seconds 120` resumes a
frozen official listing/policy/edition under `data/venues/cvpr2025-main` by default.
`--track workshop`, `--cache PATH`, `--overrides PATH`, and `--report PATH` are
explicit options. `--max-requests 0` validates retained page hashes without
network traffic. Listing inputs are bounded to20 MB, individual responses to2 MB,
and metadata requests are paced at least one second after the previous response.

Only title-screened include/review candidates are prioritized. Each verified
publication must match the official listing's title, authors, edition, track and
PDF URL; linked arXiv IDs and official author abstracts are retained separately
with source evidence. A publication year is not an invented original preprint
day. Missing author abstracts remain missing. Incomplete/duplicate abstracts,
source conflicts and corrupted hashes fail verification. Per-page checkpoints
and retry deadlines survive budget stops; a changed listing/policy needs a
separate explicit capture directory. This command writes evidence, not canonical
papers, and selected metadata completion is not full venue reconciliation.

For CVPR2025 the current accepted table and proceedings listing each contain
2,871 records after ten reviewed title variants. A separate conference announcement
reports2,872; the one-paper aggregate discrepancy and remaining scope reviews
are retained as unresolved. Source HTML, hashes, author-list differences and
comparison evidence live under the capture directory. Canonical identity/date
verification and any eventual import are separate steps.

## Portal styling and browser acceptance

The portal uses the committed `docs/assets/portal.css`, compiled with the pinned
Tailwind version in `package-lock.json`. After editing utility classes in HTML or
browser assets, run `npm ci --ignore-scripts --include=dev` and `npm run build:css`,
then review and commit the generated CSS. CI runs `npm run check:css` to detect
stale styles. Paper-only ingestion uses the committed stylesheet.

The isolated 5,000-record fixture, project-path gzip preview server and real-browser
acceptance recipes are documented in [scripts/qa](scripts/qa/README.md). Recorded
measurements and their limits are in [the portal acceptance report](reports/portal-acceptance-20261110.md).

## Optional PDF-cluster synthesis

Install the optional dependencies with `uv sync --frozen --group research` in the
prescribed SSD environment. Prepare a new receipt without network access:

```sh
uv run --group research python -m src.deep_research --paper "<canonical-id>=<local-pdf>" --question "<research question>" --output <new-draft.json>
```

Repeat `--paper` for an explicitly selected cluster (1–30 active canonical IDs).
The operator must verify each PDF's identity. A dry run hashes each PDF, extracts
its physical pages and records provenance without sending documents or loading
credentials. It does not estimate provider tokens or generate a synthesis.

To generate a separate draft, configure `GEMINI_API_KEY` in the process or ignored
`.env.local`, then use a **new** output path and add `--execute`. This sends the
selected full PDFs and extracted page text to Gemini. The default model is the
resumption plan's `gemini-2.5-flash`; `--model` explicitly selects another model
when access or lifecycle changes. There is no automatic model fallback.

Execution first counts input tokens and refuses generation when the configured
budget is exceeded or unavailable. Defaults are 200,000 admitted input tokens
(including a 1,024-token framing reserve) and 8,192 maximum output tokens. These
are token limits, not a dollar-cost guarantee. Each SDK call has a 120-second
network timeout and one attempt; there is no automatic generation retry. The
aggregate raw PDF limit is 40 MB, with at most 200 pages per PDF. Scanned PDFs
without extractable text are rejected; no OCR is performed by this command.

The structured output separates reported claims from inference. Each claim must
cite a selected ID, physical PDF page and an exact quote present in that page's
extracted text. Every selected source must be cited or explicitly named in a
coverage gap. Unknown sources, incorrect quotes/pages, truncated/blocked output
and schema failures are refused. Existing drafts cannot be overwritten, and
output under canonical data or deployed docs is refused. Receipts retain source,
page-text, catalog and instruction hashes, model, parser version and token usage.

All generated synthesis remains **unreviewed**. Quote presence does not prove
that a claim follows from the quote, establish valid benchmark comparisons, or
verify scientific correctness. A human must review the sources and claims before
using the draft. No result enters canonical metadata, the public portal or an
extraction review store automatically. Scheduled ingestion remains deterministic.

The SDK calls follow the official [Google Gen AI SDK documentation](https://googleapis.github.io/python-genai/).
The [RadSplat dry-run receipt](reports/runs/deep-research-radsplat-dryrun-20261110.json)
proves local preparation of the 15,059,485-byte, 11-page PDF. A live generation and
reviewed multi-paper synthesis remain unverified because no Gemini key was
configured for that check.

## Optional local llama-server table candidates

`src.workers.llama_parser` supplies an opt-in worker backend for structured
numeric-table candidates. It uses the existing SSD cache, leased queue, bounded
parser subprocess and snapshot-bound human review import. It does not replace
the default deterministic ruled-table/figure parser.

Create a private JSON configuration outside canonical data:

```json
{
  "endpoint": "http://127.0.0.1:8080",
  "model_alias": "qwen-local",
  "declared_model_sha256": "<64 lowercase hex characters from the GGUF file>",
  "max_page_requests": 4,
  "max_words_per_page": 1200,
  "max_output_tokens": 2048,
  "request_timeout_seconds": 30
}
```

The entire configuration and prompt are bound into the extractor/job identity.
The model digest is operator-declared: verify the actual GGUF with `sha256sum`
and start the server using that file and the configured alias. The adapter checks
the returned alias but cannot cryptographically attest the loaded weights.

Use a separate queue for this backend and pass the same config to both commands:

```sh
uv run --group extraction python -m src.workers enqueue --queue <llama-queue> --cache <ssd-cache> --pdf <pdf> --paper-id <canonical-id> --source-url <source-url> --timeout 300 --llama-config <config.json>
uv run --group extraction python -m src.workers pass --queue <llama-queue> --cache <ssd-cache> --max-jobs 1 --llama-config <config.json>
```

Only literal loopback HTTP endpoints with explicit ports are accepted. Environment
proxies and redirects are disabled. Each selected page has one request and no
automatic retry; the normal job attempt budget still applies. The outer parser
subprocess timeout bounds the complete pass for each job, including PDF parsing
and local inference. Size/page/result limits and lease fencing continue to apply.

The adapter selects at most the configured number of pages, ordered by numeric
word density then physical page number. Pages above the word budget are skipped,
not truncated. Selected and omitted pages are recorded in result warnings. The
model returns word indices through llama-server's JSON-schema response format;
each raw numeric value is exactly one source word. Labels, units and bounding
boxes are reconstructed from source words. Multiword numeric expressions are
not combined by this backend and need separate source review.
Invalid indices/order, duplicates, model-alias mismatch and truncated output are
refused. Missing context remains null. No figure candidates are produced by this
backend. Word presence does not establish correct table semantics: all candidates
remain `review-required`, including apparently complete rows and units.

The adapter follows the official [llama-server API contract](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).
Model installation, CUDA compatibility, VRAM/context limits, live extraction
quality and headless llama-server operation must be verified on the host before
configuring its timer to use this backend. The existing timer continues to use the
deterministic parser until that rollout is validated.

## Extraction model comparison scorer

Evaluate one or more extractor groups against an explicit positive subset of the
source-reviewed numeric ledger:

```sh
uv run python -m src.workers.evaluation --reviewed data/extraction/reviewed.json --paper-id <id> --result <result.json> --report <new-report.json>
```

Repeat paper IDs and result paths for the same fixed comparison scope. Each result
must match the reviewed paper/PDF digest. At most one result per extractor and
paper is admitted. Missing paper results count as missed reference cells. Different
PDF versions need separate scoped ledgers; source hashes cannot be mixed silently.
The scorer records ledger/result hashes, review identities and per-cell outcomes.
It does not invoke a model or modify the ledger, results or canonical corpus.

Matching requires the same physical page and at least 80% of a prediction's box
inside a reviewed cell. Ambiguous or duplicate coordinate matches receive no
credit. Value comparison normalizes whitespace only and preserves case; it never converts
numbers or units. Row, column, dataset, split, metric and unit strings are reported
separately as exact, different or missing. Equivalent paraphrases can differ and
need inspection. This is quality scoring only; measure runtime and VRAM separately.

The current accepted subset has 22 cells across six papers, reviewed by Codex
from rendered sources. It is not an independent human benchmark or all table
cells. The [baseline receipt](reports/runs/extraction-reviewed-subset-baseline-20261110.json)
checks deterministic-parser self-consistency: 22 matched/exact values, with
729 additional numeric candidates outside the accepted reference subset left
unscored. No population precision or model superiority follows from those values.
Use the same scope, source digests and budgets before comparing Gemma and Qwen.

A bounded [Gemma GPU smoke test](reports/gemma-gpu-canary-20261110.md) has now
verified one source-grounded synthetic value. The optional configuration accepts
`enable_thinking` (default false); it is sent to the chat template and bound into
the extractor/job digest. Context fields were empty in this canary, and the
updated adapter is not deployed into the active worker. Live real-table quality,
full-length context, warm performance and persistent model operation remain open.

## Immutable release, retry and rollback

The weekly workflow now prepares a GitHub draft release, commits its generated
candidate, and packages a frozen site outside the working tree. The packer requires
a clean checkout and committed code/data/site inputs, verifies the public manifest
and every referenced artifact, and rebuilds the current data projection in isolation
to refuse stale source or provider-cache output. Local coordination locks are not
published. Unknown ignored/uncommitted site files are refused rather than copied.

A release ID binds the source commit/tag, code/config/dependency and canonical/
provider/review input hashes, public data build digest and every static file byte.
The public payload includes canonical `release.json`; it contains hashes and
relative input names, not raw private provider responses or credentials. Source
fingerprints cover either legacy or active monthly-store components. An input
change during packaging fails safely. The deterministic tar fixes path order,
metadata, ownership and timestamps; identical input bytes produce identical tar
bytes. Packaging fails rather than replacing an existing output directory.

From a committed candidate in the prescribed SSD environment:

```sh
uv run python -m src.releases pack --output <new-staging-directory>
uv run python -m src.releases restore --archive <release.tar> --expected-release-id <trusted-release-id> --output <new-restored-site>
```

For a tagged weekly candidate, add `--release-tag vYYYY.Www`; the CLI checks that
the local tag points to the exact candidate commit. The pack output contains
`site/`, `release.tar` and `receipt.json` with archive SHA-256 and source/release IDs.
Archives are size/file-count bounded. Restore validates the expected release ID,
all content hashes and public pointers before writing a new directory; absolute,
traversing, link, duplicate and unsupported members are refused. It never rebuilds
an old portal with current data. Retain the trusted release ID outside the archive;
accepting an arbitrary ID read from an unknown archive would not authenticate it.

The weekly workflow retains `papers-release-<release-id>-<source-attempt>` for
90 days (subject to repository retention policy) using a verified pinned upload
action. The Pages artifact is separately named by candidate and source attempt.
Deploy-only job retries consume that exact artifact name. Candidate source code
is checked out for deployed-byte verification. A GitHub release leaves draft state
only after the expected deployed release ID, manifest and every candidate file
are verified. Static-byte checks do not replace browser route/history/mobile QA.

For retries after the short-lived Pages artifact expires, or deliberate rollback,
manually dispatch `redeploy-pages.yml` with the original source run ID, its source
attempt number, and the trusted release ID from that candidate receipt. The
workflow downloads the retained archive, checks its receipt/hash, restores it,
uploads those exact bytes and verifies the deployment. It does not merge feed,
refresh signals, build artifacts, change canonical data or reuse current shards.
A matching weekly draft may be published only after verification and a source-tag
commit check. Existing data/migration reverts remain a separate reviewed Git step.

Both deployment paths share `repository-writer` serialization. Dispatch inputs
are validated and passed through environment variables. Verification has a
five-minute admission/stream budget, 20-second network timeouts and a 200 MB
decoded-byte ceiling; an in-flight request may finish its bounded transport timeout
past admission. It refuses redirects and non-HTTPS deployment bases, detects a
release changing between requests, and stores explicit success/failure diagnostics.
The CLI writes new reports outside canonical data/deployed docs and never accepts
partial verification as success.

These workflow definitions are prepared locally. Remote dispatch, artifact
retention/retrieval, Pages deployment, CDN behavior, workflow races and production
rollback still need live evidence after an authorized rollout. No production
release is claimed from local archive tests alone.
Official contracts: [upload-artifact](https://github.com/actions/upload-artifact),
[Pages artifact packaging](https://github.com/actions/upload-pages-artifact).
