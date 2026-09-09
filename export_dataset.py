"""공개 데이터셋 내보내기: 2개 도메인 features + 신규 파생 컬럼 → CSV.

가사 원문 텍스트는 포함하지 않는다 (파생 수치만).
usage: PYTHONUTF8=1 python export_dataset.py
"""
import csv
import json

DOMAINS = {"vocaloid": "work", "kpop": "work/kpop"}
NEW_COLS = ["lyrics_compression_ratio", "lyrics_title_first_s",
            "lyrics_title_count", "lyrics_first_chorus_s",
            "sync_cut_on_line_ratio", "heat_slope_first_30s",
            "heat_peak_at_ratio", "heat_peak_value"]
OUT = "dataset/features_100mv.csv"


def load_jsonl(path):
    try:
        return [json.loads(l) for l in open(path, encoding="utf-8")]
    except FileNotFoundError:
        return []


def main():
    rows = []
    for domain, workdir in DOMAINS.items():
        extra = {}
        for name in ("lyrics_structure", "heatmap_features"):
            for r in load_jsonl(f"{workdir}/{name}.jsonl"):
                extra.setdefault(r["video_id"], {}).update(
                    {k: v for k, v in r.items() if k in NEW_COLS})
        for r in load_jsonl(f"{workdir}/features_table.jsonl"):
            merged = {"domain": domain, **r}
            merged.update(extra.get(r["video_id"], {}))
            rows.append(merged)
    cols = ["domain"] + [k for k in rows[0] if k != "domain"] \
        + [c for c in NEW_COLS if c not in rows[0]]
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"OK — {OUT}: {len(rows)}행 × {len(cols)}열")


if __name__ == "__main__":
    main()
