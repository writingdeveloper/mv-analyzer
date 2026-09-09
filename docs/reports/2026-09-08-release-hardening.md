# Analyze My MV release hardening — 2026-09-08 (America/Los_Angeles)

Status: implementation and local verification complete; remote CI and production verification follow. Repository stays PRIVATE.

## Scope
- Integrate PR #2 with current master without removing the September research/production bridge work.
- Introduce report schema v2: shared structural validation, semantic ranges, source/reference fingerprints, explicit partial-PCA status. Old v1 reports must be regenerated rather than silently trusted.
- Add a network-free / GPU-free report-export command for existing features.json.
- Repair date-only formatting, localStorage failure, file import races, and page-ready assertions.
- Add a clearly labeled public-corpus demo and useful reference-only 2D/3D target projection.
- Keep motion classification experimental; AI annotation is not human acceptance.
- Validate existing and new routes under production security headers; deploy only after integration CI passes.

## Safety boundaries
No inference, model download, media reanalysis, original research-data modification, or repository visibility change.
Browser QA uses SwiftShader CPU rendering; hardware GPU use is disabled.
Raw local reports and diagnostic output stay outside the deployment allowlist.

## Verification log
Results and remaining limitations are recorded after fresh execution, not inferred from previous CI.

## Fresh local verification

- Python 3.12: **225 passed / 2 intentionally deselected**.
- Ruff F: pass. P5 input QA: 0 errors / 0 warnings. Both tracked reference CSV QA checks pass.
- Web: **71 unit tests passed**; TypeScript and production build pass.
- Chromium desktop/mobile: **58/58 passed**, including all seven routes, EN/KO, 320/390/768/1440 px,
  sample demo, local-file import without a request body/upload/storage, reload clearing, invalid/legacy
  rejection, genuine page-ready gating, date-only timezone behavior, actual CSP and metadata assets.
- Software-renderer inspection: **ANGLE / Vulkan / SwiftShader Device (Subzero)**.
- Source research inputs `dataset/`, `work/`, and model configuration are unchanged relative to
  master `557ad1c512c13749774010bad0446c907a1a9061`.
- The release integrates PR #2 with that master instead of overwriting the September research bridge.

## Defects reproduced and fixed

The original parser accepted 150th percentiles, negative counts/std/distances, unsupported corpus
IDs, inconsistent z-scores, duplicate/empty features and invalid variance. Sparse input with zero
PCA inputs still produced a median-imputed location. These conditions now fail or explicitly
withhold the projection. The shared v2 schema is checked in Python and compiled into a CSP-safe
standalone browser validator. Full precision is retained for statistics to avoid rounding a small
standard deviation to zero.

Real browser testing found an additional build-only defect: Ajv's CJS helper had a different default
export shape in Vite production than in Vitest. The build-time generator now normalizes that module
interop without runtime eval. The full file-import E2E caught and now guards this regression.
An old test also matched an SVG tooltip title instead of the visible PC1 evidence; it now targets
the actual coordinate panel rather than treating hidden tooltip content as a ready chart.

## Operational and scientific boundaries

- Schema v1 must be regenerated, not silently upgraded with invented provenance.
- Export Git identity is distinct from measurement identity. Unknown/legacy measurement identity is
  labeled unverified. Hashes identify content, not signed authenticity or independent accuracy.
- The example is an already-public, in-corpus reference row and is labeled a demo, not out-of-sample validation.
- This remains an extreme-group reference, not a market ranking or success prediction.
- New personal PCA uses equal raw-score scale for rendering; full-feature neighbor distance is
  separately explained. The existing exploratory lyrics-compression feature is explicitly labeled.
- Imported file content is not sent to a service; the demo is a fixed same-origin GET.
- No hardware GPU workload or model inference was started. No VLM/ASR model was downloaded or replaced.
- Actual human acceptance and a fresh model/CC-source experiment remain separate, unexecuted gates.
- Historical Claude-based motion labels are now explicitly identified as AI reference labels.
- Shared Three.js code remains lazy-loaded (~140 kB gzip); the Vite >500 kB raw warning is retained,
  not hidden by increasing the warning threshold.

## Cross-platform CI finding

The first integration CI exposed a canonical-hash bug not visible in the original Windows checkout:
Git line-ending conversion also affected newlines inside quoted multiline CSV cells. The logical
JSON digest now normalizes nested string line endings before hashing. The numeric corpus and source
files are not rewritten. Two regressions compare actual LF/CRLF CSV checkouts and nested JSON strings.
Schema pins and the safe demo are regenerated from the same normalized-content algorithm; fingerprint
validation remains enabled rather than being relaxed to accept arbitrary corpus content.
