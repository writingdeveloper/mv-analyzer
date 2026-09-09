"""MV 1편 전체 분석 CLI: python analyze.py <URL> [--out data] [--lang ja|ko] [--skip-vlm]"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from mv_analyzer import download, scenes as scn, audio as aud, sync as syn
from mv_analyzer import provenance
from mv_analyzer.analyze_report import build_analyze_report, write_analyze_report
from mv_analyzer.resources import ensure_gpu_available
from mv_analyzer.lyrics import HARDSUB_MIN_RATIO, asr_to_lines, clean_lyrics
from mv_analyzer.packaging import analyze_thumbnail, title_features
from mv_analyzer.vlm import (LYRICS_ADDRESSEES, LYRICS_PROMPT,
                             LYRICS_SENTIMENTS, LYRICS_TOPICS, SCENE_PROMPT,
                             SUB_PROMPT, ask, ask_text, parse_json, unload)


ROOT = Path(__file__).resolve().parent


def save(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _exists_nonempty(path):
    return os.path.exists(path) and os.path.getsize(path) > 0


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _json_stage_needs_run(base, name, refresh_stale=False):
    path = os.path.join(base, name)
    if not os.path.exists(path):
        return True
    if refresh_stale and provenance.artifact_is_stale(base, name):
        return True
    try:
        load(path)
    except (OSError, json.JSONDecodeError):
        return True
    return False


def step(base, name, fn, refresh_stale=False):
    """산출물이 있으면 재사용. 명시 요청 시 fingerprint가 stale인 것만 갱신."""
    path = os.path.join(base, name)
    if os.path.exists(path) and not (refresh_stale and provenance.artifact_is_stale(base, name)):
        try:
            result = load(path)
        except (OSError, json.JSONDecodeError):
            print(f"[repair] {name} (손상된 JSON → 재생성)", flush=True)
        else:
            print(f"[skip] {name} (기존 산출물 사용)", flush=True)
            return result
    if os.path.exists(path):
        print(f"[stale] {name} (fingerprint 변경 → 재생성)", flush=True)
    print(f"[run ] {name} ...", flush=True)
    result = fn()
    save(path, result)
    return result


def build_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default="data")
    ap.add_argument("--lang", default="ja", choices=["ja", "ko"])
    ap.add_argument("--skip-vlm", action="store_true",
                    help="GPU 단계 생략(파이프라인 자체 점검용)")
    ap.add_argument("--refresh-stale", action="store_true",
                    help="manifest fingerprint가 달라진 기존 산출물만 재생성 (legacy 캐시는 보호)")
    ap.add_argument("--force-gpu-busy", action="store_true",
                    help="GPU busy guard 우회 (다른 세션과 충돌 가능 — 명시적 사용만)")
    ap.add_argument("--web-report",
                    help="완료된 분석을 공개 안전 JSON report로 내보낼 경로")
    ap.add_argument("--benchmark-domain", default="all",
                    choices=["all", "vocaloid", "kpop"],
                    help="Web report reference corpus 범위")
    return ap


def write_web_report_if_requested(args, row, base=None):
    if not args.web_report:
        return
    manifest_path = Path(base) / "analysis_manifest.json" if base else None
    manifest = load(str(manifest_path)) if manifest_path and manifest_path.exists() else None
    kwargs = {"domain": args.benchmark_domain}
    if manifest is not None:
        kwargs["measurement_manifest"] = manifest
    report = build_analyze_report(ROOT, row, **kwargs)
    destination = Path(args.web_report)
    write_analyze_report(destination, report)
    print(f"Web report → {destination}", flush=True)


def write_existing_web_report_or_fail(args, base):
    if not args.web_report:
        return
    features_path = Path(base) / "features.json"
    if not features_path.exists() or features_path.stat().st_size == 0:
        raise SystemExit("--web-report with --skip-vlm requires a complete features.json")
    try:
        row = load(str(features_path))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit("--web-report with --skip-vlm requires a complete features.json") from exc
    write_web_report_if_requested(args, row, base)


def main():
    args = build_parser().parse_args()
    run_started = time.time()

    meta = download.fetch_meta(args.url)
    base = os.path.join(args.out, meta["id"])
    os.makedirs(base, exist_ok=True)
    save(os.path.join(base, "meta_full.json"), meta)
    slim = download.slim_meta(meta)
    save(os.path.join(base, "meta.json"), slim)
    print(f"== {slim['title']} ({slim['video_id']}) ==", flush=True)

    video = os.path.join(base, "video.mp4")
    if not _exists_nonempty(video):
        print("[run ] video 다운로드 ...", flush=True)
        download.download_video(args.url, video)
    wav = os.path.join(base, "audio.wav")
    if not _exists_nonempty(wav):
        download.extract_audio(video, wav)
    thumb_jpg = os.path.join(base, "thumbnail.jpg")
    if not os.path.exists(thumb_jpg):
        download.download_thumbnail(meta, thumb_jpg)
    subdir = os.path.join(base, "subframes")
    if not os.path.isdir(subdir) or not os.listdir(subdir):
        download.extract_subframes(video, subdir)

    scenes = step(base, "scenes.json",
                  lambda: scn.analyze_scenes(video, os.path.join(base, "keyframes")), args.refresh_stale)
    audio = step(base, "audio_features.json", lambda: aud.analyze_audio(wav), args.refresh_stale)
    loudness = step(base, "loudness.json", lambda: aud.measure_loudness(wav), args.refresh_stale)

    if args.skip_vlm:
        provenance.write_analysis_manifest(
            base, lang=args.lang, run_started_s=run_started,
            options={"skip_vlm": True, "refresh_stale": args.refresh_stale, "force_gpu_busy": args.force_gpu_busy})
        print("[skip] VLM/ASR 단계 전체 (--skip-vlm)", flush=True)
        write_existing_web_report_or_fail(args, base)
        return

    # GPU 산출물 중 실제로 재생성이 필요한 것이 있을 때만 공유 GPU busy guard를 적용한다.
    gpu_stage_names = [
        f"lyrics_asr.{args.lang}.json", "scene_tags.json", "lyrics_ocr.json",
        "thumb_tags.json", f"lyrics_tags.{args.lang}.json",
    ]
    if any(_json_stage_needs_run(base, name, args.refresh_stale) for name in gpu_stage_names):
        ensure_gpu_available(force=args.force_gpu_busy)

    # ASR (GPU) — 별도 프로세스로 실행해 종료 시 VRAM 반환.
    # VLM(Ollama)보다 먼저 실행해 동시 적재를 구조적으로 방지 (16GB 한계).
    asr_path = os.path.join(base, f"lyrics_asr.{args.lang}.json")
    if not _json_stage_needs_run(base, os.path.basename(asr_path), args.refresh_stale):
        asr = load(asr_path)
        print(f"[skip] lyrics_asr.{args.lang}.json (기존 산출물 사용)", flush=True)
    else:
        print(f"[run ] lyrics_asr.{args.lang}.json (demucs+whisper) ...", flush=True)
        unload()  # busy guard 통과 뒤에만 실행 — 다른 세션의 GPU 작업 보호
        cmd = [sys.executable, "-m", "mv_analyzer.asr_worker", wav, asr_path, "--lang", args.lang]
        subprocess.run(cmd, check=True)
        asr = load(asr_path)

    def tag_scenes():
        files = sorted(glob.glob(os.path.join(base, "keyframes", "*.jpg")))
        out = []
        for i, fp in enumerate(files):
            tag = parse_json(ask(fp, SCENE_PROMPT))
            tag["keyframe"] = os.path.basename(fp)
            out.append(tag)
            print(f"  [{i + 1}/{len(files)}] {os.path.basename(fp)}", flush=True)
        return out

    def ocr_subs():
        files = sorted(glob.glob(os.path.join(subdir, "*.jpg")))
        out = []
        for i, fp in enumerate(files):
            t = (int(re.search(r"(\d+)", os.path.basename(fp)).group()) - 1) * 2
            text = ask(fp, SUB_PROMPT)
            if text.upper() != "NONE":
                out.append({"t_s": t, "text": text})
            print(f"  [{i + 1}/{len(files)}] t={t}s", flush=True)
        return out

    # GPU 단계는 반드시 순차 실행 (16GB VRAM)
    scene_tags = step(base, "scene_tags.json", tag_scenes, args.refresh_stale)
    ocr = step(base, "lyrics_ocr.json", ocr_subs, args.refresh_stale)
    thumb = step(base, "thumb_tags.json", lambda: analyze_thumbnail(thumb_jpg), args.refresh_stale)

    ocr_stats = {"text_frames": len(ocr),
                 "total_frames": len(glob.glob(os.path.join(subdir, "*.jpg")))}
    has_hardsub = (ocr_stats["total_frames"] > 0
                   and ocr_stats["text_frames"] / ocr_stats["total_frames"]
                   >= HARDSUB_MIN_RATIO)

    # 가사 소스 선택: 하드자막 OCR이 충분(≥8라인)하면 OCR 우선(사람이 쓴 가사),
    # 아니면 ASR. 무자막 판정 시 OCR은 환각 오염 차단을 위해 아예 배제.
    ocr_lines = clean_lyrics(ocr, lang=args.lang) if has_hardsub else []
    asr_lines = asr_to_lines(asr.get("segments") or [], lang=args.lang)
    if len(ocr_lines) >= 8:
        lyric_lines, lyrics_source = ocr_lines, "ocr"
    elif asr_lines:
        lyric_lines, lyrics_source = asr_lines, "asr"
    else:
        lyric_lines, lyrics_source = [], None
    first_vocal_at_s = asr_lines[0]["t_s"] if asr_lines else None

    def tag_lyrics():
        # 저커버리지(부분 검출·환각 조각)로는 주제 추정 불가 — 8라인 미만이면 태깅 생략
        if len(lyric_lines) < 8:
            return {"topics": [], "sentiment": None, "addressee": None}
        text = "\n".join(l["line"] for l in lyric_lines)[:2000]
        raw = parse_json(ask_text(LYRICS_PROMPT + text))
        # 어휘 검증 — 목록 밖 값(플레이스홀더 반향 등)은 버린다
        return {
            "topics": [t for t in (raw.get("topics") or [])
                       if t in LYRICS_TOPICS][:2],
            "sentiment": raw.get("sentiment")
            if raw.get("sentiment") in LYRICS_SENTIMENTS else None,
            "addressee": raw.get("addressee")
            if raw.get("addressee") in LYRICS_ADDRESSEES else None,
        }

    # 캐시 파일명에 lang 포함 — ja/ko 재실행이 충돌하지 않도록
    lyrics_tags = step(base, f"lyrics_tags.{args.lang}.json", tag_lyrics, args.refresh_stale)

    # 저렴한 순수 파생 단계는 캐시하지 않는다 — 상류 산출물·옵션(--lang) 변경을 항상 반영.
    # 파일은 점검용으로 저장만 하고, 다음 실행에서 읽지 않는다.
    save(os.path.join(base, "lyrics_lines.json"),
         {"lang": args.lang, "source": lyrics_source,
          "has_hardsub": has_hardsub, "lines": lyric_lines})
    sync = syn.sync_features(scenes, audio, lyric_lines)
    save(os.path.join(base, "sync_features.json"), sync)

    from mv_analyzer.features import build_row
    row = build_row(slim, scenes, audio, loudness, scene_tags, lyric_lines,
                    thumb, title_features(slim["title"] or ""), sync,
                    lang=args.lang, lyrics_tags=lyrics_tags, ocr_stats=ocr_stats,
                    lyrics_source=lyrics_source,
                    first_vocal_at_s=first_vocal_at_s)
    save(os.path.join(base, "features.json"), row)
    provenance.write_analysis_manifest(
        base, lang=args.lang, run_started_s=run_started,
        options={"skip_vlm": False, "refresh_stale": args.refresh_stale, "force_gpu_busy": args.force_gpu_busy})
    write_web_report_if_requested(args, row, base)
    print(f"완료 → {os.path.join(base, 'features.json')} ({len(row)} 컬럼)", flush=True)


if __name__ == "__main__":
    sys.exit(main())
