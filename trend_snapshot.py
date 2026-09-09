"""트렌드 스냅샷: 표본 50편의 현재 조회수·좋아요를 재수집해 성장 추적.

usage: python trend_snapshot.py            # 스냅샷 1회 (메타만, ~3분)
       python trend_snapshot.py --report   # 저장된 스냅샷 간 성장 비교

분기별 전체 갱신(새 표본으로 메타 변화 추적)은 README '트렌드 모니터링 런북' 참조.
"""
import argparse
import csv
import datetime
import glob
import json
import os
import time

from mv_analyzer.download import fetch_meta

SNAP_DIR = "work/trend"


def cmd_snapshot():
    rows = list(csv.DictReader(open("work/sample.csv", encoding="utf-8")))
    os.makedirs(SNAP_DIR, exist_ok=True)
    stamp = datetime.date.today().isoformat()
    out = os.path.join(SNAP_DIR, f"{stamp}.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for i, r in enumerate(rows):
            vid = r["video_id"]
            try:
                m = fetch_meta(vid)
                snap = {"video_id": vid, "group": r["group"], "date": stamp,
                        "view_count": m.get("view_count"),
                        "like_count": m.get("like_count"),
                        "comment_count": m.get("comment_count"),
                        "subscriber_count": m.get("channel_follower_count")}
            except Exception as e:
                snap = {"video_id": vid, "group": r["group"], "date": stamp,
                        "error": str(e)[:200]}
            f.write(json.dumps(snap, ensure_ascii=False) + "\n")
            print(f"[{i + 1}/{len(rows)}] {vid} → "
                  f"{snap.get('view_count', 'ERR')}", flush=True)
            time.sleep(2)  # 봇 판정 완화
    print(f"스냅샷 → {out}")


def cmd_report():
    snaps = sorted(glob.glob(os.path.join(SNAP_DIR, "*.jsonl")))
    if len(snaps) < 2:
        print(f"스냅샷 {len(snaps)}개 — 비교하려면 2개 이상 필요 "
              f"(다른 날짜에 다시 실행)")
        return
    first, last = snaps[0], snaps[-1]

    def load(p):
        return {json.loads(l)["video_id"]: json.loads(l)
                for l in open(p, encoding="utf-8")}
    a, b = load(first), load(last)
    print(f"성장 비교: {os.path.basename(first)} → {os.path.basename(last)}\n")
    print(f"{'그룹':<6}{'video_id':<14}{'조회 증가':>12}{'증가율':>9}")
    growth = []
    for vid, r in b.items():
        p = a.get(vid)
        if not p or r.get("view_count") is None or p.get("view_count") is None:
            continue
        d = r["view_count"] - p["view_count"]
        pct = d / p["view_count"] * 100 if p["view_count"] else 0
        growth.append((r["group"], vid, d, pct))
    growth.sort(key=lambda x: -x[2])
    for g, vid, d, pct in growth[:15]:
        print(f"{g:<6}{vid:<14}{d:>12,}{pct:>8.1f}%")
    for grp in ["top", "bottom"]:
        ds = [d for g, _, d, _ in growth if g == grp]
        if ds:
            print(f"\n{grp}: 중앙 증가 {sorted(ds)[len(ds) // 2]:,}회 (n={len(ds)})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    cmd_report() if args.report else cmd_snapshot()
