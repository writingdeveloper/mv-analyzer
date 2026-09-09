import json
from pathlib import Path

import pytest

from mv_analyzer.web_export import assert_public_safe, build_public_snapshot

ROOT = Path(__file__).resolve().parents[1]


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def test_public_snapshot_has_expected_contract_and_counts(tmp_path):
    paths = build_public_snapshot(ROOT, tmp_path / "public")
    assert set(paths) == {
        "manifest", "overview", "videos", "features", "domains",
        "correlations", "retention", "space", "experiments", "methodology", "demo-report", "demo-reason",
    }
    manifest = _load(paths["manifest"])
    overview = _load(paths["overview"])
    videos = _load(paths["videos"])
    features = _load(paths["features"])
    domains = _load(paths["domains"])
    assert manifest["schema_version"] == 1
    assert overview["video_count"] == 100
    assert len(videos) == 100
    assert domains["vocaloid"]["n_top"] == 25
    assert domains["vocaloid"]["n_bottom"] == 25
    assert domains["kpop"]["n_top"] == 25
    assert domains["kpop"]["n_bottom"] == 25
    assert all("features" in row for row in videos)
    assert all("local_path" not in row for row in videos)
    assert features
    assert all(set(feature["labels"]) == {"ko", "en"} for feature in features)
    assert all(feature["labels"]["ko"] and feature["labels"]["en"] for feature in features)
    space = _load(paths["space"])
    assert space["normalization"]["method"] == "zscore"
    assert space["normalization"]["imputation"] == "median"
    assert len(space["loadings"]) == 3
    assert all(pc["items"] for pc in space["loadings"])
    assert all(set(item["labels"]) == {"ko", "en"} for pc in space["loadings"] for item in pc["items"])
    assert all("score" in point for point in space["points"])



def test_public_snapshot_includes_valid_reason_demo(tmp_path):
    from mv_analyzer.reason_contract import validate_reason_document
    paths = build_public_snapshot(ROOT, tmp_path / "public")
    reason = _load(paths["demo-reason"])
    validate_reason_document(reason)
    assert reason["kind"] == "mv-analyzer-reason"
    assert reason["source_report"]["source_features_sha256"] == _load(paths["demo-report"])["pipeline"]["source_features_sha256"]


def test_public_snapshot_matches_existing_dashboard_statistic(tmp_path):
    from build_dashboard import compute_domain, load_vocaloid

    legacy = compute_domain(load_vocaloid(), "test", "test")
    legacy_cut = next(x for x in legacy["numeric"] if x["id"] == "scene_cuts_per_minute")
    paths = build_public_snapshot(ROOT, tmp_path / "public")
    domains = _load(paths["domains"])
    current_cut = next(
        x for x in domains["vocaloid"]["numeric"]
        if x["id"] == "scene_cuts_per_minute"
    )
    assert current_cut["median_top"] == pytest.approx(legacy_cut["medTop"], abs=1e-3)
    assert current_cut["median_bottom"] == pytest.approx(legacy_cut["medBot"], abs=1e-3)
    assert current_cut["delta"] == pytest.approx(legacy_cut["delta"], abs=1e-3)
    assert current_cut["q"] == pytest.approx(legacy_cut["q"], abs=1e-4)


def test_public_snapshot_is_deterministic_and_safe(tmp_path):
    a = build_public_snapshot(ROOT, tmp_path / "a")
    b = build_public_snapshot(ROOT, tmp_path / "b")
    ma = _load(a["manifest"])
    mb = _load(b["manifest"])
    assert ma["snapshot_id"] == mb["snapshot_id"]
    assert ma["files"] == mb["files"]
    for key, path in a.items():
        text = Path(path).read_text(encoding="utf-8")
        if key != "manifest":
            assert ma["files"][Path(path).name]["sha256"]
        assert_public_safe(json.loads(text))


def test_public_safety_rejects_private_or_signed_values():
    bad = [
        {"x": r"C:\Users\name\secret.json"},
        {"x": "http://127.0.0.1:11434/api/generate"},
        {"x": "http://192.168.1.5/internal"},
        {"x": "https://r1---sn.googlevideo.com/videoplayback?expire=1&sig=abc"},
        {"lyrics": "raw full lyric text should not be public"},
    ]
    for value in bad:
        with pytest.raises(ValueError):
            assert_public_safe(value)


def test_git_commit_prefers_deployment_environment(monkeypatch, tmp_path):
    from mv_analyzer.web_export import _git_commit

    sha = "a" * 40
    monkeypatch.setenv("MV_ANALYZER_GIT_COMMIT", sha)
    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", "b" * 40)
    assert _git_commit(tmp_path) == sha


def test_git_commit_uses_vercel_git_sha_when_available(monkeypatch, tmp_path):
    from mv_analyzer.web_export import _git_commit

    monkeypatch.delenv("MV_ANALYZER_GIT_COMMIT", raising=False)
    sha = "b" * 40
    monkeypatch.setenv("VERCEL_GIT_COMMIT_SHA", sha)
    assert _git_commit(tmp_path) == sha


def test_public_snapshot_exposes_reference_corpus_metadata(tmp_path):
    paths = build_public_snapshot(ROOT, tmp_path / "public")
    manifest = _load(paths["manifest"])
    methodology = _load(paths["methodology"])

    assert manifest["reference_corpus"]["id"] == "extreme-reference-2026-07"
    assert manifest["reference_corpus"]["n"] == 100
    assert methodology["reference_corpus"]["label"] == "Extreme Reference Corpus v2026.07"
    assert methodology["reference_corpus"]["sampling"] == "extreme-groups"


def test_sample_expansion_prefers_public_safe_summary(tmp_path):
    from mv_analyzer.web_export import _sample_expansion
    work=tmp_path/"work"; work.mkdir()
    expected={"vocaloid":{"target_per_group":40,"eligible_population":495,"max_top":40,"max_bottom":40,"require_mv_marker":False,"channel_cap":2,"feasible":True},"kpop":{"target_per_group":40,"eligible_population":998,"max_top":38,"max_bottom":23,"require_mv_marker":True,"channel_cap":2,"feasible":False}}
    (work/"sample_expansion.json").write_text(json.dumps(expected),encoding="utf-8")
    assert _sample_expansion(tmp_path)==expected
