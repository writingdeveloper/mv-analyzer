# Open-source readiness — released

MV Analyzer now uses a deliberate two-repository model so research provenance and public source have different trust boundaries.

- **Public source:** `https://github.com/writingdeveloper/mv-analyzer`
- **Private raw provenance:** `writingdeveloper/mv-analyzer-research-private` (PRIVATE)
- **Deployed explorer:** `https://mv-analyzer.writingdeveloper.blog/`

The private provenance repository remains the source of truth for raw collection artifacts. Public source is generated from it by `scripts/build_public_release.py`, audited, and committed into a separate clean Git history. The private `.git` history must never be pushed to the public repository.

## Completed product gates

- [x] Reason Engine v1 merged and production-verified.
- [x] `reason-export` verified against an existing cached MV without network/GPU/model calls; source feature SHA remained unchanged.
- [x] Product-first README and research caveats reviewed.
- [x] Portable Analyze/Reason schemas tested for copyright/privacy leakage.
- [x] Production custom-domain regression completed after the Reason Engine release.
- [x] Public GitHub source link deployed only after the public repository existed.

## Completed open-source cleanup

- [x] Source license: **Apache-2.0** (`LICENSE`).
- [x] Dataset/rightsholder boundary documented separately in `DATA_LICENSE.md`.
- [x] Direct dependency/model notices documented in `THIRD_PARTY_LICENSES.md`; model weights are not distributed.
- [x] OpenMontage AGPLv3 boundary audited: no package dependency/import/vendor copy; JSON interoperability remains separate.
- [x] Public CSV/JSONL removes `thumb_text_content` and excludes raw lyric/subtitle/OCR text.
- [x] Raw population/enumeration/batch logs remain private provenance.
- [x] Pilot outputs and legacy self-contained HTML with embedded thumbnails are omitted from public source.
- [x] `SECURITY.md`, `CONTRIBUTING.md`, `CITATION.cff`, `NOTICE`, package metadata, issue templates, PR template, and changelog added.
- [x] Public release audit rejects secrets, private paths/networks, embedded media, unsafe dataset keys, and oversized source artifacts.
- [x] Historical private repository audited; direct visibility flip was rejected because old commits contained private paths/OCR fields/embedded-media artifacts.
- [x] Sanitized release builder works before package installation and does not inherit an ancestor Git repository.
- [x] Strict source-file fingerprints remain exact; analysis corpus/PCA fingerprints exclude only non-analysis raw OCR text.
- [x] Clean-history repository initialized from the sanitized tree, re-cloned, and audited with history result `{}`.
- [x] Sanitized clean-install verification: Python **257 passed / 2 deselected**, Web **79/79**, Playwright **60/60**.
- [x] Public source repository's own Python 3.12/3.13, Web, and `public-release` Actions jobs all passed before visibility changed to PUBLIC.
- [x] Remote public clone re-audited: 84/93-column sanitized datasets, no raw population/pilot/base64 legacy artifacts, history `{}`.
- [x] Private canonical origins on the notebook and MAIN PC were moved to `mv-analyzer-research-private` before the public name was reused.
- [x] Public source repository is **PUBLIC**; private provenance repository remains **PRIVATE**.
- [x] GitHub private vulnerability reporting, vulnerability alerts, and automated security fixes enabled on the public repository.
- [x] Production manifest matched the canonical cutover source and production Playwright passed **60/60** after the public source link was deployed.

## Ongoing release rule

Future public changes must follow this direction only:

```text
PRIVATE provenance master
  -> build_public_release.py
  -> audit_public_release.py
  -> clean public source commit
  -> public CI
```

Never merge or push the private provenance Git history into `writingdeveloper/mv-analyzer`. The public repository is a source distribution, not the raw research archive.

## Scientific/product boundary

Heavy MV analysis stays local. The hosted Web app displays public-safe static research snapshots and locally imported Analyze/Reason JSON; it does not provide server-side YouTube analysis and imported files are not designed to be uploaded. Reference-corpus percentile is descriptive and is not a market-wide percentile or success probability.
