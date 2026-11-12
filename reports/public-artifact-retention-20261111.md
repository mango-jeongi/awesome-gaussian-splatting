# Public artifact retention cleanup — 2026-11-11

The bounded cleanup implementation is committed at `194ff18`. Its real plan
removed **316 obsolete content-addressed JSON files (22,274,290 bytes)** from the
resolved `G:/My Drive/Papers/awesome-gaussian-splatting/docs/data` directory.
No directories, canonical records, provider caches or referenced artifacts were
removed. Every candidate was verified byte-for-byte against Git revision
`194ff18c6341e22215f00adb2602903759963407` before deletion, preserving an exact
recovery source.

The [plan](runs/public-cleanup-plan-20261111.json) retains **148 immutable artifacts**
across the current build and two explicitly selected prior generations. Manifest
snapshots and their trusted source commits are recorded in the
[selection receipt](runs/public-retention-selected-manifests-20261111.json).
These are local verified generations, not a claim of production deployment.

[Isolated rehearsal](runs/public-cleanup-rehearsal-20261111.json),
[Git recovery proof](runs/public-cleanup-git-recovery-20261111.json),
[actual removal receipt](runs/public-cleanup-application-20261111.json) and
[post-apply verification](runs/public-cleanup-verification-20261111.json) bind the
same plan. All current/retained hashes and transitive catalog/detail and
index/adjacency pointers verified afterward. Replaying the exact plan was a
no-op with 316 already-absent files. An ordinary offline build preserved all
149 remaining JSON files and recreated no obsolete generation.

The independent immutable rollback archive also remains exact: 64,952,320 bytes,
SHA-256 `23c24f5f369716db3e15abaea1883f658f18448aed1d461db4d387e3994999fd`,
release ID `dc211beb7af046c94dc8adb1f440bf5024ec04b8053b7cc0744eaf6e227524a9`.
Retained JSON dependencies support cached manifests; deployment rollback uses
that separately preserved immutable archive.

Build and cleanup hold the same cooperative filesystem lock. Preview validates
all inputs before removal; application rechecks the approved inventory and
manifest fences, then unlinks individual verified files under the intended root.
Default deletion ceilings are 500 files/100 MB; retained/scan limits are 5,000
entries/200 MB. Unknown files are preserved. Changed/corrupt inputs, unexpected
candidates, linked trees and overwritten plan/manifest output paths are refused.
Interrupted removal preserves protected generations and resumes from the same plan.

Feature validation passed 468 tests with one native-symlink test skipped because
this Windows host cannot create symlinks. Global lint/formatting passed. Failure
injection covers stale/forged manifests, omitted transitive pointers, corrupt or
missing artifacts, bounded deletion, interruption, replay and real lock contention.
The skip is not reported as a successful native-link exercise. See
[operator commands](../CONTRIBUTING.md#retaining-and-pruning-immutable-public-artifacts).
No storage cutover, workflow dispatch, Pages deployment or push occurred.
