"""단조성(dose-response) 확인 — Phase 4 핵심 로직.

docs/superpowers/specs/2026-07-21-paper-dataset-design.md §Phase 4.
하위/중간/상위 3그룹(view_per_sub 오름차순)에 걸쳐 사전 등록 지표가 단조 경향을
보이는지 검정한다. 통계 코어(trend_test)는 mv_analyzer.stats에 위치 —
여기는 그룹핑·중앙값 테이블·판정·리포트 렌더링만 담당.
"""
import numpy as np

from mv_analyzer.stats import bh_fdr, trend_test

# 사전 등록 지표 — 사이클 1 유의 지표 중 결정론적 측정 상위 6개(스펙 §Phase 4).
METRICS = [
    "scene_cuts_per_minute", "scene_median_shot_len_s", "scene_num_scenes",
    "hook_cuts_first_15s", "sync_beats_per_cut", "scene_min_shot_len_s",
]


def run_analysis(bottom_rows, middle_rows, top_rows, metrics=METRICS, min_n=3):
    """지표별 trend_test 실행 + BH-FDR. 표본 부족 지표는 결과에서 제외."""
    results = []
    for m in metrics:
        b = [r[m] for r in bottom_rows if r.get(m) is not None]
        mid = [r[m] for r in middle_rows if r.get(m) is not None]
        t = [r[m] for r in top_rows if r.get(m) is not None]
        if len(b) < min_n or len(mid) < min_n or len(t) < min_n:
            continue
        tr = trend_test([b, mid, t])
        med_b, med_mid, med_t = (float(np.median(b)), float(np.median(mid)),
                                 float(np.median(t)))
        if med_b <= med_mid <= med_t:
            order = "증가"
        elif med_b >= med_mid >= med_t:
            order = "감소"
        else:
            order = "비단조"
        results.append({
            "metric": m, "n_bottom": len(b), "n_middle": len(mid), "n_top": len(t),
            "med_bottom": med_b, "med_middle": med_mid, "med_top": med_t,
            "stat": tr["stat"], "p": tr["p"], "method": tr["method"],
            "median_order": order,
        })
    if results:
        qs = bh_fdr(np.array([r["p"] for r in results]))
        for r, q in zip(results, qs):
            r["q"] = float(q)
    return results


def verdict(r):
    """단조성 판정 — q<0.05 AND 중앙값 순서가 증가/감소로 일관될 때만 '성립'."""
    sig = r["q"] < 0.05
    order_ok = r["median_order"] in ("증가", "감소")
    if sig and order_ok:
        return "단조성 성립"
    if order_ok:
        return "방향 일치(비유의)"
    return "단조성 불성립"


def render_report(results, n_bottom, n_middle, n_top, generated):
    n_ok = sum(1 for r in results if verdict(r) == "단조성 성립")
    lines = [
        "# Phase 4 — 중간층 표본 단조성 확인 리포트\n",
        f"생성: {generated} · 표본: 하위 {n_bottom} / 중간 {n_middle} / 상위 {n_top} "
        "(view_per_sub 오름차순 3그룹, 보컬로이드 도메인)\n",
        "## 요약\n",
        f"- 사전 등록 지표 {len(results)}개 중 단조성 성립(q<0.05 & 중앙값 순서 일관): "
        f"**{n_ok}개**\n",
        "## 지표별 결과\n",
        "| 지표 | 하위 중앙값 | 중간 중앙값 | 상위 중앙값 | 통계량 | method | p | q(BH) | 판정 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['metric']} | {r['med_bottom']:.3f} | {r['med_middle']:.3f} "
            f"| {r['med_top']:.3f} | {r['stat']:+.3f} | {r['method']} "
            f"| {r['p']:.4f} | {r['q']:.4f} | {verdict(r)} |")
    lines.append(
        "\n주: 검정 순서는 하위<중간<상위(조회수/구독자수 비율 오름차순) 가정. "
        "'단조성 성립'은 q<0.05 **그리고** 중앙값 순서가 증가 또는 감소로 일관될 때만. "
        "불성립이어도 극단 그룹 비교 자체의 타당성을 훼손하지 않음 — dose-response "
        "근거 확보 여부만 판단(스펙 §Phase 4).\n")
    return "\n".join(lines) + "\n"
