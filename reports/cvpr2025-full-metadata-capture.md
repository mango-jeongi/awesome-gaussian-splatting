# CVPR 2025 full-metadata checkpoint — 2026-11-12

The separate full-metadata epoch verifies **1,144/2,871** official main-proceedings pages: 148 reused title-priority captures and 996 additional verified pages across two bounded passes totalling 1,000 paced requests. There are 1,727 pending pages, including four retained transport failures. Retry deadlines remain enforced; no failed source was silently counted as verified.

Pass two made 500 requests and added 497 verified pages. Its final zero-request replay verified all retained body hashes and strict title, full ordered author, year, edition/track and matching-PDF contracts, preserving every state byte. [Preparation](runs/cvpr2025-full-metadata-preparation-20261112.json), [first pass](runs/cvpr2025-full-metadata-pass1-verification-20261112.json), [second pass](runs/cvpr2025-full-metadata-pass2-verification-20261112.json).

Frozen listing is `d3ced827c00cbf4dad3be7187811e40100ecc3173aec0ce4c13f743a1d28a35d` and policy is `cb275781b3efd0119a4679c135ac88d09c60ac186045b764b0d68279fbd1be3d`. Resume with `--all-metadata` and that explicit frozen override file under `data/venues/policies/`. Later root-policy changes, including the user's adjacent-work preference, do not retrospectively reclassify this source epoch. The original 148-page epoch remains unchanged.

Verified abstract-level outcomes are {'exclude': 941, 'include': 140, 'review': 63}. Previously title-excluded pages yield {'review': 32, 'include': 23}. These automatic leads require current-scope source review; they are not accepted catalog additions or population recall measurements. [Lead evidence](../data/venues/cvpr2025-all-metadata/title-screen-rescue-evidence.json).

The independent accepted-table mapping and announcement count gap retain their earlier evidence. Metadata capture does not resolve every author, identifier, original preprint date or relevance decision. This capture changed no canonical records or provider observations; separate user-scoped reviews changed only three canonical tag/provenance records, as documented in the scope report. The catalog remains 4,103 active records and six archives. Nothing was pushed, dispatched or deployed.
