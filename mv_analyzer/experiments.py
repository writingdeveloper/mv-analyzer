"""CPU-only experiment registry and shared-GPU readiness status."""
from __future__ import annotations

from pathlib import Path

from .resources import DEFAULT_MEMORY_BUSY_MB, DEFAULT_UTIL_BUSY_PCT, gpu_status

_EXPERIMENTS = (
    {
        "id": "whisper-condition-prev",
        "label": "Whisper condition_on_previous_text A/B",
        "requires_gpu": True,
        "candidate_file": "candidate.json",
        "next": "compare baseline=true vs candidate=false on a fixed code-switch audio set",
    },
    {
        "id": "qwen3-vl-blind52",
        "label": "Qwen3-VL blind-52 A/B",
        "requires_gpu": True,
        "candidate_file": "candidate.json",
        "next": "produce 52 candidate predictions, then run mva evaluate-vlm <candidate.json>",
    },
    {
        "id": "qwen3-asr-vs-whisper",
        "label": "Qwen3-ASR vs Whisper",
        "requires_gpu": True,
        "candidate_file": "candidate.json",
        "next": "transcribe the same fixed audio set and score against the same references",
    },
    {
        "id": "music-structure",
        "label": "Functional music-structure validation",
        "requires_gpu": True,
        "candidate_file": "candidate.json",
        "next": "run mva music-structure <audio> --out <candidate.json> on the fixed subset",
    },
)


def registry():
    return [dict(row) for row in _EXPERIMENTS]


def experiment_output_path(work_dir, experiment_id):
    known = {row["id"]: row for row in _EXPERIMENTS}
    if experiment_id not in known:
        raise KeyError(f"unknown experiment: {experiment_id}")
    return Path(work_dir) / experiment_id / known[experiment_id]["candidate_file"]


def gpu_snapshot_summary(rows=None):
    rows = gpu_status() if rows is None else list(rows)
    if not rows:
        return {
            "available": False,
            "busy": False,
            "max_memory_used_mb": 0,
            "max_utilization_pct": 0,
        }
    max_mem = max(int(r.get("memory_used_mb") or 0) for r in rows)
    max_util = max(int(r.get("utilization_pct") or 0) for r in rows)
    return {
        "available": True,
        "busy": max_mem >= DEFAULT_MEMORY_BUSY_MB or max_util >= DEFAULT_UTIL_BUSY_PCT,
        "max_memory_used_mb": max_mem,
        "max_utilization_pct": max_util,
    }


def experiment_status(work_dir="work/experiments", gpu_rows=None):
    gpu = gpu_snapshot_summary(gpu_rows)
    rows = []
    for spec in _EXPERIMENTS:
        out = experiment_output_path(work_dir, spec["id"])
        if out.exists():
            state = "candidate_ready"
        elif spec["requires_gpu"] and gpu["busy"]:
            state = "blocked_gpu"
        elif spec["requires_gpu"] and not gpu["available"]:
            state = "pending_gpu"
        else:
            state = "ready"
        rows.append({**spec, "state": state, "output": str(out)})
    return {"gpu": gpu, "experiments": rows}
