"""공유 GPU 자원 충돌 방지. nvidia-smi 상태 조회만 하며 모델을 로드하지 않는다."""
from __future__ import annotations

import shutil
import subprocess

DEFAULT_MEMORY_BUSY_MB = 2048
DEFAULT_UTIL_BUSY_PCT = 35


def parse_gpu_status_csv(text: str):
    rows = []
    for line in text.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) < 2:
            continue
        try:
            rows.append({"memory_used_mb": int(float(parts[0])), "utilization_pct": int(float(parts[1]))})
        except ValueError:
            continue
    return rows


def gpu_status():
    exe = shutil.which("nvidia-smi")
    if not exe:
        return []
    proc = subprocess.run(
        [exe, "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5,
    )
    if proc.returncode != 0:
        return []
    return parse_gpu_status_csv(proc.stdout)


def ensure_gpu_available(*, force=False, memory_busy_mb=DEFAULT_MEMORY_BUSY_MB,
                         util_busy_pct=DEFAULT_UTIL_BUSY_PCT):
    """GPU가 이미 바쁘면 다른 세션을 방해하지 않고 실패시킨다."""
    if force:
        return
    rows = gpu_status()
    busy = [r for r in rows if r["memory_used_mb"] >= memory_busy_mb
            or r["utilization_pct"] >= util_busy_pct]
    if busy:
        r = busy[0]
        raise RuntimeError(
            "GPU busy: "
            f"{r['memory_used_mb']} MiB used, {r['utilization_pct']}% util. "
            "다른 세션 작업을 보호하기 위해 GPU 단계를 시작하지 않았습니다. "
            "의도적으로 공유하려면 --force-gpu-busy를 명시하세요."
        )
