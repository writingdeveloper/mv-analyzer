"""단계별 산출물 → 영상 1편 = features 1행(평탄 dict) 병합."""
from collections import Counter

from mv_analyzer.lyrics import HARDSUB_MIN_RATIO, lyrics_features


def _top(tags, key):
    c = Counter(str(t.get(key)) for t in tags if t.get(key) is not None)
    return c.most_common(1)[0][0] if c else None


def build_row(slim, scenes, audio, loudness, scene_tags, lyric_lines,
              thumb, title, sync, lang, lyrics_tags=None, ocr_stats=None,
              lyrics_source=None, first_vocal_at_s=None):
    s = scenes["summary"]
    n = max(len(scene_tags), 1)
    shot = Counter(str(t.get("shot_type")) for t in scene_tags)
    row = {}

    # 메타(기록 컬럼) — 리스트/딕트 값은 행에서 제외
    row.update({k: v for k, v in slim.items()
                if not isinstance(v, (list, dict))})

    row.update({f"scene_{k}": v for k, v in s.items()
                if not isinstance(v, (list, dict))})
    row.update({f"audio_{k}": v for k, v in audio.items()
                if not isinstance(v, (list, dict))})
    row["audio_lufs_i"] = loudness.get("lufs_i")
    row["audio_lra_lu"] = loudness.get("lra_lu")

    row["tag_style_top"] = _top(scene_tags, "style")
    row["tag_mood_top"] = _top(scene_tags, "mood")
    row["tag_closeup_ratio"] = round(shot.get("closeup", 0) / n, 3)
    row["tag_wide_ratio"] = round(shot.get("wide", 0) / n, 3)
    row["tag_avg_characters"] = round(
        sum(float(t.get("num_characters") or 0) for t in scene_tags) / n, 2)
    row["tag_lyrics_text_ratio"] = round(
        sum(bool(t.get("has_lyrics_text")) for t in scene_tags) / n, 3)

    row.update({f"lyrics_{k}": v for k, v in
                lyrics_features(lyric_lines, s["duration_s"]).items()})
    row["lyrics_lang"] = lang
    row["lyrics_source"] = lyrics_source  # "ocr" | "asr" | None
    row["lyrics_first_vocal_at_s"] = first_vocal_at_s  # ASR 기반 인트로 길이 프록시

    row.update({f"thumb_{k}": v for k, v in thumb.items()
                if not isinstance(v, (list, dict))
                and not k.startswith("thumb_")})
    row["thumb_brightness"] = thumb.get("thumb_brightness")
    row["thumb_saturation"] = thumb.get("thumb_saturation")

    row.update(title)  # title_features 반환값 — 키가 이미 title_ 프리픽스
    row.update({f"sync_{k}": v for k, v in sync.items()})

    # 가사 주제 태깅 (VLM, lang별 캐시) — 가사 없으면 전부 None
    topics = (lyrics_tags or {}).get("topics") or []
    row["lyrics_topic_1"] = topics[0] if len(topics) > 0 else None
    row["lyrics_topic_2"] = topics[1] if len(topics) > 1 else None
    row["lyrics_sentiment"] = lyrics_tags.get("sentiment") if lyrics_tags else None
    row["lyrics_addressee"] = lyrics_tags.get("addressee") if lyrics_tags else None

    # 하드자막 OCR 커버리지
    if ocr_stats:
        total = ocr_stats.get("total_frames") or 0
        ratio = round(ocr_stats.get("text_frames", 0) / total, 3) if total else None
        row["lyrics_text_frame_ratio"] = ratio
        row["lyrics_has_hardsub"] = (ratio is not None
                                     and ratio >= HARDSUB_MIN_RATIO)
    else:
        row["lyrics_text_frame_ratio"] = None
        row["lyrics_has_hardsub"] = None

    # 훅(초반 15초/10초) 지표
    scene_list = scenes.get("scenes") or []
    row["hook_cuts_first_15s"] = sum(
        1 for sc in scene_list if 0 < sc.get("start_s", 0) <= 15)
    curve = audio.get("energy_curve_10s") or []
    row["hook_energy_first_10s_ratio"] = (
        round(curve[0] / (sum(curve) / len(curve)), 3) if curve else None)
    duration = audio.get("duration_s")
    row["audio_peak_energy_ratio"] = (
        round(audio["peak_energy_at_s"] / duration, 3)
        if duration and audio.get("peak_energy_at_s") is not None else None)

    return row
