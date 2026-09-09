from mv_analyzer.monotonicity import METRICS, render_report, run_analysis, verdict


def _rows(metric, values):
    return [{metric: v} for v in values]


def test_run_analysis_detects_monotone_metric():
    metric = METRICS[0]
    bottom = _rows(metric, [1, 2, 3, 2, 1])
    middle = _rows(metric, [10, 11, 9, 10, 12])
    top = _rows(metric, [20, 21, 19, 22, 20])
    results = run_analysis(bottom, middle, top, metrics=[metric])
    assert len(results) == 1
    r = results[0]
    assert r["metric"] == metric
    assert r["median_order"] == "증가"
    assert r["med_bottom"] < r["med_middle"] < r["med_top"]
    assert r["q"] < 0.05
    assert verdict(r) == "단조성 성립"


def test_run_analysis_non_monotone_metric():
    metric = METRICS[0]
    bottom = _rows(metric, [1, 2, 1, 2, 1])
    middle = _rows(metric, [1, 2, 1, 2, 1])
    top = _rows(metric, [1, 2, 1, 2, 1])
    results = run_analysis(bottom, middle, top, metrics=[metric])
    r = results[0]
    assert verdict(r) != "단조성 성립"


def test_run_analysis_skips_metric_below_min_n():
    metric = METRICS[0]
    bottom = _rows(metric, [1, 2])       # min_n=3 미달
    middle = _rows(metric, [1, 2, 3])
    top = _rows(metric, [1, 2, 3])
    results = run_analysis(bottom, middle, top, metrics=[metric])
    assert results == []


def test_run_analysis_ignores_missing_values():
    metric = METRICS[0]
    bottom = [{metric: 1}, {metric: None}, {metric: 2}, {metric: 3}]
    middle = _rows(metric, [10, 11, 12])
    top = _rows(metric, [20, 21, 22])
    results = run_analysis(bottom, middle, top, metrics=[metric])
    assert results[0]["n_bottom"] == 3  # None 제외


def test_verdict_direction_ok_but_not_significant():
    r = {"median_order": "증가", "q": 0.5}
    assert verdict(r) == "방향 일치(비유의)"


def test_verdict_not_monotone():
    r = {"median_order": "비단조", "q": 0.001}
    assert verdict(r) == "단조성 불성립"


def test_render_report_contains_metric_and_verdict():
    metric = METRICS[0]
    bottom = _rows(metric, [1, 2, 3, 2, 1])
    middle = _rows(metric, [10, 11, 9, 10, 12])
    top = _rows(metric, [20, 21, 19, 22, 20])
    results = run_analysis(bottom, middle, top, metrics=[metric])
    report = render_report(results, 5, 5, 5, "2026-07-22")
    assert metric in report
    assert "단조성 성립" in report
    assert "하위 5" in report and "중간 5" in report and "상위 5" in report
