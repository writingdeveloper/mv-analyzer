"""분석 산출물의 재현성 메타데이터와 단계별 fingerprint."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

PIPELINE_SCHEMA_VERSION = 2
ROOT = Path(__file__).resolve().parents[1]

STAGE_FILES = {
    "scenes.json": ["mv_analyzer/scenes.py", "mv_analyzer/config.py"],
    "audio_features.json": ["mv_analyzer/audio.py"],
    "loudness.json": ["mv_analyzer/audio.py"],
    "lyrics_asr": ["mv_analyzer/asr_worker.py", "mv_analyzer/lyrics.py", "mv_analyzer/config.py"],
    "scene_tags.json": ["mv_analyzer/vlm.py", "mv_analyzer/config.py"],
    "lyrics_ocr.json": ["mv_analyzer/vlm.py", "mv_analyzer/lyrics.py", "mv_analyzer/config.py"],
    "thumb_tags.json": ["mv_analyzer/vlm.py", "mv_analyzer/packaging.py", "mv_analyzer/config.py"],
    "lyrics_tags": ["mv_analyzer/vlm.py", "mv_analyzer/lyrics.py", "mv_analyzer/config.py"],
    "sync_features.json": ["mv_analyzer/sync.py"],
    "features.json": ["mv_analyzer/features.py", "mv_analyzer/sync.py", "mv_analyzer/lyrics.py"],
}


def _stage_key(name: str) -> str:
    if name.startswith("lyrics_asr."):
        return "lyrics_asr"
    if name.startswith("lyrics_tags."):
        return "lyrics_tags"
    return name


def stage_fingerprint(name: str) -> str | None:
    files = STAGE_FILES.get(_stage_key(name))
    if not files:
        return None
    h = hashlib.sha256()
    h.update(f"schema={PIPELINE_SCHEMA_VERSION}\n".encode())
    for rel in files:
        p = ROOT / rel
        h.update(rel.encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            encoding="utf-8", stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def load_manifest(base: str | Path) -> dict | None:
    p = Path(base) / "analysis_manifest.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def artifact_is_stale(base: str | Path, name: str) -> bool:
    """기존 manifest에 fingerprint가 있는 산출물만 stale 여부를 판정한다.

    legacy 산출물은 잘못 재처리하지 않기 위해 자동 stale 취급하지 않는다.
    """
    manifest = load_manifest(base)
    if not manifest:
        return False
    item = (manifest.get("artifacts") or {}).get(name) or {}
    old = item.get("fingerprint")
    current = stage_fingerprint(name)
    return bool(old and current and old != current)



def runtime_info():
    packages = {}
    for name in [
        "yt-dlp", "scenedetect", "opencv-python", "opencv-python-headless",
        "librosa", "numpy", "demucs", "faster-whisper", "duckdb",
    ]:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    # 모델/측정 상수는 코드 fingerprint에도 들어가지만 사람이 읽을 수 있게 중복 기록한다.
    from .config import SCENE_THRESHOLD, VLM_MODEL, WHISPER_MODEL
    return {
        "python": platform.python_version(),
        "packages": packages,
        "models": {"vlm": VLM_MODEL, "asr": WHISPER_MODEL},
        "scene_threshold": SCENE_THRESHOLD,
    }

def write_analysis_manifest(base: str | Path, *, lang: str, run_started_s: float,
                            options: dict | None = None) -> dict:
    base = Path(base)
    artifacts = {}
    for p in sorted(base.glob("*.json")):
        if p.name == "analysis_manifest.json" or p.name.endswith(".tmp"):
            continue
        generated = p.stat().st_mtime >= run_started_s - 1.0
        artifacts[p.name] = {
            "status": "generated" if generated else "legacy_reused",
            "fingerprint": stage_fingerprint(p.name) if generated else None,
            "size_bytes": p.stat().st_size,
        }
    obj = {
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "runtime": runtime_info(),
        "lang": lang,
        "options": options or {},
        "artifacts": artifacts,
    }
    tmp = base / "analysis_manifest.json.tmp"
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, base / "analysis_manifest.json")
    return obj
