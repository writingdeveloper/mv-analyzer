import numpy as np
import pytest

from mv_analyzer.stats import bh_fdr, cliffs_delta, magnitude, trend_test


def test_cliffs_delta_complete_separation():
    assert cliffs_delta([10, 11, 12], [1, 2, 3]) == 1.0
    assert cliffs_delta([1, 2, 3], [10, 11, 12]) == -1.0


def test_cliffs_delta_identical_groups():
    assert abs(cliffs_delta([1, 2, 3], [1, 2, 3])) < 1e-9


def test_bh_fdr_known_values():
    q = bh_fdr(np.array([0.01, 0.04, 0.03, 0.5]))
    assert np.allclose(q, [0.04, 0.05333333, 0.05333333, 0.5])


def test_magnitude_thresholds():
    assert magnitude(0.1) == "무시"
    assert magnitude(-0.2) == "작음"
    assert magnitude(0.4) == "중간"
    assert magnitude(-0.5) == "큼"


# ---------- trend_test (Phase 4 — 단조성 검정) ----------
# 설치된 scipy(1.18)에는 scipy.stats.jonckheere가 없음 → 항상 Kendall tau 폴백 경로.


def test_trend_test_monotone_increasing_is_significant():
    rng = np.random.default_rng(0)
    bottom = rng.normal(0, 1, 30)
    middle = rng.normal(3, 1, 30)
    top = rng.normal(6, 1, 30)
    result = trend_test([bottom, middle, top])
    assert result["p"] < 0.001
    assert result["stat"] > 0.5  # 강한 양의 단조 경향
    assert result["method"] in ("jonckheere-terpstra", "kendall_tau")


def test_trend_test_monotone_decreasing_is_significant_negative():
    rng = np.random.default_rng(1)
    bottom = rng.normal(6, 1, 30)
    middle = rng.normal(3, 1, 30)
    top = rng.normal(0, 1, 30)
    result = trend_test([bottom, middle, top])
    assert result["p"] < 0.001
    assert result["stat"] < -0.5


def test_trend_test_non_monotone_not_significant():
    # 중간 그룹이 양끝보다 높음(뒤집힌 U) — 단조 경향 없음
    rng = np.random.default_rng(2)
    bottom = rng.normal(0, 1, 30)
    middle = rng.normal(6, 1, 30)
    top = rng.normal(0, 1, 30)
    result = trend_test([bottom, middle, top])
    assert result["p"] > 0.05
    assert abs(result["stat"]) < 0.3


def test_trend_test_uses_kendall_fallback_when_jt_unavailable():
    from mv_analyzer import stats as stats_mod

    if hasattr(stats_mod.stats, "jonckheere"):
        pytest.skip("설치된 scipy가 jonckheere를 제공 — 폴백 경로 미해당")
    result = trend_test([[1, 2], [3, 4], [5, 6]])
    assert result["method"] == "kendall_tau"
