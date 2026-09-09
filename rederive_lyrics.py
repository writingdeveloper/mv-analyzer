"""ASR 가사 라인 재파생 — 언어필터 버그 수정(mv_analyzer.lyrics.asr_to_lines) 반영.

GPU 재실행 없이 이미 저장된 ASR 산출물(data/<video_id>/lyrics_asr.<lang>.json)만
사용해 lyrics_lines.json을 다시 만들고, features_table.jsonl의 파생 컬럼을 갱신한다.
OCR 소스(source == "ocr")는 손대지 않는다 — 버그는 ASR 경로에만 있었다.

usage: PYTHONUTF8=1 python rederive_lyrics.py
멱등: 이미 수정된 필터로 재파생된 lyrics_lines.json을 다시 돌려도 결과가 같다.
"""
import json
import os

from mv_analyzer.lyrics import asr_to_lines, lyrics_features

DOMAINS = {"vocaloid": ("work/features_table.jsonl", "ja"),
           "kpop": ("work/kpop/features_table.jsonl", "ko")}
MIN_LINES = 8  # docs/superpowers/specs/2026-07-21-paper-dataset-design.md


def load(p):
    return json.load(open(p, encoding="utf-8"))


def save(p, obj):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def rederive_video(video_id, default_lang):
    """video_id의 lyrics_lines.json을 재파생. 반환: (변경여부, before_n, after_n) 또는
    None(대상 아님 — OCR 소스이거나 산출물 없음)."""
    lines_path = f"data/{video_id}/lyrics_lines.json"
    if not os.path.exists(lines_path):
        return None
    lj = load(lines_path)
    if lj.get("source") == "ocr":
        return None  # OCR 경로는 버그 대상 아님 — 불변

    lang = lj.get("lang") or default_lang
    asr_path = f"data/{video_id}/lyrics_asr.{lang}.json"
    if not os.path.exists(asr_path):
        return None  # 저장된 ASR 산출물 없음 — 재파생 불가

    asr = load(asr_path)
    before_n = len(lj.get("lines") or [])
    new_lines = asr_to_lines(asr.get("segments") or [], lang=lang)

    # analyze.py의 소스 선택 로직(empty-case)을 그대로 반영: 라인이 있으면 source="asr",
    # 없으면 None (OCR을 재고려하지 않음 — has_hardsub가 애초에 부족했던 케이스이므로).
    new_source = "asr" if new_lines else None
    new_lj = {"lang": lang, "source": new_source,
              "has_hardsub": lj.get("has_hardsub", False), "lines": new_lines}

    changed = new_lj != lj
    if changed:
        save(lines_path, new_lj)
    return changed, before_n, len(new_lines)


def rederive_table(table_path, default_lang):
    rows = [json.loads(line) for line in open(table_path, encoding="utf-8")]
    summary = {"n_rederived": 0, "n_now_pass": 0, "n_before_pass": 0,
               "before_lines": 0, "after_lines": 0, "details": []}

    for row in rows:
        vid = row["video_id"]
        result = rederive_video(vid, default_lang)
        if result is None:
            continue
        changed, before_n, after_n = result
        summary["n_rederived"] += 1
        summary["before_lines"] += before_n
        summary["after_lines"] += after_n
        before_pass = before_n >= MIN_LINES
        after_pass = after_n >= MIN_LINES
        summary["n_before_pass"] += before_pass
        summary["n_now_pass"] += after_pass
        if before_n != after_n:
            summary["details"].append(
                (vid, row.get("title"), before_n, after_n, before_pass, after_pass))

        # features_table 파생 컬럼 갱신 — lyrics_lines.json을 다시 읽어 일관되게 계산.
        lj = load(f"data/{vid}/lyrics_lines.json")
        lines = lj.get("lines") or []
        duration_s = row.get("scene_duration_s") or row.get("audio_duration_s")
        feats = lyrics_features(lines, duration_s)
        row["lyrics_n_lyric_lines"] = feats["n_lyric_lines"]
        row["lyrics_first_lyric_at_s"] = feats["first_lyric_at_s"]
        row["lyrics_lyric_lines_per_min"] = feats["lyric_lines_per_min"]
        row["lyrics_source"] = lj.get("source")
        # sync.py: sync_first_lyric_at_s = lyric_lines[0]["t_s"] if lyric_lines else None
        # — 이 필드만 lyric_lines에서 파생된다. sync_cut_* 등 나머지 sync 필드는 컷/비트
        # 기반이라 가사와 무관 — 손대지 않는다. lyrics_first_vocal_at_s도 asr_lines
        # 원본(필터 이전)에서 오는 것이 아니라 analyze.py에서 별도 계산되는 값으로,
        # 재실행 없이는 갱신할 수 없고 스펙상 변경 대상이 아니다 — 손대지 않는다.
        row["sync_first_lyric_at_s"] = lines[0]["t_s"] if lines else None

    with open(table_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return summary


def main():
    for domain, (table_path, default_lang) in DOMAINS.items():
        summary = rederive_table(table_path, default_lang)
        print(f"\n=== {domain} ({table_path}) ===")
        print(f"  재파생 대상(ASR/빈 소스): {summary['n_rederived']}편")
        print(f"  라인 수 합계: {summary['before_lines']} → {summary['after_lines']}")
        print(f"  ≥{MIN_LINES}라인 통과: {summary['n_before_pass']} → {summary['n_now_pass']}")
        if summary["details"]:
            print("  변경된 영상:")
            for vid, title, b, a, bp, ap in summary["details"]:
                flag = ""
                if not bp and ap:
                    flag = "  [복구]"
                elif bp and not ap:
                    flag = "  [퇴행!]"
                print(f"    {vid} {title!r}: {b} → {a}{flag}")


if __name__ == "__main__":
    main()
