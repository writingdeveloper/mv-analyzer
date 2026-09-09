import json

import pytest

from mv_analyzer import talk


def _video(root, vid, *, cpm, lufs, bpm, color, mood, n_lines=0, clip=None):
    d = root / vid
    d.mkdir()
    (d / "features.json").write_text(json.dumps({
        "video_id": vid, "title": f"title-{vid}", "duration_s": 120,
        "scene_cuts_per_minute": cpm, "audio_lufs_i": lufs, "audio_bpm": bpm,
        "tag_mood_top": mood, "tag_style_top": "anime",
    }), encoding="utf-8")
    (d / "scenes.json").write_text(json.dumps({"summary": {"duration_s": 120}, "scenes": [
        {"scene": 0, "start_s": 0, "end_s": 60, "len_s": 60, "dominant_color": color,
         "brightness": 0.5, "saturation": 0.5, "keyframe": "scene_000.jpg"},
        {"scene": 1, "start_s": 60, "end_s": 120, "len_s": 60, "dominant_color": "#101010",
         "brightness": 0.1, "saturation": 0.1, "keyframe": "scene_001.jpg"},
    ]}), encoding="utf-8")
    (d / "lyrics_lines.json").write_text(json.dumps({"lang": "ja", "source": "ocr", "lines": [
        {"t_s": i * 5.0, "line": f"line {i % 3}"} for i in range(n_lines)]}), encoding="utf-8")
    if clip is not None:
        (d / "motion_scenes.json").write_text(json.dumps({"params": {}, "scenes": [], "summary": {
            "motion_scene_n": 2, "motion_scene_clip_ratio": clip,
            "motion_scene_animated_still_ratio": 0.0, "motion_scene_static_ratio": 1 - clip}}),
            encoding="utf-8")


@pytest.fixture
def corpus(tmp_path):
    # 5편: a,b가 '취향', 나머지는 코퍼스 배경
    _video(tmp_path, "aaaaaaaaaaa", cpm=30, lufs=-8.0, bpm=150, color="#30d9dd", mood="활기", clip=0.9)
    _video(tmp_path, "bbbbbbbbbbb", cpm=28, lufs=-8.5, bpm=90, color="#31dcdd", mood="활기", clip=0.95)
    _video(tmp_path, "ccccccccccc", cpm=5, lufs=-14.0, bpm=90, color="#aa2222", mood="우울", clip=0.1)
    _video(tmp_path, "ddddddddddd", cpm=10, lufs=-12.0, bpm=100, color="#aa2222", mood="우울")
    _video(tmp_path, "eeeeeeeeeee", cpm=15, lufs=-11.0, bpm=130, color="#22aa22", mood="긴장")
    return tmp_path


def test_percentile_rank_midrank():
    assert talk.percentile_rank([1, 2, 3, 4], 4) == 87.5
    assert talk.percentile_rank([1, 2, 3, 4], 0) == 0.0
    assert talk.percentile_rank([], 1) is None
    assert talk.percentile_rank([2, 2, 2], 2) == 50.0


def test_hue_bucket():
    assert talk.hue_bucket("#000000") == "어두움"
    assert talk.hue_bucket("#cccccc") == "무채색"
    assert talk.hue_bucket("#30d9dd") == "청록"
    assert talk.hue_bucket("#ff0000") == "빨강"
    assert talk.hue_bucket("nope") is None


def test_read_id_list_strips_comments_and_urls(tmp_path):
    p = tmp_path / "fav.txt"
    p.write_text("# header\nvF0ZU2GQSzo   # baum\nhttps://www.youtube.com/watch?v=8Cm-7oCq9HA\n\n"
                 "vF0ZU2GQSzo\n", encoding="utf-8")
    assert talk.read_id_list(p) == ["vF0ZU2GQSzo", "8Cm-7oCq9HA"]


def test_profile_separates_taste_from_convention(corpus):
    r = talk.profile(["aaaaaaaaaaa", "bbbbbbbbbbb", "zzzzzzzzzzz"], corpus)
    assert r["n_videos"] == 2 and r["n_corpus"] == 5
    assert r["missing"] == ["zzzzzzzzzzz"]
    by = {d["col"]: d for d in r["numeric"]}
    assert by["scene_cuts_per_minute"]["verdict"] == "특이점·높음"
    assert by["audio_lufs_i"]["verdict"] == "특이점·높음"
    assert by["audio_bpm"]["verdict"] == "무관(편차 큼)"
    # motion_scenes.json이 있는 영상만 모션 축에 참여 (a,b,c 3편 풀; d,e는 없음)
    assert by["motion_scene_clip_ratio"]["n"] == 2
    # 풀 3편(0.9, 0.95, 0.1) 안에서 a=50·b=83백분위, 퍼짐 0.05 → 공통·관습
    assert by["motion_scene_clip_ratio"]["verdict"] == "공통·관습"
    assert by["motion_scene_clip_ratio"]["median_pct"] > 50
    assert r["numeric"][0]["verdict"].startswith("특이점")
    cat = {d["col"]: d for d in r["categorical"]}
    assert cat["tag_mood_top"]["verdict"] == "취향 신호"       # 100% vs 코퍼스 40%
    assert cat["tag_style_top"]["verdict"] == "관습"           # 코퍼스 전부 anime
    pal = r["palette"]
    top = pal["diff"][0]
    assert top["bucket"] == "청록" and top["delta"] > 0
    assert set(pal["per_video"]) == {"aaaaaaaaaaa", "bbbbbbbbbbb"}


def test_profile_all_missing(corpus):
    r = talk.profile(["zzzzzzzzzzz"], corpus)
    assert r["n_videos"] == 0 and r["missing"] == ["zzzzzzzzzzz"]
    assert r["numeric"] == [] and r["palette"] is None
