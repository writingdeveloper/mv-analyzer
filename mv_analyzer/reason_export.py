"""Offline Reason-document export over existing local analysis artifacts."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .reason import build_reason_document, write_reason_document
from .reference_corpus import canonical_sha256
from .report_export import export_existing_report

MAX_INPUT_BYTES = 2_000_000


def _features_path(source: Path) -> Path:
    source = Path(source).resolve()
    return source / "features.json" if source.is_dir() else source


def _read_features(source: Path) -> dict:
    path = _features_path(source)
    if not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("existing features.json is missing or exceeds 2 MB")
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("cannot read existing analysis JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("features.json must be an object")
    return value


def _taste_profile(favorites, data_dir):
    if not favorites:
        return None
    from .talk import profile, read_id_list
    ids = read_id_list(favorites)
    return profile(ids, str(data_dir))


def export_existing_reason(root: Path, source: Path, destination: Path, *, domain="all", favorites=None, data_dir=None) -> dict:
    root = Path(root)
    source = Path(source)
    destination = Path(destination).resolve()
    target = _read_features(source)
    data_dir = Path(data_dir) if data_dir is not None else root / "data"
    taste = _taste_profile(favorites, data_dir)
    with tempfile.TemporaryDirectory(prefix="mva-reason-") as temp_dir:
        report_path = Path(temp_dir) / "report.json"
        report = export_existing_report(root, source, report_path, domain=domain)
        document = build_reason_document(report, taste_profile=taste, target_features=target)
    if destination.exists():
        try:
            old = json.loads(destination.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("refusing to overwrite a non-reason file") from exc
        if not isinstance(old, dict) or old.get("kind") != "mv-analyzer-reason":
            raise ValueError("refusing to overwrite a non-reason file")
    write_reason_document(destination, document)
    return document


def reason_from_report_file(report_path: Path, source: Path, destination: Path, *, favorites=None, data_dir=None) -> dict:
    try:
        report = json.loads(Path(report_path).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("cannot read generated analyze report") from exc
    target = _read_features(source)
    expected = report.get("pipeline", {}).get("source_features_sha256") if isinstance(report, dict) else None
    actual = canonical_sha256(target)
    if expected != actual:
        raise ValueError("generated report source fingerprint does not match features.json")
    taste = _taste_profile(favorites, data_dir or Path(source).parent.parent)
    document = build_reason_document(report, taste_profile=taste, target_features=target)
    write_reason_document(destination, document)
    return document
