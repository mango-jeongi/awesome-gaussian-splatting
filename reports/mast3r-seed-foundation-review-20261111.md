# MASt3R baseline foundation review — 2026-11-11

MASt3R (`paper:2024-b9d0817758`, arXiv `2406.09756`) is retained as an
explicitly curated matching foundation. Its official abstract establishes the
identity and matching contribution. The independently captured official GS-CPR
abstract (`2408.11085`) states that its 3DGS camera-pose refinement pipeline uses
MASt3R for precise 2D matching. That concrete dependency resolves the earlier
absence of a specific GS role; generic 3D adjacency alone would not suffice.

The [decision receipt](runs/mast3r-seed-foundation-review-20261111.json) binds both
frozen primary records, the previous/current ledger, canonical record and reviewer.
This is agent primary-source adjudication, not an independent human benchmark.
The prior ledger is retained under `data/reviews/history/`. No canonical metadata,
provider observations, identity, date, original local PDF or archive membership
was changed.

Baseline accounting is now **141 retained, 19 unresolved, five archived**, across
all 165 original IDs. The other 19 cases still require their own evidence; this
foundation decision does not expand the corpus to all matching/3D methods.

The root relevance config adds an evidenced inclusion override for this exact
identity. Existing discovery epochs retain their original policy semantics. A
copy of the prior override document is frozen at:

`data/venues/policies/388dfe1507123d4bfb7e4bfac474e94afa84321eb5067d8a5db8f4622d8b4d0f.yaml`

The active ICCV epoch uses that prior digest, already loaded by its running
process. **Future replay/resumption must explicitly pass `--overrides` with that
frozen file**, in addition to `--all-metadata` and the original listing. The
source inventory records the path. Using the changed root config correctly fails
the policy fence instead of silently reclassifying an existing epoch. New scope
reviews can be applied later as a separate, versioned step.
