import pytest

from mv_analyzer.motion_validation import score_motion_validation, sensitivity_summary


def _rows():
    rows = []
    for i, value in enumerate([0.05, 0.08, 0.1, 0.12]):
        rows.append({"id": f"s{i}", "label": "static", "motion_mean": value})
    for i, value in enumerate([0.8, 1.0, 1.2, 1.4]):
        rows.append({"id": f"c{i}", "label": "camera_motion", "motion_mean": value})
    for i, value in enumerate([0.6, 0.9, 1.1, 1.3]):
        rows.append({"id": f"m{i}", "label": "subject_motion", "motion_mean": value})
    return rows


def test_score_motion_validation_requires_known_labels():
    with pytest.raises(ValueError, match="unknown motion label"):
        score_motion_validation([{"label": "zoom", "motion_mean": 1.0}])


def test_score_motion_validation_checks_static_lower_than_moving():
    out = score_motion_validation(_rows())
    assert out["n"] == 12
    assert out["classes"]["static"]["median"] < out["classes"]["camera_motion"]["median"]
    assert out["classes"]["static"]["median"] < out["classes"]["subject_motion"]["median"]
    assert out["passes_ordering"] is True
    assert out["comparisons"]["static_vs_camera_motion"]["cliffs_delta"] < 0
    assert out["comparisons"]["static_vs_subject_motion"]["cliffs_delta"] < 0


def test_sensitivity_summary_scores_each_parameter_cell():
    rows = []
    for fps in (1.0, 2.0):
        for row in _rows():
            rows.append({**row, "sample_fps": fps, "static_threshold": 0.35})
    out = sensitivity_summary(rows)
    assert len(out) == 2
    assert {r["sample_fps"] for r in out} == {1.0, 2.0}
    assert all(r["passes_ordering"] for r in out)


def test_measure_corpus_motion_writes_resumeable_jsonl(tmp_path):
    import cv2
    import json
    import numpy as np

    from mv_analyzer.motion_validation import measure_corpus_motion

    d = tmp_path / "abcdefghijk"
    d.mkdir()
    video = d / "video.mp4"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (80, 60))
    assert writer.isOpened()
    for i in range(12):
        frame = np.zeros((60, 80, 3), dtype=np.uint8)
        cv2.rectangle(frame, (5 + i, 20), (20 + i, 35), (255, 255, 255), -1)
        writer.write(frame)
    writer.release()

    out = tmp_path / "motion.jsonl"
    first = measure_corpus_motion(tmp_path, out, sample_fps=2.0)
    second = measure_corpus_motion(tmp_path, out, sample_fps=2.0)
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert first == {"measured": 1, "skipped": 0, "missing_video": 0}
    assert second == {"measured": 0, "skipped": 1, "missing_video": 0}
    assert rows[0]["video_id"] == "abcdefghijk"
    assert rows[0]["sample_fps"] == 2.0
    assert rows[0]["static_threshold"] == 0.35
