# CVPR 2024 full-metadata checkpoint — 2026-11-11

The separate frozen all-metadata epoch now verifies **2,713 of 2,716** official publication pages. It reuses 133 original captures and adds 2,580 verified pages across seven bounded passes totalling 2,593 paced requests. Four source-bound offline metadata corrections are included: ViewDiff, Just Add π!, Structured Model Probing and CoralSCOP. Original response times and raw listing bytes are preserved. No ordinary metadata matcher was relaxed.

The final pass made 193 requests. A subsequent zero-request replay verified all retained response hashes and publication matches, with identical state bytes. [Verification receipt](runs/cvpr2024-full-metadata-pass7-verification-20261111.json). Three failures remain: SportsSloMo, GenHowTo and DePT return HTTP 404 at their frozen listing URLs. Their retry deadlines remain intact; no alternate URL or publication identity has been assumed.

The frozen listing SHA-256 is `720265923ad5cc65224d2ce1cd9cea868c6e4589ae51c05d1493f1f9d9aea03c`. This epoch retains policy `2b923581760ff0f808a58128eeb8d805f9e40788b3a1380a512d26ec75016bcf`, even though root policy later changed for foundation reviews. Resume with `--all-metadata` and that explicit frozen override file. The original `cvpr2024-main` epoch remains unchanged.

The 2,713 verified metadata outcomes are 63 include, 176 review and 2,474 exclude. Among previously title-excluded pages, there are **15 include leads and 91 review leads**, with 2,474 exclusions. These 106 leads require scope adjudication; they are not accepted additions or population recall measurements. [Lead evidence](../data/venues/cvpr2024-all-metadata/title-screen-rescue-evidence.json).

The three new offline reviews bind exact listing and retained HTTP-200 response hashes: the Greek pi title in Just Add π!, Xue Wang in Structured Model Probing, and Put Ang in CoralSCOP. Full ordered author lists, edition/year and PDF paths were checked. Reapplication was a no-op; none creates a person alias or canonical merge. [Review receipt](runs/cvpr2024-three-metadata-reviews-20261111.json).

The independent accepted-table title discrepancy and three-paper announcement count gap remain open. Author, identifier, original-date and relevance reviews also remain incomplete. Capturing almost all pages does not establish reconciled edition coverage.

Canonical data remains 4,103 active papers and six archives. This capture changed no canonical records, provider observations or public assets. Validation passed 500 tests with one native-symlink skip, lint and format checks. All work remains local; nothing was pushed or deployed.
