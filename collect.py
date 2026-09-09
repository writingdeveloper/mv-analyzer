"""표본 수집 CLI.
  python collect.py discover  --queries queries.txt --out work/channels_candidates.csv
  python collect.py enumerate --channels work/channels.txt --out work/population.jsonl
  python collect.py sample    --population work/population.jsonl --out work/sample.csv
  python collect.py middle    --population work/population.jsonl --out work/middle/sample.csv
"""
import argparse
import csv
import json
import os
import sys

from mv_analyzer.collect import (discover_channels, enumerate_channel,
                                 filter_population, select_middle, select_sample)


def cmd_discover(args):
    with open(args.queries, encoding="utf-8") as f:
        queries = [q.strip() for q in f if q.strip()]
    chans = discover_channels(queries)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["channel_id", "channel",
                                          "channel_url", "found_via"])
        w.writeheader()
        w.writerows(chans)
    print(f"{len(chans)}개 후보 채널 → {args.out}")
    print("다음: 수동 검수 후 채널 URL만 한 줄씩 work/channels.txt로 저장")


def cmd_enumerate(args):
    with open(args.channels, encoding="utf-8") as f:
        channels = [c.strip() for c in f if c.strip()]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    done_path = args.out + ".done"  # 완료된 입력 채널 URL 기록 — 재실행 시 네트워크 호출 전 스킵
    done = set()
    if os.path.exists(done_path):
        with open(done_path, encoding="utf-8") as f:
            done = {ln.strip() for ln in f if ln.strip()}
    with open(args.out, "a", encoding="utf-8") as out_f, \
         open(done_path, "a", encoding="utf-8") as done_f:
        for i, ch in enumerate(channels):
            if ch in done:
                print(f"[{i + 1}/{len(channels)}] {ch} — 이미 완료, 스킵", flush=True)
                continue
            print(f"[{i + 1}/{len(channels)}] {ch}", flush=True)
            try:
                rows = enumerate_channel(ch)
            except Exception as e:
                print(f"  실패: {e} — 건너뜀 (다음 실행 시 재시도)", flush=True)
                continue
            for r in rows:
                out_f.write(json.dumps(r, ensure_ascii=False) + "\n")
            out_f.flush()
            done_f.write(ch + "\n")
            done_f.flush()
            print(f"  {len(rows)}편 추가", flush=True)


def _write_sample_csv(path, group_rows):
    """group_rows: [(group명, rows), ...] — sample/middle 공용 CSV 스키마."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["group", "video_id", "title", "channel",
                    "view_per_sub", "view_count", "subscriber_count", "upload_date"])
        for grp, rows in group_rows:
            for r in rows:
                w.writerow([grp, r["video_id"], r["title"], r["channel"],
                            r["view_per_sub"], r["view_count"],
                            r["subscriber_count"], r["upload_date"]])


def cmd_sample(args):
    rows_by_id = {}
    with open(args.population, encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                r = json.loads(ln)
                rows_by_id[r["video_id"]] = r
    rows = list(rows_by_id.values())
    pop = filter_population(rows, require_mv=args.require_mv)
    print(f"모집단 {len(rows)} → 필터 후 {len(pop)}"
          + (" (MV 표기 필수 모드)" if args.require_mv else ""))
    no_ratio = sum(1 for r in rows if r.get("view_per_sub") is None)
    print(f"  (view_per_sub 없음(구독자 비공개 등)으로 제외: {no_ratio}편)")
    sample = select_sample(pop, n=args.n)
    _write_sample_csv(args.out, [("top", sample["top"]), ("bottom", sample["bottom"])])
    print(f"상위 {len(sample['top'])} + 하위 {len(sample['bottom'])} → {args.out}")


def cmd_middle(args):
    """중간층 표본 추출 (Phase 4 §단조성 확인) — 극단 표본과 동일 필터, 중복 제외."""
    rows_by_id = {}
    with open(args.population, encoding="utf-8") as f:
        for ln in f:
            if ln.strip():
                r = json.loads(ln)
                rows_by_id[r["video_id"]] = r
    rows = list(rows_by_id.values())
    # 극단 표본(work/sample.csv)과 동일한 필터 기본값 — require_mv 미지정(False)
    pop = filter_population(rows)
    print(f"모집단 {len(rows)} → 필터 후 {len(pop)}")

    exclude_ids = set()
    if os.path.exists(args.features_table):
        with open(args.features_table, encoding="utf-8") as f:
            for ln in f:
                if ln.strip():
                    exclude_ids.add(json.loads(ln)["video_id"])
    print(f"기존 표본(제외 대상) {len(exclude_ids)}편 — {args.features_table}")

    middle = select_middle(pop, n=args.n, exclude_ids=exclude_ids)
    _write_sample_csv(args.out, [("middle", middle)])
    print(f"중간층 {len(middle)} → {args.out}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover")
    d.add_argument("--queries", required=True)
    d.add_argument("--out", default="work/channels_candidates.csv")
    e = sub.add_parser("enumerate")
    e.add_argument("--channels", required=True)
    e.add_argument("--out", default="work/population.jsonl")
    s = sub.add_parser("sample")
    s.add_argument("--population", required=True)
    s.add_argument("--out", default="work/sample.csv")
    s.add_argument("--n", type=int, default=25)
    s.add_argument("--require-mv", action="store_true",
                   help="제목에 MV/Official Video 표기 필수 (K-pop 등 공식 채널 도메인)")
    m = sub.add_parser("middle")
    m.add_argument("--population", default="work/population.jsonl")
    m.add_argument("--features-table", default="work/features_table.jsonl",
                   help="이미 표본으로 뽑힌 video_id를 제외하기 위한 기존 features 테이블")
    m.add_argument("--out", default="work/middle/sample.csv")
    m.add_argument("--n", type=int, default=25)
    args = ap.parse_args()
    {"discover": cmd_discover, "enumerate": cmd_enumerate,
     "sample": cmd_sample, "middle": cmd_middle}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
