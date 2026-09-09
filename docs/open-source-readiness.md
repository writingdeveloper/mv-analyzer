# Open-source readiness checklist

MV Analyzer's **canonical research repository remains PRIVATE** while the open-source distribution is prepared. The public Web Research Explorer is deployed separately. Directly flipping the canonical repository to PUBLIC is **not approved** because its historical commits contain raw provenance that is intentionally excluded from the public source distribution.

## Completed product gates

- [x] Reason Engine v1 merged and production-verified while the repository remained PRIVATE.
- [x] `reason-export` verified against an existing cached MV without network/GPU/model calls; the source feature SHA remained unchanged.
- [x] README product-first onboarding and research caveats reviewed.
- [x] Portable Analyze/Reason schemas reviewed and tested for copyright/privacy leakage.
- [x] Production custom-domain regression completed after the Reason Engine release.

## Completed open-source cleanup

- [x] Code license selected: **Apache-2.0** (`LICENSE`).
- [x] Dataset/rightsholder boundary documented separately in `DATA_LICENSE.md`.
- [x] Direct dependency/model notices documented in `THIRD_PARTY_LICENSES.md`; model weights are not distributed.
- [x] OpenMontage AGPLv3 boundary audited: no package dependency/import/vendor copy; JSON interoperability remains separate.
- [x] Public CSV/JSONL release removes `thumb_text_content` and excludes raw lyric/subtitle/OCR text.
- [x] Raw population/enumeration/batch logs remain private provenance and are omitted from the public source tree.
- [x] Pilot outputs and legacy self-contained HTML with embedded thumbnails are omitted from the public source tree.
- [x] `SECURITY.md`, `CONTRIBUTING.md`, `CITATION.cff`, `NOTICE`, and package metadata added.
- [x] Personal absolute/private-network references removed from the current public candidate.
- [x] Public-release audit rejects secrets, private paths/networks, embedded media, unsafe dataset keys, and oversized release artifacts.
- [x] Existing Git history audited; direct visibility flip rejected because old commits contain private paths/OCR fields/embedded-media artifacts.
- [x] Deterministic `scripts/build_public_release.py` creates a sanitized source tree and `PUBLIC_RELEASE_MANIFEST.json`.
- [x] Clean-history repository initialized from the sanitized tree and re-cloned successfully; history audit returned no blockers.
- [x] Sanitized tree clean-install verification: Python **257 passed / 2 deselected**, Web **79/79**, Playwright **60/60**.
- [x] Public reference-corpus fingerprint is stable when non-analysis OCR text is redacted.

## Remaining release gates

- [ ] Merge this cleanup through GitHub PR after Python 3.12/3.13, Web, and the new `public-release` CI job are all SUCCESS.
- [ ] Regenerate the sanitized tree from the final merged master SHA and repeat clean-history audit.
- [x] GitHub cutover topology selected: preserve the canonical provenance repository as PRIVATE `writingdeveloper/mv-analyzer-research-private`, then publish a **new clean-history** `writingdeveloper/mv-analyzer`.
- [x] Final public cutover explicitly approved by the project owner in the release session.
- [x] Web source-status implementation changed from the private placeholder to the public GitHub link; production deployment is gated until the public repository exists.

## Why direct PUBLIC is blocked

Deleting a file in the current `master` does not delete it from older commits or other refs. The history audit found historical local-path material, legacy base64-thumbnail HTML, and dataset/work versions containing `thumb_text_content`. No private-key/API-token hit was found in the implemented scanners, but privacy/copyright hygiene alone is sufficient to reject a direct visibility flip.

See `docs/open-source-release.md` for the clean-history release model.

## Product boundary

Heavy MV analysis stays local. The hosted Web app displays public-safe static research snapshots and locally imported Analyze/Reason JSON; it does not provide server-side YouTube analysis and imported files are not designed to be uploaded. Reference-corpus percentile is descriptive and is not a market-wide percentile or success probability.
