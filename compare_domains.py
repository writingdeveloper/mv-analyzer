"""도메인 비교: 보컬로이드 vs K-pop — 같은 방법, 다른 모집단에서 무엇이 재현되는가.

usage: python compare_domains.py
출력: docs/reports/2026-07-21-domain-comparison.md
"""
import json

import numpy as np
from scipy import stats as st

from mv_analyzer.stats import bh_fdr, cliffs_delta

FEATS = {
    "scene_cuts_per_minute": "분당 컷 수",
    "scene_median_shot_len_s": "샷 길이 중앙값(초)",
    "scene_num_scenes": "씬 수",
    "sync_beats_per_cut": "컷당 비트 수",
    "hook_cuts_first_15s": "첫 15초 컷 수",
    "tag_avg_characters": "평균 등장인물 수",
    "scene_avg_saturation": "화면 채도",
    "scene_avg_brightness": "화면 밝기",
    "audio_bpm": "BPM",
    "title_len": "제목 길이",
    "sync_cut_accel_at_peak": "피크 컷 가속",
    "thumb_num_characters": "썸네일 인물 수",
    "hook_energy_first_10s_ratio": "첫 10초 에너지",
    "duration_s": "곡 길이(초)",
}


def domain_stats(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    top = [r for r in rows if r["group"] == "top"]
    bot = [r for r in rows if r["group"] == "bottom"]
    out = {}
    ps = []
    keys = []
    for f in FEATS:
        a = [r[f] for r in top if r.get(f) is not None]
        b = [r[f] for r in bot if r.get(f) is not None]
        if len(a) < 10 or len(b) < 10:
            continue
        p = st.mannwhitneyu(a, b, alternative="two-sided").pvalue
        out[f] = {"medTop": float(np.median(a)), "medBot": float(np.median(b)),
                  "delta": cliffs_delta(a, b), "p": float(p)}
        ps.append(p)
        keys.append(f)
    for f, q in zip(keys, bh_fdr(np.array(ps))):
        out[f]["q"] = float(q)
    return out


def main():
    v = domain_stats("work/features_table.jsonl")
    k = domain_stats("work/kpop/features_table.jsonl")

    def cell(d, f):
        r = d.get(f)
        if not r:
            return "–", ""
        star = " ✓" if r["q"] < 0.05 else ""
        return f"{r['delta']:+.2f}{star}", f"{r['medTop']:g} / {r['medBot']:g}"

    lines = ["# 도메인 비교 — 보컬로이드 vs K-pop (각 상·하위 25편)\n",
             "작성: 2026-07-21 · 동일 파이프라인·동일 방법(Mann-Whitney + "
             "Cliff's δ + BH-FDR) · ✓ = q<0.05\n",
             "| feature | 보컬로이드 δ | (상/하 중앙값) | K-pop δ | (상/하 중앙값) |",
             "|---|---|---|---|---|"]
    ordering = sorted(FEATS, key=lambda f: -abs(v.get(f, {}).get("delta", 0)))
    for f in ordering:
        dv, mv = cell(v, f)
        dk, mk = cell(k, f)
        lines.append(f"| {FEATS[f]} | {dv} | {mv} | {dk} | {mk} |")

    both = [f for f in FEATS if v.get(f, {}).get("q", 1) < 0.05
            and k.get(f, {}).get("q", 1) < 0.05
            and np.sign(v[f]["delta"]) == np.sign(k[f]["delta"])]
    voc_only = [f for f in FEATS if v.get(f, {}).get("q", 1) < 0.05
                and k.get(f, {}).get("q", 1) >= 0.05]
    kpop_only = [f for f in FEATS if k.get(f, {}).get("q", 1) < 0.05
                 and v.get(f, {}).get("q", 1) >= 0.05]

    lines += ["\n## 해석\n",
              "**두 도메인 공통 유의 (같은 방향)**: "
              + (", ".join(FEATS[f] for f in both) or "없음"),
              "\n**보컬로이드만 유의**: "
              + (", ".join(FEATS[f] for f in voc_only) or "없음"),
              "\n**K-pop만 유의**: "
              + (", ".join(FEATS[f] for f in kpop_only) or "없음"),
              "\n### 요점",
              "- 보컬로이드에서는 편집 템포가 압도적 판별 요인이지만, K-pop은 "
              "상·하위 모두 이미 빠른 편집이 업계 표준이라(δ 축소) 변별력이 "
              "떨어진다 — '인기 공식'은 도메인의 제작 표준화 수준에 따라 달라진다.",
              "- 구조 검증(2026-07-21-feature-structure.md)에서 feature 간 상관 "
              "구조 자체는 두 도메인이 거의 동일(congruence 0.96)했다 — 즉 "
              "'제작 스타일의 구조'는 보편이나, '어느 축이 인기를 가르는가'는 "
              "도메인별로 다르다.",
              "\n### K-pop 해석의 한계 (필독)",
              "- 표본 원천이 공식 아티스트/레이블 채널 22개로 좁고, 하위 극단은 "
              "대형 레이블의 B급 콘텐츠(재발매판·유닛곡 등)가 다수 — 기획사 "
              "규모·프로모션이라는 강한 교란이 통제되지 않았다.",
              "- 1theK(유통사) 채널 포함으로 view_per_sub 해석이 채널 성격에 따라 "
              "이질적. K-pop 결과는 탐색적 참고로만 사용할 것.",
              "- 표본 메모: 상위 극단 중 1편(aespa)은 최초 배치에서 403으로 "
              "지연됐다가 재시도로 포함 완료 — 최종 50/50."]

    out = "docs/reports/2026-07-21-domain-comparison.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"→ {out}")
    print("공통:", [FEATS[f] for f in both])
    print("보컬로이드만:", [FEATS[f] for f in voc_only])
    print("K-pop만:", [FEATS[f] for f in kpop_only])


if __name__ == "__main__":
    main()
