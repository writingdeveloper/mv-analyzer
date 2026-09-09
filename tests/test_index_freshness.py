import json
import time

from mv_analyzer.index import build_index, search_index
from mv_analyzer.index_freshness import ensure_index, index_status


def _fixture(root):
    d = root / "abcdefghijk"
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
    return d


def test_index_freshness_and_auto_rebuild(tmp_path):
    d = _fixture(tmp_path)
    db = tmp_path / "x.duckdb"
    assert index_status(tmp_path, db)["reason"] == "missing"
    build_index(tmp_path, db)
    assert index_status(tmp_path, db)["fresh"] is True

    time.sleep(0.002)
    (d / "lyrics_lines.json").write_text(json.dumps({
        "lines": [{"t_s": 4.0, "line": "new phrase"}]
    }), encoding="utf-8")
    assert index_status(tmp_path, db)["reason"] == "source_changed"
    result = ensure_index(tmp_path, db)
    assert result["rebuilt"] is True and result["fresh"] is True
    assert search_index("new phrase", db)
