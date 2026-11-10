# Full-corpus v2 storage rehearsal — 2026-11-10

The frozen input is the 4,102-record canonical corpus with raw SHA-256
`9e0da7759d593cfa4d95f50dc30383a059b32392de22f9595cfc9a638c60daca`.
The [migration preview](runs/migration-4102-preview.json) records all IDs and
exact raw-field parity. The isolated v2 snapshot contains 48 monthly shards,
five archived records and the same record order and aliases. Its normalized
content digest is `a895773ef31e54aa811044da86de132fe1e2dffbefdb640be41e54f322cbcf91`.

The [full rehearsal receipt](runs/storage-4102-rehearsal.json) records:

- Exact model equality across every current field, record order, aliases and archive.
- Unchanged OpenAlex, Semantic Scholar, HF and reviewed-extraction sidecar hashes;
  identical source-labelled provider and trending payloads.
- Byte equality of all 68 generated v1/v2 files, including the legacy JSON export.
  A reproducibility bug in dictionary-key ordering was fixed only in that generated
  projection; the canonical corpus is unchanged. The before/after JSON values match.
- No-op store bytes and mtimes remain unchanged; repeated builds have identical bytes.
- A stale writer is refused after an accepted update, without losing that update.
- Restoring the retained manifest restores the exact previous model. Missing or
  corrupt shards fail closed. An interruption after component publication leaves
  the active manifest unchanged; unreferenced staged generations remain inactive.

All original 29 baseline edges are accounted for: 28 remain active and the removed
edge joins two explicitly archived records. The source baseline and archival
records retain the evidence; no unexplained edge loss was accepted.

The preview preserves 4,064 legacy zero citation values with unknown freshness;
these are not verified uncited papers. It also flags 61 arXiv DataCite DOIs in the
legacy publication-DOI field. They remain explicit metadata debt; this lossless
storage migration does not silently reinterpret identifiers.

Static checks confirm all seven writer definitions share `repository-writer`,
keep active writers running, and stage manifests, monthly shards, aliases, signals
and archive paths. This is not proof of successful remote dispatch, upstream race
handling or production compatibility. Writer defaults still target the legacy
canonical file. Canonical activation, live workflow rollout, release retention
and deployed rollback rehearsal remain open; the M0 exit gate is not claimed.

Reproduce with the [offline QA recipe](../scripts/qa/README.md#full-corpus-storage-rehearsal).
The rehearsal writes only into its chosen temporary directory and a report. No
canonical migration, push or deployment was performed.
