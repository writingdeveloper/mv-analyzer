"""Canonical product-facing reference-corpus contract for MV Analyzer."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


REFERENCE_CORPUS = {
    "id": "extreme-reference-2026-07",
    "label": "Extreme Reference Corpus v2026.07",
    "sampling": "extreme-groups",
    "source": "dataset/features_100mv.csv",
    "collected_at": "2026-07-21",
    "domains": ["vocaloid", "kpop"],
}


_STRING_KEYS = {
    "video_id",
    "title",
    "channel",
    "channel_id",
    "domain",
    "group",
    "upload_date",
    "collected_at",
    "audio_key",
    "tag_mood_top",
    "thumb_mood",
    "lyrics_topic_1",
    "lyrics_topic_2",
    "lyrics_sentiment",
    "lyrics_addressee",
    "lyrics_source",
}


def _coerce(key: str, value: str | None):
    if value is None or value == "":
        return None
    if key in _STRING_KEYS:
        return value
    low = value.lower()
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        number = float(value)
    except ValueError:
        return value
    if number.is_integer() and not any(token in value.lower() for token in (".", "e")):
        return int(number)
    return number


def load_reference_rows(root: Path, domain: str = "all") -> list[dict]:
    """Load the tracked reference CSV, optionally restricted to one supported domain."""
    if domain not in {"all", *REFERENCE_CORPUS["domains"]}:
        raise ValueError(f"unsupported benchmark domain: {domain}")

    path = Path(root) / str(REFERENCE_CORPUS["source"])
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [
            {key: _coerce(key, value) for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]
    if domain == "all":
        return rows
    return [row for row in rows if row.get("domain") == domain]


def canonical_sha256(value: object) -> str:
    """JSON content digest independent of OS line endings and dictionary order."""
    def normalize(item):
        # Git checkout converts line endings inside quoted multiline CSV fields too.
        if isinstance(item, str):
            return item.replace("\r\n", "\n").replace("\r", "\n")
        if isinstance(item, dict):
            return {key: normalize(child) for key, child in item.items()}
        if isinstance(item, (list, tuple)):
            return [normalize(child) for child in item]
        return item
    data = json.dumps(normalize(value), sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


NON_ANALYSIS_KEYS = {"thumb_text_content"}


def analysis_sha256(value: object) -> str:
    """Digest analytical content while excluding non-analysis raw-text fields."""
    def strip(item):
        if isinstance(item, dict):
            return {key: strip(child) for key, child in item.items() if key not in NON_ANALYSIS_KEYS}
        if isinstance(item, (list, tuple)):
            return [strip(child) for child in item]
        return item
    return canonical_sha256(strip(value))


def reference_corpus_public_metadata(rows: list[dict], domain: str = "all") -> dict:
    if domain not in {"all", *REFERENCE_CORPUS["domains"]}:
        raise ValueError(f"unsupported benchmark domain: {domain}")
    dates = sorted(str(row["collected_at"])[:10] for row in rows if row.get("collected_at"))
    return {
        "id": REFERENCE_CORPUS["id"],
        "label": REFERENCE_CORPUS["label"],
        "sampling": REFERENCE_CORPUS["sampling"],
        "domain": domain,
        "n": len(rows),
        "domains": list(REFERENCE_CORPUS["domains"]),
        "collected_at": dates[-1] if dates else REFERENCE_CORPUS["collected_at"],
        "collection_start": dates[0] if dates else REFERENCE_CORPUS["collected_at"],
        "collection_end": dates[-1] if dates else REFERENCE_CORPUS["collected_at"],
        "corpus_sha256": analysis_sha256(sorted(rows, key=lambda row: str(row.get("video_id")))),
    }
