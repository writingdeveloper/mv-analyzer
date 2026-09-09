#!/usr/bin/env python3
"""Build a deterministic, sanitized source tree suitable for a clean-history public mirror."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

POLICY_VERSION = "public-release-v1"
DROP_FIELDS = {"thumb_text_content"}
EXCLUDED_PREFIXES = (
    ".claude/",
    "docs/superpowers/",
    "pilot/",
    "docs/reports/vendor/",
)
EXCLUDED_FILES = {
    "CLAUDE.md",
    "docs/reports/dashboard.html",
    "docs/reports/dashboard_template.html",
    "docs/reports/mv-space.html",
    "docs/reports/mv-space_template.html",
}
WORK_ALLOWLIST = {
    "work/features_table.jsonl",
    "work/kpop/features_table.jsonl",
    "work/middle/features_table.jsonl",
    "work/sample.csv",
    "work/kpop/sample.csv",
    "work/middle/sample.csv",
    "work/reliability_sample.json",
    "work/reliability_labels_A.json",
    "work/reliability_labels_B.json",
    "work/heatmap_curves.json",
    "work/heatmap_summary.json",
    "work/lyrics_structure_summary.json",
    "work/premiere_summary.json",
    "work/sample_expansion.json",
}
SANITIZED_CSV = {"dataset/features_50mv.csv", "dataset/features_100mv.csv"}
SANITIZED_JSONL = {
    "work/features_table.jsonl",
    "work/kpop/features_table.jsonl",
    "work/middle/features_table.jsonl",
}


def _repo_files(root: Path) -> list[str]:
    # Never inherit an ancestor repository. A generated public tree may live under
    # canonical/dist/, where `git -C public-tree` would otherwise walk upward and
    # return paths from the private canonical checkout.
    if (root / ".git").exists():
        try:
            out = subprocess.check_output(
                ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard"],
                text=True,
                encoding="utf-8",
                stderr=subprocess.DEVNULL,
            )
            return sorted({line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()})
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts and "node_modules" not in path.parts and "test-results" not in path.parts
    )


def _source_commit(root: Path) -> str:
    if (root / ".git").exists():
        try:
            return subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, encoding="utf-8", stderr=subprocess.DEVNULL
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    manifest = root / "PUBLIC_RELEASE_MANIFEST.json"
    if manifest.exists():
        try:
            value = json.loads(manifest.read_text(encoding="utf-8")).get("source_commit")
            if isinstance(value, str) and value:
                return value
        except (OSError, json.JSONDecodeError):
            pass
    return "unknown"


def _included(path: str) -> bool:
    if path in EXCLUDED_FILES or any(path.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return False
    if path.startswith("work/") and path not in WORK_ALLOWLIST:
        return False
    if path.startswith("dist/") or "/node_modules/" in path or path.startswith("web/test-results/"):
        return False
    return True


def _sanitize_csv(src: Path, dst: Path) -> None:
    with src.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fields = [field for field in (reader.fieldnames or []) if field not in DROP_FIELDS]
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open("w", encoding="utf-8", newline="") as target:
            writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            for row in reader:
                for field in DROP_FIELDS:
                    row.pop(field, None)
                writer.writerow({field: row.get(field, "") for field in fields})


def _sanitize_jsonl(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with src.open(encoding="utf-8-sig") as source, dst.open("w", encoding="utf-8", newline="\n") as target:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict):
                for field in DROP_FIELDS:
                    row.pop(field, None)
            target.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def _sanitize_reliability_sample(src: Path, dst: Path) -> None:
    rows = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("reliability sample must be a list")
    clean = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        clean.append({key: value for key, value in row.items() if key != "image"})
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")



def _rewrite_public_demo_source_fingerprints(out: Path) -> list[str]:
    """Make portable demo provenance match the sanitized public source row exactly."""
    from mv_analyzer.reference_corpus import canonical_sha256, load_reference_rows

    rows = {str(row.get("video_id")): row for row in load_reference_rows(out)}
    changed = []
    report_paths = [out / "examples/demo-report.json", out / "web/e2e/fixtures/analyze-report.json"]
    public_hash = None
    for path in report_paths:
        if not path.exists():
            continue
        obj = json.loads(path.read_text(encoding="utf-8"))
        video_id = str(obj.get("video", {}).get("video_id") or "")
        if video_id not in rows:
            raise ValueError(f"demo video is not in sanitized reference corpus: {video_id}")
        public_hash = canonical_sha256(rows[video_id])
        obj["pipeline"]["source_features_sha256"] = public_hash
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        changed.append(path.relative_to(out).as_posix())
    reason_path = out / "examples/demo-reason.json"
    if reason_path.exists() and public_hash:
        obj = json.loads(reason_path.read_text(encoding="utf-8"))
        obj["source_report"]["source_features_sha256"] = public_hash
        reason_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        changed.append(reason_path.relative_to(out).as_posix())
    return changed

def build_public_release(root: Path, out: Path) -> dict:
    root, out = root.resolve(), out.resolve()
    if out == root or root in out.parents and out.name == ".git":
        raise ValueError("refusing unsafe public-release destination")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    included, omitted, sanitized = [], [], []
    for rel in _repo_files(root):
        if not _included(rel):
            omitted.append(rel)
            continue
        src, dst = root / rel, out / rel
        if not src.is_file():
            continue
        if rel in SANITIZED_CSV:
            _sanitize_csv(src, dst); sanitized.append(rel)
        elif rel in SANITIZED_JSONL:
            _sanitize_jsonl(src, dst); sanitized.append(rel)
        elif rel == "work/reliability_sample.json":
            _sanitize_reliability_sample(src, dst); sanitized.append(rel)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        included.append(rel)

    for rel in _rewrite_public_demo_source_fingerprints(out):
        if rel not in sanitized:
            sanitized.append(rel)

    manifest = {
        "policy_version": POLICY_VERSION,
        "source_commit": _source_commit(root),
        "history_mode": "clean-history-required",
        "included_files": len(included),
        "sanitized_files": sorted(sanitized),
        "dropped_fields": sorted(DROP_FIELDS),
        "omitted_categories": ["private-agent-config", "internal-plans", "pilot-artifacts", "raw-work-provenance", "legacy-self-contained-html"],
    }
    (out / "PUBLIC_RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--out", default=Path("dist/public-release"), type=Path)
    args = parser.parse_args(argv)
    manifest = build_public_release(args.root, args.out)
    print(f"public release: {manifest['included_files']} files -> {args.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
