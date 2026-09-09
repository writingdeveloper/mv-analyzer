"""Validation boundary for portable evidence-backed Reason documents."""
from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from .report_contract import scan_safety

BANNED_CLAIM_TYPES = {"success_prediction", "causal_success", "artistic_quality", "psychology"}


@lru_cache(maxsize=1)
def _validator():
    schema = json.loads((Path(__file__).parent / "schemas/reason-document.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_reason_document(value):
    scan_safety(value)
    error = next(_validator().iter_errors(value), None)
    if error:
        path = ".".join(map(str, error.absolute_path)) or "reason"
        raise ValueError(f"invalid reason {path}: {error.validator}")
    ids = [claim["id"] for claim in value["claims"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate reason claim id")
    known = set(ids)
    for question, summary_ids in value["summary"].items():
        if any(claim_id not in known for claim_id in summary_ids):
            raise ValueError(f"unknown summary claim id: {question}")
    for claim in value["claims"]:
        if claim["claim_type"] in BANNED_CLAIM_TYPES:
            raise ValueError("banned reason claim type")
        if not claim["evidence"]:
            raise ValueError("reason claim requires evidence")
        if claim["question"] == "taste" and claim["scope"] != "taste_profile":
            raise ValueError("taste claim must use taste_profile scope")
    try:
        datetime.fromisoformat(value["generated_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid reason generated_at") from exc
    return value
