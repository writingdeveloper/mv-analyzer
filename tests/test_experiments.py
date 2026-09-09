from mv_analyzer.experiments import (
    experiment_output_path,
    experiment_status,
    gpu_snapshot_summary,
    registry,
)


def test_registry_has_planned_gpu_gates():
    ids = [row["id"] for row in registry()]
    assert ids == [
        "whisper-condition-prev",
        "qwen3-vl-blind52",
        "qwen3-asr-vs-whisper",
        "music-structure",
    ]
    assert all(row["requires_gpu"] for row in registry())


def test_candidate_outputs_are_isolated(tmp_path):
    path = experiment_output_path(tmp_path, "qwen3-vl-blind52")
    assert path == tmp_path / "qwen3-vl-blind52" / "candidate.json"
    assert "data" not in path.parts


def test_gpu_snapshot_summary_marks_busy():
    out = gpu_snapshot_summary([{"memory_used_mb": 12806, "utilization_pct": 100}])
    assert out["available"] is True
    assert out["busy"] is True
    assert out["max_memory_used_mb"] == 12806
    assert out["max_utilization_pct"] == 100


def test_experiment_status_reports_pending_and_completed(tmp_path):
    pending = experiment_status(tmp_path, gpu_rows=[{"memory_used_mb": 12000, "utilization_pct": 99}])
    assert pending["gpu"]["busy"] is True
    assert all(row["state"] == "blocked_gpu" for row in pending["experiments"])

    out = experiment_output_path(tmp_path, "qwen3-vl-blind52")
    out.parent.mkdir(parents=True)
    out.write_text("[]", encoding="utf-8")
    completed = experiment_status(tmp_path, gpu_rows=[])
    qwen = next(row for row in completed["experiments"] if row["id"] == "qwen3-vl-blind52")
    assert qwen["state"] == "candidate_ready"
    assert qwen["output"] == str(out)
