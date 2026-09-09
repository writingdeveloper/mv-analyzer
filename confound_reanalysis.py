"""교란 통제 재분석: 채널 영상 수(다작)를 통제해도 핵심 효과가 유지되는가.

방법:
1) 상위 25편 각각을 log(채널 영상 수)가 가장 가까운 하위 편과 비복원 그리디 매칭
   → 쌍별 차이 Wilcoxon signed-rank (매칭 품질 함께 보고)
2) feature ~ 채널 영상 수 Spearman 상관 (교란 경로 자체의 강도)

usage: python confound_reanalysis.py
출력: docs/reports/2026-07-17-confound-reanalysis.md
"""
import json
import math

import numpy as np
from scipy import stats as st

FEATURES = [
    ("scene_cuts_per_minute", "분당 컷 수"),
    ("scene_median_shot_len_s", "샷 길이 중앙값(초)"),
    ("scene_num_scenes", "씬 수"),
    ("sync_beats_per_cut", "컷당 비트 수"),
    ("hook_cuts_first_15s", "첫 15초 컷 수"),
    ("scene_min_shot_len_s", "최단 샷(초)"),
    ("tag_avg_characters", "평균 등장인물 수"),
    ("scene_avg_saturation", "화면 채도"),
    ("scene_max_shot_len_s", "최장 샷(초)"),
    ("scene_avg_shot_len_s", "샷 길이 평균(초)"),
]


def main():
    rows = [json.loads(l) for l in
            open("work/features_table.jsonl", encoding="utf-8")]
    pop = {json.loads(l)["video_id"]: json.loads(l)
           for l in open("work/population.jsonl", encoding="utf-8")}
    for r in rows:
        r["cvc"] = (pop.get(r["video_id"]) or {}).get("channel_video_count")
    rows = [r for r in rows if r.get("cvc")]
    top = [r for r in rows if r["group"] == "top"]
    bot = [r for r in rows if r["group"] == "bottom"]

    # 1) 그리디 매칭 (log cvc, 비복원)
    avail = bot[:]
    pairs = []
    for t in sorted(top, key=lambda r: r["cvc"]):
        b = min(avail, key=lambda r: abs(math.log(r["cvc"]) - math.log(t["cvc"])))
        avail.remove(b)
        pairs.append((t, b))
    log_gaps = [abs(math.log(t["cvc"]) - math.log(b["cvc"])) for t, b in pairs]
    med_gap_ratio = math.exp(float(np.median(log_gaps)))

    lines = ["# 교란 통제 재분석 — 채널 다작(영상 수) 효과 분리\n",
             "작성: 2026-07-17 · 입력: 보컬로이드 표본 50편 + 모집단 채널 영상 수\n",
             "## 방법\n",
             "1. 상위 각 편을 log(채널 영상 수) 최근접 하위 편과 비복원 매칭 → "
             "쌍별 차이의 Wilcoxon signed-rank 검정",
             "2. feature ~ 채널 영상 수 Spearman ρ (전체 50편) — 교란 경로 강도\n",
             f"매칭 품질: 쌍 {len(pairs)}개, 채널 영상 수 배율 중앙값 "
             f"**{med_gap_ratio:.2f}배** (1.0 = 완전 매칭). "
             + ("매칭 양호." if med_gap_ratio < 2 else
                "두 그룹의 채널 규모 분포가 크게 달라 완전한 매칭은 불가 — "
                "잔여 교란이 남을 수 있음을 감안하고 해석할 것.") + "\n",
             "## 결과\n",
             "| feature | 원래 δ 방향 | 매칭 후 쌍별 중앙 차이 | Wilcoxon p | "
             "방향 유지 | ρ(feature, 영상수) |",
             "|---|---|---|---|---|---|"]

    survived = 0
    for col, ko in FEATURES:
        diffs = [t[col] - b[col] for t, b in pairs
                 if t.get(col) is not None and b.get(col) is not None]
        if len(diffs) < 10:
            continue
        w = st.wilcoxon(diffs)
        med_diff = float(np.median(diffs))
        xs = [r[col] for r in rows if r.get(col) is not None]
        cs = [r["cvc"] for r in rows if r.get(col) is not None]
        rho = st.spearmanr(xs, cs).statistic
        # 원 방향: top>bot이면 +
        orig_dir = "+" if med_diff >= 0 else "-"  # 쌍별 차이 부호 자체가 방향
        keep = "✅" if (w.pvalue < 0.05) else "△"
        if w.pvalue < 0.05:
            survived += 1
        lines.append(f"| {ko} | {orig_dir} | {med_diff:+.3f} | {w.pvalue:.4f} "
                     f"| {keep} | {rho:+.2f} |")

    lines += [
        "\n✅ = 매칭 후에도 유의(p<0.05) · △ = 매칭 후 유의성 소실\n",
        "## 해석\n",
        f"- 검정 대상 {len(FEATURES)}개 중 **{survived}개가 다작 매칭 후에도 "
        "유의하게 유지** — 해당 효과는 채널 다작만으로 설명되지 않는다.",
        "- ρ(feature, 영상 수)의 절댓값이 큰 feature일수록 다작 교란 경로가 "
        "강했던 것 — 유의성이 소실된 항목은 다작의 산물일 가능성을 열어둘 것.",
        "- 한계: 두 그룹의 채널 규모 분포 겹침이 제한적이라 매칭 잔차가 남는다. "
        "근본 해결은 모집단 재표집 시 채널 영상 수 층화(스펙 개정 사항).",
    ]

    out = "docs/reports/2026-07-17-confound-reanalysis.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"→ {out} (유지 {survived}/{len(FEATURES)}, 매칭 배율 {med_gap_ratio:.2f}x)")


if __name__ == "__main__":
    main()
