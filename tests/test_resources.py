import pytest

from mv_analyzer import resources


def test_parse_gpu_status_csv():
    assert resources.parse_gpu_status_csv("12280, 100\n500, 2\n") == [
        {"memory_used_mb": 12280, "utilization_pct": 100},
        {"memory_used_mb": 500, "utilization_pct": 2},
    ]


def test_gpu_guard_rejects_busy(monkeypatch):
    monkeypatch.setattr(resources, "gpu_status", lambda: [{"memory_used_mb": 9000, "utilization_pct": 80}])
    with pytest.raises(RuntimeError, match="GPU busy"):
        resources.ensure_gpu_available()


def test_gpu_guard_force_override(monkeypatch):
    monkeypatch.setattr(resources, "gpu_status", lambda: [{"memory_used_mb": 9000, "utilization_pct": 80}])
    resources.ensure_gpu_available(force=True)
