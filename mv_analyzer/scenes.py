"""씬 경계 검출 + 씬별 색감 + 키프레임 추출. pilot/analyze_scenes.py의 함수화."""
import os

import cv2
import numpy as np
from scenedetect import ContentDetector, detect

from .config import SCENE_THRESHOLD

# 27.0(파일럿값)은 모핑/소프트 전환 애니 MV에서 컷을 전부 놓침(いよわ 실측 0/5).
# 15.0은 하드컷 감도 유지(파일럿 44→49) + 소프트 전환 검출(5/5, Adaptive와 교차 일치).
THRESHOLD = SCENE_THRESHOLD


def analyze_scenes(video_path, keyframe_dir):
    os.makedirs(keyframe_dir, exist_ok=True)
    # 재분석 시 이전 씬 수가 더 많았으면 낡은 keyframe이 남아 VLM 입력을 오염시킨다.
    for name in os.listdir(keyframe_dir):
        if name.startswith("scene_") and name.lower().endswith(".jpg"):
            try:
                os.remove(os.path.join(keyframe_dir, name))
            except OSError:
                pass
    scene_list = detect(video_path, ContentDetector(threshold=THRESHOLD))
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps
    # 컷이 하나도 없으면 전체를 1씬으로
    if not scene_list:
        from scenedetect import FrameTimecode
        scene_list = [(FrameTimecode(0, fps),
                       FrameTimecode(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), fps))]

    rows = []
    for i, (start, end) in enumerate(scene_list):
        mid = (start.frame_num + end.frame_num) // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, mid)
        ok, frame = cap.read()
        if not ok:
            continue
        small = cv2.resize(frame, (320, 180))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        _, s, v = cv2.split(hsv)
        px = small.reshape(-1, 3).astype(np.float32)
        _, labels, centers = cv2.kmeans(
            px, 3, None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0),
            3, cv2.KMEANS_PP_CENTERS)
        dom = centers[np.bincount(labels.flatten()).argmax()]
        kf_path = os.path.join(keyframe_dir, f"scene_{i:03d}.jpg")
        cv2.imwrite(kf_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        rows.append({
            "scene": i,
            "start_s": round(start.seconds, 2),
            "end_s": round(end.seconds, 2),
            "len_s": round(end.seconds - start.seconds, 2),
            "brightness": round(float(v.mean()) / 255, 3),
            "saturation": round(float(s.mean()) / 255, 3),
            "dominant_color": "#{:02x}{:02x}{:02x}".format(
                int(dom[2]), int(dom[1]), int(dom[0])),
            "keyframe": os.path.basename(kf_path),
        })
    cap.release()

    lens = [r["len_s"] for r in rows]
    summary = {
        "duration_s": round(duration, 2),
        "fps": round(fps, 3),
        "num_scenes": len(rows),
        "avg_shot_len_s": round(float(np.mean(lens)), 2) if lens else None,
        "median_shot_len_s": round(float(np.median(lens)), 2) if lens else None,
        "min_shot_len_s": round(float(np.min(lens)), 2) if lens else None,
        "max_shot_len_s": round(float(np.max(lens)), 2) if lens else None,
        "cuts_per_minute": round(len(rows) / (duration / 60), 1) if duration else None,
        "avg_brightness": round(float(np.mean([r["brightness"] for r in rows])), 3) if rows else None,
        "avg_saturation": round(float(np.mean([r["saturation"] for r in rows])), 3) if rows else None,
    }
    return {"summary": summary, "scenes": rows}
