"""생성용 레퍼런스 프레임 만들기 — 업로드본 산물이 남지 않은 첫 프레임.

`talk sanitize`는 서술에서 자막 띠·필러박스를 걷어내지만, H3의 I2VA는 **이미지**를 첫 프레임으로
쓴다. 서술을 아무리 정리해도 참조 이미지에 검은 띠와 팬자막이 박혀 있으면 생성물이 그대로 물고
들어간다. 2026-09-03 점검에서 바움쿠헨 자막판 키프레임 49장 중 29장에 좌우 240px 필러박스가
남아 있었다(값 23의 진회색이라 순수 검정 기준으로는 안 잡힌다).

두 가지를 한다:
- **깨끗한 소스로 갈아끼우기**: 같은 곡의 무자막 판본이 분석돼 있으면(`--clean-source`) 자막판의
  씬 중간 시각으로 그쪽에서 프레임을 뽑는다. 두 판본은 길이가 같고 씬 검출만 다르므로 시각으로
  맞추는 게 안전하다(프레임 번호는 fps가 다르면 어긋난다).
- **필러박스 잘라내기**: 열/행 평균이 화면 중앙값 대비 뚜렷이 낮은 가장자리를 띠로 보고 깎는다.
  잘라낸 뒤 화면비가 샷마다 달라질 수 있는데, 이 MV처럼 4:3 샷과 꽉 찬 샷을 의도적으로 섞는
  연출이면 그게 원본 의도다. 되돌리는 것은 조립 단계의 레터박스 몫.

파일 이름은 `scene_NNN.jpg`로 원래 키프레임 디렉터리와 같게 둔다 — `talk export --keyframes`에
그대로 꽂아 쓰기 위해서다.
"""
from __future__ import annotations

import json
import os

import cv2
import numpy as np

BAR_RATIO = 0.35   # 중앙값 대비 이 비율보다 어두운 가장자리를 띠로 본다
BAR_FLOOR = 6.0    # 화면 중앙값이 이보다 어두우면 띠 판정을 포기한다
MIN_BAR_RATIO = 0.015  # 변 길이의 1.5% 미만이면 인코딩 잡티로 보고 무시


def _bar_width(profile):
    """양쪽 띠 두께. 좌우가 1~2px 어긋나면 넓은 쪽으로 맞춘다 —
    같은 판본 안에서 출력 크기가 1440/1442/1443로 갈리면 조립 단계가 지저분해진다."""
    med = float(np.median(profile))
    if med < BAR_FLOOR:
        return 0, 0  # 화면 전체가 어두우면 띠와 내용을 가를 근거가 없다 (검정 카드 샷)
    thr = med * BAR_RATIO
    limit = len(profile) // 3
    lo = 0
    while lo < limit and profile[lo] < thr:
        lo += 1
    hi = 0
    while hi < limit and profile[len(profile) - 1 - hi] < thr:
        hi += 1
    if lo >= limit and hi >= limit:
        return 0, 0  # 양쪽 다 상한까지 갔다 = 띠가 아니라 어두운 화면
    floor = int(len(profile) * MIN_BAR_RATIO)
    if lo < floor and hi < floor:
        return 0, 0
    both = max(lo, hi)
    return both, both


def detect_bars(frame):
    """(left, right, top, bottom) 띠 두께. 없으면 0."""
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    left, right = _bar_width(g.mean(axis=0))
    top, bottom = _bar_width(g.mean(axis=1))
    return left, right, top, bottom


def crop_bars(frame):
    l, r, t, b = detect_bars(frame)
    if not (l or r or t or b):
        return frame, (0, 0, 0, 0)
    h, w = frame.shape[:2]
    out = frame[t:h - b, l:w - r]
    # 전부 깎여 없어지는 병리적 경우는 원본을 돌려준다
    return (frame, (0, 0, 0, 0)) if out.size == 0 else (out, (l, r, t, b))


def scene_midpoints(video_dir):
    with open(os.path.join(video_dir, "scenes.json"), encoding="utf-8") as fh:
        scenes = json.load(fh)["scenes"]
    return [(s["scene"], (float(s["start_s"]) + float(s["end_s"])) / 2.0) for s in scenes]


def build(video_id, data_dir="data", clean_source=None, out_dir=None, crop=True):
    """씬 중간 시각의 프레임을 (필요하면 다른 판본에서) 뽑아 생성용 키프레임 디렉터리를 만든다."""
    video_dir = os.path.join(data_dir, video_id)
    src_id = clean_source or video_id
    src_video = os.path.join(data_dir, src_id, "video.mp4")
    if not os.path.exists(src_video):
        raise ValueError(f"소스 영상이 없습니다: {src_video}")
    out_dir = out_dir or os.path.join("work", "exports", f"{video_id}.gen_keyframes")
    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(src_video)
    if not cap.isOpened():
        raise ValueError(f"영상을 열 수 없습니다: {src_video}")
    written, cropped, failed = [], 0, []
    for idx, t in scene_midpoints(video_dir):
        cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000.0)
        ok, frame = cap.read()
        if not ok:
            failed.append(idx)
            continue
        bars = (0, 0, 0, 0)
        if crop:
            frame, bars = crop_bars(frame)
        if any(bars):
            cropped += 1
        path = os.path.join(out_dir, f"scene_{idx:03d}.jpg")
        cv2.imwrite(path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        written.append({"scene": idx, "t_s": round(t, 3), "bars": bars,
                        "size": [frame.shape[1], frame.shape[0]]})
    cap.release()
    return {"out_dir": out_dir, "source": src_id, "n": len(written),
            "n_cropped": cropped, "failed": failed, "frames": written}
