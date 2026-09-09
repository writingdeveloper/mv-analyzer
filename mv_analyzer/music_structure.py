"""Functional music-structure candidate adapter.

The normalizer is CPU-only. External inference is opt-in, guarded, and writes only to an
explicit candidate artifact so validated baseline data is never overwritten.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from .resources import ensure_gpu_available

_LABELS = {"intro", "verse", "pre-chorus", "chorus", "bridge", "outro"}


def normalize_label(label):
    value = str(label or "").strip().lower().replace("_", "-").replace(" ", "-")
    aliases = {
        "prechorus": "pre-chorus",
        "pre--chorus": "pre-chorus",
    }
    value = aliases.get(value, value)
    return value if value in _LABELS else "unknown"


def _segment_dict(segment):
    if isinstance(segment, dict):
        return segment
    return {
        "start": getattr(segment, "start", None),
        "end": getattr(segment, "end", None),
        "label": getattr(segment, "label", None),
    }


def normalize_structure(raw):
    if not isinstance(raw, dict):
        raise ValueError("music structure result must be a dict")
    normalized = []
    for pos, item in enumerate(raw.get("segments") or []):
        row = _segment_dict(item)
        try:
            start = float(row["start"])
            end = float(row["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid segment at index {pos}") from exc
        if end <= start:
            raise ValueError(f"segment {pos}: end must be greater than start")
        label = normalize_label(row.get("label"))
        normalized.append({
            "start_s": round(start, 4),
            "end_s": round(end, 4),
            "label": label,
            "source_label": str(row.get("label") or ""),
        })
    normalized.sort(key=lambda row: (row["start_s"], row["end_s"]))
    duration = max((row["end_s"] for row in normalized), default=0.0)
    choruses = [row for row in normalized if row["label"] == "chorus"]
    chorus_duration = sum(row["end_s"] - row["start_s"] for row in choruses)
    bpm = raw.get("bpm")
    return {
        "bpm": round(float(bpm), 4) if isinstance(bpm, (int, float)) else None,
        "duration_s": round(duration, 4),
        "segments": normalized,
        "first_chorus_s": choruses[0]["start_s"] if choruses else None,
        "chorus_count": len(choruses),
        "chorus_duration_ratio": round(chorus_duration / duration, 4) if duration else None,
    }


def _load_generated_json(out_dir, audio_path):
    expected = Path(out_dir) / f"{Path(audio_path).stem}.json"
    candidates = [expected] if expected.exists() else sorted(Path(out_dir).glob("*.json"))
    if not candidates:
        raise RuntimeError("all-in-one-infer produced no JSON result")
    return json.loads(candidates[0].read_text(encoding="utf-8"))


def run_music_structure(audio_path, out_path, *, gpu_guard=ensure_gpu_available,
                        command_runner=subprocess.run, executable="all-in-one-infer",
                        temp_dir=None):
    """Run all-in-one-infer after the shared GPU guard and save a normalized candidate JSON."""
    gpu_guard()
    audio = Path(audio_path)
    if not audio.exists():
        raise FileNotFoundError(audio)
    dest = Path(out_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    if temp_dir is not None:
        generated = Path(temp_dir)
        cmd = [executable, str(audio), "-o", str(generated)]
        try:
            proc = command_runner(cmd, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace")
        except FileNotFoundError as exc:
            raise RuntimeError("all-in-one-infer is not installed") from exc
        if proc.returncode != 0:
            raise RuntimeError(f"all-in-one-infer failed: {proc.stderr[-500:]}")
        result = normalize_structure(_load_generated_json(generated, audio))
    else:
        with tempfile.TemporaryDirectory(prefix="mva-music-structure-") as tmp:
            generated = Path(tmp)
            cmd = [executable, str(audio), "-o", str(generated)]
            try:
                proc = command_runner(cmd, capture_output=True, text=True, encoding="utf-8",
                                      errors="replace")
            except FileNotFoundError as exc:
                raise RuntimeError("all-in-one-infer is not installed") from exc
            if proc.returncode != 0:
                raise RuntimeError(f"all-in-one-infer failed: {proc.stderr[-500:]}")
            result = normalize_structure(_load_generated_json(generated, audio))

    tmp_dest = Path(str(dest) + ".tmp")
    tmp_dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_dest.replace(dest)
    return result
