# Optional deep-research module — 2026-11-10

The resumption plan's missing `src/deep_research.py` is now implemented as an
explicit PDF-cluster command using the optional `research` dependency group.
It is separate from daily ingestion, backfill and canonical enrichment.

The command prepares source-hashed receipts without network access by default.
Execution requires `--execute` and `GEMINI_API_KEY`, counts input tokens before
generation, limits output, uses one attempt per SDK call, and rejects incomplete
or unsupported output. It sends full selected PDFs plus page-indexed extracted
text. Structured claims distinguish reported results from inference. Every
accepted claim cites a selected source, physical page and exact short quotation;
every selected paper is cited or has an explicit coverage gap. Results remain
unreviewed drafts. Quote presence does not establish entailment or correctness.

## Evidence

- [RadSplat preparation receipt](runs/deep-research-radsplat-dryrun-20261110.json):
  15,059,485-byte PDF, 11 physical pages, source SHA-256
  `a5a3c58ae88f74037b66cc84c737319c58dadf11246a747f2bd9fe2ab43158b1`.
  The receipt includes parser version, extracted-page digest, instruction digest
  and catalog digest. No PDF or extracted text is copied into the receipt.
- 18 focused tests pass, including input-budget refusal before generation,
  incorrect source/page/quote rejection, coverage gaps, incomplete output,
  dry-run behavior, exclusive output creation and sanitized provider errors.
- One test uses the installed Google SDK with an offline HTTP transport to
  exercise real count/generation serialization, PDF parts, structured-output
  configuration and token-usage parsing. This is not a live-provider test.
- Full suite: 384 tests passed in 105.57 seconds before the final additional SDK
  transport test was added; the complete 18-test research suite then passed.
  Ruff lint, formatting (130 files), lock consistency and the canonical build pass.
- Canonical 4,102-record input is unchanged at SHA-256
  `9e0da7759d593cfa4d95f50dc30383a059b32392de22f9595cfc9a638c60daca`.

## Remaining acceptance

No Gemini key was configured. Live token counting/generation, actual model access,
paid-request usage and reviewed multi-paper synthesis remain unverified. No
provider call was made and no generated scientific claim is presented as checked.
The separate local llama-server/table-parsing deployment, worker review pilot,
source/venue review queues, citation observation maturity and release/deployment
gates remain open. This module does not complete either phase by itself.

See [operator instructions](../CONTRIBUTING.md#optional-pdf-cluster-synthesis).
SDK calls follow the official [Google Gen AI SDK documentation](https://googleapis.github.io/python-genai/)
and [PDF input documentation](https://ai.google.dev/gemini-api/docs/document-processing).
