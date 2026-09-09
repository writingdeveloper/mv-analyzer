from mv_analyzer.features import build_row


def fixture_parts():
    tags = [
        {"style": "anime", "mood": "활기", "shot_type": "closeup", "num_characters": 1, "has_lyrics_text": True}
        for _ in range(31)
    ] + [
        {"style": "anime", "mood": "활기", "shot_type": "wide", "num_characters": 1, "has_lyrics_text": False}
        for _ in range(13)
    ]
    scenes = {
        "summary": {"duration_s": 146.24, "fps": 30.0, "num_scenes": 44, "avg_shot_len_s": 3.323, "median_shot_len_s": 2.0},
        "scenes": [
            {"scene": 0, "start_s": 0.0, "end_s": 0.67, "len_s": 0.67},
            {"scene": 1, "start_s": 0.67, "end_s": 146.24, "len_s": 145.57},
        ],
    }
    audio = {"duration_s": 146.24, "bpm": 123.0, "peak_energy_at_s": 120, "energy_curve_10s": [1.0, 1.0]}
    return scenes, audio, tags

def test_build_row_with_pilot_fixtures():
    scenes, audio, tags = fixture_parts()
    slim = {"video_id": "vF0ZU2GQSzo", "title": "t", "view_count": 445155,
            "subscriber_count": None, "view_per_sub": None, "duration_s": 146}
    lyric_lines = [{"t_s": 0, "line": "만나고"}]
    thumb = {"style": "anime", "thumb_brightness": 0.5, "thumb_saturation": 0.3}
    sync = {"cut_beat_offset_med_s": None, "cut_on_beat_ratio": None,
            "cut_accel_at_peak": 1.5, "first_cut_s": 2.0,
            "first_lyric_at_s": 0, "beats_per_cut": 6.8}
    title = {"title_len": 10, "title_has_emoji": False}
    lyrics_tags = {"topics": ["희망", "사랑"], "sentiment": "긍정",
                   "addressee": "1인칭 독백"}
    ocr_stats = {"text_frames": 63, "total_frames": 73}
    row = build_row(slim, scenes, audio, {"lufs_i": -9.9, "lra_lu": 4.6},
                    tags, lyric_lines, thumb, title, sync, lang="ko",
                    lyrics_source="ocr", first_vocal_at_s=12,
                    lyrics_tags=lyrics_tags, ocr_stats=ocr_stats)
    # 평탄 구조 + 축별 프리픽스
    assert row["video_id"] == "vF0ZU2GQSzo"
    assert row["scene_num_scenes"] == 44
    assert row["audio_bpm"] == 123.0
    assert row["audio_lufs_i"] == -9.9
    assert row["tag_style_top"] == "anime"
    assert row["tag_closeup_ratio"] == round(31 / 44, 3)
    assert row["lyrics_n_lyric_lines"] == 1
    assert row["thumb_style"] == "anime"
    assert row["title_len"] == 10
    assert row["sync_beats_per_cut"] == 6.8
    assert row["lyrics_lang"] == "ko"
    assert row["lyrics_source"] == "ocr"
    assert row["lyrics_first_vocal_at_s"] == 12

    # 가사 주제 태깅
    assert row["lyrics_topic_1"] == "희망"
    assert row["lyrics_topic_2"] == "사랑"
    assert row["lyrics_sentiment"] == "긍정"
    assert row["lyrics_addressee"] == "1인칭 독백"

    # 하드자막 OCR 커버리지
    assert row["lyrics_text_frame_ratio"] == 0.863
    assert row["lyrics_has_hardsub"] is True

    # 훅 지표 — synthetic scenes에서 start_s가 (0,15] 범위인 씬은 scene 1(0.67s)뿐
    assert row["hook_cuts_first_15s"] == 1
    # synthetic audio: peak_energy_at_s=120, duration_s=146.24
    assert row["audio_peak_energy_ratio"] == round(120 / 146.24, 3)

    # 중첩 리스트는 행에 포함하지 않는다 (energy_curve 등은 단계 JSON에만)
    assert not any(isinstance(v, (list, dict)) for v in row.values())


def test_build_row_without_lyrics_tags_or_ocr_stats():
    """lyrics_tags/ocr_stats 미전달(기본값 None) 시 관련 컬럼은 전부 None."""
    scenes, audio, tags = fixture_parts()
    slim = {"video_id": "vF0ZU2GQSzo", "title": "t", "view_count": 445155,
            "subscriber_count": None, "view_per_sub": None, "duration_s": 146}
    lyric_lines = [{"t_s": 0, "line": "만나고"}]
    thumb = {"style": "anime", "thumb_brightness": 0.5, "thumb_saturation": 0.3}
    sync = {"cut_beat_offset_med_s": None, "cut_on_beat_ratio": None,
            "cut_accel_at_peak": 1.5, "first_cut_s": 2.0,
            "first_lyric_at_s": 0, "beats_per_cut": 6.8}
    title = {"title_len": 10, "title_has_emoji": False}
    row = build_row(slim, scenes, audio, {"lufs_i": -9.9, "lra_lu": 4.6},
                    tags, lyric_lines, thumb, title, sync, lang="ko")
    assert row["lyrics_topic_1"] is None
    assert row["lyrics_topic_2"] is None
    assert row["lyrics_sentiment"] is None
    assert row["lyrics_addressee"] is None
    assert row["lyrics_text_frame_ratio"] is None
    assert row["lyrics_has_hardsub"] is None
    assert row["lyrics_source"] is None
    assert row["lyrics_first_vocal_at_s"] is None
    assert row["hook_cuts_first_15s"] == 1
