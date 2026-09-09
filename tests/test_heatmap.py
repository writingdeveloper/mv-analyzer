from mv_analyzer.heatmap import heatmap_features, peak_stats, slope_first_30s


def make_heatmap(values, duration=200.0):
    n = len(values)
    step = duration / n
    return [{"start_time": i * step, "end_time": (i + 1) * step, "value": v}
            for i, v in enumerate(values)]


def test_slope_negative_for_decaying_start():
    hm = make_heatmap([1.0 - i * 0.01 for i in range(100)], duration=200.0)
    assert slope_first_30s(hm) < 0


def test_slope_none_with_too_few_points():
    hm = make_heatmap([1.0, 0.5], duration=400.0)  # 30초 안 구간 부족
    assert slope_first_30s(hm) is None


def test_peak_skips_head_spike():
    values = [1.0] + [0.1] * 69 + [0.9] + [0.1] * 29  # 시작 스파이크 + 70% 지점 피크
    ratio, value = peak_stats(make_heatmap(values, 200.0), 200.0)
    assert abs(ratio - 0.7) < 0.02 and value == 0.9


def test_heatmap_features_empty_returns_none():
    assert heatmap_features([], 200.0) is None
