"""Portable, public-safe benchmark report for one locally analyzed MV."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import os
import tempfile
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .feature_policy import P5_NUMERIC
from .reference_corpus import analysis_sha256, canonical_sha256, load_reference_rows, reference_corpus_public_metadata
from .web_export import (
    FEATURE_LABELS_EN,
    FEATURE_LABELS_KO,
    SPACE_FEATURES,
    _git_commit,
)

REPORT_SCHEMA_VERSION = 2
REPORT_KIND = "mv-analyzer-report"
MIN_REFERENCE_COVERAGE = 20
MIN_DISTANCE_COVERAGE = 0.60

REPORT_NUMERIC_FEATURES = [
    feature
    for feature in P5_NUMERIC
    if feature in FEATURE_LABELS_KO and feature in FEATURE_LABELS_EN
]
DISTANCE_FEATURES = list(REPORT_NUMERIC_FEATURES)



def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _feature_category(feature: str) -> str:
    if feature in {"scene_avg_saturation", "scene_avg_brightness"}:
        return "visual"
    if feature.startswith("scene_"):
        return "editing"
    if feature.startswith("hook_"):
        return "hook"
    if feature.startswith("audio_"):
        return "audio"
    if feature.startswith("lyrics_") or feature.startswith("tag_lyrics_"):
        return "lyrics"
    if feature.startswith("thumb_") or feature.startswith("title_"):
        return "packaging"
    if feature.startswith("sync_"):
        return "synchronization"
    if feature.startswith("tag_"):
        return "visual"
    return "metadata"


def summarize_numeric(values: list[float], value: float) -> dict:
    clean = np.asarray([float(v) for v in values if math.isfinite(float(v))], dtype=float)
    if clean.size < 2:
        raise ValueError("numeric benchmark requires at least two finite reference values")
    mean = float(clean.mean())
    std = float(clean.std())
    below = int(np.sum(clean < float(value)))
    equal = int(np.sum(clean == float(value)))
    percentile = 100.0 * (below + 0.5 * equal) / clean.size
    return {
        "z": None if std == 0 else (float(value) - mean) / std,
        "percentile": round(percentile, 1),
        "reference_median": float(np.median(clean)),
        "reference_mean": mean,
        "reference_std": std,
        "reference_n": int(clean.size),
    }


def fit_reference_pca(reference_rows: list[dict], target: dict, features: list[str]) -> dict:
    usable = [
        feature
        for feature in features
        if sum(_finite(row.get(feature)) for row in reference_rows) >= min(3, len(reference_rows))
    ]
    if len(usable) < 3 or len(reference_rows) < 3:
        raise ValueError("PCA requires at least three usable features and reference rows")

    matrix = np.asarray(
        [
            [float(row[f]) if _finite(row.get(f)) else np.nan for f in usable]
            for row in reference_rows
        ],
        dtype=float,
    )
    medians = np.nanmedian(matrix, axis=0)
    missing = np.where(np.isnan(matrix))
    matrix[missing] = np.take(medians, missing[1])
    means = matrix.mean(axis=0)
    stds = matrix.std(axis=0)
    nonconstant = stds > 0
    if int(np.sum(nonconstant)) < 3:
        raise ValueError("PCA requires at least three non-constant reference features")
    matrix = matrix[:, nonconstant]
    medians = medians[nonconstant]
    means = means[nonconstant]
    stds = stds[nonconstant]
    usable = [feature for feature, keep in zip(usable, nonconstant) if bool(keep)]

    z = (matrix - means) / stds
    _, singular, vt = np.linalg.svd(z, full_matrices=False)
    n_components = min(3, vt.shape[0])
    loadings = vt[:n_components].copy()
    scores = z @ loadings.T
    for index in range(n_components):
        pivot = int(np.argmax(np.abs(loadings[index])))
        if loadings[index, pivot] < 0:
            loadings[index] *= -1
            scores[:, index] *= -1

    reference_scale = np.max(np.abs(scores), axis=0)
    reference_scale[reference_scale == 0] = 1.0
    target_values = np.asarray(
        [float(target[f]) if _finite(target.get(f)) else medians[index] for index, f in enumerate(usable)],
        dtype=float,
    )
    target_z = (target_values - means) / stds
    target_score = target_z @ loadings.T
    target_display = target_score / reference_scale
    variance = singular**2
    variance = variance / variance.sum()

    observed = sum(_finite(target.get(f)) for f in usable)
    coverage = observed / len(usable)
    available = coverage >= MIN_DISTANCE_COVERAGE
    basis_id = analysis_sha256({
        "features": usable,
        "reference": sorted(reference_rows, key=lambda row: str(row.get("video_id"))),
        "loadings": np.round(loadings, 8).tolist(),
        "preprocessing": "median-population-zscore-svd-pivot-sign-v1",
    })
    return {
        "status": "available" if available else "insufficient_coverage",
        "observed_count": observed,
        "coverage": coverage,
        "imputed_features": [f for f in usable if not _finite(target.get(f))],
        "experimental_features": [f for f in usable if f not in P5_NUMERIC],
        "basis_id": basis_id,
        "reference_points": [
            {"video_id": row.get("video_id"), "title": row.get("title"),
             "domain": row.get("domain"), "group": row.get("group"),
             "score": [float(v) for v in scores[index,:3]],
             "display": [float(v) for v in (scores[index,:3] / reference_scale[:3])]}
            for index, row in enumerate(reference_rows)
        ],
        "features": usable,
        "score": [float(value) for value in target_score[:3]] if available else None,
        "display": [float(value) for value in target_display[:3]] if available else None,
        "explained_variance_pct": [round(float(value) * 100, 2) for value in variance[:3]],
        "loadings": [[round(float(value), 8) for value in row] for row in loadings[:3]],
        "reference_scale": [round(float(value), 8) for value in reference_scale[:3]],
    }


def _standardization(reference_rows: list[dict], target: dict) -> tuple[list[str], dict[str, tuple[float, float]], float]:
    stats: dict[str, tuple[float, float]] = {}
    usable: list[str] = []
    for feature in DISTANCE_FEATURES:
        values = [float(row[feature]) for row in reference_rows if _finite(row.get(feature))]
        if len(values) < MIN_REFERENCE_COVERAGE or not _finite(target.get(feature)):
            continue
        mean = float(np.mean(values))
        std = float(np.std(values))
        if std == 0:
            continue
        stats[feature] = (mean, std)
        usable.append(feature)
    coverage = len(usable) / len(DISTANCE_FEATURES) if DISTANCE_FEATURES else 0.0
    return usable, stats, coverage


def _distance(target: dict, row: dict, usable: list[str], stats: dict[str, tuple[float, float]]) -> float | None:
    terms = []
    for feature in usable:
        if not _finite(row.get(feature)):
            continue
        _, std = stats[feature]
        terms.append(((float(target[feature]) - float(row[feature])) / std) ** 2)
    required = math.ceil(len(DISTANCE_FEATURES) * MIN_DISTANCE_COVERAGE)
    if len(terms) < required:
        return None
    return math.sqrt(sum(terms) / len(terms))


def _neighbors_and_centroids(reference_rows: list[dict], target: dict) -> tuple[list[dict], dict]:
    usable, stats, coverage = _standardization(reference_rows, target)
    empty = {
        "top_distance": None,
        "bottom_distance": None,
        "closer_group": None,
        "coverage": round(coverage, 3),
    }
    if coverage < MIN_DISTANCE_COVERAGE:
        return [], empty

    neighbors = []
    for row in reference_rows:
        if row.get("video_id") == target.get("video_id"):
            continue
        distance = _distance(target, row, usable, stats)
        if distance is None:
            continue
        neighbors.append(
            {
                "video_id": row.get("video_id"),
                "title": row.get("title"),
                "channel": row.get("channel"),
                "domain": row.get("domain"),
                "group": row.get("group"),
                "distance": round(distance, 4),
            }
        )
    neighbors.sort(key=lambda row: (row["distance"], str(row["video_id"])))

    centroid_distances: dict[str, float | None] = {}
    for group in ("top", "bottom"):
        group_rows = [row for row in reference_rows if row.get("group") == group]
        terms = []
        for feature in usable:
            values = [float(row[feature]) for row in group_rows if _finite(row.get(feature))]
            if not values:
                continue
            _, std = stats[feature]
            terms.append(((float(target[feature]) - float(np.mean(values))) / std) ** 2)
        required = math.ceil(len(DISTANCE_FEATURES) * MIN_DISTANCE_COVERAGE)
        centroid_distances[group] = math.sqrt(sum(terms) / len(terms)) if len(terms) >= required else None

    top_distance = centroid_distances["top"]
    bottom_distance = centroid_distances["bottom"]
    closer = None
    if top_distance is not None and bottom_distance is not None:
        if not math.isclose(top_distance, bottom_distance, abs_tol=1e-4, rel_tol=0):
            closer = "top" if top_distance < bottom_distance else "bottom"
    return neighbors[:5], {
        "top_distance": None if top_distance is None else float(top_distance),
        "bottom_distance": None if bottom_distance is None else float(bottom_distance),
        "closer_group": closer,
        "coverage": round(coverage, 3),
    }


def _package_version() -> str:
    try:
        return importlib.metadata.version("mv-analyzer")
    except importlib.metadata.PackageNotFoundError:
        return "0.2.0"


def _feature_schema_id() -> str:
    digest = hashlib.sha256("\n".join(REPORT_NUMERIC_FEATURES).encode("utf-8")).hexdigest()[:12]
    return f"p5-formal-{digest}"


def build_analyze_report(root: Path, target: dict, *, domain: str = "all", measurement_manifest: dict | None = None) -> dict:
    root = Path(root)
    if not isinstance(target, dict):
        raise ValueError("features.json must be an object")
    for feature in REPORT_NUMERIC_FEATURES:
        value = target.get(feature)
        if value is not None and (not _finite(value) or abs(float(value)) > 1e12):
            raise ValueError(f"invalid measured numeric feature: {feature}")
    reference_rows = load_reference_rows(root, domain)
    metadata = reference_corpus_public_metadata(reference_rows, domain)

    feature_rows = []
    for feature in REPORT_NUMERIC_FEATURES:
        value = target.get(feature)
        if not _finite(value):
            continue
        values = [float(row[feature]) for row in reference_rows if _finite(row.get(feature))]
        if len(values) < MIN_REFERENCE_COVERAGE:
            continue
        summary = summarize_numeric(values, float(value))
        if summary["z"] is None:
            continue
        feature_rows.append(
            {
                "id": feature,
                "labels": {"ko": FEATURE_LABELS_KO[feature], "en": FEATURE_LABELS_EN[feature]},
                "category": _feature_category(feature),
                "value": float(value),
                **summary,
            }
        )

    if not feature_rows:
        raise ValueError("features.json has no usable measured numeric features")

    pca_features = [
        feature
        for feature in SPACE_FEATURES
        if sum(_finite(row.get(feature)) for row in reference_rows) >= MIN_REFERENCE_COVERAGE
    ]
    pca_fit = fit_reference_pca(reference_rows, target, pca_features)
    neighbors, centroids = _neighbors_and_centroids(reference_rows, target)
    commit = _git_commit(root)
    benchmark = {
        "corpus_id": metadata["id"],
        "label": metadata["label"],
        "sampling": metadata["sampling"],
        "domain": metadata["domain"],
        "n": metadata["n"],
        "collected_at": metadata["collected_at"],
        "collection_start": metadata["collection_start"],
        "collection_end": metadata["collection_end"],
        "corpus_sha256": metadata["corpus_sha256"],
        "target_in_reference": any(row.get("video_id") == target.get("video_id") for row in reference_rows),
        "warning": "descriptive-reference-only",
    }
    manifest = measurement_manifest if isinstance(measurement_manifest, dict) else {}
    artifacts = manifest.get("artifacts")
    artifact = artifacts.get("features.json") if isinstance(artifacts, dict) else None
    artifact = artifact if isinstance(artifact, dict) else {}
    measured_sha = manifest.get("git_commit")
    recorded = (artifact.get("status") == "generated" and isinstance(artifact.get("fingerprint"), str)
                and isinstance(measured_sha, str) and re.fullmatch(r"[0-9a-f]{40}", measured_sha))
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "kind": REPORT_KIND,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "pipeline": {
            "version": _package_version(),
            "git_commit": commit,
            "feature_schema": _feature_schema_id(),
            "source_features_sha256": canonical_sha256(target),
            "measurement_git_commit": measured_sha if recorded else None,
            "measurement_status": "recorded" if recorded else "unverified",
        },
        "video": {
            "video_id": target.get("video_id"),
            "title": target.get("title"),
            "channel": target.get("channel"),
            "upload_date": target.get("upload_date"),
            "duration_s": round(float(target["duration_s"]), 5) if _finite(target.get("duration_s")) else None,
        },
        "benchmark": benchmark,
        "features": feature_rows,
        "pca": {key: value for key, value in pca_fit.items() if key not in {"loadings", "reference_scale"}},
        "neighbors": neighbors,
        "centroids": centroids,
    }
    assert_analyze_report_safe(report)
    return report


def assert_analyze_report_safe(report: object) -> None:
    from .report_contract import validate_report
    validate_report(report)


def write_analyze_report(path: Path, report: dict) -> None:
    destination = Path(path)
    assert_analyze_report_safe(report)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # A unique sibling temporary file avoids concurrent writers clobbering each other.
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                         prefix=destination.name + ".", suffix=".tmp", delete=False) as handle:
            temp = Path(handle.name)
            json.dump(report, handle, ensure_ascii=False, indent=2, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, destination)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()
