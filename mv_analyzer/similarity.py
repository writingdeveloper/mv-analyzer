"""분석 feature 공간에서 유사 MV와 이상치를 찾는 CPU 전용 도구."""
from __future__ import annotations

import json
import math
from pathlib import Path

from .extensions import derived_features

COLS = [
    "scene_cuts_per_minute", "scene_median_shot_len_s", "scene_num_scenes",
    "hook_cuts_first_15s", "audio_bpm", "audio_lufs_i",
    "sync_cut_on_beat_ratio", "sync_first_lyric_at_s", "duration_s",
    "tag_avg_characters", "scene_avg_saturation", "scene_avg_brightness",
    "lyrics_lyric_lines_per_min", "ext_scene_brightness_std",
    "ext_scene_saturation_std", "ext_color_change_mean",
    "ext_color_unique_ratio", "ext_lyrics_first_chorus_ratio",
]


def _rows(data_dir):
    out = []
    for p in Path(data_dir).glob("*/features.json"):
        try:
            row = json.loads(p.read_text(encoding="utf-8"))
            d = p.parent
            scenes = json.loads((d / "scenes.json").read_text(encoding="utf-8")) if (d / "scenes.json").exists() else {}
            lyrics = json.loads((d / "lyrics_lines.json").read_text(encoding="utf-8")) if (d / "lyrics_lines.json").exists() else {}
            row.update(derived_features(row, scenes, lyrics))
            out.append(row)
        except (OSError, json.JSONDecodeError):
            pass
    return out


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def _scale(rows):
    stats = {}
    for c in COLS:
        xs = [float(r[c]) for r in rows if isinstance(r.get(c), (int, float))]
        if len(xs) < 3:
            continue
        med = _median(xs)
        mad_scale = _median([abs(x - med) for x in xs]) * 1.4826
        q1 = xs[len(xs) // 4]
        q3 = xs[(3 * len(xs)) // 4]
        iqr_scale = (q3 - q1) / 1.349 if q3 > q1 else 0.0
        range_floor = (max(xs) - min(xs)) / 20.0
        scale = max(mad_scale, iqr_scale, range_floor, 1e-9)
        stats[c] = (med, scale)
    return stats


def _distance(a, b, stats):
    ds = []
    for c, (_, scale) in stats.items():
        x, y = a.get(c), b.get(c)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            ds.append(((float(x) - float(y)) / scale) ** 2)
    return math.sqrt(sum(ds) / len(ds)) if ds else math.inf


def similar(video_id, data_dir="data", limit=10):
    rows = _rows(data_dir)
    target = {r.get("video_id"): r for r in rows}.get(video_id)
    if not target:
        return []
    stats = _scale(rows)
    scored = []
    for r in rows:
        if r.get("video_id") == video_id:
            continue
        d = _distance(target, r, stats)
        if math.isfinite(d):
            scored.append({
                "video_id": r.get("video_id"), "title": r.get("title"),
                "channel": r.get("channel"), "distance": round(d, 4),
            })
    return sorted(scored, key=lambda x: x["distance"])[:limit]


def outliers(data_dir="data", limit=10):
    rows = _rows(data_dir)
    stats = _scale(rows)
    scored = []
    for r in rows:
        ds = []
        for c, (med, scale) in stats.items():
            x = r.get(c)
            if isinstance(x, (int, float)):
                ds.append(((float(x) - med) / scale) ** 2)
        if ds:
            score = math.sqrt(sum(ds) / len(ds))
            scored.append({
                "video_id": r.get("video_id"), "title": r.get("title"),
                "channel": r.get("channel"), "score": round(score, 4),
            })
    return sorted(scored, key=lambda x: -x["score"])[:limit]


def benchmark(video_id, data_dir="data"):
    """각 수치 feature가 전체 코퍼스에서 어느 백분위인지 반환."""
    rows = _rows(data_dir)
    target = {r.get("video_id"): r for r in rows}.get(video_id)
    if not target:
        return []
    out = []
    for c in COLS:
        x = target.get(c)
        xs = sorted(float(r[c]) for r in rows if isinstance(r.get(c), (int, float)))
        if not isinstance(x, (int, float)) or len(xs) < 2:
            continue
        below = sum(v < float(x) for v in xs)
        equal = sum(v == float(x) for v in xs)
        pct = 100.0 * (below + 0.5 * equal) / len(xs)
        out.append({"feature": c, "value": x, "percentile": round(pct, 1), "n": len(xs)})
    return out
