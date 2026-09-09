"""기존 산출물만으로 계산하는 결정론적 확장 feature (GPU/미디어 재처리 없음)."""
from __future__ import annotations

import math
import statistics

from .lyrics_structure import MIN_LINES, first_chorus_s


def _rgb(hex_color):
    if not isinstance(hex_color, str) or len(hex_color) != 7 or not hex_color.startswith("#"):
        return None
    try:
        return tuple(int(hex_color[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    except ValueError:
        return None


def _p90(xs):
    if not xs:
        return None
    ys = sorted(xs)
    idx = min(len(ys) - 1, math.ceil(0.9 * len(ys)) - 1)
    return ys[idx]


def scene_dynamics(scenes_obj):
    scenes = (scenes_obj or {}).get("scenes") or []
    br = [float(s["brightness"]) for s in scenes if isinstance(s.get("brightness"), (int, float))]
    sat = [float(s["saturation"]) for s in scenes if isinstance(s.get("saturation"), (int, float))]
    colors = [c for c in (_rgb(s.get("dominant_color")) for s in scenes) if c]
    changes = []
    for a, b in zip(colors, colors[1:]):
        # RGB unit-cube Euclidean distance, normalized to [0, 1].
        changes.append(math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))) / math.sqrt(3))
    unique_colors = {s.get("dominant_color") for s in scenes if _rgb(s.get("dominant_color"))}
    return {
        "ext_scene_brightness_std": round(statistics.pstdev(br), 4) if len(br) >= 2 else 0.0 if br else None,
        "ext_scene_saturation_std": round(statistics.pstdev(sat), 4) if len(sat) >= 2 else 0.0 if sat else None,
        "ext_color_change_mean": round(sum(changes) / len(changes), 4) if changes else 0.0 if colors else None,
        "ext_color_change_p90": round(_p90(changes), 4) if changes else 0.0 if colors else None,
        "ext_color_unique_ratio": round(len(unique_colors) / len(colors), 4) if colors else None,
    }


def derived_features(features, scenes_obj, lyrics_obj):
    out = scene_dynamics(scenes_obj)
    lines = (lyrics_obj or {}).get("lines") or []
    chorus = first_chorus_s(lines) if len(lines) >= MIN_LINES else None
    duration = (features or {}).get("duration_s")
    out["ext_lyrics_first_chorus_s"] = chorus
    out["ext_lyrics_first_chorus_ratio"] = (
        round(float(chorus) / float(duration), 4)
        if chorus is not None and isinstance(duration, (int, float)) and duration > 0 else None
    )
    return out
