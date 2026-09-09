import os
import time

from mv_analyzer import provenance


def test_stage_fingerprint_is_stable():
    a = provenance.stage_fingerprint("scenes.json")
    assert a and a == provenance.stage_fingerprint("scenes.json")


def test_manifest_marks_old_file_legacy(tmp_path):
    p = tmp_path / "scenes.json"
    p.write_text("{}", encoding="utf-8")
    old = time.time() - 10
    os.utime(p, (old, old))
    m = provenance.write_analysis_manifest(tmp_path, lang="ja", run_started_s=time.time())
    assert m["artifacts"]["scenes.json"]["status"] == "legacy_reused"
    assert m["artifacts"]["scenes.json"]["fingerprint"] is None
    assert m["runtime"]["models"]["vlm"]
    assert m["runtime"]["models"]["asr"]


def test_artifact_stale_only_when_manifest_has_fingerprint(tmp_path, monkeypatch):
    p = tmp_path / "scenes.json"
    p.write_text("{}", encoding="utf-8")
    current = provenance.stage_fingerprint("scenes.json")
    (tmp_path / "analysis_manifest.json").write_text(
        __import__("json").dumps({"artifacts": {"scenes.json": {"fingerprint": current}}}),
        encoding="utf-8",
    )
    assert provenance.artifact_is_stale(tmp_path, "scenes.json") is False
