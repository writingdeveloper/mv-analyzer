"""VLM 후보 결과를 기존 블라인드 라벨과 CPU로 채점하는 재사용 QA 게이트."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import stats as st

FIELDS = ("mood", "shot_type", "style")


def cohen_kappa(a, b):
    if not a or len(a) != len(b):
        return None
    labels = sorted(set(a) | set(b))
    idx = {label: i for i, label in enumerate(labels)}
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa = np.bincount([idx[x] for x in a], minlength=len(labels)) / n
    pb = np.bincount([idx[x] for x in b], minlength=len(labels)) / n
    pe = float(np.dot(pa, pb))
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def _indexed(rows):
    out = {}
    for pos, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        i = row.get("i", pos)
        out[int(i)] = row.get("qwen") if isinstance(row.get("qwen"), dict) else row
    return out


def score_predictions(predictions, labels):
    pred = _indexed(predictions)
    ref = _indexed(labels)
    common = sorted(set(pred) & set(ref))
    result = {"n": len(common), "categorical": {}, "num_characters": {}}
    if not common:
        return result

    for field in FIELDS:
        a = [str(pred[i].get(field)) for i in common]
        b = [str(ref[i].get(field)) for i in common]
        accuracy = sum(x == y for x, y in zip(a, b)) / len(common)
        result["categorical"][field] = {
            "accuracy": round(accuracy, 4),
            "kappa": round(float(cohen_kappa(a, b)), 4),
        }

    pa = [float(pred[i].get("num_characters") or 0) for i in common]
    rb = [float(ref[i].get("num_characters") or 0) for i in common]
    exact = sum(x == y for x, y in zip(pa, rb)) / len(common)
    within1 = sum(abs(x - y) <= 1 for x, y in zip(pa, rb)) / len(common)
    rho = st.spearmanr(pa, rb).statistic if len(common) >= 2 else None
    result["num_characters"] = {
        "exact": round(exact, 4),
        "within1": round(within1, 4),
        "spearman_rho": round(float(rho), 4) if rho is not None and np.isfinite(rho) else None,
    }
    return result


def load_reference_labels(paths):
    rows = []
    for path in paths:
        obj = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(obj, list):
            raise ValueError(f"labels must be a list: {path}")
        rows.extend(obj)
    return rows


def load_baseline(sample_path):
    obj = json.loads(Path(sample_path).read_text(encoding="utf-8"))
    if not isinstance(obj, list):
        raise ValueError("sample must be a list")
    return [{"i": i, **(row.get("qwen") or {})} for i, row in enumerate(obj)]
