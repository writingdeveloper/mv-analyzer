"""전역 움직임 분해 기반 씬 모션 분류 (v2 실험) — 분산 기준의 개념 오류를 고치기 위한 시제품.

v1(`motion.classify_scene_motion`)은 광류 크기의 **분산**이 작으면 "정지 그림 위 카메라"라고 봤다.
2026-09-03 사람 라벨 45건 대조에서 이 가정이 깨졌다. 순수 팬은 화면 전체가 같은 크기로 흐르니
분산이 작지만, **줌**은 중심에서 멀수록 크게 흘러 분산이 커진다(m026: 정지 일러스트 줌인데
mag 10.1 · var 81.7 → motion_clip 오분류). 어떤 임계값을 골라도 3분류 최대 일치율 0.578.

v2는 프레임쌍마다 아핀 변환을 추정해 광류를 **전역 성분 + 잔차**로 가른다.
- 전역 크기 작고 잔차 작다 → static_image
- 전역 크기 크고 잔차 작다 → animated_still (팬·줌·회전 전부 포함, 이게 v1이 못 하던 것)
- 잔차 크다 → motion_clip

카메라가 움직이면서 피사체도 움직이는 경우는 잔차가 크므로 motion_clip으로 간다 —
"작화가 움직이는가"를 재려는 원래 목적에 맞다.
"""
from __future__ import annotations

import cv2
import numpy as np

V2_PARAMS = {"static_global": 0.35, "still_residual": 0.45, "max_height": 360, "edge_margin": 0.05}


def decompose_flow(gray_a, gray_b, edge_margin=0.05):
    """광류를 아핀 전역 성분과 잔차로 분해. (전역 크기, 잔차 크기)를 돌려준다."""
    flow = cv2.calcOpticalFlowFarneback(gray_a, gray_b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    h, w = flow.shape[:2]
    my, mx = int(h * edge_margin), int(w * edge_margin)
    f = flow[my:h - my, mx:w - mx]
    hh, ww = f.shape[:2]
    ys, xs = np.mgrid[0:hh, 0:ww].astype(np.float32)
    # 성긴 격자에서 아핀을 최소제곱으로 푼다 (RANSAC 없이 — 잔차 자체가 관심 대상이라 전부 쓴다)
    step = max(1, min(hh, ww) // 40)
    X = np.stack([xs[::step, ::step].ravel(), ys[::step, ::step].ravel(),
                  np.ones(xs[::step, ::step].size, np.float32)], axis=1)
    U = f[::step, ::step, 0].ravel()
    V = f[::step, ::step, 1].ravel()
    coef_u, *_ = np.linalg.lstsq(X, U, rcond=None)
    coef_v, *_ = np.linalg.lstsq(X, V, rcond=None)
    pred_u, pred_v = X @ coef_u, X @ coef_v
    global_mag = float(np.mean(np.hypot(pred_u, pred_v)))
    residual = float(np.mean(np.hypot(U - pred_u, V - pred_v)))
    return round(global_mag, 4), round(residual, 4)


def classify_v2(global_mag, residual, *, static_global=0.35, still_residual=0.45):
    if residual >= still_residual:
        return "motion_clip"
    return "animated_still" if global_mag >= static_global else "static_image"
