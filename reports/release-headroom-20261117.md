# Release headroom — November 17, 2026

Removed 200 verified obsolete public artifacts (115,399,955 bytes). The public
site fell from 220,969,911 to 105,569,956 bytes. The release cap remains
200,000,000 bytes. Cleanup was previewed under a 300 MB historical scan ceiling
and a 150 MB deletion ceiling; the first 100 MB deletion-budget preview refused
without deleting files.

The current provider-refreshed generation `de12c951…`, previous validated
checkpoint `51c5e1c4…`, and independently verified published `v2026.W46`
generation `09ad2687…` were preserved with all transitive detail and graph files.
The newly selected snapshots replace older live-tree retention selections;
older snapshot files and immutable release archives remain historical evidence.

Every removed file was backed up outside the repository and hash-verified before
removal. The backup receipt records its absolute path and SHA-256. Applying the
same plan again produced a no-op. No canonical paper, provider observation,
review decision, source cache or deployed site was changed by cleanup.

The latest automated `feed` observation commit `5f8bd38` was integrated before
planning so its current artifact generation is protected. A subsequent build
replay preserved the exact current manifest. All protected artifact hashes,
canonical schema, 34 cleanup/release tests, Ruff lint and formatting passed.
Archive/restore rehearsal is recorded outside the repository against the
committed candidate, avoiding a receipt that refers to its own commit.

This is reclaimed headroom at this checkpoint, not a bound on future artifact
growth. New daily builds continue retaining generations; review retention again
before release packaging if the tree approaches the cap. Automatic pruning was
not introduced.

[Selected generations](runs/public-retention-selected-manifests-20261117.json) ·
[Exact plan](runs/public-headroom-plan-20261117.json) ·
[Backup](runs/public-headroom-backup-20261117.json) ·
[Application](runs/public-headroom-application-20261117.json) ·
[Verification](runs/public-headroom-verification-20261117.json)
