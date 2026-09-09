import json

import cv2
import numpy as np

from mv_analyzer.motion import (classify_motion, classify_scene_motion, measure_scene_motion,
                                summarize_scene_motion)

FPS, W, H, N = 10.0, 160, 120, 30


def _texture(seed=3):
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 255, (H * 2, W * 2), dtype=np.uint8)
    return cv2.GaussianBlur(base, (0, 0), 4)  # 큰 구조가 있는 텍스처 (flow 추정 가능)


def _write(path, frames):
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    assert out.isOpened()
    for fr in frames:
        out.write(cv2.cvtColor(fr, cv2.COLOR_GRAY2BGR))
    out.release()


def _static():
    tex = _texture()[:H, :W]
    return [tex.copy() for _ in range(N)]


def _pan():
    tex = _texture()
    return [tex[10:10 + H, 10 + i * 2:10 + i * 2 + W].copy() for i in range(N)]


def _object():
    tex = _texture()[:H, :W]
    frames = []
    for i in range(N):
        fr = tex.copy()
        x = 10 + i * 2
        cv2.rectangle(fr, (x, 20), (x + 80, 100), 255, -1)
        frames.append(fr)
    return frames


def test_classify_motion_thresholds():
    assert classify_motion(0.1, 50.0) == "static_image"
    assert classify_motion(3.0, 0.5) == "animated_still"
    assert classify_motion(3.0, 5.0) == "motion_clip"


def test_scene_motion_three_classes(tmp_path):
    whole = [{"scene": 0, "start_s": 0.0, "end_s": N / FPS}]
    results = {}
    for name, frames in (("static", _static()), ("pan", _pan()), ("object", _object())):
        p = tmp_path / f"{name}.mp4"
        _write(p, frames)
        results[name] = classify_scene_motion(p, whole, gap_s=0.2)[0]
    assert results["static"]["motion_type"] == "static_image"
    assert results["pan"]["flow_mag_mean"] > results["static"]["flow_mag_mean"]
    assert results["pan"]["flow_variance"] < results["object"]["flow_variance"]
    assert results["pan"]["motion_type"] == "animated_still"
    assert results["object"]["motion_type"] == "motion_clip"


def test_short_scene_and_summary(tmp_path):
    p = tmp_path / "mixed.mp4"
    _write(p, _static()[:10] + _object()[:20])
    scenes = [{"scene": 0, "start_s": 0.0, "end_s": 1.0},
              {"scene": 1, "start_s": 1.0, "end_s": 1.2},   # gap(0.4s)보다 짧은 씬
              {"scene": 2, "start_s": 1.2, "end_s": 3.0}]
    rows = classify_scene_motion(p, scenes)
    assert [r["scene"] for r in rows] == [0, 1, 2]
    assert all(r["n_pairs"] >= 1 for r in rows)
    s = summarize_scene_motion(rows)
    assert s["motion_scene_n"] == 3
    total = (s["motion_scene_static_ratio"] + s["motion_scene_animated_still_ratio"]
             + s["motion_scene_clip_ratio"])
    assert abs(total - 1.0) < 1e-6
    assert 0.0 <= s["motion_scene_clip_time_ratio"] <= 1.0


def test_measure_scene_motion_writes_json(tmp_path):
    d = tmp_path / "abcdefghijk"
    d.mkdir()
    _write(d / "video.mp4", _object())
    (d / "scenes.json").write_text(json.dumps({"scenes": [
        {"scene": 0, "start_s": 0.0, "end_s": 1.5}, {"scene": 1, "start_s": 1.5, "end_s": 3.0}]}),
        encoding="utf-8")
    payload = measure_scene_motion(d)
    saved = json.loads((d / "motion_scenes.json").read_text(encoding="utf-8"))
    assert saved["summary"] == payload["summary"]
    assert len(saved["scenes"]) == 2
    assert saved["params"]["gap_s"] == 0.4


def test_summary_handles_unknown_only():
    s = summarize_scene_motion([{"scene": 0, "start_s": 0, "end_s": 1, "motion_type": "unknown"}])
    assert s["motion_scene_n"] == 0 and s["motion_scene_unknown"] == 1
    assert s["motion_scene_clip_ratio"] is None
