"""Human-label validation helpers for the experimental optical-flow instrument."""
from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy import stats

from .stats import cliffs_delta

LABELS = ("static", "camera_motion", "subject_motion")


def _values(rows, label):
    return [float(r["motion_mean"]) for r in rows
            if r.get("label") == label and isinstance(r.get("motion_mean"), (int, float))]


def _class_summary(values):
    return {
        "n": len(values),
        "mean": round(float(np.mean(values)), 4) if values else None,
        "median": round(float(np.median(values)), 4) if values else None,
    }


def _comparison(a, b):
    if not a or not b:
        return {"n_a": len(a), "n_b": len(b), "cliffs_delta": None, "p": None}
    test = stats.mannwhitneyu(a, b, alternative="two-sided")
    return {
        "n_a": len(a),
        "n_b": len(b),
        "cliffs_delta": round(float(cliffs_delta(a, b)), 4),
        "p": round(float(test.pvalue), 6),
    }


def score_motion_validation(rows):
    rows = list(rows)
    unknown = sorted({str(r.get("label")) for r in rows if r.get("label") not in LABELS})
    if unknown:
        raise ValueError(f"unknown motion label: {', '.join(unknown)}")
    values = {label: _values(rows, label) for label in LABELS}
    classes = {label: _class_summary(vals) for label, vals in values.items()}
    moving = values["camera_motion"] + values["subject_motion"]
    med_static = classes["static"]["median"]
    med_camera = classes["camera_motion"]["median"]
    med_subject = classes["subject_motion"]["median"]
    passes = (
        med_static is not None and med_camera is not None and med_subject is not None
        and med_static < med_camera and med_static < med_subject
    )
    return {
        "n": sum(len(v) for v in values.values()),
        "classes": classes,
        "passes_ordering": passes,
        "comparisons": {
            "static_vs_camera_motion": _comparison(values["static"], values["camera_motion"]),
            "static_vs_subject_motion": _comparison(values["static"], values["subject_motion"]),
            "static_vs_all_motion": _comparison(values["static"], moving),
        },
        "interpretation": (
            "optical flow validates overall motion magnitude only; camera and subject labels "
            "are human-defined strata, not automatic classifier outputs"
        ),
    }


def sensitivity_summary(rows):
    grouped = defaultdict(list)
    for row in rows:
        key = (float(row.get("sample_fps")), float(row.get("static_threshold")))
        grouped[key].append(row)
    result = []
    for (fps, threshold), items in sorted(grouped.items()):
        score = score_motion_validation(items)
        result.append({
            "sample_fps": fps,
            "static_threshold": threshold,
            "n": score["n"],
            "passes_ordering": score["passes_ordering"],
            "classes": score["classes"],
            "comparisons": score["comparisons"],
        })
    return result


def measure_corpus_motion(data_dir, out_path, *, sample_fps=2.0, static_threshold=0.35):
    """Measure all local 11-character video directories into a resumable experimental JSONL."""
    import json
    import re
    from pathlib import Path

    from .motion import analyze_motion

    root = Path(data_dir)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            existing.add((row.get("video_id"), float(row.get("sample_fps", 0)),
                          float(row.get("static_threshold", 0))))
    measured = skipped = missing = 0
    video_re = re.compile(r"[A-Za-z0-9_-]{11}")
    for d in sorted(root.iterdir()) if root.exists() else []:
        if not d.is_dir() or not video_re.fullmatch(d.name):
            continue
        key = (d.name, float(sample_fps), float(static_threshold))
        if key in existing:
            skipped += 1
            continue
        video = d / "video.mp4"
        if not video.exists():
            missing += 1
            continue
        metrics = analyze_motion(video, sample_fps=sample_fps,
                                 static_threshold=static_threshold)
        row = {
            "video_id": d.name,
            "sample_fps": float(sample_fps),
            "static_threshold": float(static_threshold),
            **metrics,
        }
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        measured += 1
    return {"measured": measured, "skipped": skipped, "missing_video": missing}
