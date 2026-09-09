"""대화 레이어: 이미 분석된 영상 산출물을 조인·검색해 '증거'로 되돌려준다.

측정은 하지 않는다 — data/<id>/ 에 쌓인 결과만 읽어 시간축으로 묶는 읽기 전용 계층.
추론·대화는 호출자(Claude Code)가 맡고, 여기서는 타임스탬프가 붙은 근거만 낸다.
"""
import json
import os
import re
import unicodedata

ARTIFACTS = {
    "features": "features.json",
    "scenes": "scenes.json",
    "scene_tags": "scene_tags.json",
    "lyrics": "lyrics_lines.json",
    "audio": "audio_features.json",
    "sync": "sync_features.json",
    "thumb": "thumb_tags.json",
    "loudness": "loudness.json",
    "meta": "meta.json",
    "motion_scenes": "motion_scenes.json",  # 씬별 모션 3분류 (실험 측정기, 없을 수 있음)
}


def _read(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load(vid, data_dir="data"):
    """영상 1편의 산출물 묶음. 없는 항목은 None."""
    d = os.path.join(data_dir, vid)
    if not os.path.isdir(d):
        return None
    b = {k: _read(os.path.join(d, fn)) for k, fn in ARTIFACTS.items()}
    b["video_id"] = vid
    b["dir"] = d
    return b


def list_ids(data_dir="data"):
    """features.json이 있는 = 분석 완료된 영상 id 목록."""
    if not os.path.isdir(data_dir):
        return []
    return sorted(v for v in os.listdir(data_dir)
                  if os.path.exists(os.path.join(data_dir, v, "features.json")))


def catalog(data_dir="data"):
    """전체 목록의 한 줄 요약 — 무엇을 얘기할 수 있는지 훑기용."""
    rows = []
    for vid in list_ids(data_dir):
        f = _read(os.path.join(data_dir, vid, "features.json")) or {}
        rows.append({
            "video_id": vid,
            "title": f.get("title"),
            "channel": f.get("channel"),
            "duration_s": f.get("duration_s"),
            "upload_date": f.get("upload_date"),
            "view_per_sub": f.get("view_per_sub"),
            "num_scenes": f.get("scene_num_scenes"),
            "cuts_per_minute": f.get("scene_cuts_per_minute"),
            "bpm": f.get("audio_bpm"),
            "key": f.get("audio_key"),
            "style": f.get("tag_style_top"),
            "mood": f.get("tag_mood_top"),
            "lyrics_lang": f.get("lyrics_lang"),
            "lyrics_source": f.get("lyrics_source"),
            "n_lyric_lines": f.get("lyrics_n_lyric_lines"),
        })
    return rows


# --- 시간축 ---------------------------------------------------------------

def cut_times(bundle):
    """컷(씬 전환) 시각 목록 — 첫 씬 시작(0초)은 컷이 아니므로 제외."""
    scenes = (bundle.get("scenes") or {}).get("scenes") or []
    return [s["start_s"] for s in scenes[1:]]


def cuts_in_window(bundle, t0, t1):
    return sum(1 for t in cut_times(bundle) if t0 <= t < t1)


ENERGY_BIN_S = 10  # energy_curve_10s = 10초 버킷 (audio.py: peak = argmax*10)


def energy_at(bundle, t):
    """해당 10초 버킷의 에너지 + 곡 전체 최고 버킷 대비 비율."""
    curve = (bundle.get("audio") or {}).get("energy_curve_10s") or []
    if not curve:
        return None
    i = max(0, min(int(t // ENERGY_BIN_S), len(curve) - 1))
    peak = max(curve) or None
    return {"bin": i, "bin_s": [i * ENERGY_BIN_S, (i + 1) * ENERGY_BIN_S],
            "n_bins": len(curve), "value": curve[i],
            "peak_at_s": curve.index(max(curve)) * ENERGY_BIN_S,
            "ratio_to_peak": round(curve[i] / peak, 3) if peak else None}


def scene_at(bundle, t):
    """시각 t를 포함하는 씬 + 그 씬의 VLM 태그."""
    scenes = (bundle.get("scenes") or {}).get("scenes") or []
    tags = bundle.get("scene_tags") or []
    for i, s in enumerate(scenes):
        if s["start_s"] <= t < s["end_s"] or (i == len(scenes) - 1 and t >= s["start_s"]):
            out = dict(s)
            if i < len(tags):
                out["tags"] = tags[i]
            out["keyframe_path"] = os.path.join(bundle["dir"], "keyframes",
                                                s.get("keyframe", ""))
            return out
    return None


def lyrics_between(bundle, t0, t1):
    lines = (bundle.get("lyrics") or {}).get("lines") or []
    return [l for l in lines if t0 <= l.get("t_s", -1) < t1]


def timeline(bundle):
    """씬·가사·에너지 피크를 하나의 시간순 이벤트 열로 병합."""
    ev = []
    scenes = (bundle.get("scenes") or {}).get("scenes") or []
    tags = bundle.get("scene_tags") or []
    for i, s in enumerate(scenes):
        e = {"t_s": round(s["start_s"], 2), "kind": "scene", "scene": s["scene"],
             "len_s": s["len_s"], "brightness": s.get("brightness"),
             "saturation": s.get("saturation"),
             "dominant_color": s.get("dominant_color"),
             "keyframe": s.get("keyframe")}
        if i < len(tags):
            t = tags[i]
            e.update({k: t.get(k) for k in
                      ("setting", "mood", "shot_type", "style",
                       "num_characters", "visual_elements", "has_lyrics_text")})
        ev.append(e)

    for l in (bundle.get("lyrics") or {}).get("lines") or []:
        ev.append({"t_s": l.get("t_s"), "kind": "lyric", "line": l.get("line")})

    a = bundle.get("audio") or {}
    if a.get("peak_energy_at_s") is not None:
        ev.append({"t_s": a["peak_energy_at_s"], "kind": "peak_energy",
                   "note": "곡 최고 에너지 지점"})

    return sorted(ev, key=lambda e: (e.get("t_s") is None, e.get("t_s") or 0))


def at(bundle, t, window=8.0):
    """시각 t의 전체 맥락 — 화면·가사·리듬·에너지를 한 번에.

    음수 또는 영상 길이 밖의 시각은 잘못된 근거를 반환하지 않도록 거부한다.
    """
    f = bundle.get("features") or {}
    dur = f.get("duration_s") or (bundle.get("scenes") or {}).get(
        "summary", {}).get("duration_s")
    if t < 0:
        raise ValueError("time must be >= 0")
    if dur is not None and t > dur:
        raise ValueError(f"time {t} exceeds duration {dur}")
    sc = scene_at(bundle, t)
    ctx = {
        "video_id": bundle["video_id"],
        "title": f.get("title"),
        "t_s": t,
        "position_ratio": round(t / dur, 3) if dur else None,
        "scene": sc,
        "lyrics_near": lyrics_between(bundle, t - window, t + window),
        "cuts_last_30s": cuts_in_window(bundle, max(0.0, t - 30), t),
        "energy": energy_at(bundle, t),
    }
    return ctx


# --- 검색 -----------------------------------------------------------------

def _norm(s):
    return unicodedata.normalize("NFKC", str(s or "")).casefold()


def search(query, data_dir="data", ids=None, limit=50):
    """가사 라인·씬 태그·제목을 가로질러 찾고 타임스탬프를 붙여 돌려준다."""
    q = _norm(query)
    hits = []
    for vid in (ids or list_ids(data_dir)):
        b = load(vid, data_dir)
        if not b:
            continue
        f = b.get("features") or {}
        title = f.get("title")
        if q in _norm(title) or q in _norm(f.get("channel")):
            hits.append({"video_id": vid, "title": title, "t_s": None,
                         "where": "title", "text": title})
        for l in (b.get("lyrics") or {}).get("lines") or []:
            if q in _norm(l.get("line")):
                hits.append({"video_id": vid, "title": title,
                             "t_s": l.get("t_s"), "where": "lyric",
                             "text": l.get("line")})
        scenes = (b.get("scenes") or {}).get("scenes") or []
        for i, tg in enumerate(b.get("scene_tags") or []):
            blob = " ".join(filter(None, [
                str(tg.get("setting")), str(tg.get("mood")),
                str(tg.get("style")), str(tg.get("shot_type")),
                " ".join(tg.get("visual_elements") or [])]))
            if q in _norm(blob):
                t0 = scenes[i]["start_s"] if i < len(scenes) else None
                hits.append({"video_id": vid, "title": title, "t_s": t0,
                             "where": f"scene#{i}", "text": blob.strip()})
        if len(hits) >= limit:
            break
    return hits[:limit]


# --- 비교 -----------------------------------------------------------------

NUM_COLS = [
    ("scene_cuts_per_minute", "분당 컷 수"),
    ("scene_median_shot_len_s", "샷 길이 중앙값(초)"),
    ("scene_num_scenes", "씬 수"),
    ("hook_cuts_first_15s", "첫 15초 컷 수"),
    ("audio_bpm", "BPM"),
    ("audio_lufs_i", "라우드니스(LUFS)"),
    ("sync_cut_on_beat_ratio", "비트 정렬 컷 비율"),
    ("sync_first_lyric_at_s", "첫 가사 시점(초)"),
    ("duration_s", "길이(초)"),
    ("tag_avg_characters", "평균 등장인물"),
    ("scene_avg_saturation", "채도"),
    ("scene_avg_brightness", "밝기"),
    ("lyrics_lyric_lines_per_min", "분당 가사 줄"),
]
CAT_COLS = [
    ("tag_style_top", "작화 스타일"),
    ("tag_mood_top", "지배적 무드"),
    ("audio_key", "조성"),
    ("lyrics_sentiment", "가사 정서"),
    ("lyrics_addressee", "가사 화자 대상"),
    ("lyrics_topic_1", "가사 주제"),
    ("thumb_composition", "썸네일 구도"),
]


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def compare(vids, data_dir="data"):
    """여러 편의 공통점·편차 — '내가 좋아하는 것들의 공통 형태' 질문용."""
    rows = []
    for vid in vids:
        f = (load(vid, data_dir) or {}).get("features")
        if f:
            rows.append(f)
    if not rows:
        return None

    numeric = []
    for col, ko in NUM_COLS:
        vals = [r[col] for r in rows if isinstance(r.get(col), (int, float))]
        if len(vals) < 2:
            continue
        med = _median(vals)
        spread = (max(vals) - min(vals)) / abs(med) if med else None
        numeric.append({"col": col, "label": ko, "n": len(vals),
                        "median": round(med, 3), "min": round(min(vals), 3),
                        "max": round(max(vals), 3),
                        "spread_ratio": round(spread, 3) if spread is not None else None})
    # 편차가 작은 순 = 공통된 형질
    numeric.sort(key=lambda d: (d["spread_ratio"] is None, d["spread_ratio"]))

    categorical = []
    for col, ko in CAT_COLS:
        vals = [r.get(col) for r in rows if r.get(col)]
        if not vals:
            continue
        counts = {}
        for v in vals:
            counts[str(v)] = counts.get(str(v), 0) + 1
        top, cnt = max(counts.items(), key=lambda kv: kv[1])
        categorical.append({"col": col, "label": ko, "top": top,
                            "share": round(cnt / len(vals), 3), "n": len(vals),
                            "counts": counts})
    categorical.sort(key=lambda d: -d["share"])

    return {"n_videos": len(rows),
            "videos": [{"video_id": r.get("video_id"), "title": r.get("title")}
                       for r in rows],
            "numeric": numeric, "categorical": categorical}


def extract_video_id(arg):
    """URL이든 id든 11자 video_id로."""
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", arg)
    return m.group(1) if m else arg


# --- 프로파일: 취향 목록 vs 코퍼스 ------------------------------------------
#
# compare()가 "목록 안에서 무엇이 공통인가"라면, profile()은 그 공통점이 코퍼스 전체
# 대비 어디에 놓이는지(백분위)를 붙여 '취향의 특이점'과 '장르 관습'을 가른다.
# 여섯 편 전부 anime·활기여도 코퍼스 대부분이 그렇다면 취향 정보가 아니다.

PROFILE_EXT_COLS = [
    ("ext_scene_brightness_std", "밝기 변동(씬 간)"),
    ("ext_color_change_mean", "색 변화 평균"),
    ("ext_color_unique_ratio", "고유색 비율"),
    ("ext_lyrics_first_chorus_ratio", "첫 후렴 위치(곡 비율)"),
    ("motion_scene_clip_ratio", "실제 움직임 씬 비율"),
    ("motion_scene_animated_still_ratio", "정지 일러스트+카메라 비율"),
    ("motion_scene_static_ratio", "정지 이미지 씬 비율"),
]
HUE_BUCKETS = ["빨강", "주황", "노랑", "초록", "청록", "파랑", "보라", "자홍"]
VERDICT_ORDER = {"특이점·높음": 0, "특이점·낮음": 0, "공통": 1, "공통·관습": 2, "무관(편차 큼)": 3}


def read_id_list(path):
    """한 줄에 하나씩 id/URL, '#' 뒤는 주석. 순서 유지·중복 제거."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            token = line.split("#", 1)[0].strip()
            if not token:
                continue
            vid = extract_video_id(token.split()[0])
            if vid not in out:
                out.append(vid)
    return out


def _row_with_ext(bundle):
    from .extensions import derived_features
    f = dict(bundle.get("features") or {})
    f.update(derived_features(f, bundle.get("scenes"), bundle.get("lyrics")))
    f.update((bundle.get("motion_scenes") or {}).get("summary") or {})
    return f


def corpus_rows(data_dir="data"):
    """분석 완료 전편의 features(+파생 ext) — video_id → row."""
    rows = {}
    for vid in list_ids(data_dir):
        b = load(vid, data_dir)
        if b:
            rows[vid] = _row_with_ext(b)
    return rows


def percentile_rank(values, v):
    vals = [x for x in values if isinstance(x, (int, float))]
    if not vals:
        return None
    less = sum(1 for x in vals if x < v)
    eq = sum(1 for x in vals if x == v)
    return round(100.0 * (less + 0.5 * eq) / len(vals), 1)


def hue_bucket(hex_color):
    import colorsys
    if not isinstance(hex_color, str) or len(hex_color) != 7 or not hex_color.startswith("#"):
        return None
    try:
        r, g, b = (int(hex_color[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    except ValueError:
        return None
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if v < 0.2:
        return "어두움"
    if s < 0.15:
        return "무채색"
    return HUE_BUCKETS[int((h * 360 + 22.5) // 45) % 8]


def palette_distribution(scenes_obj):
    """씬 길이 가중 색상 버킷 분포 (합 1)."""
    weight = {}
    for s in (scenes_obj or {}).get("scenes") or []:
        k = hue_bucket(s.get("dominant_color"))
        if k:
            weight[k] = weight.get(k, 0.0) + float(s.get("len_s") or 0.0)
    total = sum(weight.values())
    return {k: round(w / total, 4) for k, w in weight.items()} if total else {}


def _mean_dist(dists):
    keys = set().union(*dists) if dists else set()
    return {k: round(sum(d.get(k, 0.0) for d in dists) / len(dists), 4) for k in keys}


def profile(vids, data_dir="data", hi=70.0, lo=30.0, spread_tol=0.35):
    """취향 목록의 공통 형질을 코퍼스 백분위와 함께 — 특이점 / 공통 / 관습 / 무관."""
    corpus = corpus_rows(data_dir)
    found = [v for v in vids if v in corpus]
    missing = [v for v in vids if v not in corpus]
    if not found:
        return {"n_videos": 0, "n_corpus": len(corpus), "videos": [], "missing": missing,
                "numeric": [], "categorical": [], "palette": None}

    numeric = []
    for col, label in NUM_COLS + PROFILE_EXT_COLS:
        pool = [r.get(col) for r in corpus.values()]
        pts = []
        for v in found:
            x = corpus[v].get(col)
            if isinstance(x, (int, float)):
                pts.append({"video_id": v, "value": x, "pct": percentile_rank(pool, x)})
        if not pts:
            continue
        vals = [p["value"] for p in pts]
        pcts = [p["pct"] for p in pts]
        med, med_pct = _median(vals), _median(pcts)
        spread = (max(vals) - min(vals)) / abs(med) if med else None
        if all(p >= hi for p in pcts):
            verdict = "특이점·높음"
        elif all(p <= lo for p in pcts):
            verdict = "특이점·낮음"
        elif spread is not None and spread <= spread_tol:
            verdict = "공통·관습" if lo < med_pct < hi else "공통"
        else:
            verdict = "무관(편차 큼)"
        numeric.append({"col": col, "label": label, "n": len(pts), "median": round(med, 3),
                        "median_pct": round(med_pct, 1), "min_pct": min(pcts), "max_pct": max(pcts),
                        "spread_ratio": round(spread, 3) if spread is not None else None,
                        "verdict": verdict, "points": pts})
    numeric.sort(key=lambda d: (VERDICT_ORDER[d["verdict"]], -abs(d["median_pct"] - 50)))

    categorical = []
    for col, label in CAT_COLS:
        vals = [corpus[v].get(col) for v in found if corpus[v].get(col)]
        if not vals:
            continue
        counts = {}
        for x in vals:
            counts[str(x)] = counts.get(str(x), 0) + 1
        top, cnt = max(counts.items(), key=lambda kv: kv[1])
        share = cnt / len(vals)
        pool = [str(r.get(col)) for r in corpus.values() if r.get(col)]
        corpus_share = pool.count(top) / len(pool) if pool else None
        if share >= 0.8 and corpus_share is not None and corpus_share < 0.5:
            verdict = "취향 신호"
        elif corpus_share is not None and corpus_share >= 0.5:
            verdict = "관습"
        else:
            verdict = "혼재"
        categorical.append({"col": col, "label": label, "top": top, "share": round(share, 3),
                            "corpus_share": round(corpus_share, 3) if corpus_share is not None else None,
                            "n": len(vals), "verdict": verdict, "counts": counts})
    categorical.sort(key=lambda d: (-d["share"], -(d["share"] - (d["corpus_share"] or 0))))

    fav_d = [palette_distribution(load(v, data_dir).get("scenes")) for v in found]
    corp_d = [palette_distribution(load(v, data_dir).get("scenes")) for v in corpus]
    fav_mean, corp_mean = _mean_dist(fav_d), _mean_dist(corp_d)
    keys = set(fav_mean) | set(corp_mean)
    diff = sorted(({"bucket": k, "favorites": fav_mean.get(k, 0.0), "corpus": corp_mean.get(k, 0.0),
                    "delta": round(fav_mean.get(k, 0.0) - corp_mean.get(k, 0.0), 4)} for k in keys),
                  key=lambda d: -d["delta"])
    palette = {"favorites": fav_mean, "corpus": corp_mean, "diff": diff,
               "per_video": dict(zip(found, fav_d))}

    return {"n_videos": len(found), "n_corpus": len(corpus),
            "videos": [{"video_id": v, "title": corpus[v].get("title")} for v in found],
            "missing": missing, "numeric": numeric, "categorical": categorical,
            "palette": palette}
