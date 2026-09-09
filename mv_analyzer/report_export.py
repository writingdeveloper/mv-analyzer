"""Offline report export from an existing local features file (no media/model IO)."""
from __future__ import annotations

import json
from pathlib import Path

from .analyze_report import build_analyze_report, write_analyze_report

MAX_INPUT_BYTES = 2_000_000


def export_existing_report(root: Path, source: Path, destination: Path, *, domain: str = "all") -> dict:
    source = Path(source).resolve()
    if source.is_dir():
        source = source / "features.json"
    destination = Path(destination).resolve()
    manifest_path = source.parent / "analysis_manifest.json"
    if destination in {source, manifest_path, (Path(root)/"dataset/features_100mv.csv").resolve()}:
        raise ValueError("output must not overwrite source measurements or the reference corpus")
    if not source.is_file() or source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("existing features.json is missing or exceeds 2 MB")
    try:
        row = json.loads(source.read_text(encoding="utf-8-sig"))
        manifest = None
        if manifest_path.exists():
            if manifest_path.stat().st_size > MAX_INPUT_BYTES:
                raise ValueError("analysis manifest exceeds 2 MB")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if destination.exists():
            old = json.loads(destination.read_text(encoding="utf-8-sig"))
            if not isinstance(old,dict) or old.get("kind") != "mv-analyzer-report":
                raise ValueError("refusing to overwrite a non-report file")
    except (OSError,json.JSONDecodeError) as exc:
        raise ValueError("cannot read existing analysis JSON") from exc
    report = build_analyze_report(root,row,domain=domain,measurement_manifest=manifest)
    write_analyze_report(destination,report)
    return report
