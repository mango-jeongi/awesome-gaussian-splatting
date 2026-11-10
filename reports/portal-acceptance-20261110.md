# Portal acceptance checkpoint — 2026-11-10

The actual 4,102-record catalog and a fresh 5,000-record synthetic fixture were
exercised in Microsoft Edge 157.0.4341.42 on Windows 11, Core Ultra 9 285H
(16 cores / 16 logical processors), with Playwright CLI 0.1.24. The fixture cycles
current metadata under synthetic IDs and contains 254,949 directed edges, including
a 4,999-citation hub. Its data digest is `cb719c622c75afb1a9cf077afbc8a2bdf9dbbd0a5757a569249d931b232c0624`.
Canonical data was unchanged by QA. Nothing was pushed or deployed.

## Recorded performance

Cold loads used five distinct document navigations, disabled caches, a 1440×1000
viewport, 4× CPU slowdown, 10/1 Mbps and 100 ms latency. A local project-path server
served gzip. Readiness means 50 mounted cards followed by two animation frames.
Cross-origin transfer sizes can be unavailable without Timing-Allow-Origin;
same-origin JSON bytes are retained in the raw results.

| Scenario | Median | Slowest | Target |
| --- | ---: | ---: | --- |
| Actual catalog cold load | 1642.8 ms | 2038.0 ms | Median ≤3,000 ms |
| 5,000-record cold load | 1815.2 ms | 1932.0 ms | Median ≤3,000 ms |
| 5,000-record warm year filter | 119.3 ms | 188.7 ms | Median ≤150 ms |
| 5,000-record warm sorting | 109.0 ms | 221.0 ms | Median ≤150 ms |

Five observations support these medians and slowest results, not a robust p95.
The fixture index is 1,961,693 bytes uncompressed and
511,208 bytes gzipped, below 4 MB. The largest detail shard
is 497,114 bytes, below 500 KB. The fixture API
build/model-validation/graph run took 4.018
seconds. That API timing is not a live release build/deployment measurement.

The dense hub detail route improved from 3327.3 ms
with 5,049 mounted relationship links to 323.4 ms
with at most 100 links, at 4× CPU slowdown and the same network profile after the
index loaded. All 100 citation pages were traversed, reaching all 4,999 unique
targets. Inline expansion passed the same bounded-list and routing checks.

Graph limits passed: global 300 nodes / 1,200 edges, one-hop 80 / 200, two-hop
150 / 400. At 4× CPU slowdown on unthrottled loopback, the ego views were ready
728.0 ms and
1538.8 ms after their final required
resource responses, below the two-second ego target. Raw results retain global
overview timings separately; that view is not assigned the ego latency target.

## Changes and functional verification

- Relationship groups paginate 50 links, preserving every target and total count
  in standalone and inline details. Accessible heading IDs remain unique.
- Unchanged card nodes are reused with a 100-entry limit. Fresh markup is compared
  before reuse; manifest reinitialization clears the cache. Provider switches and
  automatic snapshot expiry passed; expired scores become unavailable.
- Browser Tailwind compilation was replaced by locked precompiled CSS using the
  same classes/theme. CI rebuilds the asset and checks for drift. See the official
  [CLI installation](https://v3.tailwindcss.com/docs/installation) and
  [Play CDN guidance](https://v3.tailwindcss.com/docs/installation/play-cdn).
- Semantic `hidden` state overrides display utilities. Graph canvases stay
  contained during resizing. Mobile pages remained 390 px wide at 390×844.
- Pagination, code/year filters, title order, keyboard shortcut and theme controls
  passed. Full abstract search, versioned arXiv/DOI/new CVF aliases, reload,
  back/forward, archived and unknown-ID routes passed on real catalog records.
- Provider observations stayed lazy and source-separated. An intentionally aborted
  request exercised retry handling; that expected network failure is separate from
  uncaught runtime errors.

All 366 Python tests, Ruff lint and formatting passed after the portal changes.
Compiled-CSS freshness is checked locally before the commit. The updated GitHub
CI definition has not been executed remotely. Owned browsers and preview servers
were stopped after QA.

[Raw evidence](browser/20261110/summary.json) includes individual samples, source
and measured asset hashes. [Reproduction recipes](../scripts/qa/README.md) provide
the isolated fixture builder, gzip preview server and Playwright CLI functions.
This checkpoint does not prove remote writer coordination, deployed asset digests,
release rollback, full source/venue completeness, provider coverage or genuine
multi-day velocity; those broader pipeline gates remain open.
