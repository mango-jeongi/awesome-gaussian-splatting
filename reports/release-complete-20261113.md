# Completed bounded operations and release rehearsal — 2026-11-13

The bounded run completed locally. CVPR 2023 publication-page capture is complete; catalog scope and unresolved bibliographic dispositions remain explicit. No push, deployment, tag or production rollback was performed.

| Verification | Result |
| --- | --- |
| CVPR 2023 metadata | 2,353/2,353 verified; zero pending or failed pages; all prior captures preserved |
| Canonical catalog | 4,130 active records, eight archived; 14 reviewed feed additions and one explicit source exclusion |
| Baseline preservation | All original 4,116 records, archives, aliases, 165 seed rows and provider-cache bytes preserved |
| Quality gates | Ruff, formatting, 581 tests, 4,130-record validation, and compiled CSS passed |
| Rehearsed candidate | `7c1d4507a96a0a0c8a77c490b97e1992a1bd776f` |
| Release ID | `a16c325f5adc14428ff81df36ef5542a746d40fc9c8a5e16d064575f6f384681` |
| Archive | 111,820,800 bytes; 229 files; two independent packs byte-identical |
| Archive SHA-256 | `c820558f9071a58ba4ba93d98583d610cc0825379b81130f6270f38ec8b1b579` |
| Restore | Every one of the 229 restored files byte-verified; current input digest matches |
| Runtime | Original extraction timer and proxy active; worker pointer unchanged; model server stopped and port 8791 closed |

[Machine rehearsal receipt](runs/release-complete-20261113.json), [baseline preservation](runs/final-baseline-preservation-20261113.json), [runtime invariants](runs/final-runtime-and-invariants-20261113.json), and [final coverage](coverage.md) retain the evidence. The final approval checkpoint adds reports only; its owned release inputs remain identical to this verified candidate.

The current Git tree contains no raw HTML/PDF under `data/`; 71 raw files remain intact on NVMe with committed digests. Bounded cleanup removed 251,900,485 bytes of obsolete generated public artifacts, retaining the current and two verified prior builds and a local backup. The resulting 111,584,596-byte site fits the unchanged 200 MB cap. The active canonical writer remains v1; v2 snapshot/migration support is implemented but not activated.

The 52 unopened venue cells and six unresolved legacy seeds remain in their typed dispositions. CVPR 2023 still has 176 adjacent/foundation scope-review leads, six accepted-only titles and 14 author discrepancies; no automatic CVPR 2023 import is claimed. The Gemma diagnostic produced invalid source-word selections, so no prediction was accepted and its precision/recall is not scorable; deterministic numeric recall was 4/4 on the reviewed page subset.

Semantic Scholar's absent key caused a zero-request skip while preserving its cache. There are zero matured velocity windows. The bounded OpenAlex sampling timer remains active for **November 15, 2026 at 9:21:29 p.m. Pacific**; its offline admission check includes the earliest mature paper. The completed CVPR retry timer was disabled after its successful two-request pass.

Archives and restored output remain local on NVMe. The next external action requires the user's requested approval: `git push --atomic origin main:main feed:feed`.
