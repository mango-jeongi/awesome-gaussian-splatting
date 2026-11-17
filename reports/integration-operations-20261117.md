# Integrated checkpoint — November 17, 2026

Current `origin/feed` at `6b39ff6` was fast-forwarded onto local main. All 11
additional papers were reviewed against their retained source-backed title and
abstract; their upstream inclusions were retained. This is relevance review,
not independent reproduction or full-paper metadata verification.

The local OpenAlex cache was backed up with SHA-256
`ca9daad2c33433b199e3ef8a0ce734534ed82a0322deabfb2ad3f72da7a5b247`.
Its 4,014 genuine samples were merged with upstream's 3,914 by paper/provider
identity and UTC day. There were no conflicting same-day samples. Latest attempt
metadata and latest successful values were reconciled independently; 100 local
observations were restored. No timestamp was synthesized. The original GS paper
retains its measured +131 provider-count change over 7.000022 days (about 18.71/day).

The regenerated public projection has 4,141 active records, eight archives,
27,479 internal citation edges and 3,481 connected records. One velocity window
is eligible. The new machine-readable coverage snapshot is
[runs/coverage-integrated-20261117.json](runs/coverage-integrated-20261117.json).
The extraction ledger's corpus binding predates the 11 new papers; these remain
unobserved in extraction coverage. Existing accepted decisions were preserved.

Validation: 581 tests, canonical schema, Ruff lint/format, compiled CSS parity,
Bash syntax and systemd unit verification passed. The sync fixture verified clean
fast-forward, preservation of untracked work and divergence, and skips for
working branches and detached HEAD. Archive rehearsal is recorded separately.

## Operations

The MSI host has user lingering enabled. Its extraction timer and proxy were
active. The completed OpenAlex one-shot has no next run and can be retired once
this cache checkpoint is durable. The new five-minute checkout timer uses no
model calls and only advances clean main/feed checkouts to matching upstream.
It does not upgrade the separately pinned extraction runtime.

Daily ingestion and provider workflow runs succeeded, but the latest OpenAlex
and Semantic Scholar reports explicitly say `skipped: missing_credential`, with
zero requests. A green workflow does not prove fresh provider observations.
Repository secrets must be configured for ongoing remote observations; no secret
was copied or printed during this checkpoint.

[Weekly release run 43671586895](https://github.com/mango-jeongi/awesome-gaussian-splatting/actions/runs/43671586895)
deployed its candidate but failed exact-file verification. Its metadata includes
`.nojekyll`, which returns 404. The official upload action excludes hidden files
by default. Both weekly and retained-archive upload paths now explicitly include
hidden files from the already validated candidate. This fixes the evidenced
packaging mismatch; successful live redeployment remains a separate verification
gate. No release is claimed verified by this local change.

## Bounded quality review

Three frozen CVPR 2023 leads were inspected offline: Pointersect, NeuralEditor
and Frequency-Modulated Point Cloud Rendering. Their abstracts establish
point-cloud/NeRF rendering, but do not alone justify Gaussian or adjacent-splatting
inclusion. All remain explicit holds pending method-level evidence. No frozen
capture, canonical record, six accepted-only titles, 14 author discrepancies,
52 unopened venue cells or six unresolved seeds was changed. The source-bound
reasons are in [the review receipt](runs/cvpr2023-bounded-scope-review-20261117.json).
No new Gemma generation was run; layout grounding remains an offline prerequisite.

## Gemini in Hermes

Hermes supports native Google AI Studio Gemini keys. Set `GOOGLE_API_KEY` or
`GEMINI_API_KEY` privately in `~/.hermes/.env`, then run `hermes model` and choose
Google AI Studio. Use the native `https://generativelanguage.googleapis.com/v1beta`
endpoint. The installed host currently has no `hermes` command on PATH; this
checkpoint did not install a harness or make a paid model call.
[Hermes provider documentation](https://hermes-agent.nousresearch.com/docs/guides/google-gemini).

Google AI Pro includes $10/month in developer Cloud credits. Claim the benefit
using the primary subscriber's Google account and link billing to the project
that owns the API key. Google's November 13 announcement says these credits can
fund Gemini API use and describes a $5 minimum API prepayment/balance requirement.
Confirm your project's credited balance before use; the credit is an allowance,
not a spending cap. Configure available spend controls before a bounded pilot.
[Google benefits FAQ](https://developers.google.com/profile/help/benefits) ·
[Google's credit activation announcement](https://blog.google/innovation-and-ai/technology/developers-tools/google-cloud-credits-gdp-ai-studio/).

The linked always-on-agent discussion points to Anthropic's five primitives:
event inbox, timers, memory, permissions and outbox. For this repository, a plain
Git/systemd poll is sufficient for checkout freshness; an LLM need not run on each
poll. Durable extraction jobs and bounded observation workflows remain separate.
The Reddit author's quota figures are their own measurements, not a prediction
for this homelab. [Anthropic guide](https://claude.com/resources/articles/building-always-on-agents).
The second Reddit short link could not be resolved after repeated retrieval;
its content was not inferred from the other post.
