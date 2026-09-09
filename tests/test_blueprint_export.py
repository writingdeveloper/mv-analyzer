import json
import os

from mv_analyzer.blueprint_export import FIVE_ASPECTS, build_openmontage_analysis, export_openmontage
from mv_analyzer.talk import load


def _make(root, vid="abcdefghijk", with_motion=True):
    d = root / vid
    (d / "keyframes").mkdir(parents=True)
    (d / "features.json").write_text(json.dumps({
        "video_id": vid, "title": "demo", "duration_s": 20, "width": 1920, "height": 1080,
        "channel": "ch", "tag_mood_top": "활기", "tag_style_top": "anime",
        "audio_lufs_i": -9.0, "hook_cuts_first_15s": 3, "lyrics_topic_1": "사랑",
    }), encoding="utf-8")
    (d / "scenes.json").write_text(json.dumps({
        "summary": {"duration_s": 20, "avg_shot_len_s": 10, "min_shot_len_s": 8, "max_shot_len_s": 12,
                    "cuts_per_minute": 3.0, "median_shot_len_s": 10, "avg_brightness": 0.5,
                    "avg_saturation": 0.4},
        "scenes": [
            {"scene": 0, "start_s": 0.0, "end_s": 8.0, "len_s": 8.0, "dominant_color": "#30d9dd",
             "brightness": 0.6, "saturation": 0.5, "keyframe": "scene_000.jpg"},
            {"scene": 1, "start_s": 8.0, "end_s": 20.0, "len_s": 12.0, "dominant_color": "#101010",
             "brightness": 0.1, "saturation": 0.1, "keyframe": "scene_001.jpg"},
        ]}), encoding="utf-8")
    (d / "scene_tags.json").write_text(json.dumps([
        {"setting": "실내", "num_characters": 1, "shot_type": "closeup", "style": "anime",
         "mood": "활기", "has_lyrics_text": True, "visual_elements": ["꽃"]},
        {"setting": "야외", "num_characters": 2, "shot_type": "wide", "style": "anime",
         "mood": "긴장", "has_lyrics_text": False, "visual_elements": []},
    ]), encoding="utf-8")
    (d / "lyrics_lines.json").write_text(json.dumps({"lang": "ja", "source": "ocr", "has_hardsub": True,
        "lines": [{"t_s": 1.0, "line": "alpha"}, {"t_s": 3.0, "line": "beta"},
                  {"t_s": 9.0, "line": "gamma"}]}), encoding="utf-8")
    (d / "audio_features.json").write_text(json.dumps({
        "bpm": 120.0, "key": "C major", "energy_curve_10s": [0.5, 1.0], "peak_energy_at_s": 10,
        "beat_times_s": [0.0, 0.5, 1.0, 7.9, 8.4, 9.0]}), encoding="utf-8")
    (d / "sync_features.json").write_text(json.dumps({"cut_on_beat_ratio": 0.5, "beats_per_cut": 4,
                                                       "first_cut_s": 8.0}), encoding="utf-8")
    if with_motion:
        (d / "motion_scenes.json").write_text(json.dumps({"params": {}, "scenes": [
            {"scene": 0, "motion_type": "animated_still", "flow_variance": 0.8},
            {"scene": 1, "motion_type": "motion_clip", "flow_variance": 9.1}]}), encoding="utf-8")
    return d


def test_build_matches_openmontage_shape(tmp_path):
    _make(tmp_path)
    raw = build_openmontage_analysis(load("abcdefghijk", tmp_path))
    assert raw["version"] == "1.0"
    assert raw["source"]["duration_seconds"] == 20 and raw["source"]["resolution"] == "1920x1080"
    scenes = raw["structure_analysis"]["scenes"]
    assert [s["scene_index"] for s in scenes] == [0, 1]
    assert scenes[0]["start_time"] == 0.0 and scenes[0]["end_time"] == 8.0
    # 5요소는 의도적으로 비워 둔다 (reference-lab의 vision enrichment 흐름)
    for s in scenes:
        assert not any(k in s for k in FIVE_ASPECTS)
    assert scenes[0]["transcript"] == "alpha / beta"
    assert scenes[1]["transcript"] == "gamma"
    assert scenes[0]["motion_type"] == "animated_still" and scenes[1]["flow_variance"] == 9.1
    hint = scenes[1]["mv_analyzer"]
    assert hint["num_characters"] == 2 and hint["dominant_color"] == "#101010"
    assert hint["cut_beat_offset_s"] == 0.1          # 8.0 vs 가장 가까운 비트 7.9
    assert scenes[0]["mv_analyzer"]["cut_beat_offset_s"] is None   # 첫 씬 시작은 컷이 아님
    assert scenes[0]["energy_level"] == "medium" and scenes[1]["energy_level"] == "high"
    kf = raw["keyframes"]
    assert len(kf) == 2 and os.path.isabs(kf[0]["path"]) and kf[0]["path"].endswith("scene_000.jpg")
    assert kf[1]["timestamp"] == 14.0
    sp = raw["style_profile"]
    assert sp["color_palette"]["primary_colors"][0] == "#101010"   # 12초 > 8초 (길이 가중)
    assert sp["rhythm_profile"]["cut_on_beat_ratio"] == 0.5
    assert sp["beat_grid_s"] == [0.0, 0.5, 1.0, 7.9, 8.4, 9.0]
    assert sp["lyrics_profile"]["n_lines"] == 3 and sp["subtitle_style"] == "hardsub"
    assert raw["structure_analysis"]["pacing_profile"]["pacing_style"] == "slow_cut_beat_locked"
    assert "motion_classification" in raw["_analysis_meta"]["steps_completed"]
    assert raw["narration_transcript"]["full_text"] == ""


def test_build_without_motion_omits_motion_fields(tmp_path):
    _make(tmp_path, with_motion=False)
    raw = build_openmontage_analysis(load("abcdefghijk", tmp_path))
    assert "motion_type" not in raw["structure_analysis"]["scenes"][0]
    assert "motion_classification" not in raw["_analysis_meta"]["steps_completed"]


def test_export_writes_file_and_handles_missing(tmp_path):
    _make(tmp_path)
    out, payload = export_openmontage("abcdefghijk", tmp_path, out_path=tmp_path / "x" / "a.json")
    assert os.path.exists(out)
    assert json.loads(open(out, encoding="utf-8").read())["source"]["title"] == "demo"
    assert payload["_analysis_meta"]["source_tool"] == "mv-analyzer"
    assert export_openmontage("nope", tmp_path) == (None, None)
