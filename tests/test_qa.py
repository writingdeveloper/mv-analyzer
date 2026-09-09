import json

from mv_analyzer.qa import CORE, scan_data


def test_scan_data_detects_complete_and_partial(tmp_path):
    complete = tmp_path / "aaaaaaaaaaa"
    complete.mkdir()
    for n in CORE:
        (complete / n).write_text(json.dumps({"x": 1}), encoding="utf-8")
    partial = tmp_path / "bbbbbbbbbbb"
    partial.mkdir()
    (partial / "features.json").write_text("{}", encoding="utf-8")
    s = scan_data(tmp_path)
    assert s["complete"] == 1 and s["partial"] == 1
    assert s["feature_widths"]


def test_scan_detects_feature_schema_variants(tmp_path):
    for vid, extra in [("aaaaaaaaaaa", {}), ("bbbbbbbbbbb", {"different": 1})]:
        d = tmp_path / vid
        d.mkdir()
        for n in CORE:
            obj = {"video_id": vid}
            if n == "features.json":
                obj.update(extra)
            (d / n).write_text(json.dumps(obj), encoding="utf-8")
    s = scan_data(tmp_path)
    assert len(s["feature_schema_variants"]) == 2
