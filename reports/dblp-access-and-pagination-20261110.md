# DBLP pagination and live-access evidence — 2026-11-10

A bounded one-request live probe used the official publication search endpoint
with literal query `venue:CVPR: year:2023:`, `h=1`, `f=0`, `c=0`, and JSON format.
The provider returned HTTP 202 and a 2,935-byte HTML body, not a valid DBLP JSON
page. The [probe receipt](../data/venues/dblp-cvpr2023-probe/probe.json) records
status, observation time, query parameters, body digest and content type. The
raw HTML is retained only in local scratch and is not published as paper data.
No retry, browser challenge bypass, alternate host or watermark advance was
attempted. DBLP coverage remains unresolved; this is not a zero-result query.

Inspection also found an unsupported total-result limit in the client. DBLP's
[official API documentation](https://dblp.org/faq/13501473.html) caps `h` (hits per
page) at 1,000 and documents `f` for pagination. The client previously rejected
any source total above 1,000, preventing even a correctly paged large inventory.
It now continues within the explicit request budget instead. A fixture with
1,001 records over two pages verifies complete, duplicate-free accounting.
This proves client behavior, not current live access beyond 1,000 records.

Search calls now also enforce a wall-time admission budget (default 120 seconds,
including pacing) and a streamed decoded-response budget (default 2 MB per page).
A request already waiting on transport can finish its bounded 20-second network
timeout beyond the admission deadline. Page sizes above the requested `h`,
malformed/non-string keys, source-count drift, repeated IDs, short pages,
non-JSON responses and request exhaustion all fail without returning a partial
inventory as complete. Existing one-second request pacing is retained.

Nine focused DBLP/venue tests pass, including six new regressions for a source
over 1,000 results, partial-budget refusal, response-size bounds, oversized pages,
deadline-aware pacing and malformed keys. Ruff lint and formatting pass. The
4,102-record canonical catalog is unchanged; no venue cell was promoted based
on the failed live probe. Live source discovery/reconciliation remains open.

Full suite: 426 tests passed in 87.13 seconds. Global Ruff lint and formatting
(143 files) pass. The CVPR 2023 source inventory records the failed DBLP probe as
deferred evidence, while its partial coverage and remaining DBLP work stay open.
