"""실행 환경 점검. 모델 추론/CUDA 작업은 하지 않는다."""
from __future__ import annotations

import importlib.util
import shutil
import sys
import urllib.request


def inspect_environment(check_services=False):
    checks = []

    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    add("python>=3.12", sys.version_info >= (3, 12), sys.version.split()[0])
    for exe in ["ffmpeg", "git", "deno", "ollama"]:
        path = shutil.which(exe)
        add(exe, bool(path), path or "not found")
    for mod in ["yt_dlp", "scenedetect", "cv2", "librosa", "duckdb"]:
        add(mod, importlib.util.find_spec(mod) is not None, "python module")
    if check_services:
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1) as r:
                add("ollama-api", r.status == 200, "health endpoint only; no inference")
        except Exception as e:
            add("ollama-api", False, str(e))
    return checks
