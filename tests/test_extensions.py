from mv_analyzer.extensions import derived_features, scene_dynamics


def test_scene_dynamics_color_change():
    x = scene_dynamics({"scenes": [
        {"brightness": 0.2, "saturation": 0.1, "dominant_color": "#000000"},
        {"brightness": 0.8, "saturation": 0.9, "dominant_color": "#ffffff"},
    ]})
    assert x["ext_scene_brightness_std"] == 0.3
    assert x["ext_color_change_mean"] == 1.0
    assert x["ext_color_unique_ratio"] == 1.0


def test_derived_chorus_ratio():
    lines = [{"t_s": i * 10, "line": f"line {i}"} for i in range(7)]
    lines += [{"t_s": 70, "line": "repeat chorus"}, {"t_s": 80, "line": "repeat chorus"}]
    x = derived_features({"duration_s": 100}, {"scenes": []}, {"lines": lines})
    assert x["ext_lyrics_first_chorus_s"] == 80
    assert x["ext_lyrics_first_chorus_ratio"] == 0.8
