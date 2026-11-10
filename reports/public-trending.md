# Public discovery ranking

Added lazy provider-specific trending snapshots and a discovery sort with
complete/partial/unavailable coverage filters. Formula/version, original-date
age window, configured weights, actual weights used, HF observation dates, and
measured velocity dates/windows/corrections are visible. OpenAlex and S2 use
separate citation histories; HF is a separate shared community component. The
UI explicitly calls this a discovery ranking, not scientific quality. Zero is
valid, missing components remain unavailable, and partial weights renormalize.

Snapshots derive their evaluation clock from recorded canonical/provider input
timestamps, preserving deterministic no-op builds. They expire at the earliest
of24 hours, a supporting component's freshness boundary, or an eligible paper's
original-date age boundary. This invalidates the percentile pool when membership
changes. Future/expired snapshots yield no score. A timer automatically rerenders
at the boundary, including a tab left open, without inventing new observations.

Per-paper history is indexed once before computing velocity. The hashed public
artifact dictionary-encodes repeated velocity field names while preserving
provider ID, successful timestamps, baseline, elapsed days, raw delta, signed
velocity and correction flag. Repeated canonical IDs/dates already in the index
are omitted. The real artifact is69636 bytes
(4007 gzip); the5,000-paper two-provider complete-signal
fixture with realistic-length canonical IDs is3540598 bytes, below4 MB.
The compact initial index remains unchanged; trending loads only on selection
or a coverage filter, with visible failed-fetch retry and URL restoration.

All317 tests passed in22.77s; six new integration regressions cover hand-calculated
complete/partial scores, source separation, genuine zero, missing data, earliest
expiry, indexed history lookups, browser ordering/expiry and the payload gate.
The stronger realistic-ID fixture was rerun: six tests passed in1.59s. Lint,
format106 files, build, schema190 records, artifact hashes, diff checks and a
byte-identical no-op manifest pass.

Real Edge QA verifies0 initial ranking requests and1 after selection; complete/
partial filters, formula/version/weights/dates, provider isolation, reload URL
state, expired snapshots, automatic deadline expiry, failed-request recovery, and
390px mobile without overflow pass. The intentional network-abort error and
existing Tailwind CDN warning are expected. Browsers and loopback server stopped.

Current real coverage for each provider is0 complete /1 HF-only partial /189
unavailable. The displayed partial score45.59 has no citation velocity and
uses HF weight1.00. This is a real cached community observation, not a measured
velocity or a scientific-quality claim. Fixture velocity calculations do not
prove live history maturity. The current snapshot is as of2026-11-09T22:42:54.729566+00:00,
valid before2026-11-10T22:42:54.729566+00:00.

Canonical190 active/five archived and raw SHA-256 remain unchanged. No push or
deployment occurred. S2 keyed live success, a real minimum seven-day measured
interval, all source/backfill coverage, workflow/secrets rollout, and the broader
M0-M5 release/deployment acceptance gates remain open.
