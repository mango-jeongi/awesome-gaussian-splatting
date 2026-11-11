# Immutable release and rollback rehearsal — 2026-11-10

The local release implementation now binds source revision/tag, build-input
fingerprints and every published file into one release ID. It preserves the
existing public data build digest as a separate identity. HTML, JavaScript or CSS
changes therefore produce a different release even when the canonical data is
unchanged. The packer checks a clean committed checkout, excludes coordination
locks, refuses other ignored/uncommitted site files, validates public pointers and
rebuilds the data projection in isolation before freezing it. Changes during
packaging fail safely.

## Full-corpus evidence

The [rehearsal receipt](runs/release-4102-rehearsal-20261110.json) records an actual
4,102-record candidate from clean source commit
`ef4b18cb1f38d83042ae088e9efc87d90d2dbe7f`:

- Release ID: `dc211beb7af046c94dc8adb1f440bf5024ec04b8053b7cc0744eaf6e227524a9`.
- Public data build: `ca6f62226f48ed5ce627ebf449fc44a5afb6c2ded9183ed808d26976d738bdee`.
- Archive: 64,952,320 bytes; SHA-256
  `23c24f5f369716db3e15abaea1883f658f18448aed1d461db4d387e3994999fd`.
- Two packaging passes produced identical receipts and tar bytes.
- Restoring the archive reproduced all 393 files exactly in a new directory.
- The deployed-byte verifier checked those 393 files through a real localhost HTTP
  server under `/awesome-gaussian-splatting/`: 394 requests including the metadata
  fence, 64,717,780 decoded bytes, 3.1448 seconds without throttling. A test-only
  transport routed its HTTPS-shaped API requests to loopback HTTP. This does not
  establish public TLS/CDN behavior, browser route functionality or cold-load budgets.
- The owned HTTP server was shut down and its thread joined successfully.

The archive remains in the local SSD workspace under
`work/release-ef4b18c/candidate/release.tar`; it is not committed or published.
The raw canonical catalog stayed at SHA-256
`9e0da7759d593cfa4d95f50dc30383a059b32392de22f9595cfc9a638c60daca`.
The receipt intentionally identifies the rehearsed source commit, rather than
claiming that later documentation or validation-hardening commits were packaged.

## Workflow behavior prepared locally

The weekly workflow now uploads the frozen `site/` payload, retains an immutable
rollback tar and receipt for 90 days subject to repository policy, and passes the
exact candidate revision and Pages artifact name to deployment. Artifact names
include the source run attempt, so a deploy-only job retry uses the producer's
original artifact. A new GitHub release is a draft until deployed-byte verification
succeeds. The deployed manifest and every site file must match the expected ID.
Verification also rechecks metadata at the end to detect a deployment changing
between requests. Failure diagnostics are retained and do not count as success.

The manual `redeploy-pages.yml` workflow takes a trusted source run ID/attempt and
release ID, verifies the retained archive, restores it and deploys those exact
bytes. It does not merge feed, refresh providers or rebuild old data. Both paths
share repository-writer serialization. A matching weekly draft can become public
only after verification and source-tag matching. Repository data/migration reverts
remain a separate reviewed Git operation.

After the full-corpus snapshot above, the publishing job gained the same compiled
CSS freshness gate as CI; the local CSS check passed without asset changes. A
near-limit regression also separated the 200 MB site budget from the repeated
metadata-fence overhead (up to 2 MB), while retaining the site's own size bound.
These later refinements do not alter the earlier archive or its stated identity.

## Validation and limits

The original full suite passed 450 tests in 107.82 seconds. Release tests cover
stable bytes, code-only/HTML-only identity changes, missing/corrupt artifacts,
stale canonical/provider output, expected-ID mismatch, exact prior-snapshot
restoration, unsafe/link members, monthly-store inputs and ignored-file refusal.
The final budget case is included in the follow-up validation below. Both workflow
YAMLs and all 16 final Bash blocks pass local parsing. The real ISO week format was
checked at year boundaries: 2021-01-01 -> v2020.W53, 2021-01-04 -> v2021.W01,
and 2024-12-30 -> v2025.W01.

No workflow was pushed or dispatched, no GitHub release was created, and no Pages
site was deployed. Actual artifact retention/retrieval, remote writer races, public
manifest/routes, CDN propagation and production rollback remain unverified. This
closes local packaging/restoration work, not the full M5 or Phase 2/3 gates.
See [operator instructions](../CONTRIBUTING.md#immutable-release-retry-and-rollback).

Final follow-up: all 451 tests passed in 40.46 seconds, including all 17 release
regressions and the near-limit metadata fence case. Global Ruff lint/formatting
(149 files), CSS freshness and whitespace checks pass.
