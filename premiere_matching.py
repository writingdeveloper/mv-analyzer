"""프리미어 효과 분석: 모집단 채널 내 매칭 쌍 → log(view_per_sub) Wilcoxon.

usage: PYTHONUTF8=1 python premiere_matching.py
"""
import json
import math
import statistics

from scipy import stats as st

from mv_analyzer.collect import filter_population
from mv_analyzer.premiere import build_pairs

DOMAINS = {"vocaloid": "work/population.jsonl",
           "kpop": "work/kpop/population.jsonl"}
MIN_PAIRS = 10   # 미만이면 보조 분석으로 강등 (스펙 1-C)
REPORT = "docs/reports/2026-07-21-premiere-matching.md"

KPOP_NOTE = ("멀티 아티스트 레이블 채널 구조로 채널 내 매칭이 팬덤 규모를 통제하지 못함 "
             "— 게이트/해석에서 제외.")


def main():
    summary = {}
    md = ["# 프리미어 채널 내 매칭 분석 (2026-07-21)", "",
          "같은 채널의 프리미어 vs 비프리미어 최근접 매칭(≤180일) — "
          "채널 수준 교란 통제. 매칭 전 mv_analyzer.collect.filter_population으로 "
          "비-MV 콘텐츠(응원법·콘셉트 클립·라이브 등)를 제목 휴리스틱으로 제외"
          "(kpop은 require_mv=True로 MV 표기 필수). "
          "검정: 쌍대 log(view_per_sub) Wilcoxon.", ""]
    for domain, path in DOMAINS.items():
        rows = [json.loads(l) for l in open(path, encoding="utf-8")]
        rows = filter_population(rows, require_mv=(domain == "kpop"))
        pairs = build_pairs(rows)
        diffs = [math.log(p["view_per_sub"]) - math.log(c["view_per_sub"])
                 for p, c in pairs]
        entry = {"n_pairs": len(pairs), "wilcoxon_p": None,
                 "median_log_ratio": None, "median_ratio": None,
                 "auxiliary": len(pairs) < MIN_PAIRS}
        if len(pairs) >= MIN_PAIRS:
            w = st.wilcoxon(diffs)
            med = statistics.median(diffs)
            entry.update(wilcoxon_p=float(w.pvalue),
                         median_log_ratio=float(med),
                         median_ratio=float(math.exp(med)))
        if domain == "kpop":
            # 구조적으로 불가피한 교란(멀티 아티스트 레이블 채널) — 쌍 수와
            # 무관하게 항상 보조 분석으로 강등. 수치는 투명성을 위해 유지.
            entry["auxiliary"] = True
            entry["note"] = KPOP_NOTE
        summary[domain] = entry
        md.append(f"## {domain}: 쌍 {len(pairs)}개"
                  + (" — 보조 분석" if entry["auxiliary"] else ""))
        if entry["wilcoxon_p"] is not None:
            md += ["", f"- Wilcoxon p = {entry['wilcoxon_p']:.4f}",
                   f"- 중앙 배율(프리미어/비프리미어) = {entry['median_ratio']:.2f}×", ""]
        if domain == "kpop":
            md += ["> **한계**: K-pop은 레이블 메가 채널(예: HYBE LABELS)이 "
                   "여러 아티스트를 동시 호스팅하므로, 채널 내 최근접 매칭이라도 "
                   "프리미어 영상과 비프리미어 통제가 서로 다른 아티스트일 수 있어 "
                   "팬덤 규모를 통제하지 못한다. 가용 메타데이터(채널 단위)로는 "
                   "구조적으로 해결 불가 — 위 수치는 참고용으로만 보고하며 "
                   "게이트·해석 판단에서는 제외한다.", ""]
    with open("work/premiere_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print("OK —", {d: s["n_pairs"] for d, s in summary.items()})


if __name__ == "__main__":
    main()
