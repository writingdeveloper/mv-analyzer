"""게이트 판정: 신규 분석 3종 summary → 논문 진행 여부.

기준(스펙): 1개 이상에서 q<0.05 그리고 |δ|>=0.33, 또는 매칭 p<0.05.
usage: PYTHONUTF8=1 python gate_report.py  (PASS면 exit 0)
"""
import json
import sys

Q_MAX, DELTA_MIN, P_MAX = 0.05, 0.33, 0.05
REPORT = "docs/reports/2026-07-21-new-analyses-gate.md"


def load(p):
    return json.load(open(p, encoding="utf-8"))


def main():
    hits = []
    for name, path in [("가사 구조", "work/lyrics_structure_summary.json"),
                       ("히트맵", "work/heatmap_summary.json")]:
        for domain, entry in load(path).items():
            for r in entry.get("stats", []):
                if r.get("q", 1) < Q_MAX and abs(r["delta"]) >= DELTA_MIN:
                    hits.append(f"[{name}/{domain}] {r['metric']}: "
                                f"δ {r['delta']:+.2f}, q {r['q']:.4f}")
    for domain, e in load("work/premiere_summary.json").items():
        if not e["auxiliary"] and e["wilcoxon_p"] is not None \
                and e["wilcoxon_p"] < P_MAX:
            hits.append(f"[프리미어/{domain}] Wilcoxon p {e['wilcoxon_p']:.4f}, "
                        f"중앙 배율 {e['median_ratio']:.2f}× (쌍 {e['n_pairs']})")
    verdict = "PASS" if hits else "FAIL"
    md = ["# 신규 분석 게이트 판정 (2026-07-21)", "",
          f"기준: q<{Q_MAX} 그리고 |δ|≥{DELTA_MIN}, 또는 매칭 p<{P_MAX}", "",
          f"## 판정: **{verdict}**", ""]
    md += [f"- {h}" for h in hits] or ["- 기준을 충족한 결과 없음 → 재기획 복귀"]
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"{verdict}: {len(hits)}건")
    for h in hits:
        print(" ", h)
    sys.exit(0 if hits else 1)


if __name__ == "__main__":
    main()
