"""DuckDB 캐시 freshness 추적.

JSON 산출물이 source of truth다. DB 옆 sidecar에는 데이터/파생 코드 fingerprint만
저장하며, 검색 전 비교해 stale DB를 자동 재생성할 수 있다.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

VIDEO_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")
INDEX_SCHEMA_VERSION = 1
SOURCE_FILES = ("features.json", "lyrics_lines.json", "scenes.json", "scene_tags.json")


def meta_path(db_path):
    return Path(str(db_path) + ".meta.json")


def _video_dirs(data_dir):
    root = Path(data_dir)
    if not root.exists():
        return []
    return [d for d in sorted(root.iterdir())
            if d.is_dir() and VIDEO_ID_RE.fullmatch(d.name)]


def source_signature(data_dir="data"):
    h = hashlib.sha256()
    h.update(f"index-schema={INDEX_SCHEMA_VERSION}\n".encode())
    here = Path(__file__).parent
    for code in (here / "index.py", here / "extensions.py", Path(__file__)):
        h.update(code.name.encode())
        h.update(code.read_bytes())
    for d in _video_dirs(data_dir):
        for name in SOURCE_FILES:
            p = d / name
            if not p.exists():
                continue
            st = p.stat()
            h.update(f"{d.name}/{name}\0{st.st_size}\0{st.st_mtime_ns}\n".encode())
    return h.hexdigest()[:24]


def read_meta(db_path):
    p = meta_path(db_path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def clear_meta(db_path):
    meta_path(db_path).unlink(missing_ok=True)


def write_meta(data_dir, db_path, signature):
    p = meta_path(db_path)
    obj = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "source_signature": signature,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    tmp = Path(str(p) + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def index_status(data_dir="data", db_path="work/mv_analyzer.duckdb"):
    db = Path(db_path)
    expected = source_signature(data_dir)
    meta = read_meta(db_path)
    actual = meta.get("source_signature")
    schema = meta.get("schema_version")
    exists = db.exists()
    fresh = bool(exists and actual == expected and schema == INDEX_SCHEMA_VERSION)
    reason = "fresh" if fresh else (
        "missing" if not exists else
        "legacy_or_invalid" if not meta else
        "schema_changed" if schema != INDEX_SCHEMA_VERSION else
        "source_changed"
    )
    return {
        "exists": exists,
        "fresh": fresh,
        "reason": reason,
        "expected_signature": expected,
        "indexed_signature": actual,
        "built_at": meta.get("built_at"),
    }


def ensure_index(data_dir="data", db_path="work/mv_analyzer.duckdb"):
    status = index_status(data_dir, db_path)
    if status["fresh"]:
        return {**status, "rebuilt": False, "counts": None}
    from .index import build_index
    counts = None
    for _ in range(2):
        counts = build_index(data_dir, db_path)
        status = index_status(data_dir, db_path)
        if status["fresh"]:
            return {**status, "rebuilt": True, "counts": counts}
    raise RuntimeError("index source changed repeatedly during rebuild")
