"""측정 신뢰도: qwen2.5vl 태깅 vs 독립 라벨러(강한 모델) 일치율.

입력: work/reliability_sample.json (+qwen 태그),
      work/reliability_labels_A.json / _B.json (블라인드 라벨)
출력: docs/reports/2026-07-17-measurement-reliability.md
"""
import json

from scipy import stats as st

from mv_analyzer.reliability import cohen_kappa



def main():
    items = json.load(open("work/reliability_sample.json", encoding="utf-8"))
    labels = {}
    for part in ["A", "B"]:
        for l in json.load(open(f"work/reliability_labels_{part}.json",
                                encoding="utf-8")):
            labels[l["i"]] = l

    rows = [(it["qwen"], labels[i]) for i, it in enumerate(items) if i in labels]
    n = len(rows)
    lines = ["# 측정 신뢰도 검증 — VLM 태깅 vs 독립 라벨러\n",
             f"작성: 2026-07-17 · 표본: 키프레임 {n}장 "
             f"(보컬로이드 표본 26편 × 2장, 층화 무작위)\n",
             "방법: qwen2.5vl:7b(파이프라인)의 태그를, 태그를 보지 않은 독립 "
             "라벨러(상위 모델 Claude)가 동일 폐쇄 어휘로 블라인드 라벨링한 "
             "결과와 대조. 일치율 + Cohen's κ.\n",
             "| 항목 | 일치율 | Cohen's κ | 판정 |",
             "|---|---|---|---|"]

    verdicts = {}
    for field in ["mood", "shot_type", "style"]:
        a = [str(q.get(field)) for q, l in rows]
        b = [str(l.get(field)) for q, l in rows]
        acc = sum(x == y for x, y in zip(a, b)) / n
        k = cohen_kappa(a, b)
        grade = ("높음" if k >= 0.6 else "중간" if k >= 0.4 else
                 "낮음 — 해당 컬럼 해석 주의")
        verdicts[field] = (acc, k, grade)
        lines.append(f"| {field} | {acc:.0%} | {k:.2f} | {grade} |")

    qa = [float(q.get("num_characters") or 0) for q, l in rows]
    la = [float(l.get("num_characters") or 0) for q, l in rows]
    exact = sum(x == y for x, y in zip(qa, la)) / n
    within1 = sum(abs(x - y) <= 1 for x, y in zip(qa, la)) / n
    rho = st.spearmanr(qa, la).statistic
    lines.append(f"| num_characters | 정확 {exact:.0%} / ±1 {within1:.0%} "
                 f"| ρ={rho:.2f} | {'높음' if rho >= 0.7 else '중간' if rho >= 0.5 else '낮음'} |")

    lines += ["\n## 해석 기준\n",
              "- κ 0.6+ = substantial, 0.4~0.6 = moderate (Landis & Koch)",
              "- 이 검증은 '재현성'(temp 0 동일 출력)과 별개인 **정확성** 근거다. "
              "독립 라벨러도 모델이므로 사람 라벨 대비 완전한 정답은 아니며, "
              "두 모델이 같은 체계적 오류를 공유할 가능성은 남는다.",
              "- κ가 낮은 항목은 P5 해석에서 가중을 낮출 것.\n"]

    out = "docs/reports/2026-07-17-measurement-reliability.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"→ {out} (n={n})")
    for f_, (acc, k, g) in verdicts.items():
        print(f"  {f_}: {acc:.0%} / κ={k:.2f} ({g})")
    print(f"  num_characters: 정확 {exact:.0%}, ±1 {within1:.0%}, ρ={rho:.2f}")


if __name__ == "__main__":
    main()
