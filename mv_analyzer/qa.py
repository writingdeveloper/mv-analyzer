"""GPU를 사용하지 않는 데이터/프로젝트 QA."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

from . import provenance

CORE = ["features.json", "scenes.json", "audio_features.json", "loudness.json",
        "scene_tags.json", "lyrics_lines.json", "sync_features.json",
        "thumb_tags.json", "meta.json"]
VIDEO_ID_RE = re.compile(r"[A-Za-z0-9_-]{11}")


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _semantic_checks(d: Path, loaded: dict):
    errors = []
    warnings = []
    f = loaded.get("features.json") or {}
    scenes_obj = loaded.get("scenes.json") or {}
    tags = loaded.get("scene_tags.json") or []
    lyrics = loaded.get("lyrics_lines.json") or {}
    audio = loaded.get("audio_features.json") or {}

    if f.get("video_id") and f.get("video_id") != d.name:
        errors.append(f"video_id mismatch: folder={d.name} features={f.get('video_id')}")

    scenes = scenes_obj.get("scenes") or []
    summary = scenes_obj.get("summary") or {}
    if summary.get("num_scenes") is not None and summary.get("num_scenes") != len(scenes):
        errors.append(f"scene count mismatch: summary={summary.get('num_scenes')} rows={len(scenes)}")
    if isinstance(tags, list) and scenes and len(tags) != len(scenes):
        errors.append(f"scene/tag count mismatch: scenes={len(scenes)} tags={len(tags)}")

    missing_kf = []
    for sc in scenes:
        name = sc.get("keyframe")
        if name and not (d / "keyframes" / name).exists():
            missing_kf.append(name)
    if missing_kf:
        errors.append(f"missing keyframes: {len(missing_kf)}")

    durations = []
    for label, value in [
        ("features", f.get("duration_s")),
        ("scenes", summary.get("duration_s")),
        ("audio", audio.get("duration_s")),
    ]:
        if isinstance(value, (int, float)):
            durations.append((label, float(value)))
    if len(durations) >= 2:
        vals = [v for _, v in durations]
        if max(vals) - min(vals) > 1.5:
            errors.append("duration mismatch: " + ", ".join(f"{k}={v}" for k, v in durations))

    source = lyrics.get("source")
    lines = lyrics.get("lines") or []
    if source is None and lines:
        warnings.append(f"lyrics source missing with {len(lines)} lines")
    if source and not lines:
        warnings.append(f"lyrics source={source} but no lines")

    bad_numbers = []
    for k, v in f.items():
        if isinstance(v, float) and not math.isfinite(v):
            bad_numbers.append(k)
    if bad_numbers:
        errors.append("non-finite feature values: " + ", ".join(bad_numbers[:10]))
    return errors, warnings


def scan_data(data_dir="data"):
    root = Path(data_dir)
    result = {
        "directories": 0, "complete": 0, "partial": 0,
        "json_errors": [], "semantic_errors": [], "warnings": [],
        "missing": {}, "feature_widths": {}, "feature_schema_variants": {},
        "manifest_count": 0, "stale_artifacts": [], "tmp_files": [],
    }
    if not root.exists():
        return result
    missing = Counter()
    widths = Counter()
    schemas = {}
    dirs = [p for p in root.iterdir() if p.is_dir() and VIDEO_ID_RE.fullmatch(p.name)]
    result["directories"] = len(dirs)
    for d in dirs:
        absent = [x for x in CORE if not (d / x).exists()]
        if absent:
            result["partial"] += 1
            for x in absent:
                missing[x] += 1
        else:
            result["complete"] += 1
        manifest = provenance.load_manifest(d)
        if manifest:
            result["manifest_count"] += 1
            for artifact in (manifest.get("artifacts") or {}):
                if provenance.artifact_is_stale(d, artifact):
                    result["stale_artifacts"].append({"video_id": d.name, "artifact": artifact})
        for p in d.glob("*.tmp"):
            result["tmp_files"].append(str(p))

        loaded = {}
        for name in CORE:
            p = d / name
            if not p.exists():
                continue
            try:
                obj = _read_json(p)
                loaded[name] = obj
                if name == "features.json" and isinstance(obj, dict):
                    widths[len(obj)] += 1
                    keys = tuple(sorted(obj.keys()))
                    sig = hashlib.sha256("\n".join(keys).encode()).hexdigest()[:12]
                    item = schemas.setdefault(sig, {"count": 0, "n_keys": len(keys), "sample_video_id": d.name})
                    item["count"] += 1
            except (OSError, json.JSONDecodeError) as e:
                result["json_errors"].append({"video_id": d.name, "file": name, "error": str(e)})
        if not absent and not any(x["video_id"] == d.name for x in result["json_errors"]):
            errors, warnings = _semantic_checks(d, loaded)
            result["semantic_errors"].extend({"video_id": d.name, "error": e} for e in errors)
            result["warnings"].extend({"video_id": d.name, "warning": w} for w in warnings)

    result["missing"] = dict(missing)
    result["feature_widths"] = dict(sorted(widths.items()))
    result["feature_schema_variants"] = schemas
    return result


def ok(scan):
    return (not scan["json_errors"] and not scan["semantic_errors"]
            and not scan["tmp_files"] and len(scan["feature_schema_variants"]) <= 1)
