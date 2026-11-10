# Relevance policy v2 and foundation import

`gs-topic-v2` meets the plan's 95% include-precision and include-recall targets on
the frozen, balanced 100-candidate development fixture. Its source packet and all
annotations are unchanged from the failed v1 evaluation. The final policy also
meets both numeric thresholds on a separate, identity-disjoint 100-record challenge.

| Evaluation | Confirmed-include precision | Include recall | Scope |
| --- | ---: | ---: | --- |
| Original v1 baseline | 44/49 = 89.80% | 44/50 = 88.00% | Frozen development labels |
| Final v2 development | 50/50 = 100% | 50/50 = 100% | All five required phenomena covered |
| First v2 challenge | 61/63 = 96.83% | 61/68 = 89.71% | Saved before challenge-driven corrections |
| Final v2 challenge | 68/68 = 100% | 68/68 = 100% | Challenge subsequently used for refinement |

These are agent-reviewed development results. The reviewer also wrote the policy;
neither sample is blinded or independently human-adjudicated. The challenge was
selected separately without policy outputs, but was then used to improve the rules.
It is no longer an untouched holdout. These figures do not establish population-wide
accuracy. The challenge supplements the balanced fixture and does not independently
cover all five required phenomena; its `sample_thresholds_met` composition flag is
therefore false even though its numeric precision/recall flags pass.

Development composition remains 47 early broad-query hits, 32 early GS hits, ten
medical/sensor seed records, eight adjacent reconstruction seeds and three explicitly
curated NeRF foundations. Source quality is 82 official arXiv metadata records and
18 legacy seed descriptions. The challenge comprises 21 unused early arXiv records,
49 arXiv update records selected by identifier hash, and 30 HF discovery records
selected by identifier hash. Normalized identifier inventories are disjoint.

HF challenge descriptions come from captured `paper.summary`, never `ai_summary`;
they remain provider-supplied descriptions, not independently verified author
abstracts. This fixture does not change the canonical HF abstract-ownership policy.
The saved daily arXiv page lacks a response timestamp, so its challenge capture
explicitly records local page-persistence time as an observation time, with that
basis preserved. No provider fetch timestamp or citation-history snapshot was invented.

The new rules require geometric representation evidence rather than any co-occurrence
of “3D Gaussian” and reconstruction. Gaussian statistical fields, density profiles,
wave packets and smoothing are distinguished from splat primitives. Explicitly
splatted Gaussians are recognized in either word order. Editing, segmentation,
simulation and robotics contexts now work, and Gaussian scene methods can be
recognized without “splatting” in the title. Statistical model ambiguity remains
reviewable. Explicit non-Gaussian primitive competitors, including beta splats and
hexagonal primitives, enter scope review. Medical, thermal, SAR and robotics GS
applications remain eligible.

The development fixture has 50 correct includes, 26 correct excludes and 13 correct
review outcomes. Eleven annotated negatives still enter review; they are not
automatically admitted or silently removed. All 100 challenge outcomes agree with
their frozen labels: 68 includes, 30 excludes and two scope-review cases.

Three exact-ID foundation overrides now carry reviewed scope justifications and
hash-linked official source metadata: original NeRF (`2003.08934`), mip-NeRF
(`2103.13415`) and Instant-NGP (`2201.05989`). Their verified original dates are
2020-03-19, 2021-03-24 and 2022-01-16. Their canonical import added exactly three
records; all 192 previous record values were preserved. The catalog now contains
195 records. Import replay preserved the canonical bytes. Instant-NGP's published
DOI and all three arXiv aliases resolve to their stable canonical IDs.

Local public artifacts were rebuilt and validated: 47 referenced descriptors pass
path/size/hash checks; the compact index is 78,084 bytes; foundation aliases and lazy
details resolve; a repeat build produces identical bytes. The current public graph
has 29 stored edges. No commit, push, GitHub workflow rollout or Pages deployment
occurred. The old-policy daily checkpoint correctly refuses reuse before making a
provider request, retaining the frozen evidence rather than mixing policy versions.

All 271 tests pass on the 195-record corpus; lint/format and schema validation pass.
The 5,000-record scaling fixture was corrected to clear an original arXiv DOI when
assigning a synthetic identity; production alias-collision validation was preserved.
Current extraction coverage is 11 processed, 153 source-materialization tasks,
30 unavailable and one unsupported record. This is not 153 completed parser jobs.
Cached momentum still has 131 single-snapshot records and 64 without observations;
there is no measured velocity yet. Trending remains one partial and 194 unavailable.

Reproduce the development report with:

```sh
uv run python -m src.cli evaluate-relevance --report reports/relevance/gs-topic-v2-development-final.json
```

For the challenge, also supply `--packet tests/fixtures/relevance-challenge/candidates.json`,
`--annotations tests/fixtures/relevance-challenge/annotations.json` and
`--sources tests/fixtures/relevance-challenge/sources`.

Original labels, source captures, v1 report, first challenge report and historical
policy source snapshots remain retained. Seed reconciliation, full historical and
venue coverage, writer/v2 rollout, scheduled provider integration, remote-runtime
updates, local model architecture and the remaining deployment/acceptance gates
remain unfinished. Passing these local relevance fixtures does not complete the goal.
