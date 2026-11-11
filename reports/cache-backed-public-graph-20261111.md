# Cache-backed public graph — 2026-11-11

The public builder now projects validated OpenAlex cache observations into its
own in-memory database before generating records, citation lineage and graph
artifacts. It does not refresh a provider, construct an HTTP client, or save the
projection over canonical bibliographic data. The CLI citation path reuses the
same projection helper. Reviewed metadata and provider-identity fences remain
in force; collisions fail before the builder writes any public output.

A successful observed reference list is authoritative, including an empty list.
For sources without accepted reference observations, valid materialized legacy
edges are preserved and retain their legacy provenance. This avoids treating an
unknown reference list as a verified empty one. Endpoint, duplicate/self-edge,
reverse-adjacency and active/archive invariants remain enforced.

After the reviewed SAR-GS merge, the actual public graph contains **27,329
directed internal edges across 4,101 active records**, connecting 3,462 records;
639 are isolated in this observed graph. Reference provenance is observed for
3,792 nodes and legacy/unverified for 309. There are 69,453 source references
without an active-corpus match. This is partial source coverage, not scientific
isolation or complete citation recall. Canonical v1 still stores its prior 28
materialized edges; the larger graph is an offline cache-derived public
projection, not a rewrite of bibliography ownership.

The [build/repeat receipt](runs/cache-backed-public-build-20261111.json) binds
canonical/cache/model/manifest hashes and implementation-file hashes. A repeat
build left all 475 public files byte-identical, with canonical and provider cache
bytes unchanged. Index size is 1,716,505 bytes; largest detail shard is 492,412
bytes. Browser evidence binds build digest
`ac4e0b920b14a7d660b9735b470f1ce8dc0b82c0491d2f2bd9b930a022a06f24`.

[Actual Chromium acceptance](browser/20261111/cache-graph-actual.json), with its
[recipe](browser/20261111/cache_graph_actual.js), verified the old SAR-GS route
redirects to the preserved seed and displays its full authors/original date.
Edge 157.0.4341.42 used 4x CPU slowdown and unthrottled loopback. Global/one-hop/
two-hop views respected 300/1,200, 80/200 and 150/400 caps. Ego post-resource
layout times were 359.1 and 501.6 ms, below the two-second gate. Mobile width was
390/390 pixels and no page errors were observed. These are specific route/graph
checks, not a new five-sample cold-load benchmark or public CDN/TLS verification.
The owned browser closed; no preview Python process remained and a bounded TCP
probe could not connect to port 8894.

All **458 tests passed in 37.85 seconds**; global Ruff and formatting (157 files)
pass. New end-to-end cases cover v1/v2 source immutability, retained successful
values after a failed attempt, authoritative empty references, preservation of
unobserved legacy edges, repeat bytes and identity failure before output.
The [final full-corpus storage rehearsal](runs/storage-4101-cache-20261111.json)
reverified 48 monthly shards, complete field/order/alias/archive parity,
byte-identical v1/v2 public output (84 current files), provider/review sidecars,
no-op bytes/mtimes, stale-writer fencing, rollback and corruption/interruption
failure paths. Canonical activation and remote writer rollout remain pending.

The implementation is committed separately from generated data. No push,
workflow dispatch, production Pages deployment or production rollback occurred.
