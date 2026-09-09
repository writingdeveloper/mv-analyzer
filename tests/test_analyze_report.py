import json
from pathlib import Path

import numpy as np
import pytest

from mv_analyzer.analyze_report import (
    assert_analyze_report_safe,
    build_analyze_report,
    fit_reference_pca,
    summarize_numeric,
    write_analyze_report,
)
from mv_analyzer.reference_corpus import load_reference_rows


ROOT = Path(__file__).resolve().parents[1]


def test_midrank_percentile_and_population_zscore():
    values = [10.0, 20.0, 20.0, 30.0]
    stat = summarize_numeric(values, 20.0)

    assert stat["reference_mean"] == pytest.approx(20.0)
    assert stat["reference_std"] == pytest.approx(float(np.std(values)))
    assert stat["percentile"] == 50.0
    assert stat["z"] == pytest.approx(0.0)
    assert stat["reference_n"] == 4


def test_reference_pca_fit_does_not_depend_on_imported_target():
    reference = [
        {"a": 1.0, "b": 1.0, "c": 2.0},
        {"a": 2.0, "b": 3.0, "c": 1.0},
        {"a": 3.0, "b": 2.0, "c": 4.0},
        {"a": 4.0, "b": 5.0, "c": 3.0},
        {"a": 5.0, "b": 4.0, "c": 6.0},
    ]
    first = fit_reference_pca(reference, {"a": 3.0, "b": 3.0, "c": 3.0}, ["a", "b", "c"])
    extreme = fit_reference_pca(reference, {"a": 3000.0, "b": -4000.0, "c": 9000.0}, ["a", "b", "c"])

    assert np.asarray(first["loadings"]) == pytest.approx(np.asarray(extreme["loadings"]))
    assert first["reference_scale"] == pytest.approx(extreme["reference_scale"])
    assert first["explained_variance_pct"] == pytest.approx(extreme["explained_variance_pct"])
    assert first["score"] != extreme["score"]


def test_build_analyze_report_uses_tracked_reference_corpus():
    target = dict(load_reference_rows(ROOT, "all")[0])
    report = build_analyze_report(ROOT, target, domain="all")

    assert report["schema_version"] == 2
    assert report["kind"] == "mv-analyzer-report"
    assert report["benchmark"]["corpus_id"] == "extreme-reference-2026-07"
    assert report["benchmark"]["domain"] == "all"
    assert report["benchmark"]["n"] == 100
    assert report["benchmark"]["warning"] == "descriptive-reference-only"
    assert report["video"]["video_id"] == target["video_id"]
    assert report["features"]
    assert all("labels" in feature and set(feature["labels"]) == {"ko", "en"} for feature in report["features"])
    assert all(feature["category"] for feature in report["features"])
    assert len(report["pca"]["score"]) == 3
    assert len(report["pca"]["display"]) == 3
    assert len(report["neighbors"]) <= 5
    assert all(row["video_id"] != target["video_id"] for row in report["neighbors"])
    assert report["centroids"]["coverage"] >= 0.60
    assert_analyze_report_safe(report)


def test_domain_filter_changes_benchmark_population():
    target = dict(load_reference_rows(ROOT, "vocaloid")[0])
    report = build_analyze_report(ROOT, target, domain="vocaloid")

    assert report["benchmark"]["domain"] == "vocaloid"
    assert report["benchmark"]["n"] == 50
    assert all(row["domain"] == "vocaloid" for row in report["neighbors"])


@pytest.mark.parametrize(
    "mutation",
    [
        {"raw_lyrics": "copyrighted text"},
        {"thumb_text_content": "OCR text"},
        {"local_path": r"C:\\Users\\name\\secret.json"},
        {"x": r"C:\\Users\\name\\secret.json"},
        {"x": "file:///tmp/video.mp4"},
        {"x": "http://127.0.0.1:11434/api/generate"},
        {"x": "http://192.168.1.5/internal"},
        {"x": "https://r1---sn.googlevideo.com/videoplayback?expire=1&sig=abc"},
    ],
)
def test_report_rejects_unsafe_content(mutation):
    report = {
        "schema_version": 1,
        "kind": "mv-analyzer-report",
        "video": {"video_id": "abcdefghijk", "title": "Example", "channel": "Channel"},
    }
    report.update(mutation)

    with pytest.raises(ValueError, match="unsafe|local path|private|signed"):
        assert_analyze_report_safe(report)


def test_atomic_writer_leaves_safe_json_and_no_tmp(tmp_path):
    target = dict(load_reference_rows(ROOT, "all")[0])
    report = build_analyze_report(ROOT, target)
    destination = tmp_path / "my-mv.json"

    write_analyze_report(destination, report)

    assert json.loads(destination.read_text(encoding="utf-8"))["kind"] == "mv-analyzer-report"
    assert not (tmp_path / "my-mv.json.tmp").exists()


def test_atomic_writer_does_not_publish_unsafe_report(tmp_path):
    destination = tmp_path / "unsafe.json"
    report = {"schema_version": 1, "kind": "mv-analyzer-report", "raw_lyrics": "do not publish"}

    with pytest.raises(ValueError):
        write_analyze_report(destination, report)

    assert not destination.exists()
    assert not (tmp_path / "unsafe.json.tmp").exists()
