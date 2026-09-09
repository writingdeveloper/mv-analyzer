"""ASR 워커: demucs 보컬 분리 + faster-whisper 전사.

별도 프로세스로 실행해 종료 시 VRAM을 완전 반환한다
(GPU 단계 동시 적재 금지 — 16GB 한계, Ollama VLM과 순차 실행).

usage: python -m mv_analyzer.asr_worker <audio.wav> <out.json> [--lang ja]
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

from .config import ASR_CONDITION_ON_PREVIOUS_TEXT, ASR_VAD_FILTER, WHISPER_MODEL


def separate_vocals(audio_path, tmp_dir):
    """demucs htdemucs 2-stem 보컬 분리 → vocals.wav 경로 반환."""
    proc = subprocess.run(
        [sys.executable, "-m", "demucs.separate", "--two-stems", "vocals",
         "-n", "htdemucs", "-o", tmp_dir, audio_path],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"demucs 실패(rc={proc.returncode}): {proc.stderr[-500:]}")
    name = os.path.splitext(os.path.basename(audio_path))[0]
    vocals = os.path.join(tmp_dir, "htdemucs", name, "vocals.wav")
    if not os.path.exists(vocals):
        raise RuntimeError(f"demucs 산출물 없음: {vocals}")
    return vocals


def transcribe(vocals_path, lang):
    """faster-whisper 전사. CUDA 실패 시 CPU int8 폴백."""
    from faster_whisper import WhisperModel
    try:
        model = WhisperModel(WHISPER_MODEL, device="cuda",
                             compute_type="float16")
        device = "cuda"
    except Exception as e:
        print(f"CUDA 초기화 실패 → CPU int8 폴백: {e}", file=sys.stderr)
        model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        device = "cpu"
    segments, info = model.transcribe(vocals_path, language=lang,
                                      vad_filter=ASR_VAD_FILTER,
                                      condition_on_previous_text=ASR_CONDITION_ON_PREVIOUS_TEXT)
    segs = [{"start": round(s.start, 2), "end": round(s.end, 2),
             "text": s.text.strip()} for s in segments if s.text.strip()]
    return segs, device


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("out_json")
    ap.add_argument("--lang", default="ja")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        vocals = separate_vocals(args.audio, tmp)
        segs, device = transcribe(vocals, args.lang)

    tmp_path = args.out_json + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump({"lang": args.lang, "device": device, "segments": segs},
                  f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, args.out_json)
    print(f"ASR 완료: {len(segs)} 세그먼트 ({device}) → {args.out_json}")


if __name__ == "__main__":
    sys.exit(main())
