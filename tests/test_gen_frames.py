import json

import cv2
import numpy as np
import pytest

from mv_analyzer import gen_frames as gf


def _frame(w=320, h=180, bar=0, value=180):
    im = np.full((h, w, 3), value, np.uint8)
    if bar:
        im[:, :bar] = 5
        im[:, w - bar:] = 5
    return im


def test_detect_bars_finds_pillarbox():
    assert gf.detect_bars(_frame(bar=40))[:2] == (40, 40)
    assert gf.detect_bars(_frame())[:2] == (0, 0)


def test_thin_edges_are_ignored():
    # 변 길이의 1.5% 미만(320px에서 4px)은 인코딩 잡티로 본다
    assert gf.detect_bars(_frame(bar=3))[:2] == (0, 0)


def test_crop_is_symmetric_even_when_bars_differ():
    im = _frame(bar=40)
    im[:, 320 - 38:] = 180          # 오른쪽 띠만 2px 얇게
    im[:, 320 - 40:320 - 38] = 5
    out, bars = gf.crop_bars(im)
    assert bars[0] == bars[1], "좌우가 어긋나도 출력 크기는 하나로 모여야 한다"
    assert out.shape[1] == 320 - 2 * bars[0]


def test_dark_frame_is_not_cropped_away():
    dark = np.full((180, 320, 3), 4, np.uint8)
    out, bars = gf.crop_bars(dark)
    assert bars == (0, 0, 0, 0) and out.shape == dark.shape


def _fixture_video(path, n_frames=60, bar=0):
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 30.0, (320, 180))
    for i in range(n_frames):
        vw.write(_frame(bar=bar, value=60 + i * 2))
    vw.release()


def test_build_uses_clean_source_and_names_like_keyframes(tmp_path):
    for vid, bar in (("subbed", 40), ("clean", 40)):
        d = tmp_path / vid
        d.mkdir()
        _fixture_video(d / "video.mp4", bar=bar)
    (tmp_path / "subbed" / "scenes.json").write_text(json.dumps({"summary": {}, "scenes": [
        {"scene": 0, "start_s": 0.0, "end_s": 1.0},
        {"scene": 1, "start_s": 1.0, "end_s": 2.0}]}), encoding="utf-8")

    out = tmp_path / "gen"
    r = gf.build("subbed", str(tmp_path), clean_source="clean", out_dir=str(out))
    assert r["n"] == 2 and r["source"] == "clean" and not r["failed"]
    assert (out / "scene_000.jpg").exists() and (out / "scene_001.jpg").exists()
    assert r["n_cropped"] == 2
    assert cv2.imread(str(out / "scene_000.jpg")).shape[1] == 320 - 80


def test_build_rejects_missing_source(tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "scenes.json").write_text(json.dumps({"scenes": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        gf.build("x", str(tmp_path))
