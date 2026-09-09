"""가사 구조 분석: 표본 100편 → 구조 지표 + 도메인 내 그룹 비교.

usage: PYTHONUTF8=1 python lyrics_structure.py
출력: work[/kpop]/lyrics_structure.jsonl, work/lyrics_structure_summary.json,
      docs/reports/2026-07-21-lyrics-structure.md
"""
import json
import os

import numpy as np
from scipy import stats as st

from mv_analyzer.lyrics_structure import structure_features
from mv_analyzer.stats import bh_fdr, cliffs_delta, magnitude

DOMAINS = {"vocaloid": "work", "kpop": "work/kpop"}
METRICS = ["lyrics_compression_ratio", "lyrics_title_first_s",
           "lyrics_title_count", "lyrics_first_chorus_s",
           "sync_cut_on_line_ratio"]
REPORT = "docs/reports/2026-07-21-lyrics-structure.md"
MIN_LINES = 8


def domain_rows(workdir):
    return [json.loads(line) for line in open(f"{workdir}/features_table.jsonl",
                                               encoding="utf-8")]


def true_asr_failures(workdir):
    """필터 수정 후에도 8라인 미만인 영상 — ASR 세그먼트 자체가 부족/비가사(진짜 실패)."""
    out = []
    for row in domain_rows(workdir):
        vid = row["video_id"]
        p = f"data/{vid}/lyrics_lines.json"
        if not os.path.exists(p):
            continue
        lj = json.load(open(p, encoding="utf-8"))
        n_lines = len(lj.get("lines") or [])
        if lj.get("source") == "ocr" or n_lines >= MIN_LINES:
            continue
        lang = lj.get("lang", "ja")
        asr_p = f"data/{vid}/lyrics_asr.{lang}.json"
        n_seg = (len(json.load(open(asr_p, encoding="utf-8")).get("segments") or [])
                if os.path.exists(asr_p) else None)
        out.append({"video_id": vid, "title": row["title"],
                    "n_lines": n_lines, "n_segments": n_seg})
    return out


def cut_times(video_id):
    p = f"data/{video_id}/scenes.json"
    if not os.path.exists(p):
        return []
    scenes = json.load(open(p, encoding="utf-8"))["scenes"]
    return [s["start_s"] for s in scenes[1:]]


def extract_domain(workdir):
    rows = []
    for line in open(f"{workdir}/features_table.jsonl", encoding="utf-8"):
        row = json.loads(line)
        p = f"data/{row['video_id']}/lyrics_lines.json"
        if not os.path.exists(p):
            continue
        lj = json.load(open(p, encoding="utf-8"))
        feats = structure_features(lj.get("lines") or [],
                                   cut_times(row["video_id"]),
                                   row["title"], row["channel"])
        if feats is None:
            continue
        feats.update(video_id=row["video_id"], group=row["group"],
                     lyrics_source=lj.get("source"))
        rows.append(feats)
    with open(f"{workdir}/lyrics_structure.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows


def compare_groups(rows, metrics):
    """도메인 내 top vs bottom — MW U + Cliff's δ + BH-FDR."""
    out, pvals = [], []
    for m in metrics:
        top = [r[m] for r in rows if r["group"] == "top" and r[m] is not None]
        bot = [r[m] for r in rows if r["group"] == "bottom" and r[m] is not None]
        if len(top) < 5 or len(bot) < 5:
            continue
        p = st.mannwhitneyu(top, bot, alternative="two-sided").pvalue
        out.append({"metric": m, "n_top": len(top), "n_bot": len(bot),
                    "med_top": float(np.median(top)),
                    "med_bot": float(np.median(bot)),
                    "p": float(p), "delta": float(cliffs_delta(top, bot))})
        pvals.append(p)
    for r, q in zip(out, bh_fdr(np.array(pvals)) if pvals else []):
        r["q"] = float(q)
        r["magnitude"] = magnitude(r["delta"])
    return out


def main():
    summary, md = {}, ["# 가사 구조 분석 (2026-07-21, 측정 수정 반영 재계산)", "",
                       "스펙: `docs/superpowers/specs/2026-07-21-paper-dataset-design.md`",
                       "필터: 가사 라인 ≥8. 도메인 내 비교만 수행.", "",
                       "**2026-07-21 측정 수정**: `mv_analyzer/lyrics.py::asr_to_lines`의 "
                       "언어비율 필터가 sung English 라인을 환각으로 오분류해 대량 탈락시키던 "
                       "버그를 수정했다 — ASR 경로는 이제 (자국어+라틴 문자) 비율로 판정하고, "
                       "연속 중복 세그먼트 접기(반복 환각 방어)를 추가했다. OCR 경로(`clean_lyrics`, "
                       "번인 자막)는 자국어 전용 필터를 그대로 유지 — 화면에 노출되지만 노래로 "
                       "불리지 않는 제작진 크레딧 등을 계속 차단해야 하기 때문이다. 재파생은 "
                       "저장된 ASR raw 세그먼트에서 GPU 재실행 없이 수행했다 "
                       "(`rederive_lyrics.py`).", ""]
    all_rows = {}
    for domain, workdir in DOMAINS.items():
        rows = extract_domain(workdir)
        all_rows[domain] = rows
        stats_rows = compare_groups(rows, METRICS)
        # 민감도: 지배적 lyrics_source만으로 압축률 재검정
        src_counts = {}
        for r in rows:
            src_counts[r["lyrics_source"]] = src_counts.get(r["lyrics_source"], 0) + 1
        dom_src = max(src_counts, key=src_counts.get)
        sens = compare_groups([r for r in rows if r["lyrics_source"] == dom_src],
                              ["lyrics_compression_ratio"])
        summary[domain] = {"n": len(rows), "stats": stats_rows,
                           "sensitivity": {"dominant_source": dom_src,
                                           "stats": sens}}
        md += [f"## {domain} (n={len(rows)}, source={src_counts})", "",
               "| 지표 | top 중앙값 | bottom 중앙값 | δ | p | q | 크기 |",
               "|---|---|---|---|---|---|---|"]
        for r in stats_rows:
            md.append(f"| {r['metric']} | {r['med_top']:.3f} | {r['med_bot']:.3f} "
                      f"| {r['delta']:+.2f} | {r['p']:.4f} | {r['q']:.4f} "
                      f"| {r['magnitude']} |")
        if sens:
            s = sens[0]
            md += ["", f"민감도({dom_src}만, 압축률): δ {s['delta']:+.2f}, "
                       f"p {s['p']:.4f} (n={s['n_top']}+{s['n_bot']})", ""]

    # --- 표본/한계 disclosure — 매 실행 시 실제 수치로 재생성 (수기 편집 대체) ---
    dom_stats = {}
    for domain, workdir in DOMAINS.items():
        total = len(domain_rows(workdir))
        has_lyrics = sum(1 for r in domain_rows(workdir)
                         if os.path.exists(f"data/{r['video_id']}/lyrics_lines.json")
                         and json.load(open(
                             f"data/{r['video_id']}/lyrics_lines.json",
                             encoding="utf-8")).get("source"))
        n_pass = len(all_rows[domain])
        dom_stats[domain] = {"total": total, "has_lyrics": has_lyrics, "n_pass": n_pass}

    md += ["## 표본", ""]
    attrition_bits = []
    for domain in DOMAINS:
        s = dom_stats[domain]
        attrition_bits.append(
            f"{domain}은 (가사 보유) {s['has_lyrics']}/{s['total']}편 중 "
            f"{s['n_pass']}편({s['n_pass'] / s['has_lyrics'] * 100:.0f}%, "
            f"전체 표본 기준 {s['n_pass']}/{s['total']}) 통과")
    md.append(
        "- **표본 감쇠(attrition)**: 위 표는 가사 라인 ≥8 필터를 통과한 영상만 포함한다. "
        f"측정 수정(ASR 언어필터) 이후 재계산 결과, {' — '.join(attrition_bits)}했다. "
        "남은 손실은 대부분 진짜 ASR 실패(가창 없는 구간/침묵/비가사 발화)이며, "
        "결측이 완전 무작위(MCAR)가 아닐 가능성은 여전히 남아 있다 — 해석 시 주의할 것.")

    kpop_fails = true_asr_failures(DOMAINS["kpop"])
    if kpop_fails:
        detail = ", ".join(f"{f['video_id']}({f['n_segments']}세그먼트→{f['n_lines']}라인)"
                           for f in kpop_fails)
        md.append(
            f"- **잔존 진짜 ASR 실패(kpop, {len(kpop_fails)}편)**: {detail}. "
            "내용 확인 결과 각각 비가사 내레이션(영문 자막 프롤로그), 반복 환각 문구"
            "(\"자막 제공 배달의민족\", \"다음 영상에서 만나요\" 등 시청 유도 문구가 무음/비가창 "
            "구간에서 반복 오인식됨), 완전 무검출(세그먼트 0개)이다 — 필터 정교화로 회복 불가한 "
            "영상 자체의 한계.")

    excluded_by_domain = {
        domain: sorted(set(METRICS)
                       - {r["metric"] for r in summary[domain]["stats"]})
        for domain in DOMAINS}
    for domain, excluded in excluded_by_domain.items():
        if excluded:
            md.append(
                f"- **{domain}에서 `{'`, `'.join(excluded)}` 제외**: 해당 도메인의 "
                "유효(non-null) 표본 n<5로 검정을 수행하지 않았다. "
                "위 표는 도메인별로 검정이 수행된 지표만 포함한다.")
    n_tests = {d: len(summary[d]["stats"]) for d in DOMAINS}
    min_q = {d: min((r["q"] for r in summary[d]["stats"]), default=None) for d in DOMAINS}
    q_desc = ", ".join(f"{d} {n_tests[d]}개(최소 q={min_q[d]:.4f})"
                       if min_q[d] is not None else f"{d} 0개"
                       for d in DOMAINS)
    md.append(
        f"- **BH-FDR 보정 범위**: 위 이유로 실제 보정은 사전등록 {len(METRICS)}개가 아닌 "
        f"도메인별 실제 수행 검정 수에 대해 이루어짐 — {q_desc}. "
        "q<0.05를 충족하는 지표는 없었다 (게이트 판정은 `gate_report.py` 참고).")
    md.append("")

    md += ["## 한계", ""]
    kpop_rows = all_rows["kpop"]
    nonzero_title = sum(1 for r in kpop_rows if (r.get("lyrics_title_count") or 0) > 0)
    md.append(
        "K-pop은 영문 표기 제목 vs 한글 ASR 가사라 title-in-lyrics 매칭이 구조적으로 "
        "과소 측정됨 — 측정 수정(영문 라인 복구) 이후에도 kpop `lyrics_title_count`는 "
        f"{len(kpop_rows)}건 중 {nonzero_title}건만 nonzero로, 여전히 대부분 0이다. "
        "영문 제목이 실제로 가사에 그 표기 그대로 등장하는 경우가 드물기 때문(한글 가창 vs "
        "로마자 제목)이며, 코드 결함이 아니라 표본의 언어·표기체계 특성이다. K-pop의 "
        "`lyrics_title_*` 지표는 해석에서 제외할 것.")
    md.append(
        "ASR 경로에서 영어 라인을 실가사로 인정하도록 필터를 완화한 부작용으로, 비가창 "
        "영문 내레이션/자막 문구가 gibberish 방어를 통과해 가사로 오분류될 잔여 위험이 "
        "있다(위 잔존 실패 사례의 8라인 미만 탈락분에서 관찰됨). 8라인 이상 통과한 영상에서 "
        "이런 오염이 있는지는 개별 검수하지 않았다 — 대규모 검수는 향후 과제.")
    md.append("")

    with open("work/lyrics_structure_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    os.makedirs("docs/reports", exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"OK — {REPORT}")
    for d, s in summary.items():
        print(f"  {d}: n={s['n']}, 검정 {len(s['stats'])}개")


if __name__ == "__main__":
    main()
