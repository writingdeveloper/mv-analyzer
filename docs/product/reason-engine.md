# Reason Engine v1

Reason Engine converts validated MV Analyzer measurements into auditable claims before rendering prose.

## Contract

`AnalyzeReport v2 → reference evidence → optional Taste Profile evidence → Claim Engine → ReasonDocument v1 → deterministic KO/EN prose`.

The Claim Engine owns support, contradiction, scope and confidence. Language rendering never upgrades an insufficient or contradicted claim.

### Distinctive

A product-level distinctive candidate requires `|z| >= 0.75` or a reference-corpus percentile in the outer 20%. These are explanation heuristics, not statistical-significance gates.

### Feel

A feel claim normally requires two compatible measured axes, for example high close-up ratio plus low wide ratio, or high onset density plus high peak-energy concentration.

### Taste

Taste is opt-in. Fewer than four analyzed favorites cannot create a supported taste reason. Four–five is low-confidence; six or more may be medium-confidence. `talk.profile()` high-variance axes become explicit `not_supported` evidence when relevant. Shared conventions are not relabeled as personal taste. Failed scene-motion metrics are excluded.

## Interfaces

```bash
mva reason-export data/VIDEO_ID --out reason.json --favorites favorites.txt
mva explain YOUTUBE_URL --lang ko --out reason.json
```

The public static Web app accepts report v2 or Reason v1 locally in browser memory. It never uploads imported files. The `So why? / 그래서 왜?` section precedes PCA and raw feature tables, and every visible claim has an evidence disclosure.

## Limits

The current benchmark is an extreme-group research corpus, not a representative market distribution. Reason Engine does not predict success, future views, artistic quality, personality, identity or mental state.
