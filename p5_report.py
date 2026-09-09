"""P5 통계 분석: features 테이블 → 상·하위 그룹 비교 리포트 + 차트.

- 수치형: Mann-Whitney U + Cliff's delta(효과크기) + BH-FDR q값
- 이진/범주형: 그룹별 비율·분포 비교 (Fisher exact)
- 산출물: docs/reports/2026-07-16-p5-report.md + docs/reports/figs/*.png

usage: python p5_report.py [--table work/features_table.jsonl]
"""
import argparse
import json
import os
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from mv_analyzer.stats import bh_fdr, cliffs_delta, magnitude

# ---------- 분석 대상 컬럼 ----------
# 중앙 정책에서 정식 allowlist를 가져온다. ext_*/motion_* 실험 feature는
# 별도 신뢰성/사전등록 게이트 전에는 기존 P5 분석에 자동 포함되지 않는다.
from mv_analyzer.feature_policy import (
    P5_BINARY as BINARY, P5_CATEGORICAL as CATEGORICAL,
    P5_NUMERIC as NUMERIC, audit_rows,
)

C_TOP, C_BOT = "#2a78d6", "#eb6834"   # dataviz 검증 통과 팔레트
SURFACE = "#fcfcfb"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="work/features_table.jsonl")
    ap.add_argument("--outdir", default="docs/reports")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.table, encoding="utf-8")]
    audit = audit_rows(rows)
    if audit["errors"]:
        raise ValueError("P5 input QA failed: " + "; ".join(audit["errors"]))
    for warning in audit["warnings"]:
        print(f"[P5 QA warning] {warning}")
    # channel_video_count는 모집단 테이블에만 있음 — video_id로 조인
    try:
        pop = {json.loads(l)["video_id"]: json.loads(l)
               for l in open("work/population.jsonl", encoding="utf-8")}
        for r in rows:
            r.setdefault("channel_video_count",
                         (pop.get(r["video_id"]) or {}).get("channel_video_count"))
    except FileNotFoundError:
        pass
    top = [r for r in rows if r["group"] == "top"]
    bot = [r for r in rows if r["group"] == "bottom"]
    figdir = os.path.join(args.outdir, "figs")
    os.makedirs(figdir, exist_ok=True)

    plt.rcParams.update({
        "font.family": "Malgun Gothic", "axes.unicode_minus": False,
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "axes.edgecolor": "#c3c2b7", "axes.linewidth": 0.8,
        "axes.grid": True, "grid.color": "#e8e7e0", "grid.linewidth": 0.6,
        "text.color": "#1a1a19", "axes.labelcolor": "#1a1a19",
        "xtick.color": "#5f5e56", "ytick.color": "#5f5e56",
    })

    # ---------- 수치형 비교 ----------
    results = []
    for col in NUMERIC:
        a = [r[col] for r in top if r.get(col) is not None]
        b = [r[col] for r in bot if r.get(col) is not None]
        if len(a) < 10 or len(b) < 10:
            continue
        p = stats.mannwhitneyu(a, b, alternative="two-sided").pvalue
        results.append({
            "feature": col, "n_top": len(a), "n_bot": len(b),
            "med_top": float(np.median(a)), "med_bot": float(np.median(b)),
            "delta": cliffs_delta(a, b), "p": float(p),
        })
    qs = bh_fdr(np.array([r["p"] for r in results]))
    for r, q in zip(results, qs):
        r["q"] = float(q)
    results.sort(key=lambda r: -abs(r["delta"]))

    # ---------- 이진 비교 ----------
    bin_rows = []
    for col in BINARY:
        ta = sum(1 for r in top if r.get(col) is True)
        tb = sum(1 for r in bot if r.get(col) is True)
        na = sum(1 for r in top if r.get(col) is not None)
        nb = sum(1 for r in bot if r.get(col) is not None)
        if na < 10 or nb < 10:
            continue
        p = stats.fisher_exact([[ta, na - ta], [tb, nb - tb]]).pvalue
        bin_rows.append({"feature": col, "top": f"{ta}/{na}",
                         "bot": f"{tb}/{nb}", "p": float(p)})

    # ---------- 범주형 분포 ----------
    cat_rows = []
    for col in CATEGORICAL:
        ct = Counter(str(r.get(col)) for r in top if r.get(col) is not None)
        cb = Counter(str(r.get(col)) for r in bot if r.get(col) is not None)
        cat_rows.append({"feature": col,
                         "top": ", ".join(f"{k} {v}" for k, v in ct.most_common(4)),
                         "bot": ", ".join(f"{k} {v}" for k, v in cb.most_common(4))})

    # ---------- 교란변수 점검 ----------
    conf_rows = []
    for col in ["subscriber_count", "channel_video_count"]:
        a = [r[col] for r in top if r.get(col) is not None]
        b = [r[col] for r in bot if r.get(col) is not None]
        if len(a) < 5 or len(b) < 5:
            continue
        p = stats.mannwhitneyu(a, b).pvalue
        conf_rows.append({"feature": col, "med_top": float(np.median(a)),
                          "med_bot": float(np.median(b)),
                          "delta": cliffs_delta(a, b), "p": float(p)})

    # ---------- 그림 1: 효과크기 랭킹 ----------
    show = [r for r in results if abs(r["delta"]) >= 0.147][:15]
    fig, ax = plt.subplots(figsize=(8, max(3, 0.42 * len(show))))
    ys = np.arange(len(show))[::-1]
    colors = [C_TOP if r["delta"] > 0 else C_BOT for r in show]
    ax.barh(ys, [r["delta"] for r in show], height=0.6, color=colors, zorder=3)
    ax.axvline(0, color="#5f5e56", linewidth=0.8, zorder=4)
    ax.set_yticks(ys, [r["feature"] for r in show], fontsize=9)
    for y, r in zip(ys, show):
        marker = " *" if r["q"] < 0.05 else ""
        ax.text(r["delta"] + (0.02 if r["delta"] > 0 else -0.02), y,
                f"{r['delta']:+.2f}{marker}", va="center", fontsize=8,
                ha="left" if r["delta"] > 0 else "right", color="#1a1a19")
    ax.set_xlim(-1, 1)
    ax.set_xlabel("Cliff's delta  (+ = 상위 그룹이 큼 / - = 하위 그룹이 큼, * = q<0.05)")
    ax.set_title("상위 vs 하위 그룹 — 효과크기 랭킹 (|δ|≥0.147, 상위 15개)",
                 fontsize=11, loc="left")
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(os.path.join(figdir, "effect_ranking.png"), dpi=150)
    plt.close(fig)

    # ---------- 그림 2: 상위 판별 feature 분포 (스트립) ----------
    top4 = [r["feature"] for r in results[:4]]
    fig, axes = plt.subplots(1, 4, figsize=(11, 3.2))
    rng = np.random.default_rng(7)
    for ax, col in zip(axes, top4):
        for gi, (grp, color) in enumerate([(top, C_TOP), (bot, C_BOT)]):
            vals = [r[col] for r in grp if r.get(col) is not None]
            x = gi + rng.uniform(-0.12, 0.12, len(vals))
            ax.scatter(x, vals, s=22, color=color, alpha=0.75,
                       edgecolors=SURFACE, linewidths=0.8, zorder=3)
            ax.hlines(np.median(vals), gi - 0.22, gi + 0.22,
                      color=color, linewidth=2, zorder=4)
        ax.set_xticks([0, 1], ["상위", "하위"], fontsize=9)
        ax.set_title(col, fontsize=9, loc="left")
        ax.grid(axis="x", visible=False)
    fig.suptitle("판별력 상위 4개 feature 분포 (점=영상, 굵은 선=중앙값)",
                 fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(os.path.join(figdir, "top_features_strip.png"), dpi=150)
    plt.close(fig)

    # ---------- 리포트 ----------
    def fmt(v):
        return f"{v:,.3f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)

    sig = [r for r in results if r["q"] < 0.05]
    med_mid = [r for r in results if 0.33 <= abs(r["delta"])]
    lines = []
    lines.append("# P5 통계 분석 리포트 — 보컬로이드 MV 상·하위 극단 비교\n")
    lines.append(f"생성: 2026-07-16 · 표본: 상위 {len(top)} / 하위 {len(bot)} "
                 f"(조회수/구독자수 비율 극단, 채널당 최대 2편) · "
                 f"features {len(rows[0])}컬럼\n")
    lines.append("## 0. 요약\n")
    lines.append(f"- 수치형 {len(results)}개 비교 중 BH-FDR q<0.05 유의: "
                 f"**{len(sig)}개**, |δ|≥0.33(중간 이상 효과): {len(med_mid)}개")
    lines.append("- 해석 한계(스펙 §7): 인과 주장 불가 · 극단 그룹 설계로 효과크기 "
                 "과대추정 경향 · 일반화 범위는 2025-04~2026-04 보컬로이드 신곡\n")
    lines.append("![효과크기 랭킹](figs/effect_ranking.png)\n")
    lines.append("![상위 feature 분포](figs/top_features_strip.png)\n")

    lines.append("## 1. 수치형 feature — 효과크기 랭킹\n")
    lines.append("| feature | 상위 중앙값 | 하위 중앙값 | Cliff's δ | 크기 | p | q(BH) |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in results:
        star = " **✓**" if r["q"] < 0.05 else ""
        lines.append(f"| {r['feature']} | {fmt(r['med_top'])} | {fmt(r['med_bot'])} "
                     f"| {r['delta']:+.3f} | {magnitude(r['delta'])} "
                     f"| {r['p']:.4f} | {r['q']:.4f}{star} |")

    lines.append("\n## 2. 이진 feature (Fisher exact)\n")
    lines.append("| feature | 상위 | 하위 | p |")
    lines.append("|---|---|---|---|")
    for r in bin_rows:
        lines.append(f"| {r['feature']} | {r['top']} | {r['bot']} | {r['p']:.4f} |")

    lines.append("\n## 3. 범주형 분포 (그룹별 상위 4)\n")
    lines.append("| feature | 상위 그룹 | 하위 그룹 |")
    lines.append("|---|---|---|")
    for r in cat_rows:
        lines.append(f"| {r['feature']} | {r['top']} | {r['bot']} |")

    lines.append("\n## 4. 교란변수 점검\n")
    lines.append("| 변수 | 상위 중앙값 | 하위 중앙값 | δ | p |")
    lines.append("|---|---|---|---|---|")
    for r in conf_rows:
        lines.append(f"| {r['feature']} | {fmt(r['med_top'])} | {fmt(r['med_bot'])} "
                     f"| {r['delta']:+.3f} | {r['p']:.4f} |")
    lines.append("\n주: 구독자수는 비율 지표의 분모라 그룹 간 차이가 있으면 채널 규모 "
                 "효과가 잔존한다는 뜻 — 해석 시 반드시 참조.\n")

    out_md = os.path.join(args.outdir, "2026-07-16-p5-report.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"리포트 → {out_md}")
    print(f"유의(q<0.05) {len(sig)}개: "
          + ", ".join(f"{r['feature']}({r['delta']:+.2f})" for r in sig[:12]))


if __name__ == "__main__":
    main()
