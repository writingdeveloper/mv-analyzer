import os
import subprocess

import pytest

from mv_analyzer.scenes import analyze_scenes

PILOT_MP4 = os.path.join("pilot", "video.mp4")


@pytest.fixture(scope="module")
def test_clip(tmp_path_factory):
    """색이 두 번 바뀌는 12초 합성 클립 → 씬 3개 기대."""
    d = tmp_path_factory.mktemp("clip")
    parts = []
    for i, color in enumerate(["red", "blue", "green"]):
        p = str(d / f"{i}.mp4")
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                        f"color=c={color}:s=320x180:d=4:r=24", p],
                       check=True, capture_output=True)
        parts.append(p)
    lst = d / "list.txt"
    lst.write_text("\n".join(f"file '{p}'" for p in parts))
    out = str(d / "clip.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i",
                    str(lst), "-c", "copy", out], check=True, capture_output=True)
    return out


def test_analyze_scenes_synthetic(test_clip, tmp_path):
    out = analyze_scenes(test_clip, str(tmp_path / "kf"))
    assert out["summary"]["num_scenes"] == 3
    assert abs(out["summary"]["duration_s"] - 12.0) < 0.5
    row = out["scenes"][0]
    for key in ["start_s", "end_s", "len_s", "brightness", "saturation",
                "dominant_color", "keyframe"]:
        assert key in row
    assert len(os.listdir(tmp_path / "kf")) == 3


@pytest.mark.slow
@pytest.mark.media
@pytest.mark.skipif(not os.path.exists(PILOT_MP4), reason="pilot 미디어 없음")
def test_pilot_regression(tmp_path):
    out = analyze_scenes(PILOT_MP4, str(tmp_path / "kf"))
    assert out["summary"]["num_scenes"] == 49  # threshold 15.0 재기준선 (27.0 시절 44)


def test_no_cut_video_yields_single_scene(tmp_path):
    """단색 클립은 컷이 없어도 전체를 1씬으로 반환해야 한다."""
    clip = str(tmp_path / "solid.mp4")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    "color=c=blue:s=320x180:d=5:r=24", clip],
                   check=True, capture_output=True)
    out = analyze_scenes(clip, str(tmp_path / "kf"))
    assert out["summary"]["num_scenes"] == 1
    assert abs(out["scenes"][0]["end_s"] - 5.0) < 0.5
    assert len(os.listdir(tmp_path / "kf")) == 1


def test_reanalysis_cleans_stale_keyframes(test_clip, tmp_path):
    kf = tmp_path / "kf_reuse"
    kf.mkdir()
    (kf / "scene_999.jpg").write_bytes(b"stale")
    analyze_scenes(test_clip, str(kf))
    assert not (kf / "scene_999.jpg").exists()
    assert len(list(kf.glob("scene_*.jpg"))) == 3
