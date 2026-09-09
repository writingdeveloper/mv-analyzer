"""CPU optical-flow motion metrics.

기존 연구 feature에 자동 혼합하지 않는 opt-in 측정기다. 정식 도입 전에는
동일 코퍼스 일괄 재처리 + 신뢰성 게이트가 필요하다.
"""
from __future__ import annotations


import cv2
import numpy as np


def _percentile(values, q):
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=np.float32), q))


def analyze_motion(video_path, sample_fps=2.0, max_width=320, static_threshold=0.35):
    """Farneback optical flow 기반 샷 내부 움직임 요약.

    sample_fps 만큼만 읽고 max_width로 축소해 CPU 비용을 제한한다.
    반환값은 픽셀/샘플 간 flow magnitude이며 비교용 상대 지표다.
    """
    if sample_fps <= 0:
        raise ValueError("sample_fps must be > 0")
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"cannot open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if fps <= 0 or frame_count <= 0:
        cap.release()
        raise ValueError("invalid video metadata")
    step = max(1, int(round(fps / sample_fps)))

    prev = None
    magnitudes = []
    sampled = 0
    frame_idx = 0
    try:
        while frame_idx < frame_count:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ok, frame = cap.read()
            if not ok:
                break
            h, w = frame.shape[:2]
            if w > max_width:
                scale = max_width / w
                frame = cv2.resize(frame, (max_width, max(1, int(round(h * scale)))))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev is not None:
                flow = cv2.calcOpticalFlowFarneback(
                    prev, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
                )
                mag = cv2.magnitude(flow[..., 0], flow[..., 1])
                finite = mag[np.isfinite(mag)]
                if finite.size:
                    magnitudes.append(float(np.mean(finite)))
            prev = gray
            sampled += 1
            frame_idx += step
    finally:
        cap.release()

    duration_s = frame_count / fps
    if not magnitudes:
        return {
            "motion_sample_fps": sample_fps,
            "motion_sampled_frames": sampled,
            "motion_mean": None,
            "motion_median": None,
            "motion_p90": None,
            "motion_static_ratio": None,
            "motion_peak_at_s": None,
            "duration_s": round(duration_s, 3),
        }

    arr = np.asarray(magnitudes, dtype=np.float32)
    peak_i = int(np.argmax(arr))
    return {
        "motion_sample_fps": sample_fps,
        "motion_sampled_frames": sampled,
        "motion_mean": round(float(np.mean(arr)), 4),
        "motion_median": round(float(np.median(arr)), 4),
        "motion_p90": round(_percentile(magnitudes, 90), 4),
        "motion_static_ratio": round(float(np.mean(arr < static_threshold)), 4),
        "motion_peak_at_s": round((peak_i + 1) / sample_fps, 3),
        "duration_s": round(duration_s, 3),
    }


# --- 씬별 움직임 3분류 -----------------------------------------------------
#
# 개념: 정지 이미지는 flow가 거의 없고, 정지 일러스트 위의 팬/줌은 화면 전체가 같은
# 방향으로 흐르므로 flow 크기의 분산이 작고, 실제 작화/피사체 움직임은 부분마다 흐름이
# 달라 분산이 크다. 보컬로이드 MV에서는 곧 "일러스트 한 장 + 카메라워크"인지 "작화가
# 움직이는지"의 구분이라 제작 투자 프록시 후보다. 임계값은 360p·0.4초 간격 기준의
# 휴리스틱이며 정식 채택 전 사람 라벨 검증이 필요하다 (feature_policy: motion_* 실험).

SCENE_MOTION_TYPES = ("static_image", "animated_still", "motion_clip")
SCENE_MOTION_PARAMS = {"pairs_per_scene": 3, "pair_every_s": 5.0, "max_pairs_per_scene": 12,
                       "gap_s": 0.4, "max_height": 360,
                       "static_mag": 0.5, "still_var": 2.0, "edge_margin": 0.05}


def _to_gray(frame, max_height):
    h, w = frame.shape[:2]
    if h > max_height:
        scale = max_height / h
        frame = cv2.resize(frame, (max(1, int(round(w * scale))), max_height))
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def _scene_sample_plan(scenes, fps, pairs_per_scene, gap_s, pair_every_s=5.0,
                       max_pairs_per_scene=12):
    """씬별 (t, t+gap) 프레임 쌍 인덱스. gap보다 짧은 씬은 씬 길이의 절반 간격.

    긴 씬(정지 일러스트 MV는 씬 하나가 수 분)은 pair_every_s마다 쌍을 추가해
    표본이 성기지 않게 한다 (상한 max_pairs_per_scene).
    """
    plan = []
    for s in scenes:
        start, end = float(s["start_s"]), float(s["end_s"])
        dur = max(0.0, end - start)
        gap = gap_s if dur > gap_s * 1.5 else max(1.0 / fps, dur / 2)
        want = max(pairs_per_scene, int(dur // pair_every_s)) if pair_every_s else pairs_per_scene
        n = max(1, min(max_pairs_per_scene, want, int(dur // gap))) if dur > 0 else 1
        span = max(0.0, dur - gap)
        pairs = []
        for i in range(n):
            t = start + (i + 0.5) * span / n
            ia = max(0, int(round(t * fps)))
            ib = max(ia + 1, int(round((t + gap) * fps)))
            pairs.append((ia, ib))
        plan.append(pairs)
    return plan


def _grab_frames(cap, needed, max_height):
    """임의 탐색 대신 한 번의 순차 디코딩으로 필요한 프레임만 회수 (seek 비용 회피)."""
    frames = {}
    want = iter(sorted(needed))
    nxt = next(want, None)
    idx = 0
    while nxt is not None:
        if not cap.grab():
            break
        if idx == nxt:
            ok, frame = cap.retrieve()
            if ok:
                frames[idx] = _to_gray(frame, max_height)
            nxt = next(want, None)
        idx += 1
    return frames


def _flow_stats(gray_a, gray_b, edge_margin):
    flow = cv2.calcOpticalFlowFarneback(gray_a, gray_b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
    mag = cv2.magnitude(flow[..., 0], flow[..., 1])
    h, w = mag.shape
    my, mx = int(h * edge_margin), int(w * edge_margin)
    if my and mx and h > 2 * my and w > 2 * mx:
        mag = mag[my:h - my, mx:w - mx]  # 경계 아티팩트 제외
    mag = mag[np.isfinite(mag)]
    if not mag.size:
        return None
    return float(np.mean(mag)), float(np.var(mag))


def classify_motion(mean_mag, variance, *, static_mag=0.5, still_var=2.0):
    if mean_mag < static_mag:
        return "static_image"
    if variance < still_var:
        return "animated_still"
    return "motion_clip"


def classify_scene_motion(video_path, scenes, **params):
    """씬 목록(scenes.json의 scenes) 각각을 static_image / animated_still / motion_clip으로.

    씬당 최대 pairs_per_scene개의 (t, t+gap) 프레임 쌍을 균등 배치해 Farneback flow의
    평균 크기·분산을 재고, 쌍 평균으로 분류한다. gap보다 짧은 씬은 씬 길이의 절반 간격.
    """
    p = {**SCENE_MOTION_PARAMS, **params}
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"cannot open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
    if fps <= 0:
        cap.release()
        raise ValueError("invalid video metadata")
    plan = _scene_sample_plan(scenes, fps, p["pairs_per_scene"], p["gap_s"],
                              p["pair_every_s"], p["max_pairs_per_scene"])
    try:
        frames = _grab_frames(cap, {i for pairs in plan for pair in pairs for i in pair},
                              p["max_height"])
    finally:
        cap.release()
    results = []
    for s, pairs in zip(scenes, plan):
        stats = []
        for ia, ib in pairs:
            a, b = frames.get(ia), frames.get(ib)
            if a is None or b is None or a.shape != b.shape:
                continue
            st = _flow_stats(a, b, p["edge_margin"])
            if st:
                stats.append(st)
        row = {"scene": s.get("scene"), "start_s": float(s["start_s"]),
               "end_s": float(s["end_s"]), "n_pairs": len(stats)}
        if not stats:
            row.update({"motion_type": "unknown", "flow_mag_mean": None,
                        "flow_variance": None})
        else:
            mean_mag = sum(x[0] for x in stats) / len(stats)
            var = sum(x[1] for x in stats) / len(stats)
            row.update({"motion_type": classify_motion(mean_mag, var,
                                                       static_mag=p["static_mag"],
                                                       still_var=p["still_var"]),
                        "flow_mag_mean": round(mean_mag, 4),
                        "flow_variance": round(var, 4)})
        results.append(row)
    return results


def summarize_scene_motion(results):
    """씬별 분류 → 영상 1편 요약 (motion_scene_* 실험 지표)."""
    known = [r for r in results if r.get("motion_type") in SCENE_MOTION_TYPES]
    n = len(known)
    total_len = sum(max(0.0, r["end_s"] - r["start_s"]) for r in known) or None

    def ratio(kind):
        return round(sum(1 for r in known if r["motion_type"] == kind) / n, 4) if n else None

    def time_ratio(kind):
        if not total_len:
            return None
        return round(sum(max(0.0, r["end_s"] - r["start_s"])
                         for r in known if r["motion_type"] == kind) / total_len, 4)

    var = [r["flow_variance"] for r in known if isinstance(r.get("flow_variance"), (int, float))]
    mag = [r["flow_mag_mean"] for r in known if isinstance(r.get("flow_mag_mean"), (int, float))]
    return {
        "motion_scene_n": n,
        "motion_scene_unknown": len(results) - n,
        "motion_scene_static_ratio": ratio("static_image"),
        "motion_scene_animated_still_ratio": ratio("animated_still"),
        "motion_scene_clip_ratio": ratio("motion_clip"),
        "motion_scene_clip_time_ratio": time_ratio("motion_clip"),
        "motion_scene_flow_var_median": round(float(np.median(var)), 4) if var else None,
        "motion_scene_flow_mag_median": round(float(np.median(mag)), 4) if mag else None,
    }


def measure_scene_motion(video_dir, **params):
    """data/<id>/ 한 편: scenes.json을 읽어 분류하고 motion_scenes.json으로 저장."""
    import json
    from pathlib import Path
    d = Path(video_dir)
    scenes = json.loads((d / "scenes.json").read_text(encoding="utf-8")).get("scenes") or []
    p = {**SCENE_MOTION_PARAMS, **params}
    results = classify_scene_motion(d / "video.mp4", scenes, **p)
    payload = {"params": p, "scenes": results, "summary": summarize_scene_motion(results)}
    (d / "motion_scenes.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    return payload


def measure_corpus_scene_motion(data_dir="data", out_path="work/experiments/motion/scenes_corpus.jsonl",
                                *, log=None, **params):
    """코퍼스 전체 씬별 모션 분류 — 같은 파라미터로 이미 계산된 편은 건너뛴다."""
    import json
    import re
    from pathlib import Path
    root = Path(data_dir)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    p = {**SCENE_MOTION_PARAMS, **params}
    video_re = re.compile(r"[A-Za-z0-9_-]{11}")
    measured = skipped = missing = 0
    for d in sorted(root.iterdir()) if root.exists() else []:
        if not d.is_dir() or not video_re.fullmatch(d.name):
            continue
        if not (d / "video.mp4").exists() or not (d / "scenes.json").exists():
            missing += 1
            continue
        prev = d / "motion_scenes.json"
        if prev.exists():
            try:
                if json.loads(prev.read_text(encoding="utf-8")).get("params") == p:
                    skipped += 1
                    continue
            except ValueError:
                pass
        payload = measure_scene_motion(d, **p)
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"video_id": d.name, **p, **payload["summary"]},
                                ensure_ascii=False) + "\n")
        measured += 1
        if log:
            s = payload["summary"]
            log(f"{d.name} n={s['motion_scene_n']} still={s['motion_scene_animated_still_ratio']} "
                f"clip={s['motion_scene_clip_ratio']}")
    return {"measured": measured, "skipped": skipped, "missing": missing, "out": str(out)}
