"""히트맵 리텐션 분석 — K-pop 그룹 비교 + 훅 매개 상관, 보컬로이드 top 내 연속.

보컬로이드는 히트맵 보유가 top 24/bottom 4로 편중(히트맵 존재 자체가 인기의
결과)이라 그룹 비교를 하지 않는다. 스펙 1-B 참조.

usage: PYTHONUTF8=1 python heatmap_analysis.py
"""
import json

import numpy as np
from scipy import stats as st

from mv_analyzer.heatmap import heatmap_features
from mv_analyzer.stats import bh_fdr, cliffs_delta, magnitude

DOMAINS = {"vocaloid": "work", "kpop": "work/kpop"}
HEAT_METRICS = ["heat_slope_first_30s", "heat_peak_at_ratio", "heat_peak_value"]
HOOK_METRICS = ["hook_cuts_first_15s", "scene_cuts_per_minute"]
REPORT = "docs/reports/2026-07-21-heatmap-retention.md"


def load_joined(workdir):
    """표본 features_table + population heatmap join → 행 목록."""
    heat = {}
    for line in open(f"{workdir}/population.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if d.get("heatmap"):
            heat[d["video_id"]] = d["heatmap"]
    rows = []
    for line in open(f"{workdir}/features_table.jsonl", encoding="utf-8"):
        row = json.loads(line)
        hf = heatmap_features(heat.get(row["video_id"]), row["duration_s"]) \
            if row["video_id"] in heat else None
        if hf is None:
            continue
        hf.update(video_id=row["video_id"], group=row["group"],
                  view_per_sub=row["view_per_sub"],
                  **{m: row[m] for m in HOOK_METRICS})
        rows.append(hf)
    with open(f"{workdir}/heatmap_features.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows


def main():
    summary = {}
    md = ["# 히트맵 리텐션 분석 (2026-07-21)", "",
          "보컬로이드는 히트맵 보유 편중(top 24/bottom 4 — 선택 편향)으로 "
          "그룹 비교 제외, top 내 연속 분석만 수행.", ""]

    # --- K-pop: 그룹 비교 + 매개 상관 ---
    rows = load_joined("work/kpop")
    top = [r for r in rows if r["group"] == "top"]
    bot = [r for r in rows if r["group"] == "bottom"]
    stats_rows, pvals = [], []
    for m in HEAT_METRICS:
        a = [r[m] for r in top if r[m] is not None]
        b = [r[m] for r in bot if r[m] is not None]
        if len(a) < 5 or len(b) < 5:
            continue
        p = st.mannwhitneyu(a, b, alternative="two-sided").pvalue
        stats_rows.append({"metric": m, "n_top": len(a), "n_bot": len(b),
                           "med_top": float(np.median(a)),
                           "med_bot": float(np.median(b)),
                           "p": float(p), "delta": float(cliffs_delta(a, b))})
        pvals.append(p)
    for r, q in zip(stats_rows, bh_fdr(np.array(pvals)) if pvals else []):
        r["q"] = float(q)
        r["magnitude"] = magnitude(r["delta"])
    mediation = []
    for hook in HOOK_METRICS:
        pair = [(r[hook], r["heat_slope_first_30s"]) for r in rows
                if r["heat_slope_first_30s"] is not None]
        rho, p = st.spearmanr([x for x, _ in pair], [y for _, y in pair])
        mediation.append({"pair": f"{hook} × heat_slope_first_30s",
                          "rho": float(rho), "p": float(p), "n": len(pair)})
    summary["kpop"] = {"n_top": len(top), "n_bot": len(bot),
                       "stats": stats_rows, "mediation": mediation}
    md += [f"## K-pop (top {len(top)} / bottom {len(bot)})", "",
           "| 지표 | top 중앙값 | bottom 중앙값 | δ | p | q | 크기 |",
           "|---|---|---|---|---|---|---|"]
    for r in stats_rows:
        md.append(f"| {r['metric']} | {r['med_top']:.4f} | {r['med_bot']:.4f} "
                  f"| {r['delta']:+.2f} | {r['p']:.4f} | {r['q']:.4f} "
                  f"| {r['magnitude']} |")
    md += ["", "### 매개 논증: 훅 feature × 초반 리텐션 기울기 (Spearman)", ""]
    for m in mediation:
        md.append(f"- {m['pair']}: ρ {m['rho']:+.2f}, p {m['p']:.4f} (n={m['n']})")

    # --- 보컬로이드: top 내 연속 분석 ---
    vrows = [r for r in load_joined("work") if r["group"] == "top"]
    continuous = []
    for m in HEAT_METRICS:
        pair = [(r[m], r["view_per_sub"]) for r in vrows if r[m] is not None]
        if len(pair) < 10:
            continue
        rho, p = st.spearmanr([x for x, _ in pair], [y for _, y in pair])
        continuous.append({"metric": m, "rho": float(rho), "p": float(p),
                           "n": len(pair)})
    summary["vocaloid"] = {"n_top": len(vrows),
                           "note": "히트맵 보유 선택 편향 — top 내 연속 분석만",
                           "continuous": continuous}
    md += ["", f"## 보컬로이드 top 내 연속 분석 (n={len(vrows)})", ""]
    for c in continuous:
        md.append(f"- {c['metric']} × view_per_sub: ρ {c['rho']:+.2f}, "
                  f"p {c['p']:.4f} (n={c['n']})")

    # 대시보드용: K-pop 그룹별 평균 리플레이 곡선 (곡 길이 정규화 100구간)
    heat_raw = {}
    for line in open("work/kpop/population.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if d.get("heatmap"):
            heat_raw[d["video_id"]] = d["heatmap"]
    curves = {}
    for grp in ("top", "bottom"):
        mats = [[h["value"] for h in heat_raw[r["video_id"]]]
                for r in rows if r["group"] == grp
                and len(heat_raw.get(r["video_id"], [])) == 100]
        if mats:
            curves[grp] = [round(float(v), 4) for v in np.mean(mats, axis=0)]
    with open("work/heatmap_curves.json", "w", encoding="utf-8") as f:
        json.dump(curves, f)

    with open("work/heatmap_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"OK — {REPORT} (kpop n={len(rows)}, vocaloid top n={len(vrows)})")


if __name__ == "__main__":
    main()
