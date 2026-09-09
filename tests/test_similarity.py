import json

from mv_analyzer.similarity import COLS, outliers, similar


def _write(root, vid, offset):
    d = root / vid
    d.mkdir()
    r = {"video_id": vid, "title": vid, "channel": "c"}
    for i, c in enumerate(COLS):
        r[c] = i + offset
    (d / "features.json").write_text(json.dumps(r), encoding="utf-8")


def test_similar_orders_nearest(tmp_path):
    _write(tmp_path, "aaaaaaaaaaa", 0)
    _write(tmp_path, "bbbbbbbbbbb", 1)
    _write(tmp_path, "ccccccccccc", 10)
    rows = similar("aaaaaaaaaaa", tmp_path, 2)
    assert rows[0]["video_id"] == "bbbbbbbbbbb"


def test_outliers_returns_rows(tmp_path):
    for i, v in enumerate(["aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc", "ddddddddddd"]):
        _write(tmp_path, v, i * i)
    assert len(outliers(tmp_path, 2)) == 2
