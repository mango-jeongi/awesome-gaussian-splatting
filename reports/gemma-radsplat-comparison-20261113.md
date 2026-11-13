# Bounded Gemma and deterministic extraction comparison — 2026-11-13

One service run and one generation reproduced the prior source-word selection failure. The harness rejected repeated/reordered metric indices and repeated unit indices, omitted the warm repeat, and stopped the dedicated service. No prediction was accepted or published. The extraction runtime pointer and reviewed ledger are unchanged.

| Observation | Result |
| --- | --- |
| Scope | RadSplat physical page 6, 498 source words, four existing accepted numeric cells |
| Deterministic numeric recall | 4/4 reviewed cells matched with exact values |
| Deterministic exact values among matched cells | 4/4; 35 candidates outside the accepted subset remain unscored |
| Deterministic context | Row/column strings differed for all four cells; dataset, split, metric and unit were missing |
| Gemma precision/recall | Not scorable: invalid source selections, zero valid results |
| Population precision | Unavailable for both methods; this ledger is not exhaustive table annotation |
| Generation | 10.564 seconds, 8,278 prompt tokens, 404 completion tokens, zero cached prompt tokens |
| Service lifecycle | 17.364 seconds total; inactive/dead, exit 0, Restart=no, 35-minute outer bound |
| Cleanup | Port 8791 closed; 69 MiB GPU use after stop; extraction timer and proxy active |

The four reference cells are prior source-inspected labels, not an independent human benchmark. Exact numeric recall on one selected page does not establish full-table recall, context accuracy, or model superiority. The unchanged index-only prompt lacks layout coordinates. No retry or prompt change was made after rejection.

Evidence: [service and generation receipt](runs/gemma-radsplat-real-page-20261113.json), [production evaluator comparison](runs/gemma-radsplat-comparison-20261113.json), and [hash-validated worker sync](runs/co-located-worker-sync-20261113.json). The 98-candidate deterministic result is preserved in the repository review queue; existing accepted decisions remain intact.

[Post-run artifact attestation](runs/gemma-runtime-attestation-20261113.json) confirms the staged model SHA-256 matches the prior verified pin. Its measured size is 5,154,941,280 bytes; the handoff byte count was stale.
