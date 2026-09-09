import json

import numpy as np

from mv_analyzer import motion_label as ml


def _write(root, vid, types):
    d = root / vid
    d.mkdir()
    (d / "motion_scenes.json").write_text(json.dumps({"params": {}, "summary": {}, "scenes": [
        {"scene": i, "start_s": i * 2.0, "end_s": i * 2.0 + 2.0, "motion_type": t,
         "flow_mag_mean": 0.1, "flow_variance": 0.1}
        for i, t in enumerate(types)]}), encoding="utf-8")


def test_scene_rows_skips_videos_without_measurement(tmp_path):
    _write(tmp_path, "aaa", ["static_image", "motion_clip"])
    (tmp_path / "bbb").mkdir()
    rows = ml._scene_rows(tmp_path)
    assert [r["video_id"] for r in rows] == ["aaa", "aaa"]
    assert rows[0]["predicted"] == "static_image"


def test_stratified_sample_is_balanced_and_deterministic(tmp_path):
    _write(tmp_path, "aaa", ["motion_clip"] * 40 + ["static_image"] * 10 + ["animated_still"] * 5)
    rows = ml._scene_rows(tmp_path)
    picked = ml.stratified_sample(rows, n=9, seed=7)
    counts = {}
    for r in picked:
        counts[r["predicted"]] = counts.get(r["predicted"], 0) + 1
    assert counts == {"static_image": 3, "animated_still": 3, "motion_clip": 3}
    again = ml.stratified_sample(ml._scene_rows(tmp_path), n=9, seed=7)
    assert [r["scene"] for r in picked] == [r["scene"] for r in again]
    # item_id가 클래스 순서를 드러내면 블라인드가 깨진다
    assert [r["predicted"] for r in picked] != ["static_image"] * 3 + ["animated_still"] * 3 + ["motion_clip"] * 3


def test_strip_times_burst_is_dense_where_stills_are_not():
    stills = ml._strip_times(0.0, 10.0, "stills")
    burst = ml._strip_times(0.0, 10.0, "burst")
    assert len(stills) == 4 and len(burst) == 6
    gaps = [round(b - a, 3) for a, b in zip(burst[1:5], burst[2:5])]
    assert gaps == [0.1, 0.1, 0.1], "연사 구간은 0.1초 간격이어야 연속 움직임이 보인다"


def test_cohens_kappa_matches_hand_computation():
    cls = ["a", "b"]
    assert ml.cohens_kappa(["a", "a", "b", "b"], ["a", "a", "b", "b"], cls) == 1.0
    assert ml.cohens_kappa(["a", "b", "a", "b"], ["a", "a", "b", "b"], cls) == 0.0
    assert ml.cohens_kappa([], [], cls) is None


def test_score_reports_gate_and_per_class(tmp_path):
    key = [{"item_id": f"m{i}", "predicted": p} for i, p in enumerate(
        ["motion_clip"] * 4 + ["static_image"] * 2)]
    sheet = [{"item_id": f"m{i}", "label": l} for i, l in enumerate(
        ["motion_clip"] * 4 + ["static_image", "motion_clip"])]
    kp, sp = tmp_path / "key.jsonl", tmp_path / "sheet.jsonl"
    for path, rows in ((kp, key), (sp, sheet)):
        path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    r = ml.score(str(sp), str(kp))
    assert r["n_labeled"] == 6 and r["agreement"] == round(5 / 6, 3)
    assert r["per_class"]["motion_clip"]["precision"] == 1.0
    assert r["per_class"]["static_image"]["precision"] == 0.5
    assert r["passed"] is (r["agreement"] >= 0.75 and r["kappa"] >= 0.6)


def test_score_without_labels_errors(tmp_path):
    kp, sp = tmp_path / "key.jsonl", tmp_path / "sheet.jsonl"
    kp.write_text(json.dumps({"item_id": "m0", "predicted": "motion_clip"}), encoding="utf-8")
    sp.write_text(json.dumps({"item_id": "m0", "label": None}), encoding="utf-8")
    assert "error" in ml.score(str(sp), str(kp))


def test_compose_joins_frames_with_separators():
    frames = [np.zeros((10, 4, 3), np.uint8), np.zeros((10, 6, 3), np.uint8)]
    strip = ml._compose(frames, 10)
    assert strip.shape == (10, 4 + 6 + 6, 3)
