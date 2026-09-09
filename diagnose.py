"""MV 진단: 임의 영상을 분석해 연구 벤치마크(상·하위 극단 50편)와 비교.

usage: python diagnose.py <URL 또는 video_id> [--lang ja|ko]
  - data/<id>/features.json이 없으면 analyze.py를 먼저 실행(GPU, ~10분)
  - 산출: 콘솔 진단표 + data/<id>/diagnosis.md

주의: 이 진단은 "상위 그룹과 닮았는가"를 보여줄 뿐, 인기를 예측하지 않는다.
빠른 컷·작화량 등은 제작 투자의 프록시일 수 있다 (리포트 §5.3).
"""
import argparse
import json
import os
import re
import subprocess
import sys

# 판정 대상: P5에서 q<0.05 유의였던 수치 feature (방향 = 상위 그룹이 큰 쪽이 +)
SIG_FEATURES = [
    ("scene_cuts_per_minute", "분당 컷 수", +1),
    ("scene_median_shot_len_s", "샷 길이 중앙값(초)", -1),
    ("scene_avg_shot_len_s", "샷 길이 평균(초)", -1),
    ("scene_num_scenes", "씬 수", +1),
    ("sync_beats_per_cut", "컷당 비트 수", -1),
    ("scene_max_shot_len_s", "최장 샷(초)", -1),
    ("hook_cuts_first_15s", "첫 15초 컷 수", +1),
    ("scene_min_shot_len_s", "최단 샷(초)", -1),
    ("tag_avg_characters", "평균 등장인물 수", +1),
    ("scene_avg_saturation", "화면 채도", +1),
]
# 참고 표시용 패키징 (Fisher 유의)
PACKAGING = [
    ("thumb_has_text", "썸네일 텍스트", False, "상위 그룹은 대부분 텍스트 없음(9/25 vs 24/25)"),
    ("was_premiere", "프리미어 공개", True, "상위 그룹 13/25 vs 하위 4/25"),
]


def median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def percentile_rank(xs, v):
    """xs 안에서 v의 백분위(0~100)."""
    xs = sorted(xs)
    below = sum(1 for x in xs if x < v)
    equal = sum(1 for x in xs if x == v)
    return 100 * (below + equal / 2) / len(xs)


def verdict(value, med_top, med_bot, direction):
    """상·하위 중앙값 중 어느 쪽에 가까운가 — 방향 반영."""
    mid = (med_top + med_bot) / 2
    if direction > 0:
        return "상위형" if value >= mid else "하위형"
    return "상위형" if value <= mid else "하위형"


def extract_video_id(arg):
    m = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", arg)
    return m.group(1) if m else arg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--lang", default="ja", choices=["ja", "ko"])
    ap.add_argument("--table", default="work/features_table.jsonl")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    vid = extract_video_id(args.video)
    feat_path = os.path.join(args.out, vid, "features.json")
    if not os.path.exists(feat_path):
        print(f"features 없음 → 전체 분석 실행 (~10분): {vid}", flush=True)
        rc = subprocess.run([sys.executable, "analyze.py",
                             f"https://www.youtube.com/watch?v={vid}",
                             "--out", args.out, "--lang", args.lang]).returncode
        if rc != 0 or not os.path.exists(feat_path):
            print("분석 실패 — 진단 중단", file=sys.stderr)
            return 1
    with open(feat_path, encoding="utf-8") as f:
        row = json.load(f)
    bench = [json.loads(l) for l in open(args.table, encoding="utf-8")]
    top = [r for r in bench if r["group"] == "top"]
    bot = [r for r in bench if r["group"] == "bottom"]

    lines = [f"# MV 진단 — {row.get('title')}",
             f"\n영상: https://www.youtube.com/watch?v={vid} · 채널: {row.get('channel')}",
             "벤치마크: 보컬로이드 신곡 상·하위 극단 각 25편 (2025-04~2026-04)\n",
             "| feature | 이 영상 | 상위 중앙값 | 하위 중앙값 | 상위 그룹 내 백분위 | 판정 |",
             "|---|---|---|---|---|---|"]
    n_top_like = 0
    judged = 0
    for col, ko, direction in SIG_FEATURES:
        v = row.get(col)
        if v is None:
            continue
        ta = [r[col] for r in top if r.get(col) is not None]
        ba = [r[col] for r in bot if r.get(col) is not None]
        mt, mb = median(ta), median(ba)
        pct = percentile_rank(ta, v)
        vd = verdict(v, mt, mb, direction)
        judged += 1
        n_top_like += vd == "상위형"
        mark = "🔵" if vd == "상위형" else "🟠"
        lines.append(f"| {ko} | **{round(v, 3)}** | {round(mt, 3)} | {round(mb, 3)} "
                     f"| {pct:.0f}% | {mark} {vd} |")

    lines.append("\n**패키징 참고**\n")
    for col, ko, good, note in PACKAGING:
        v = row.get(col)
        state = "—" if v is None else ("✅ 상위형" if v == good else "⚠️ 하위형")
        lines.append(f"- {ko}: {v} → {state} ({note})")

    score = f"{n_top_like}/{judged}"
    lines.insert(3, f"**종합: 유의 feature {judged}개 중 {score}개가 상위 그룹 프로파일과 일치**\n")
    lines.append("\n> 주의: '상위형'은 뜬 곡들과 형태가 닮았다는 뜻이지 인기 예측이 아니다. "
                 "편집 리듬·작화량은 제작 투자 규모의 프록시일 수 있다 "
                 "(docs/reports/2026-07-16-p5-report.md §5.3).")

    out_md = os.path.join(args.out, vid, "diagnosis.md")
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\n저장 → {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
