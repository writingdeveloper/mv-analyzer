import cv2
import numpy as np

from mv_analyzer.motion import analyze_motion


def _video(path, moving):
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (160, 120))
    assert out.isOpened()
    for i in range(30):
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        x = 20 + (i * 2 if moving else 0)
        cv2.rectangle(frame, (x, 40), (x + 30, 70), (255, 255, 255), -1)
        out.write(frame)
    out.release()


def test_motion_distinguishes_moving_from_static(tmp_path):
    static = tmp_path / "static.mp4"
    moving = tmp_path / "moving.mp4"
    _video(static, False)
    _video(moving, True)
    a = analyze_motion(static, sample_fps=5)
    b = analyze_motion(moving, sample_fps=5)
    assert a["motion_mean"] is not None
    assert b["motion_mean"] > a["motion_mean"]
    assert b["motion_static_ratio"] <= a["motion_static_ratio"]


def test_motion_rejects_bad_rate(tmp_path):
    try:
        analyze_motion(tmp_path / "none.mp4", sample_fps=0)
    except ValueError as e:
        assert "sample_fps" in str(e)
    else:
        raise AssertionError("expected ValueError")
