import numpy as np

from mv_analyzer.motion_global import classify_v2, decompose_flow


def _texture(h=180, w=320, seed=3):
    rng = np.random.default_rng(seed)
    return np.clip(rng.normal(128, 60, (h, w)), 0, 255).astype(np.uint8)


def test_pure_translation_is_global_not_residual():
    a = _texture()
    b = np.roll(a, 6, axis=1)
    g, r = decompose_flow(a, b)
    assert g > 3.0, "화면 전체가 밀리면 전역 성분이 커야 한다"
    assert r < g / 2, "순수 팬에는 잔차가 거의 없어야 한다"
    assert classify_v2(g, r, static_global=0.35, still_residual=r + 1) == "animated_still"


def test_local_object_motion_shows_up_as_residual():
    a = _texture()
    b = a.copy()
    # 배경은 그대로 두고 밝은 사각형 하나만 옮긴다 (추적 가능한 국소 움직임)
    a[60:110, 60:110] = 255
    b[60:110, 78:128] = 255
    g, r = decompose_flow(a, b)
    assert r > g, "일부 영역만 움직이면 아핀으로 설명되지 않아 잔차가 커진다"
    assert classify_v2(g, r, still_residual=0.45) == "motion_clip"


def test_identical_frames_are_static():
    a = _texture()
    g, r = decompose_flow(a, a.copy())
    assert g < 0.35 and r < 0.45
    assert classify_v2(g, r) == "static_image"
