"""리플레이 히트맵(most-replayed) 파생 지표.

heatmap: [{"start_time": s, "end_time": s, "value": 0..1}] — 100구간.
첫 구간은 관행적으로 value≈1(시작 스파이크)이라 피크 탐지에서 곡 앞 5% 제외.
"""
import numpy as np

HEAD_SKIP_RATIO = 0.05


def _mid_times_values(heatmap):
    t = np.array([(h["start_time"] + h["end_time"]) / 2 for h in heatmap])
    v = np.array([h["value"] for h in heatmap], dtype=float)
    return t, v


def slope_first_30s(heatmap):
    """0~30초 value의 선형 기울기(1/s). 음수일수록 초반 이탈이 가파름."""
    t, v = _mid_times_values(heatmap)
    m = t <= 30.0
    if m.sum() < 3:
        return None
    return round(float(np.polyfit(t[m], v[m], 1)[0]), 6)


def peak_stats(heatmap, duration_s):
    """(피크 위치/곡 길이 비율, 피크 값) — 곡 앞 5% 제외."""
    t, v = _mid_times_values(heatmap)
    m = t >= duration_s * HEAD_SKIP_RATIO
    if not m.any():
        return None, None
    i = int(np.argmax(v[m]))
    return round(float(t[m][i] / duration_s), 4), round(float(v[m][i]), 4)


def heatmap_features(heatmap, duration_s):
    if not heatmap or not duration_s:
        return None
    ratio, value = peak_stats(heatmap, duration_s)
    return {"heat_slope_first_30s": slope_first_30s(heatmap),
            "heat_peak_at_ratio": ratio, "heat_peak_value": value}
