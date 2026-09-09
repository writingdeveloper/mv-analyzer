import json

from mv_analyzer.index import build_index, search_index


def test_build_and_search_index(tmp_path):
    d = tmp_path / "abcdefghijk"
    d.mkdir()
    (d / "features.json").write_text(json.dumps({
        "video_id": "abcdefghijk", "title": "Night Test", "channel": "Demo"
    }), encoding="utf-8")
    (d / "lyrics_lines.json").write_text(json.dumps({
        "lines": [{"t_s": 12.0, "line": "hello moon"}]
    }), encoding="utf-8")
    (d / "scenes.json").write_text(json.dumps({
        "scenes": [{"scene": 0, "start_s": 0.0, "end_s": 5.0}]
    }), encoding="utf-8")
    (d / "scene_tags.json").write_text(json.dumps([{
        "setting": "city", "mood": "dark", "style": "anime", "shot_type": "wide",
        "visual_elements": ["moon"]
    }]), encoding="utf-8")
    db = tmp_path / "x.duckdb"
    counts = build_index(tmp_path, db)
    assert counts == {"features": 1, "lyrics": 1, "scenes": 1}
    assert search_index("moon", db)
