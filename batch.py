"""P4 배치 드라이버: sample.csv의 영상을 순차 분석하고 features 테이블로 병합.

- 영상별 subprocess 실행 → 한 편의 실패가 배치를 중단시키지 않음
- features.json 존재 시 스킵(이어하기) — analyze.py 자체의 단계별 이어하기와 이중 안전망
- 종료 시 work/features_table.jsonl 생성 (group 컬럼 포함, P5 입력)

usage: python batch.py [--sample work/sample.csv] [--lang ja]
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import time
import urllib.request

OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"


def ollama_alive():
    try:
        with urllib.request.urlopen(OLLAMA_TAGS, timeout=5):
            return True
    except Exception:
        return False


def require_ollama(retries=3, wait_s=60):
    """Ollama 헬스체크 — 다운이면 대기·재시도 후 False.

    서버가 죽은 채 배치를 계속 돌리면 편당 수 분씩 낭비하며 전량 실패한다(실측).
    """
    for i in range(retries):
        if ollama_alive():
            return True
        print(f"Ollama 응답 없음 — {wait_s}초 후 재확인 ({i + 1}/{retries})",
              flush=True)
        time.sleep(wait_s)
    return ollama_alive()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", default="work/sample.csv")
    ap.add_argument("--out", default="data")
    ap.add_argument("--lang", default="ja")
    ap.add_argument("--table", default="work/features_table.jsonl")
    ap.add_argument("--pause", type=int, default=20,
                    help="영상 간 대기 초 (YouTube 봇 판정 완화)")
    args = ap.parse_args()

    with open(args.sample, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"배치 대상 {len(rows)}편 (상위 {sum(r['group'] == 'top' for r in rows)}"
          f" / 하위 {sum(r['group'] == 'bottom' for r in rows)})", flush=True)

    fails = []
    completed_now = []
    skipped_existing = []
    aborted = False
    for i, r in enumerate(rows):
        vid = r["video_id"]
        feat = os.path.join(args.out, vid, "features.json")
        if os.path.exists(feat):
            skipped_existing.append(vid)
            print(f"[{i + 1}/{len(rows)}] {vid} — 이미 완료, 스킵", flush=True)
            continue
        if not require_ollama():
            print("Ollama 미기동 — 배치 조기 중단 (재기동 후 python batch.py 재실행)",
                  flush=True)
            aborted = True
            break
        print(f"[{i + 1}/{len(rows)}] {vid} ({r.get('title', '')[:40]}) 시작",
              flush=True)
        t0 = time.time()
        proc = subprocess.run(
            [sys.executable, "analyze.py",
             f"https://www.youtube.com/watch?v={vid}",
             "--out", args.out, "--lang", args.lang])
        ok = proc.returncode == 0 and os.path.exists(feat)
        print(f"  → {'완료' if ok else '실패'} ({time.time() - t0:.0f}s)",
              flush=True)
        if ok:
            completed_now.append(vid)
        else:
            fails.append(vid)
        if args.pause:
            time.sleep(args.pause)

    # features 테이블 병합 (완료된 것만)
    groups = {r["video_id"]: r["group"] for r in rows}
    n = 0
    tmp = args.table + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            feat = os.path.join(args.out, r["video_id"], "features.json")
            if not os.path.exists(feat):
                continue
            with open(feat, encoding="utf-8") as ff:
                row = json.load(ff)
            row["group"] = groups[r["video_id"]]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    os.replace(tmp, args.table)

    available = n
    pending = len(rows) - available - len(fails)
    print(f"배치 종료: 신규 성공 {len(completed_now)}, 기존 완료 {len(skipped_existing)}, "
          f"실패 {len(fails)}, 미처리 {max(0, pending)} / 전체 {len(rows)}"
          f"{' (Ollama 다운으로 조기 중단)' if aborted else ''}", flush=True)
    if fails:
        print("실패: " + ", ".join(fails), flush=True)
    print(f"features 테이블 {n}행 → {args.table}", flush=True)
    return 1 if fails or aborted else 0


if __name__ == "__main__":
    sys.exit(main())
