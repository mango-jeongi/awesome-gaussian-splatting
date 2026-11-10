# Manual backfill and reviewed worker dispatch

Added `manual-backfill.yml` and `manual-worker-import.yml`, each dispatch-only,
preview by default, and serialized with all other writers through the existing
non-cancelling `repository-writer` group. Inputs are mapped through environment
variables and validated before use. Both re-fetch feed, capture its expected
parent, run build/schema/lint/format/full fixture tests, recheck the parent, then
use an ordinary push. A source-operation failure is reported after valid saved
checkpoints/diagnostics; no Pages deployment is part of these workflows.

Backfill uses the actual frozen CLI with a stable run key, explicit exclusive
UTC cutoff, optional unchanged lower boundary,1–100 requests, resume and preview/
apply. Existing query/policy/date fencing and canonical identity/relevance/CAS
validation remain authoritative. Saved passes resume from committed evidence.
Runner loss can discard an uncommitted pass; replay begins from the last saved
checkpoint, and no uncommitted prefix is claimed durable or complete.

Reviewed imports select committed `<key>.review.json` and `<key>.result.json`
under `data/extraction/review-inputs`. Preparation validates types, exact result
bytes, an active canonical paper, and matching canonical source provenance. It
fetches only approved HTTPS arXiv/CVF PDF origins, caps source retrieval at50 MB/
120 seconds/four requests, validates every redirect independently, and requires
the PDF signature and exact extraction PDF digest. Prior destination bytes
survive failure and temporary partial files are removed. Prepared PDF bytes
remain in runner temporary storage, outside generated commit paths.

The existing reviewed importer enforces source/result/canonical hashes, reviewer
time, accepted table context and figure reuse rules. Preview writes no ledger;
apply/replay modifies only the approved ledger and checked generated output.
The dispatch does not publish source PDFs or copy unreviewed crops. Unsupported
public sources or revised source bytes require explicit source/review resolution.
Contributor instructions and the README generator describe the same contracts.

## Evidence

All340 tests passed in24.01s, including16 new fixture/failure/workflow cases.
Coverage includes digest mutation, unsafe URLs, redirects escaping the origin
allowlist even with a following injected client, byte/time caps, temporary-file
cleanup, canonical-source mismatch before traffic, review preview/apply/replay,
canonical preservation, dispatch input handling, branch guards and check order.
Both manual YAML documents and10 Bash blocks validate. Lint/format112 Python
files, build, schema190 records and diff checks pass.

The live local backfill canary for `[2026-11-01,2026-11-09)` accounted for40
records using one request, then resumed with0 source requests and1 comparator
request (comparator36). A third invocation used0 requests. It proposed37 includes/
3 reviews,6 insertions and31 updates; all were dry runs. This narrow interval is
not proof of full historical coverage. No canonical write occurred.

Worker-source/materialization and review application were tested with HTTP/PDF
fixtures, not a live Actions run or transfer of user PDFs. Canonical190 active/
five archived and raw SHA remain unchanged. No commit/push/dispatch/deployment
occurred. Compatible branch rollout, real manual dispatch/race rehearsal, full
source and venue inventories, real reviewed-source workflow proof, live S2 access,
genuine7-day history maturity, and broader M0-M5 acceptance remain outstanding.
