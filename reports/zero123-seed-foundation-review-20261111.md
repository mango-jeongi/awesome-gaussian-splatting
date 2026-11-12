# Zero-1-to-3 baseline foundation review — 2026-11-11

Zero-1-to-3 (`paper:2023-49bc7a3f60`, arXiv `2303.11328`) is retained as an explicitly curated image-conditioned generation foundation. DreamGaussian's primary method description, Section 3.1 of arXiv `2309.16653v2`, adopts the Zero-1-to-3 XL prior family for score-distillation optimization of 3D Gaussians and cites the original Zero-1-to-3 paper. This is a specific Gaussian-splatting pipeline dependency; it does not admit arbitrary diffusion or neighboring 3D methods.

Two bounded primary-source captures retain the complete source bytes, observed timestamps and hashes. The [decision receipt](runs/zero123-seed-foundation-review-20261111.json) binds those captures, the prior/current seed ledger, the unchanged canonical record and the policy transition. This is agent source inspection, not independent human review. The canonical title, abbreviated author display, metadata, identifiers, dates, provider observations, archives and local PDFs are unchanged; a bibliographic refresh is not claimed.

All 165 baseline IDs remain accounted for: **142 retained, 18 unresolved and five archived**. The other 164 ledger rows remain identical. The prior ledger is retained under `data/reviews/history/`, and all 142 retained record hashes validate.

The new root policy is `874351bf074345bef286fac3b1de915a154ce8c90dec27b827526592a8f0ba79`. Existing capture/application epochs keep their frozen semantics. In particular, CVPR 2024 continues to require `--all-metadata --overrides data/venues/policies/2b923581760ff0f808a58128eeb8d805f9e40788b3a1380a512d26ec75016bcf.yaml`; ICCV 2025 retains its separate `388dfe...` policy. No old epoch is silently reclassified or restarted under the new root config.

The two unchanged agent-labelled 100-record benchmark packets were rerun under the new policy; their results are saved separately under `reports/relevance/zero123-foundation-*.json`. These samples do not establish independent-human or population-wide precision/recall. Nothing was pushed or deployed.

The primary packet measures 0.98 inclusion precision and 0.98 recall and meets its declared sample gate. The challenge packet measures 1.00/1.00, but does not independently satisfy the required primary-sample phenomenon composition. Both packets retain identical predictions before/after this specific override; the primary mismatches predate it. Gold annotations were not relabelled. See the [before/after comparison](runs/zero123-foundation-policy-comparison-20261111.json).
