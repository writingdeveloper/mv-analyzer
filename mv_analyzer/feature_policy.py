"""정식 통계 분석 feature 정책과 입력 QA.

실험 feature(ext_*, motion_*)는 탐색/인덱스에는 쓸 수 있지만 기존 P5 가설검정에
자동 포함하지 않는다. 정식 도입은 별도 사전등록/신뢰성 게이트 후 allowlist 변경.
"""
from __future__ import annotations

import math
from collections import Counter

P5_NUMERIC = [
    "duration_s", "scene_num_scenes", "scene_avg_shot_len_s",
    "scene_median_shot_len_s", "scene_min_shot_len_s", "scene_max_shot_len_s",
    "scene_cuts_per_minute", "scene_avg_brightness", "scene_avg_saturation",
    "audio_bpm", "audio_rms_mean", "audio_rms_std",
    "audio_spectral_centroid_hz", "audio_onsets_per_sec",
    "audio_peak_energy_ratio", "audio_lufs_i", "audio_lra_lu",
    "tag_closeup_ratio", "tag_wide_ratio", "tag_avg_characters",
    "tag_lyrics_text_ratio", "lyrics_n_lyric_lines", "lyrics_lyric_lines_per_min",
    "lyrics_first_lyric_at_s", "lyrics_first_vocal_at_s", "lyrics_text_frame_ratio",
    "thumb_brightness", "thumb_saturation", "thumb_num_characters",
    "title_len", "title_bracket_segments", "title_exclaim_count",
    "sync_cut_beat_offset_med_s", "sync_cut_on_beat_ratio",
    "sync_cut_accel_at_peak", "sync_first_cut_s", "sync_beats_per_cut",
    "hook_cuts_first_15s", "hook_energy_first_10s_ratio", "upload_hour",
]
P5_BINARY = [
    "title_has_emoji", "title_has_mv_mark", "was_premiere", "has_nico_link",
    "lyrics_has_hardsub", "thumb_has_text",
]
P5_CATEGORICAL = [
    "tag_mood_top", "thumb_mood", "lyrics_topic_1", "lyrics_sentiment",
    "lyrics_addressee", "lyrics_source", "audio_key", "upload_weekday",
]
P5_CONFOUNDERS = ["subscriber_count", "channel_video_count", "upload_date"]
EXPERIMENTAL_PREFIXES = ("ext_", "motion_")


def audit_rows(rows, min_group_n=10):
    result = {
        "n_rows": len(rows),
        "groups": {},
        "errors": [],
        "warnings": [],
        "missing_formal_columns": [],
        "constant_numeric": [],
        "low_coverage_numeric": [],
        "nonfinite_numeric": [],
        "experimental_columns": [],
    }
    if not rows:
        result["errors"].append("table is empty")
        return result

    groups = Counter(str(r.get("group")) for r in rows if r.get("group") is not None)
    result["groups"] = dict(groups)
    for name in ("top", "bottom"):
        if groups.get(name, 0) < min_group_n:
            result["errors"].append(
                f"group {name!r} has {groups.get(name, 0)} rows; need >= {min_group_n}")

    keys = set().union(*(r.keys() for r in rows))
    formal = set(P5_NUMERIC + P5_BINARY + P5_CATEGORICAL)
    result["missing_formal_columns"] = sorted(formal - keys)
    if result["missing_formal_columns"]:
        result["warnings"].append(
            f"{len(result['missing_formal_columns'])} formal columns absent from table")
    result["experimental_columns"] = sorted(
        k for k in keys if k.startswith(EXPERIMENTAL_PREFIXES))

    for col in P5_NUMERIC:
        vals = [r.get(col) for r in rows if isinstance(r.get(col), (int, float))]
        bad = [v for v in vals if isinstance(v, float) and not math.isfinite(v)]
        if bad:
            result["nonfinite_numeric"].append(col)
            result["errors"].append(f"non-finite values in {col}")
            continue
        finite = [float(v) for v in vals if not isinstance(v, float) or math.isfinite(v)]
        if finite and len(set(finite)) <= 1:
            result["constant_numeric"].append(col)
        for group in ("top", "bottom"):
            n = sum(1 for r in rows
                    if r.get("group") == group and isinstance(r.get(col), (int, float))
                    and not (isinstance(r.get(col), float) and not math.isfinite(r.get(col))))
            if n < min_group_n:
                result["low_coverage_numeric"].append({"feature": col, "group": group, "n": n})
    if result["constant_numeric"]:
        result["warnings"].append(
            f"{len(result['constant_numeric'])} formal numeric columns are constant")
    if result["low_coverage_numeric"]:
        result["warnings"].append(
            f"{len(result['low_coverage_numeric'])} feature/group pairs are below coverage gate")
    return result


def audit_ok(audit):
    return not audit["errors"]
