"""씬별 모션 3분류기의 사람 라벨 게이트 — 층화 표본 추출 · 스트립 생성 · 채점.

`motion_scene_*`는 `feature_policy`의 실험 접두사라 가설검정에 들어가지 못한다. 들어가려면
2026-07-17 측정 정확도 검증과 같은 절차를 통과해야 한다: 분류 결과를 보지 않은 독립 라벨러가
같은 폐쇄 어휘로 블라인드 라벨링하고, 일치율과 Cohen's κ를 낸다.

**사전 등록한 게이트(라벨링 전에 고정)**: 일치율 ≥ 0.75 **그리고** κ ≥ 0.60(Landis & Koch substantial).
둘 중 하나라도 미달이면 채택하지 않는다. 클래스별로 κ가 갈리면 약한 클래스는 서술에서 가중을 낮춘다.

라벨러가 보는 근거는 분류기와 다르게 잡았다. 분류기는 0.4초 간격 프레임쌍의 광류를 보지만,
스트립은 씬 중간의 0.1초 간격 4연사와 씬 앞·끝 두 장을 나란히 붙인다. 같은 그림이 통째로 밀리면
카메라, 그림 자체가 달라지면 움직임 — 사람이 실제로 그렇게 본다. 근거가 겹치지 않아야 독립 검증이
된다. (`_strip_times` 주석에 1차 프로토콜이 왜 실패했는지 적어 두었다.)
"""
from __future__ import annotations

import json
import os
import random

import cv2
import numpy as np

from .motion import SCENE_MOTION_TYPES

LABEL_DIR = os.path.join("work", "experiments", "motion", "label")
# 라벨러에게 주는 폐쇄 어휘 (분류기 클래스와 1:1)
VOCAB = {
    "static_image": "정지 — 전부 사실상 같은 그림, 아무것도 움직이지 않음",
    "animated_still": "카메라만 — 같은 그림이 통째로 밀리거나 확대/축소됨 (팬·줌)",
    "motion_clip": "움직임 — 그림 자체가 달라짐 (인물·사물이 움직이거나 작화가 바뀜)",
}
GATE = {"min_agreement": 0.75, "min_kappa": 0.60}


def _scene_rows(data_dir="data"):
    """모든 영상의 motion_scenes.json에서 (video_id, scene, 예측 클래스, 구간)을 편다."""
    rows = []
    for vid in sorted(os.listdir(data_dir)):
        path = os.path.join(data_dir, vid, "motion_scenes.json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        for s in doc.get("scenes") or []:
            if s.get("motion_type") not in SCENE_MOTION_TYPES:
                continue
            rows.append({"video_id": vid, "scene": s.get("scene"),
                         "start_s": s.get("start_s"), "end_s": s.get("end_s"),
                         "predicted": s.get("motion_type")})
    return rows


def stratified_sample(rows, n=45, seed=20260903):
    """클래스별로 고르게 뽑는다. 코퍼스가 motion_clip에 쏠려 있어 무작위로는 희소 클래스가 안 잡힌다."""
    rng = random.Random(seed)
    by_class = {}
    for r in rows:
        by_class.setdefault(r["predicted"], []).append(r)
    per = max(1, n // max(1, len(by_class)))
    picked = []
    for cls in SCENE_MOTION_TYPES:
        pool = by_class.get(cls) or []
        rng.shuffle(pool)
        picked.extend(pool[:per])
    # 남는 자리는 큰 풀에서 채운다
    if len(picked) < n:
        rest = [r for r in rows if r not in picked]
        rng.shuffle(rest)
        picked.extend(rest[:n - len(picked)])
    rng.shuffle(picked)  # 파일명 순서로 클래스가 드러나지 않게
    for i, r in enumerate(picked, 1):
        r["item_id"] = f"m{i:03d}"
    return picked


def _strip_times(start_s, end_s, protocol="burst"):
    """라벨러가 볼 시각들.

    protocol="stills"(1차 시도): 씬 앞·+0.4초·중간·끝 네 장. 2026-09-03 파일럿에서 이 방식은
    **연속적인 작은 흔들림을 못 본다**는 것이 드러났다 — 0.4초에 8px씩 진동하는 씬(m016)도
    멀리 떨어진 정지 프레임에서는 같은 자리로 돌아와 있어 사람이 '정지'로 읽는다.
    protocol="burst"(기본): 중간 지점에서 0.1초 간격 4연사 + 씬 앞·끝 두 장. 연사가 연속 움직임을,
    양 끝 두 장이 내용 변화와 프레이밍 이동을 드러낸다.
    """
    span = max(0.0, (end_s or 0) - (start_s or 0))
    head = start_s + min(0.15, span * 0.05)
    tail = end_s - min(0.3, span * 0.1)
    if protocol == "stills":
        return [head, head + 0.4, start_s + span / 2, tail]
    mid = start_s + span / 2
    return [head, mid, mid + 0.1, mid + 0.2, mid + 0.3, tail]


def _compose(frames, height):
    gap = np.full((height, 6, 3), 255, np.uint8)
    strip = frames[0]
    for f in frames[1:]:
        strip = np.hstack([strip, gap, f])
    return strip


def make_strips(video_path, jobs, height=220, protocol="burst"):
    """한 영상에서 여러 씬의 스트립을 만든다. 씬마다 시각 탐색 — 씬 수가 적어 순차 디코딩보다 싸다.

    jobs: [(out_path, start_s, end_s), ...]. 만들어진 out_path 목록을 돌려준다.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []
    made = []
    for out_path, start_s, end_s in jobs:
        frames = []
        for t in _strip_times(start_s, end_s, protocol):
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000.0)
            ok, frame = cap.read()
            if not ok:
                continue
            h, w = frame.shape[:2]
            scale = height / float(h)
            frames.append(cv2.resize(frame, (max(1, int(w * scale)), height)))
        if len(frames) < 2:
            continue
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        cv2.imwrite(out_path, _compose(frames, height), [int(cv2.IMWRITE_JPEG_QUALITY), 88])
        made.append(out_path)
    cap.release()
    return made


def build(data_dir="data", n=45, seed=20260903, out_dir=LABEL_DIR, protocol="burst"):
    """표본 추출 + 스트립 생성 + 블라인드 시트/정답키 기록."""
    picked = stratified_sample(_scene_rows(data_dir), n, seed)
    os.makedirs(out_dir, exist_ok=True)
    by_video = {}
    for r in picked:
        r["image"] = os.path.join(out_dir, f"{r['item_id']}.jpg")
        by_video.setdefault(r["video_id"], []).append(r)
    ok = set()
    for vid, items in by_video.items():
        jobs = [(r["image"], r["start_s"], r["end_s"]) for r in items]
        ok.update(make_strips(os.path.join(data_dir, vid, "video.mp4"), jobs, protocol=protocol))
    sheet = [{"item_id": r["item_id"], "image": r["image"].replace("\\", "/"), "label": None}
             for r in picked if r["image"] in ok]
    key = [{k: v for k, v in r.items() if k != "image"} for r in picked if r["image"] in ok]
    failed = [r["item_id"] for r in picked if r["image"] not in ok]
    sheet_path = os.path.join(out_dir, "sheet.jsonl")
    key_path = os.path.join(out_dir, "key.jsonl")
    for path, rows in ((sheet_path, sheet), (key_path, key)):
        with open(path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"n_items": len(sheet), "failed": failed, "sheet": sheet_path, "key": key_path,
            "seed": seed, "protocol": protocol, "vocab": VOCAB, "gate": GATE,
            "by_class": {c: sum(1 for k in key if k["predicted"] == c) for c in SCENE_MOTION_TYPES}}


def cohens_kappa(a, b, classes):
    n = len(a)
    if not n:
        return None
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in classes)
    return None if pe >= 1.0 else round((po - pe) / (1 - pe), 3)


def score(sheet_path, key_path):
    def _read(p):
        with open(p, encoding="utf-8") as fh:
            return {json.loads(l)["item_id"]: json.loads(l) for l in fh if l.strip()}
    sheet, key = _read(sheet_path), _read(key_path)
    pairs = [(key[i]["predicted"], sheet[i]["label"]) for i in sorted(key)
             if sheet.get(i, {}).get("label") in SCENE_MOTION_TYPES]
    if not pairs:
        return {"n_labeled": 0, "error": "라벨이 하나도 채워지지 않았습니다"}
    pred = [p for p, _ in pairs]
    human = [h for _, h in pairs]
    agree = sum(1 for p, h in pairs if p == h) / len(pairs)
    kappa = cohens_kappa(pred, human, list(SCENE_MOTION_TYPES))
    confusion = {c: {d: 0 for d in SCENE_MOTION_TYPES} for c in SCENE_MOTION_TYPES}
    for p, h in pairs:
        confusion[p][h] += 1
    per_class = {}
    for c in SCENE_MOTION_TYPES:
        tp = confusion[c][c]
        n_pred = sum(confusion[c].values())
        n_true = sum(confusion[d][c] for d in SCENE_MOTION_TYPES)
        per_class[c] = {"n_pred": n_pred, "n_human": n_true,
                        "precision": round(tp / n_pred, 3) if n_pred else None,
                        "recall": round(tp / n_true, 3) if n_true else None}
    passed = agree >= GATE["min_agreement"] and (kappa or 0) >= GATE["min_kappa"]
    return {"n_labeled": len(pairs), "n_items": len(key), "agreement": round(agree, 3),
            "kappa": kappa, "gate": GATE, "passed": bool(passed),
            "confusion": confusion, "per_class": per_class}
