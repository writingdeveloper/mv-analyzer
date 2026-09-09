"""YouTube 자막 트랙 가용성 스캔 — 네트워크만 쓰고 GPU·모델은 건드리지 않는다.

가사 출처 후보로서 '원곡 언어 수동 자막 트랙'이 코퍼스에 얼마나 있는지 재는 조사용이다.
측정 파이프라인을 바꾸지 않으며(가사 출처는 여전히 OCR/ASR), 결과는 work/ 아래 JSONL에
이어쓰기로 쌓인다. 자막 본문은 받지 않고 트랙 목록(언어 코드)만 기록한다.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

NON_LYRIC_TRACKS = {"live_chat"}  # 자막이 아닌 트랙


def _base_lang(code):
    return str(code or "").split("-")[0].lower()


def summarize_tracks(info, lyrics_lang=None):
    """yt-dlp info dict → 트랙 요약. 원곡 언어(lyrics_lang) 트랙 존재 여부를 따로 표시."""
    manual = sorted(k for k in (info.get("subtitles") or {}) if k not in NON_LYRIC_TRACKS)
    auto = sorted(k for k in (info.get("automatic_captions") or {}) if k not in NON_LYRIC_TRACKS)
    lang = _base_lang(lyrics_lang) if lyrics_lang else None
    return {
        "manual_langs": manual,
        "n_manual": len(manual),
        "has_original_lang_track": bool(lang) and any(_base_lang(c) == lang for c in manual),
        "has_auto": bool(auto),
        "auto_has_original_lang": bool(lang) and any(_base_lang(c) == lang for c in auto),
    }


def fetch_info(video_id, *, sleep_s=0.0):
    """자막 메타데이터만 조회 (다운로드 없음)."""
    import yt_dlp
    opts = {"skip_download": True, "quiet": True, "no_warnings": True,
            "writesubtitles": False, "writeautomaticsub": False}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    if sleep_s:
        time.sleep(sleep_s)
    return info


def _existing_ids(out_path):
    p = Path(out_path)
    if not p.exists():
        return set()
    ids = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.add(json.loads(line).get("video_id"))
    return ids


def scan_corpus(data_dir="data", out_path="work/caption_scan.jsonl", *, limit=None,
                sleep_s=1.0, fetch=fetch_info, log=None):
    """features.json이 있는 영상 전부를 스캔해 JSONL로 이어쓴다 (이어하기 지원)."""
    root = Path(data_dir)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = _existing_ids(out)
    ids = sorted(v for v in os.listdir(root) if (root / v / "features.json").exists()) if root.exists() else []
    scanned = skipped = failed = 0
    for vid in ids:
        if vid in done:
            skipped += 1
            continue
        if limit is not None and scanned >= limit:
            break
        f = json.loads((root / vid / "features.json").read_text(encoding="utf-8"))
        row = {"video_id": vid, "title": f.get("title"), "lyrics_lang": f.get("lyrics_lang"),
               "lyrics_source": f.get("lyrics_source")}
        try:
            info = fetch(vid, sleep_s=sleep_s)
            row.update(summarize_tracks(info, f.get("lyrics_lang")))
            row["error"] = None
        except Exception as exc:  # 네트워크/추출 실패는 기록하고 계속
            row.update({"manual_langs": [], "n_manual": 0, "has_original_lang_track": False,
                        "has_auto": False, "auto_has_original_lang": False, "error": str(exc)[:200]})
            failed += 1
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        scanned += 1
        if log:
            log(f"{vid} manual={row['manual_langs'] or '-'} orig={row['has_original_lang_track']} "
                f"[{row['lyrics_lang']}/{row['lyrics_source']}]")
    return {"scanned": scanned, "skipped": skipped, "failed": failed, "out": str(out)}


def summarize_scan(rows):
    """스캔 결과 집계 — 가사 결손 복구 가능 편수, ASR→자막 승급 가능 편수 등."""
    rows = [r for r in rows if not r.get("error")]
    n = len(rows)
    has_manual = sum(1 for r in rows if r.get("n_manual"))
    has_orig = sum(1 for r in rows if r.get("has_original_lang_track"))
    by_source = {}
    for r in rows:
        src = str(r.get("lyrics_source"))
        d = by_source.setdefault(src, {"n": 0, "with_original_track": 0})
        d["n"] += 1
        d["with_original_track"] += 1 if r.get("has_original_lang_track") else 0
    recoverable = [r["video_id"] for r in rows
                   if not r.get("lyrics_source") and r.get("has_original_lang_track")]
    asr_upgradable = [r["video_id"] for r in rows
                      if r.get("lyrics_source") == "asr" and r.get("has_original_lang_track")]
    return {"n": n, "with_manual_track": has_manual, "with_original_lang_track": has_orig,
            "by_lyrics_source": by_source, "missing_lyrics_recoverable": recoverable,
            "asr_upgradable": asr_upgradable}
