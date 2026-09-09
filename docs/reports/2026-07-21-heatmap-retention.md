# 히트맵 리텐션 분석 (2026-07-21)

보컬로이드는 히트맵 보유 편중(top 24/bottom 4 — 선택 편향)으로 그룹 비교 제외, top 내 연속 분석만 수행.

## K-pop (top 25 / bottom 21)

| 지표 | top 중앙값 | bottom 중앙값 | δ | p | q | 크기 |
|---|---|---|---|---|---|---|
| heat_slope_first_30s | -0.0013 | -0.0043 | +0.25 | 0.1581 | 0.4744 | 작음 |
| heat_peak_at_ratio | 0.4375 | 0.5650 | -0.15 | 0.3958 | 0.5937 | 작음 |
| heat_peak_value | 1.0000 | 1.0000 | -0.05 | 0.7406 | 0.7406 | 무시 |

### 매개 논증: 훅 feature × 초반 리텐션 기울기 (Spearman)

- hook_cuts_first_15s × heat_slope_first_30s: ρ -0.24, p 0.1089 (n=46)
- scene_cuts_per_minute × heat_slope_first_30s: ρ +0.31, p 0.0344 (n=46)

## 보컬로이드 top 내 연속 분석 (n=24)

- heat_slope_first_30s × view_per_sub: ρ +0.10, p 0.6537 (n=24)
- heat_peak_at_ratio × view_per_sub: ρ -0.23, p 0.2712 (n=24)
- heat_peak_value × view_per_sub: ρ +0.23, p 0.2898 (n=24)
