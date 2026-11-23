# Papers repository instructions

- Follow [CONTRIBUTING.md](CONTRIBUTING.md) for branch, commit, PR and validation conventions. Use a short branch from current `main` for human and agent contributions. Keep `feed` for scheduled data writers. Keep the closing keyword in the PR description for issues fully resolved by that merge.
- Use the locked `uv` environment and a local SSD for raw HTML, PDFs, model weights and scratch outputs. Keep raw source caches and credentials outside Git. Use tracked metadata, source digests, evidence receipts and review decisions for reproducibility.
- When changing generated content, edit its source first. `src/builder.py` generates `README.md`. Use the documented build for catalog and Pages artifacts, and keep the UI and CLI contracts compatible unless the change calls for a migration.
- Preserve stable paper IDs, source observation times, and provider-specific histories. Treat ambiguous matches, untrusted extraction output, and unclear figure reuse as review work. Preserve quarantine and retry evidence and resume from the existing checkpoint with the documented limits.
- Validate the persisted result and link its evidence in the PR. For data paths, check relevant schema, identity, replay, and rejection cases. For releases, bind the artifact to its source commit and use the approved immutable archive for retries or rollback.
- Start with offline fixtures and the checks affected by the change. Follow [the release and worker procedures](CONTRIBUTING.md) for live operations. Keep maintenance commits small and report the exact check outcome.
