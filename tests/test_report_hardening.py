import copy
from pathlib import Path

import pytest

from mv_analyzer.analyze_report import build_analyze_report, assert_analyze_report_safe
from mv_analyzer.reference_corpus import load_reference_rows, reference_corpus_public_metadata

ROOT = Path(__file__).resolve().parents[1]


def full_report():
    return build_analyze_report(ROOT, dict(load_reference_rows(ROOT)[0]))


def test_sparse_target_never_gets_fabricated_pca_coordinates():
    r = build_analyze_report(ROOT, {"video_id": "abcdefghijk", "title": "Sparse", "channel": "Test", "duration_s": 120})
    assert r["pca"]["status"] == "insufficient_coverage"
    assert r["pca"]["observed_count"] == 0
    assert r["pca"]["score"] is None
    assert r["pca"]["display"] is None
    assert not r["neighbors"]


def test_empty_target_is_not_a_completed_analysis():
    with pytest.raises(ValueError):
        build_analyze_report(ROOT, {"video_id": "abcdefghijk", "title": "Empty", "channel": "Test"})


@pytest.mark.parametrize("path,value", [
    (("features",0,"percentile"),150),
    (("features",0,"reference_n"),-1),
    (("features",0,"reference_std"),-2),
    (("features",0,"z"),987654),
    (("centroids","coverage"),9),
    (("neighbors",0,"distance"),-1),
    (("benchmark","corpus_id"),"unknown-corpus"),
    (("pca","explained_variance_pct"),[200,-100,50]),
])
def test_python_report_boundary_rejects_impossible_values(path,value):
    r = full_report()
    node = r
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    with pytest.raises(ValueError):
        assert_analyze_report_safe(r)


@pytest.mark.parametrize("field", ["empty", "duplicate"])
def test_report_features_are_nonempty_and_unique(field):
    r = full_report()
    r["features"] = [] if field == "empty" else [*r["features"], copy.deepcopy(r["features"][0])]
    with pytest.raises(ValueError):
        assert_analyze_report_safe(r)


@pytest.mark.parametrize("text", ["/home/user/private.json", "\\\\server\\share\\private.json", "http://[::1]/private", "100.98.70.103"])
def test_report_rejects_cross_platform_paths_and_internal_hosts(text):
    r = full_report()
    r["video"]["title"] = text
    with pytest.raises(ValueError):
        assert_analyze_report_safe(r)


def test_corpus_date_range_is_derived_not_hardcoded():
    rows = load_reference_rows(ROOT)
    m = reference_corpus_public_metadata(rows)
    assert m["collection_start"] == "2026-07-16"
    assert m["collection_end"] == "2026-07-21"
    assert len(m["corpus_sha256"]) == 64


def test_report_separates_measurement_from_export_provenance():
    r = full_report()
    assert r["schema_version"] == 2
    assert len(r["pipeline"]["source_features_sha256"]) == 64
    assert r["pipeline"]["measurement_git_commit"] is None
    assert r["pipeline"]["measurement_status"] == "unverified"
    assert len(r["pca"]["basis_id"]) == 64
    assert r["pca"]["observed_count"] == len(r["pca"]["features"])
    assert len(r["pca"]["reference_points"]) == 100
    assert "lyrics_compression_ratio" in r["pca"]["experimental_features"]


def test_report_writer_refuses_nan_json(tmp_path):
    from mv_analyzer.analyze_report import write_analyze_report
    r = full_report()
    r["features"][0]["value"] = float("nan")
    with pytest.raises(ValueError):
        write_analyze_report(tmp_path / "bad.json", r)
    assert not (tmp_path / "bad.json").exists()
