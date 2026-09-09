"""mv-analyzer 산출물 → OpenMontage 호환 분석 JSON (openmontage-reference-lab의 --from-analysis 입력).

reference-lab은 OpenMontage(AGPL)의 VideoAnalyzer 출력 형식을 정규화해 샷 설계도와
생성 프롬프트(H3 등)를 만든다. 이 모듈은 그 *입력 형식*만 맞춰 주는 얇은 변환기라,
두 저장소는 코드 의존 없이 JSON 한 장으로만 만난다.

원칙:
- 5요소(subject / subject_motion / scene / spatial_framing / camera)는 비워 둔다.
  VLM 태그는 손실 압축이라(mv-talk 원칙), reference-lab이 'VISION ENRICHMENT REQUIRED'로
  표시하고 에이전트가 키프레임을 직접 보고 채우는 흐름을 그대로 탄다.
- 대신 씬마다 mv-analyzer가 실제로 잰 것(색·밝기·인물 수·샷 타입·비트 오프셋·모션 분류·
  에너지)을 `mv_analyzer` 필드로 넘기고, 전체 리듬 프로파일·비트 그리드를 style_profile에 싣는다.
- 가사 라인은 씬별 transcript로 들어가므로 산출 파일은 work/exports/ (gitignore) 밖으로
  내보내지 않는다.
"""
from __future__ import annotations

import datetime as _dt
import json
import os

from .extensions import derived_features
from .talk import ENERGY_BIN_S, load, lyrics_between

EXPORT_DIR = os.path.join("work", "exports")
FIVE_ASPECTS = ("subject", "subject_motion", "scene", "spatial_framing", "camera")


def _weighted_palette(scenes, k=5):
    weight = {}
    for s in scenes:
        c = s.get("dominant_color")
        if isinstance(c, str) and c.startswith("#") and len(c) == 7:
            weight[c] = weight.get(c, 0.0) + float(s.get("len_s") or 0.0)
    return [c for c, _ in sorted(weight.items(), key=lambda kv: -kv[1])[:k]]


def _nearest_beat_offset(t, beats):
    if not beats:
        return None
    return round(min(abs(t - b) for b in beats), 3)


def _energy_level(ratio):
    if ratio is None:
        return "unknown"
    return "high" if ratio >= 0.8 else "medium" if ratio >= 0.5 else "low"


def _pacing_style(cpm, beat_ratio):
    speed = "fast" if (cpm or 0) >= 20 else "medium" if (cpm or 0) >= 10 else "slow"
    locked = "_beat_locked" if (beat_ratio or 0) >= 0.4 else ""
    return f"{speed}_cut{locked}"


def _motion_by_scene(bundle):
    path = os.path.join(bundle["dir"], "motion_scenes.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        rows = (json.load(fh) or {}).get("scenes") or []
    return {r.get("scene"): r for r in rows}


def build_openmontage_analysis(bundle, keyframe_dir=None):
    """load()로 얻은 묶음 → OpenMontage raw analysis 형식 dict."""
    f = bundle.get("features") or {}
    scenes_obj = bundle.get("scenes") or {}
    scenes = scenes_obj.get("scenes") or []
    summary = scenes_obj.get("summary") or {}
    tags = bundle.get("scene_tags") or []
    audio = bundle.get("audio") or {}
    sync = bundle.get("sync") or {}
    lyrics = bundle.get("lyrics") or {}
    beats = audio.get("beat_times_s") or []
    curve = audio.get("energy_curve_10s") or []
    peak = max(curve) if curve else None
    motion = _motion_by_scene(bundle)
    vid = bundle["video_id"]
    # 생성용으로는 자막·필러박스를 걷어낸 프레임 세트를 꽂을 수 있다 (gen_frames.build)
    kf_dir = os.path.abspath(keyframe_dir or os.path.join(bundle["dir"], "keyframes"))

    out_scenes, keyframes = [], []
    for i, s in enumerate(scenes):
        start, end = float(s["start_s"]), float(s["end_s"])
        tg = tags[i] if i < len(tags) else {}
        m = motion.get(s.get("scene")) or {}
        mid = (start + end) / 2  # 씬 중간점의 10초 버킷 (시작점은 직전 씬 버킷에 걸치기 쉬움)
        bin_i = min(int(mid // ENERGY_BIN_S), len(curve) - 1) if curve else None
        e_ratio = round(curve[bin_i] / peak, 3) if curve and peak else None
        lines = lyrics_between(bundle, start, end)
        rec = {
            "scene_index": i,
            "start_time": round(start, 3),
            "end_time": round(end, 3),
            "transcript": " / ".join(str(l.get("line") or "") for l in lines),
            "visual_type": "other",
            "energy_level": _energy_level(e_ratio),
            "mv_analyzer": {
                "setting_hint": tg.get("setting"),
                "mood_hint": tg.get("mood"),
                "shot_type_hint": tg.get("shot_type"),
                "style_hint": tg.get("style"),
                "num_characters": tg.get("num_characters"),
                "visual_elements": tg.get("visual_elements") or [],
                "has_lyrics_text": tg.get("has_lyrics_text"),
                "dominant_color": s.get("dominant_color"),
                "brightness": s.get("brightness"),
                "saturation": s.get("saturation"),
                "cut_beat_offset_s": _nearest_beat_offset(start, beats) if i > 0 else None,
                "energy_ratio_to_peak": e_ratio,
                "n_lyric_lines": len(lines),
            },
        }
        if m.get("motion_type") in ("static_image", "animated_still", "motion_clip"):
            rec["motion_type"] = m["motion_type"]
            rec["flow_variance"] = m.get("flow_variance")
        out_scenes.append(rec)
        if s.get("keyframe"):
            keyframes.append({"timestamp": round((start + end) / 2, 3), "scene_index": i,
                              "path": os.path.join(kf_dir, s["keyframe"]), "description": ""})

    ext = derived_features(f, scenes_obj, lyrics)
    steps = ["metadata", "scene_detect", "keyframes", "color", "audio", "beat_grid"]
    if lyrics.get("lines"):
        steps.append(f"lyrics_{lyrics.get('source')}")
    if motion:
        steps.append("motion_classification")
    if tags:
        steps.append("vlm_scene_tags_as_hints")

    return {
        "version": "1.0",
        "source": {
            "type": "youtube",
            "url": f"https://www.youtube.com/watch?v={vid}",
            "title": f.get("title"),
            "duration_seconds": f.get("duration_s") or summary.get("duration_s"),
            "resolution": f"{f.get('width')}x{f.get('height')}" if f.get("width") else "",
            "platform_metadata": {"channel": f.get("channel"), "upload_date": f.get("upload_date"),
                                  "view_count": f.get("view_count"),
                                  "subscriber_count": f.get("subscriber_count")},
        },
        "content_analysis": {"summary": "", "topics": [t for t in (f.get("lyrics_topic_1"), f.get("lyrics_topic_2")) if t],
                             "target_audience": "general"},
        "structure_analysis": {
            "total_scenes": len(out_scenes),
            "scenes": out_scenes,
            "pacing_profile": {
                "avg_scene_duration_seconds": summary.get("avg_shot_len_s"),
                "shortest_scene_seconds": summary.get("min_shot_len_s"),
                "longest_scene_seconds": summary.get("max_shot_len_s"),
                "cuts_per_minute": summary.get("cuts_per_minute"),
                "pacing_style": _pacing_style(summary.get("cuts_per_minute"), sync.get("cut_on_beat_ratio")),
            },
        },
        "narration_transcript": {
            "full_text": "",  # 가사 전문은 싣지 않는다 — 씬별 transcript로만
            "segments": [{"text": l.get("line"), "start": l.get("t_s")} for l in (lyrics.get("lines") or [])],
            "language": lyrics.get("lang"),
            "word_count": None,
        },
        "keyframes": keyframes,
        "style_profile": {
            "audio_energy_profile": {"has_energy_data": bool(curve), "energy_curve_10s": curve,
                                     "peak_energy_at_s": audio.get("peak_energy_at_s")},
            "narration_style": {"has_narration": bool(lyrics.get("lines")), "speaker_count": None,
                                "delivery_style": "sung", "words_per_minute": None},
            "color_palette": {"primary_colors": _weighted_palette(scenes, 3),
                              "accent_colors": _weighted_palette(scenes, 6)[3:],
                              "overall_mood": f.get("tag_mood_top") or ""},
            "typography_observed": "",
            "transition_types": ["hard cut"],
            "music_style": f"BPM {audio.get('bpm')} · {audio.get('key')} · LUFS {f.get('audio_lufs_i')}",
            "subtitle_style": "hardsub" if lyrics.get("has_hardsub") else "",
            "production_quality": "",
            "closest_playbook": "",
            "playbook_delta": "",
            "rhythm_profile": {
                "bpm": audio.get("bpm"), "key": audio.get("key"),
                "cuts_per_minute": summary.get("cuts_per_minute"),
                "median_shot_len_s": summary.get("median_shot_len_s"),
                "cut_on_beat_ratio": sync.get("cut_on_beat_ratio"),
                "beats_per_cut": sync.get("beats_per_cut"),
                "first_cut_s": sync.get("first_cut_s"),
                "hook_cuts_first_15s": f.get("hook_cuts_first_15s"),
                "loudness_lufs": f.get("audio_lufs_i"),
            },
            "beat_grid_s": beats,
            "visual_profile": {
                "style_top": f.get("tag_style_top"), "mood_top": f.get("tag_mood_top"),
                "closeup_ratio": f.get("tag_closeup_ratio"), "avg_characters": f.get("tag_avg_characters"),
                "avg_brightness": summary.get("avg_brightness"), "avg_saturation": summary.get("avg_saturation"),
                **{k: v for k, v in ext.items() if k.startswith("ext_scene") or k.startswith("ext_color")},
            },
            "lyrics_profile": {
                "lang": lyrics.get("lang"), "source": lyrics.get("source"),
                "n_lines": len(lyrics.get("lines") or []),
                "topic": f.get("lyrics_topic_1"), "sentiment": f.get("lyrics_sentiment"),
                "addressee": f.get("lyrics_addressee"),
                "first_chorus_s": ext.get("ext_lyrics_first_chorus_s"),
            },
        },
        "replication_guidance": {"suggested_pipeline": "", "suggested_playbook": "",
                                 "key_elements_to_replicate": [], "elements_requiring_custom_work": [],
                                 "estimated_complexity": "", "motion_required": bool(motion),
                                 "creative_differentiation_seeds": []},
        "_analysis_meta": {
            "source_tool": "mv-analyzer",
            "exported_at": _dt.datetime.now().isoformat(timespec="seconds"),
            "video_id": vid,
            "depth": "mv_analyzer_full",
            "steps_completed": steps,
            "steps_failed": [],
            "keyframe_count": len(keyframes),
            "scene_count": len(out_scenes),
            "has_transcript": bool(lyrics.get("lines")),
            "vision_enrichment_note": "5요소는 의도적으로 비움 — 키프레임을 직접 보고 채울 것",
        },
    }


def export_openmontage(vid, data_dir="data", out_path=None, keyframe_dir=None):
    bundle = load(vid, data_dir)
    if not bundle:
        return None, None
    payload = build_openmontage_analysis(bundle, keyframe_dir)
    out = out_path or os.path.join(EXPORT_DIR, f"{vid}.openmontage.json")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    return out, payload
