import csv
import json
from pathlib import Path

from mv_analyzer.reference_corpus import load_reference_rows, reference_corpus_public_metadata
from scripts.audit_public_release import audit_public_release
from scripts.build_public_release import build_public_release

ROOT = Path(__file__).resolve().parents[1]


def _csv_header(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as fh:
        return next(csv.reader(fh))


def test_public_release_builder_creates_clean_sanitized_tree(tmp_path):
    out = tmp_path / "public"
    manifest = build_public_release(ROOT, out)
    assert manifest["history_mode"] == "clean-history-required"
    assert (out / "LICENSE").exists()
    assert (out / "NOTICE").exists()
    assert (out / "THIRD_PARTY_LICENSES.md").exists()
    assert (out / "DATA_LICENSE.md").exists()
    assert (out / "SECURITY.md").exists()
    assert (out / "CONTRIBUTING.md").exists()
    assert (out / "CITATION.cff").exists()
    assert not (out / "CLAUDE.md").exists()
    assert not (out / ".claude").exists()
    assert not (out / "docs/superpowers").exists()
    assert not (out / "pilot").exists()
    assert not (out / "docs/reports/mv-space.html").exists()
    assert not (out / "work/population.jsonl").exists()
    assert not (out / "work/kpop/population.jsonl").exists()
    assert "thumb_text_content" not in _csv_header(out / "dataset/features_100mv.csv")
    assert "thumb_text_content" not in _csv_header(out / "dataset/features_50mv.csv")
    first = json.loads((out / "work/features_table.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert "thumb_text_content" not in first
    reliability = json.loads((out / "work/reliability_sample.json").read_text(encoding="utf-8"))
    assert reliability and all("image" not in row for row in reliability)
    demo = json.loads((out / "examples/demo-report.json").read_text(encoding="utf-8"))
    reason = json.loads((out / "examples/demo-reason.json").read_text(encoding="utf-8"))
    rows = {str(row.get("video_id")): row for row in load_reference_rows(out)}
    from mv_analyzer.reference_corpus import canonical_sha256
    expected_source = canonical_sha256(rows[demo["video"]["video_id"]])
    assert demo["pipeline"]["source_features_sha256"] == expected_source
    assert reason["source_report"]["source_features_sha256"] == expected_source
    assert audit_public_release(out) == []


def test_public_release_preserves_reference_corpus_identity(tmp_path):
    out = tmp_path / "public"
    build_public_release(ROOT, out)
    private_hash = reference_corpus_public_metadata(load_reference_rows(ROOT))["corpus_sha256"]
    public_hash = reference_corpus_public_metadata(load_reference_rows(out))["corpus_sha256"]
    assert public_hash == private_hash


def test_openmontage_is_interoperability_only_not_a_runtime_dependency():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert "openmontage" not in pyproject
    for path in (ROOT / "mv_analyzer").glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        assert "import openmontage" not in text
        assert "from openmontage" not in text


def test_public_release_audit_ignores_generated_dependency_and_build_dirs(tmp_path):
    out = tmp_path / "public"
    build_public_release(ROOT, out)
    generated = [
        out / "web/node_modules/fake/package.js",
        out / "web/dist/assets/bundle.js",
        out / "web/test-results/trace.txt",
        out / ".venv/cache.txt",
    ]
    for path in generated:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("data:" + "image/png;" + "base64," + "GENERATED\n" + ("x" * 2_100_000), encoding="utf-8")
    assert audit_public_release(out) == []


def _git(cwd, *args):
    import subprocess
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True, encoding="utf-8")


def test_git_history_audit_accepts_clean_history_with_policy_source_mentions(tmp_path):
    from scripts.audit_git_history import audit_history
    repo = tmp_path / "clean"
    repo.mkdir()
    _git(repo, "init", "-b", "master")
    _git(repo, "config", "user.email", "qa@example.invalid")
    _git(repo, "config", "user.name", "MV Analyzer QA")
    (repo / "scripts").mkdir()
    (repo / "scripts/policy.py").write_text('FORBIDDEN = "thumb_text_content"\nPATTERN = "data:" + "image/png;" + "base64,"\n', encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "clean")
    assert audit_history(repo) == {}


def test_git_history_audit_rejects_historical_public_data_ocr_field(tmp_path):
    from scripts.audit_git_history import audit_history
    repo = tmp_path / "dirty"
    repo.mkdir()
    _git(repo, "init", "-b", "master")
    _git(repo, "config", "user.email", "qa@example.invalid")
    _git(repo, "config", "user.name", "MV Analyzer QA")
    (repo / "dataset").mkdir()
    (repo / "dataset/x.csv").write_text("video_id,thumb_text_content\na,hello\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "dirty")
    assert "thumbnail_ocr_field" in audit_history(repo)


def test_public_release_cli_bootstraps_without_installed_package(tmp_path):
    import subprocess
    import sys
    out = tmp_path / "public-cli"
    proc = subprocess.run(
        [sys.executable, "-S", str(ROOT / "scripts/build_public_release.py"), "--root", str(ROOT), "--out", str(out)],
        cwd=tmp_path, capture_output=True, text=True, encoding="utf-8",
    )
    assert proc.returncode == 0, proc.stderr
    assert (out / "PUBLIC_RELEASE_MANIFEST.json").exists()
    assert audit_public_release(out) == []


def test_public_release_builder_does_not_inherit_ancestor_git_repo(tmp_path):
    outer = tmp_path / "outer"
    outer.mkdir()
    _git(outer, "init", "-b", "master")
    _git(outer, "config", "user.email", "qa@example.invalid")
    _git(outer, "config", "user.name", "MV Analyzer QA")

    nested = outer / "nested-public-source"
    build_public_release(ROOT, nested)
    # The nested source intentionally has no local .git but does have an ancestor .git.
    assert not (nested / ".git").exists()
    (outer / "outer-only.txt").write_text("must not leak into nested builds", encoding="utf-8")
    _git(outer, "add", ".")
    _git(outer, "commit", "-m", "outer")

    second = tmp_path / "rebuilt"
    manifest = build_public_release(nested, second)
    assert (second / "dataset/features_100mv.csv").exists()
    assert not (second / "outer-only.txt").exists()
    assert manifest["source_commit"] == json.loads((nested / "PUBLIC_RELEASE_MANIFEST.json").read_text(encoding="utf-8"))["source_commit"]
    assert audit_public_release(second) == []
