# Changelog

All notable user-facing changes to MV Analyzer are documented here.

## [0.2.0] - 2026-09-09

### Added
- Evidence-backed Reason Engine with separate distinctive, feel, and optional personal-taste claims.
- `mva reason-export` for offline explanation export from cached analysis.
- `mva explain` for URL-first local analysis followed by deterministic explanation.
- Analyze Web view with local-only Analyze/Reason JSON import and “So why?” shown before PCA/details.
- Bilingual English/Korean Research Explorer, Compare, Samples, Methodology, and Three.js Data Constellation.
- Public-safe report/reason schemas, provenance fingerprints, malformed-input rejection, and browser privacy checks.
- Apache-2.0 source release, separate data-rights notice, contribution/security/citation documentation.
- Reproducible sanitized clean-history public release builder and history/source audits.

### Changed
- Reference-corpus identity now uses an analysis fingerprint that excludes non-analysis thumbnail OCR text while strict source-file fingerprints remain exact.
- Public datasets omit `thumb_text_content`; public 50-MV and 100-MV tables contain 84 and 93 columns respectively.
- Raw collection logs, population snapshots, pilot artifacts, private paths, and legacy embedded-thumbnail HTML remain in private provenance only.

### Research boundary
- Extreme Reference Corpus v2026.07 remains a descriptive extreme-group benchmark, not a market percentile or causal/success predictor.
- Failed experimental motion-scene classification is not promoted to a formal Reason claim.
