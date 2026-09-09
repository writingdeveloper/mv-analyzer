import pytest

from mv_analyzer import talk


def _bundle():
    return {
        "video_id": "abcdefghijk",
        "features": {"title": "demo", "duration_s": 20},
        "scenes": {"summary": {"duration_s": 20}, "scenes": [
            {"scene": 0, "start_s": 0, "end_s": 20, "len_s": 20, "keyframe": "a.jpg"}
        ]},
        "scene_tags": [],
        "lyrics": {"lines": []},
        "audio": {"energy_curve_10s": [0.2, 0.8]},
        "dir": "data/abcdefghijk",
    }


def test_energy_at_clamps_negative_index():
    out = talk.energy_at(_bundle(), -1)
    assert out["bin"] == 0
    assert out["value"] == 0.2


def test_at_rejects_negative_time():
    with pytest.raises(ValueError):
        talk.at(_bundle(), -1)


def test_at_rejects_time_past_duration():
    with pytest.raises(ValueError):
        talk.at(_bundle(), 21)
