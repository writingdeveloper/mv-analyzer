"""Public, deterministic Web snapshot builder.

The browser-facing app consumes only JSON produced by this module.  The
exporter deliberately uses tracked research tables and never reads raw local
media, local model endpoints, or arbitrary files from ``data/``.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import os
import re
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import stats as st

from .feature_policy import P5_NUMERIC
from .reference_corpus import load_reference_rows, reference_corpus_public_metadata
from .reliability import load_baseline, load_reference_labels, score_predictions
from .stats import bh_fdr, cliffs_delta

PUBLIC_SCHEMA_VERSION = 1

FEATURE_LABELS_KO = {
    "scene_median_shot_len_s": "샷 길이 중앙값(초)",
    "scene_avg_shot_len_s": "샷 길이 평균(초)",
    "scene_cuts_per_minute": "분당 컷 수",
    "scene_num_scenes": "씬 수",
    "sync_beats_per_cut": "컷당 비트 수",
    "scene_max_shot_len_s": "최장 샷(초)",
    "hook_cuts_first_15s": "첫 15초 컷 수",
    "scene_min_shot_len_s": "최단 샷(초)",
    "tag_avg_characters": "평균 등장인물 수",
    "scene_avg_saturation": "화면 채도",
    "scene_avg_brightness": "화면 밝기",
    "audio_spectral_centroid_hz": "스펙트럼 중심(Hz)",
    "audio_bpm": "BPM",
    "sync_cut_accel_at_peak": "피크 구간 컷 가속",
    "hook_energy_first_10s_ratio": "첫 10초 에너지 비율",
    "thumb_saturation": "썸네일 채도",
    "thumb_brightness": "썸네일 밝기",
    "sync_first_cut_s": "첫 컷 시점(초)",
    "tag_closeup_ratio": "클로즈업 비율",
    "lyrics_first_vocal_at_s": "첫 보컬 시점(초)",
    "audio_rms_mean": "RMS 에너지",
    "audio_lufs_i": "라우드니스(LUFS)",
    "audio_lra_lu": "라우드니스 범위(LU)",
    "thumb_num_characters": "썸네일 인물 수",
    "lyrics_lyric_lines_per_min": "분당 가사 라인",
    "lyrics_n_lyric_lines": "가사 라인 수",
    "title_bracket_segments": "제목 괄호 수",
    "audio_rms_std": "에너지 변동",
    "tag_wide_ratio": "와이드샷 비율",
    "sync_cut_on_beat_ratio": "정박 컷 비율",
    "audio_onsets_per_sec": "온셋 밀도(/초)",
    "title_exclaim_count": "제목 느낌표",
    "title_len": "제목 길이",
    "duration_s": "곡 길이(초)",
    "upload_hour": "업로드 시각",
    "lyrics_text_frame_ratio": "자막 프레임 비율",
    "sync_cut_beat_offset_med_s": "컷-비트 오프셋(초)",
    "audio_peak_energy_ratio": "피크 위치(비율)",
    "lyrics_first_lyric_at_s": "첫 가사 시점(초)",
    "tag_lyrics_text_ratio": "가사 텍스트 씬 비율",
    "lyrics_compression_ratio": "가사 압축률",
    "lyrics_title_first_s": "곡명 첫 등장(초)",
    "lyrics_title_count": "곡명 등장 라인 수",
    "lyrics_first_chorus_s": "첫 후렴 도달(초)",
    "sync_cut_on_line_ratio": "컷-가사라인 정렬률",
    "heat_slope_first_30s": "초반 30초 리텐션 기울기",
    "heat_peak_at_ratio": "리플레이 피크 위치(비율)",
    "heat_peak_value": "리플레이 피크 값",
}
FEATURE_LABELS_EN = {
    "scene_median_shot_len_s": "Median shot length (s)",
    "scene_avg_shot_len_s": "Average shot length (s)",
    "scene_cuts_per_minute": "Cuts per minute",
    "scene_num_scenes": "Scene count",
    "sync_beats_per_cut": "Beats per cut",
    "scene_max_shot_len_s": "Longest shot (s)",
    "hook_cuts_first_15s": "Cuts in first 15s",
    "scene_min_shot_len_s": "Shortest shot (s)",
    "tag_avg_characters": "Avg. characters",
    "scene_avg_saturation": "Frame saturation",
    "scene_avg_brightness": "Frame brightness",
    "audio_spectral_centroid_hz": "Spectral centroid (Hz)",
    "audio_bpm": "BPM",
    "sync_cut_accel_at_peak": "Cut acceleration at peak",
    "hook_energy_first_10s_ratio": "First-10s energy ratio",
    "thumb_saturation": "Thumbnail saturation",
    "thumb_brightness": "Thumbnail brightness",
    "sync_first_cut_s": "First cut time (s)",
    "tag_closeup_ratio": "Close-up ratio",
    "lyrics_first_vocal_at_s": "First vocal time (s)",
    "audio_rms_mean": "RMS energy",
    "audio_lufs_i": "Loudness (LUFS)",
    "audio_lra_lu": "Loudness range (LU)",
    "thumb_num_characters": "Thumbnail character count",
    "lyrics_lyric_lines_per_min": "Lyric lines per minute",
    "lyrics_n_lyric_lines": "Lyric line count",
    "title_bracket_segments": "Title bracket segments",
    "audio_rms_std": "Energy variation",
    "tag_wide_ratio": "Wide-shot ratio",
    "sync_cut_on_beat_ratio": "On-beat cut ratio",
    "audio_onsets_per_sec": "Onset density (/s)",
    "title_exclaim_count": "Title exclamation count",
    "title_len": "Title length",
    "duration_s": "Duration (s)",
    "upload_hour": "Upload hour",
    "lyrics_text_frame_ratio": "Text-frame ratio",
    "sync_cut_beat_offset_med_s": "Median cut-beat offset (s)",
    "audio_peak_energy_ratio": "Peak position ratio",
    "lyrics_first_lyric_at_s": "First lyric time (s)",
    "tag_lyrics_text_ratio": "Lyric-text scene ratio",
    "lyrics_compression_ratio": "Lyrics compression ratio",
    "lyrics_title_first_s": "First title appearance (s)",
    "lyrics_title_count": "Title-line count",
    "lyrics_first_chorus_s": "First chorus time (s)",
    "sync_cut_on_line_ratio": "Cut-to-lyric-line alignment",
    "heat_slope_first_30s": "First-30s retention slope",
    "heat_peak_at_ratio": "Replay-peak position ratio",
    "heat_peak_value": "Replay-peak value",
    "thumb_has_text": "Thumbnail has text",
    "was_premiere": "Premiered",
    "lyrics_has_hardsub": "Hard subtitles",
    "has_nico_link": "Niconico link",
    "title_has_mv_mark": "MV marker in title",
    "title_has_emoji": "Emoji in title",
    "tag_mood_top": "Scene mood",
    "thumb_mood": "Thumbnail mood",
    "lyrics_topic_1": "Lyrics topic",
    "lyrics_sentiment": "Lyrics sentiment",
    "lyrics_addressee": "Lyrics addressee",
    "lyrics_source": "Lyrics source",
    "view_per_sub": "Views / subscribers",
}


def _labels(feature: str, ko: str | None = None) -> dict[str, str]:
    ko_label = ko or FEATURE_LABELS_KO.get(feature) or PUBLIC_BINARY.get(feature) or PUBLIC_CATEGORICAL.get(feature) or feature
    return {"ko": ko_label, "en": FEATURE_LABELS_EN.get(feature, feature)}

PUBLIC_NUMERIC = list(FEATURE_LABELS_KO)
PUBLIC_BINARY = {
    "thumb_has_text": "썸네일 텍스트",
    "was_premiere": "프리미어 공개",
    "lyrics_has_hardsub": "하드자막",
    "has_nico_link": "니코니코 링크",
    "title_has_mv_mark": "제목 MV 표기",
    "title_has_emoji": "제목 이모지",
}
PUBLIC_CATEGORICAL = {
    "tag_mood_top": "장면 분위기",
    "thumb_mood": "썸네일 분위기",
    "lyrics_topic_1": "가사 주제",
    "lyrics_sentiment": "가사 정서",
    "lyrics_addressee": "가사 화자",
    "lyrics_source": "가사 소스",
}
SPACE_FEATURES = [
    "scene_cuts_per_minute", "scene_median_shot_len_s", "scene_num_scenes",
    "sync_beats_per_cut", "hook_cuts_first_15s", "scene_min_shot_len_s",
    "tag_avg_characters", "scene_avg_saturation", "scene_max_shot_len_s",
    "scene_avg_shot_len_s", "lyrics_compression_ratio",
]
CORRELATION_FEATURES = [
    "scene_cuts_per_minute", "scene_median_shot_len_s", "scene_avg_saturation",
    "scene_avg_brightness", "tag_avg_characters", "tag_closeup_ratio",
    "audio_bpm", "audio_rms_mean", "audio_spectral_centroid_hz",
    "hook_cuts_first_15s", "sync_cut_on_beat_ratio", "view_per_sub",
]
IDENTITY_KEYS = (
    "video_id", "title", "channel", "domain", "group", "view_count",
    "subscriber_count", "view_per_sub", "upload_date",
)

_DRIVE_RE = re.compile(r"\b[A-Za-z]:[\/]")
_IP_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")
_UNSAFE_KEYS = {"lyrics", "raw_lyrics", "formats", "requested_formats", "local_path"}


def _coerce(key: str, value: str | None):
    if value is None or value == "":
        return None
    if key in {"video_id", "title", "channel", "channel_id", "domain", "group",
               "upload_date", "collected_at", "audio_key", "tag_mood_top",
               "thumb_mood", "lyrics_topic_1", "lyrics_topic_2",
               "lyrics_sentiment", "lyrics_addressee", "lyrics_source"}:
        return value
    low = value.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        num = float(value)
    except ValueError:
        return value
    if num.is_integer() and not any(c in value.lower() for c in (".", "e")):
        return int(num)
    return num


def _read_rows(root: Path) -> list[dict]:
    return load_reference_rows(root, "all")


def _is_private_ip(text: str) -> bool:
    for match in _IP_RE.findall(text):
        try:
            ip = ipaddress.ip_address(match)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return True
    return False


def assert_public_safe(value: object) -> None:
    """Reject values that must never cross the public static-data boundary."""
    def walk(obj, key: str | None = None):
        if key in _UNSAFE_KEYS:
            raise ValueError(f"unsafe public key: {key}")
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, str(k))
            return
        if isinstance(obj, (list, tuple)):
            for item in obj:
                walk(item, key)
            return
        if not isinstance(obj, str):
            return
        low = obj.lower()
        drive_path = len(obj) >= 3 and obj[0].isalpha() and obj[1] == ":" and obj[2] in ("\\", "/")
        if drive_path or "file://" in low:
            raise ValueError("local path in public data")
        if "localhost" in low or _is_private_ip(obj):
            raise ValueError("private host in public data")
        if "googlevideo.com" in low or ("expire=" in low and ("sig=" in low or "signature=" in low)):
            raise ValueError("signed media URL in public data")
    walk(value)


def _finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def build_domain_summary(rows: list[dict], min_n: int = 10) -> dict:
    top = [r for r in rows if r.get("group") == "top"]
    bottom = [r for r in rows if r.get("group") == "bottom"]
    numeric = []
    for feature in PUBLIC_NUMERIC:
        a = [float(r[feature]) for r in top if _finite_number(r.get(feature))]
        b = [float(r[feature]) for r in bottom if _finite_number(r.get(feature))]
        if len(a) < min_n or len(b) < min_n:
            continue
        numeric.append({
            "id": feature,
            "label": FEATURE_LABELS_KO[feature],
            "labels": _labels(feature, FEATURE_LABELS_KO[feature]),
            "median_top": round(float(np.median(a)), 3),
            "median_bottom": round(float(np.median(b)), 3),
            "delta": round(float(cliffs_delta(a, b)), 3),
            "p": float(st.mannwhitneyu(a, b, alternative="two-sided").pvalue),
        })
    if numeric:
        qvals = bh_fdr(np.asarray([x["p"] for x in numeric], dtype=float))
        for row, q in zip(numeric, qvals):
            row["q"] = round(float(q), 4)
            row["significant"] = bool(q < 0.05)
            del row["p"]
    numeric.sort(key=lambda x: (-abs(x["delta"]), x["id"]))

    binary = []
    for feature, label in PUBLIC_BINARY.items():
        at = [r.get(feature) for r in top if isinstance(r.get(feature), bool)]
        ab = [r.get(feature) for r in bottom if isinstance(r.get(feature), bool)]
        if len(at) < min_n or len(ab) < min_n:
            continue
        yes_t, yes_b = sum(at), sum(ab)
        p = st.fisher_exact([[yes_t, len(at) - yes_t], [yes_b, len(ab) - yes_b]]).pvalue
        binary.append({
            "id": feature, "label": label, "labels": _labels(feature, label),
            "top": int(yes_t), "n_top": len(at),
            "bottom": int(yes_b), "n_bottom": len(ab),
            "p": round(float(p), 4),
        })
    binary.sort(key=lambda x: (x["p"], x["id"]))

    categorical = []
    for feature, label in PUBLIC_CATEGORICAL.items():
        ct = Counter(str(r[feature]) for r in top if r.get(feature) not in (None, ""))
        cb = Counter(str(r[feature]) for r in bottom if r.get(feature) not in (None, ""))
        keys = [k for k, _ in (ct + cb).most_common(8)]
        if keys:
            categorical.append({
                "id": feature, "label": label, "labels": _labels(feature, label), "categories": keys,
                "top": [ct.get(k, 0) for k in keys],
                "bottom": [cb.get(k, 0) for k in keys],
            })
    return {
        "n_top": len(top), "n_bottom": len(bottom),
        "numeric": numeric, "binary": binary, "categorical": categorical,
    }


def _feature_metadata(rows: list[dict]) -> list[dict]:
    keys = set().union(*(r.keys() for r in rows))
    output = []
    for feature in PUBLIC_NUMERIC:
        if feature not in keys:
            continue
        output.append({
            "id": feature,
            "label": FEATURE_LABELS_KO[feature],
            "labels": _labels(feature, FEATURE_LABELS_KO[feature]),
            "kind": "numeric",
            "status": "formal" if feature in P5_NUMERIC else "experimental",
        })
    for feature, label in PUBLIC_BINARY.items():
        if feature in keys:
            output.append({"id": feature, "label": label, "labels": _labels(feature, label), "kind": "binary", "status": "formal"})
    for feature, label in PUBLIC_CATEGORICAL.items():
        if feature in keys:
            output.append({"id": feature, "label": label, "labels": _labels(feature, label), "kind": "categorical", "status": "formal"})
    return output


def _public_videos(rows: list[dict]) -> list[dict]:
    feature_keys = set(PUBLIC_NUMERIC) | set(PUBLIC_BINARY) | set(PUBLIC_CATEGORICAL)
    output = []
    for row in rows:
        public = {key: row.get(key) for key in IDENTITY_KEYS}
        public["features"] = {
            key: row.get(key) for key in sorted(feature_keys)
            if key in row and row.get(key) is not None
        }
        output.append(public)
    return sorted(output, key=lambda x: (str(x.get("domain")), str(x.get("group")), str(x.get("video_id"))))


def _correlation_snapshot(rows: list[dict]) -> dict:
    output = {"method": "spearman", "domains": {}}
    for domain in sorted({str(r.get("domain")) for r in rows}):
        subset = [r for r in rows if str(r.get("domain")) == domain]
        features = [f for f in CORRELATION_FEATURES if sum(_finite_number(r.get(f)) for r in subset) >= 20]
        matrix = []
        for a in features:
            line = []
            for b in features:
                pairs = [(float(r[a]), float(r[b])) for r in subset if _finite_number(r.get(a)) and _finite_number(r.get(b))]
                if len(pairs) < 3:
                    line.append(None)
                    continue
                av, bv = zip(*pairs)
                rho = st.spearmanr(av, bv).statistic
                line.append(round(float(rho), 4) if np.isfinite(rho) else None)
            matrix.append(line)
        output["domains"][domain] = {"features": features, "matrix": matrix}
    return output


def build_space_snapshot(rows: list[dict]) -> dict:
    features = [f for f in SPACE_FEATURES if sum(_finite_number(r.get(f)) for r in rows) >= 20]
    mat = np.asarray([
        [float(r[f]) if _finite_number(r.get(f)) else np.nan for f in features]
        for r in rows
    ], dtype=float)
    med = np.nanmedian(mat, axis=0)
    missing = np.where(np.isnan(mat))
    mat[missing] = np.take(med, missing[1])
    std = mat.std(axis=0)
    std[std == 0] = 1.0
    z = (mat - mat.mean(axis=0)) / std
    _, singular, vt = np.linalg.svd(z, full_matrices=False)
    scores = z @ vt[:3].T
    loadings = vt[:3].copy()
    for i in range(min(3, loadings.shape[0])):
        pivot = int(np.argmax(np.abs(loadings[i])))
        if loadings[i, pivot] < 0:
            scores[:, i] *= -1
            loadings[i] *= -1
    scale = np.max(np.abs(scores), axis=0)
    scale[scale == 0] = 1.0
    coords = scores[:, :3] / scale[:3]
    variance = singular ** 2
    variance = variance / variance.sum()
    points = []
    for i, row in enumerate(rows):
        points.append({
            "id": row.get("video_id"), "title": row.get("title"),
            "channel": row.get("channel"), "domain": row.get("domain"),
            "group": row.get("group"),
            "pca": [round(float(v), 5) for v in coords[i, :3]],
            "score": [round(float(v), 5) for v in scores[i, :3]],
        })
    loading_rows = []
    for pc_index in range(min(3, loadings.shape[0])):
        ranked = sorted(
            zip(features, loadings[pc_index]),
            key=lambda item: (-abs(float(item[1])), item[0]),
        )[:5]
        loading_rows.append({
            "component": f"PC{pc_index + 1}",
            "items": [
                {
                    "feature": feature,
                    "label": FEATURE_LABELS_KO.get(feature, feature),
                    "labels": _labels(feature, FEATURE_LABELS_KO.get(feature, feature)),
                    "loading": round(float(weight), 5),
                }
                for feature, weight in ranked
            ],
        })
    return {
        "features": features,
        "normalization": {
            "method": "zscore",
            "imputation": "median",
            "coordinate_scaling": "max_abs_per_pc",
        },
        "explained_variance_pct": [round(float(v) * 100, 2) for v in variance[:3]],
        "loadings": loading_rows,
        "points": sorted(points, key=lambda x: str(x["id"])),
    }


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sample_expansion(root: Path) -> dict:
    summary_path = root / "work" / "sample_expansion.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if isinstance(summary, dict) and set(summary) == {"vocaloid", "kpop"}:
            return summary

    from .collect import filter_population, select_sample

    result = {}
    specs = {
        "vocaloid": (root / "work" / "population.jsonl", False),
        "kpop": (root / "work" / "kpop" / "population.jsonl", True),
    }
    for domain, (path, require_mv) in specs.items():
        rows = _read_jsonl(path)
        filtered = filter_population(rows, require_mv=require_mv)
        selected = select_sample(filtered, n=40, cap_per_channel=2)
        result[domain] = {
            "target_per_group": 40,
            "eligible_population": len(filtered),
            "max_top": len(selected["top"]),
            "max_bottom": len(selected["bottom"]),
            "require_mv_marker": require_mv,
            "channel_cap": 2,
            "feasible": len(selected["top"]) >= 40 and len(selected["bottom"]) >= 40,
        }
    return result


def _reliability_baseline(root: Path) -> dict | None:
    sample = root / "work" / "reliability_sample.json"
    labels = [
        root / "work" / "reliability_labels_A.json",
        root / "work" / "reliability_labels_B.json",
    ]
    if not sample.exists() or not all(p.exists() for p in labels):
        return None
    return score_predictions(load_baseline(sample), load_reference_labels(labels))


def _git_commit(root: Path) -> str:
    for key in ("MV_ANALYZER_GIT_COMMIT", "VERCEL_GIT_COMMIT_SHA", "GITHUB_SHA"):
        value = os.environ.get(key, "").strip()
        if re.fullmatch(r"[0-9a-fA-F]{7,64}", value):
            return value.lower()
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        )
        return proc.stdout.strip()
    except Exception:
        return "unknown"


def _write_json(path: Path, value: object) -> None:
    assert_public_safe(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _public_experiments() -> dict:
    from .experiments import registry

    return {
        "items": [
            {
                "id": item["id"],
                "label": item["label"],
                "state": "pending_validation",
                "status_class": "pending",
            }
            for item in registry()
        ],
        "note": "후보 모델/측정기는 고정 표본 A/B 검증 후에만 정식 결과로 승격됩니다.",
        "note_key": "fixed_sample_promotion",
    }


def build_public_snapshot(root: Path, out_dir: Path, *, require_git_commit: bool = False) -> dict[str, Path]:
    root = Path(root).resolve()
    out_dir = Path(out_dir)
    rows = _read_rows(root)
    if not rows:
        raise ValueError("public source dataset is empty")

    domains = {
        domain: build_domain_summary([r for r in rows if r.get("domain") == domain])
        for domain in sorted({str(r.get("domain")) for r in rows})
    }
    domain_counts = {
        domain: {
            "total": sum(r.get("domain") == domain for r in rows),
            "top": sum(r.get("domain") == domain and r.get("group") == "top" for r in rows),
            "bottom": sum(r.get("domain") == domain and r.get("group") == "bottom" for r in rows),
        }
        for domain in domains
    }
    collected = sorted(str(r.get("collected_at")) for r in rows if r.get("collected_at"))
    generated_at = collected[-1] if collected else "unknown"
    commit = _git_commit(root)
    if require_git_commit and commit == "unknown":
        raise RuntimeError("git commit provenance is required for this public snapshot")
    reliability = _reliability_baseline(root)
    expansion = _sample_expansion(root)
    reference_corpus = reference_corpus_public_metadata(rows, "all")

    retention_path = root / "work" / "heatmap_curves.json"
    retention = json.loads(retention_path.read_text(encoding="utf-8")) if retention_path.exists() else {}
    features = _feature_metadata(rows)
    payloads = {
        "overview": {
            "video_count": len(rows),
            "domain_counts": domain_counts,
            "headline_effects": {d: domains[d]["numeric"][:10] for d in domains},
            "reliability_baseline": reliability,
            "generated_at": generated_at,
            "causal_warning": "관찰된 차이는 연관성을 보여주며 인과효과를 증명하지 않습니다.",
        },
        "videos": _public_videos(rows),
        "features": features,
        "domains": domains,
        "correlations": _correlation_snapshot(rows),
        "retention": retention,
        "space": build_space_snapshot(rows),
        "experiments": _public_experiments(),
        "methodology": {
            "reference_corpus": reference_corpus,
            "study": {
                "sampling": "조회수/구독자수 비율의 상·하위 극단 비교",
                "sampling_key": "views_per_sub_extremes",
                "window": "2025-04-01 ~ 2026-04-01",
                "domains": ["vocaloid", "kpop"],
                "current_sample": domain_counts,
                "expansion": expansion,
            },
            "pipeline": ["PySceneDetect", "OpenCV", "librosa", "Qwen2.5-VL", "demucs + faster-whisper"],
            "reliability_baseline": reliability,
            "feature_policy": {
                "formal_count": sum(1 for f in features if f["status"] == "formal"),
                "experimental_count": sum(1 for f in features if f["status"] == "experimental"),
            },
            "caveat_ids": [
                "extreme_group_effect_inflation",
                "channel_production_confounding",
                "kpop_expansion_shortfall",
            ],
            "caveats": [
                "극단 그룹 설계 특성상 효과크기가 과대추정될 수 있습니다.",
                "제작 투자 규모와 채널 규모가 시각·공개 전략 feature와 함께 변할 수 있습니다.",
                "K-pop 40/40 확장은 현재 MV 표기·채널당 2편 규칙을 유지하면 모집단 확장이 더 필요합니다.",
            ],
        },
    }

    # Reproducible examples from the already-public reference corpus, never personal artifacts.
    demo_path = root / "examples" / "demo-report.json"
    if demo_path.exists():
        from .analyze_report import assert_analyze_report_safe
        demo = json.loads(demo_path.read_text(encoding="utf-8"))
        assert_analyze_report_safe(demo)
        payloads["demo-report"] = demo

    reason_demo_path = root / "examples" / "demo-reason.json"
    if reason_demo_path.exists():
        from .reason_contract import validate_reason_document
        reason_demo = json.loads(reason_demo_path.read_text(encoding="utf-8"))
        validate_reason_document(reason_demo)
        if "demo-report" in payloads:
            report_fingerprint = payloads["demo-report"]["pipeline"]["source_features_sha256"]
            if reason_demo["source_report"]["source_features_sha256"] != report_fingerprint:
                raise ValueError("demo reason source fingerprint does not match demo report")
        payloads["demo-reason"] = reason_demo

    paths: dict[str, Path] = {}
    for name, value in payloads.items():
        path = out_dir / f"{name}.json"
        _write_json(path, value)
        paths[name] = path

    files = {
        path.name: {"sha256": _sha256(path), "bytes": path.stat().st_size}
        for path in sorted(paths.values(), key=lambda p: p.name)
    }
    digest_input = "\n".join(f"{name}:{meta['sha256']}" for name, meta in sorted(files.items()))
    snapshot_id = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:16]
    manifest = {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "generated_at": generated_at,
        "git_commit": commit,
        "source": "dataset/features_100mv.csv",
        "domains": sorted(domains),
        "reference_corpus": reference_corpus,
        "files": files,
    }
    manifest_path = out_dir / "manifest.json"
    _write_json(manifest_path, manifest)
    paths["manifest"] = manifest_path
    return paths
