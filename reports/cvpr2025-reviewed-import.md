# CVPR2025 reviewed canonical expansion

Applied110 new source-verified CVPR2025 records and enriched four existing IDs.
The catalog now has300 active records and five losslessly archived records.
All190 old IDs, DOI/arXiv/OpenAlex identifiers and original dates remain intact;
186 old records are byte-equivalent as model records. The four changed records
receive official venue/abstract/provenance metadata; the exact field audit is in
the import receipt. The full pre-import JSON is retained as an immutable rollback
snapshot under data/baselines. Save used the canonical compare-and-swap lock.

All101 linked arXiv records were retrieved in three exact-ID paced requests.
99 pass normalized title/author/date checks directly. Instruct-4DGS adds only a
method-name title prefix with the same three authors. The sparse-point-cloud
paper has the same five complete authors in reversed two-token name order.
Both exceptions have explicit source-snapshot-bound Codex reviews; the global
identity matcher was not relaxed.47 unlinked publications retain honest year
precision. Original dates and conference publication year remain separate; later
journal DOIs were not copied into the conference publication slot.

Manual review caught three comparison-only false inclusions in v2: Convex
Splatting, Sparse Voxels Rasterization, and PBR-NeRF. Policy gs-topic-v3 defers
these to review. Source-backed development regressions were added without
relabelling either frozen100-record packet. Both unchanged benchmark packets
still score1.00 precision/recall; these are agent-reviewed purposive fixtures,
not independent-human or population-wide accuracy claims. The old v2 capture is
retained and an explicit zero-request migration revalidates the148 source pages
under v3. The final packet is114 include/34 review; no review case was imported.

Replay produces114 unchanged records/34 review dispositions and zero inserts,
updates or merges. Baseline mapping remains140 retained/five archived/20 unresolved
across all165 original IDs. DroneSplat's one changed retained-record review hash
was refreshed only after preserving its prior ledger/snapshot and recording the
new official source evidence; all140 current retained hashes revalidate.

Post-import full suite:357 passed in27.37s; lint/format118 files, public build and
schema300 records pass. No push/deployment or v2 canonical cutover occurred.
Source completeness,34 venue scope reviews, excluded-title recall, the one-paper
announcement discrepancy, other venue cells, real S2/live velocity, local model
architecture and broader M0-M5 release gates remain open.
