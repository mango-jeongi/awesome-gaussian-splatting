# Cache-backed full-corpus release rehearsal — 2026-11-11

The committed 4,101-paper candidate at `8187fadfefe1c967d3da8bb1c2246f9fece6d865` packaged successfully after separating canonical model identity from the cache-projected public model identity. Two independent packs from the same clean checkout produced byte-identical 83,681,280-byte archives. The release ID is `f754a55aafad61e7c25b04a0f00153f9e3cf7590d1fb375057a7c999933b0fd4`.

A fresh restore verified all 160 archive files against their archive bytes. The existing earlier 393-file rollback archive also passed the current archive verifier and retained its previously recorded SHA-256. The new archive binds public build `c66588bd7eb843b66f6ab5c829607a431c051aa43ab394b7b11ebd7b9d00e75f` and records distinct canonical and cache-projected model hashes.

Evidence: [machine receipt](runs/release-cache-backed-rehearsal-20261111.json). Archives and restored output remain on the local SSD under the Codex workspace `work/release-8187fad`; they are not checked into the repository.

This was an offline local pack/restore exercise. No push, deployment, workflow dispatch, production rollback, CDN verification, or remote retention retrieval occurred. Those operational gates remain open.
