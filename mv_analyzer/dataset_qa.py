"""공개 CSV 데이터셋 구조/표본 불변식 QA."""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

SPECS = {
    "features_50mv.csv": {"rows": 50, "cols": (84, 85), "groups": {"top": 25, "bottom": 25}},
    "features_100mv.csv": {
        "rows": 100, "cols": (93, 94), "groups": {"top": 50, "bottom": 50},
        "domains": {"vocaloid": 50, "kpop": 50},
    },
}


def audit_dataset(path, spec):
    p = Path(path)
    result = {"path": str(p), "errors": [], "rows": 0, "cols": 0}
    if not p.exists():
        result["errors"].append("missing file")
        return result
    with p.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        cols = reader.fieldnames or []
    result["rows"] = len(rows)
    result["cols"] = len(cols)
    ids = [r.get("video_id") for r in rows]
    result["unique_video_ids"] = len(set(ids))
    result["groups"] = dict(Counter(r.get("group") for r in rows))
    result["domains"] = dict(Counter(r.get("domain") for r in rows if r.get("domain")))
    if len(rows) != spec["rows"]:
        result["errors"].append(f"rows {len(rows)} != {spec['rows']}")
    expected_cols = spec["cols"]
    allowed_cols = set(expected_cols) if isinstance(expected_cols, (tuple, list, set)) else {expected_cols}
    if len(cols) not in allowed_cols:
        result["errors"].append(f"cols {len(cols)} not in {sorted(allowed_cols)}")
    if len(set(ids)) != len(rows) or any(not x for x in ids):
        result["errors"].append("video_id must be non-empty and unique")
    for key, expected in spec.get("groups", {}).items():
        if result["groups"].get(key, 0) != expected:
            result["errors"].append(f"group {key}={result['groups'].get(key, 0)} != {expected}")
    for key, expected in spec.get("domains", {}).items():
        if result["domains"].get(key, 0) != expected:
            result["errors"].append(f"domain {key}={result['domains'].get(key, 0)} != {expected}")
    return result


def audit_all(dataset_dir="dataset"):
    root = Path(dataset_dir)
    reports = [audit_dataset(root / name, spec) for name, spec in SPECS.items()]
    return {"ok": not any(r["errors"] for r in reports), "datasets": reports}
