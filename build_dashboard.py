"""features 테이블 → 자체완결 대시보드 HTML (다중 도메인, 데이터·통계 내장).

도메인: 보컬로이드(work/features_table.jsonl, 완결) + K-pop(진행분, 잠정).
usage: python build_dashboard.py
"""
import csv
import datetime
import json
import os
from collections import Counter

import numpy as np
from scipy import stats as st

from mv_analyzer.stats import bh_fdr, cliffs_delta

KO = {
    "scene_median_shot_len_s": "샷 길이 중앙값(초)",
    "scene_avg_shot_len_s": "샷 길이 평균(초)",
    "scene_cuts_per_minute": "분당 컷 수",
    "scene_num_scenes": "씬 수",
    "sync_beats_per_cut": "컷당 비트 수",
    "scene_max_shot_len_s": "최장 샷(초)",
    "hook_cuts_first_15s": "첫 15초 컷 수",
    "scene_min_shot_len_s": "최단 샷(초)",
    "tag_avg_characters": "평균 등장인물 수",
    "scene_avg_saturation": "화면 채도",
    "scene_avg_brightness": "화면 밝기",
    "audio_spectral_centroid_hz": "스펙트럼 중심(Hz)",
    "audio_bpm": "BPM",
    "sync_cut_accel_at_peak": "피크 구간 컷 가속",
    "hook_energy_first_10s_ratio": "첫 10초 에너지 비율",
    "thumb_saturation": "썸네일 채도",
    "thumb_brightness": "썸네일 밝기",
    "sync_first_cut_s": "첫 컷 시점(초)",
    "tag_closeup_ratio": "클로즈업 비율",
    "lyrics_first_vocal_at_s": "첫 보컬 시점(초)",
    "audio_rms_mean": "RMS 에너지",
    "audio_lufs_i": "라우드니스(LUFS)",
    "audio_lra_lu": "라우드니스 범위(LU)",
    "thumb_num_characters": "썸네일 인물 수",
    "lyrics_lyric_lines_per_min": "분당 가사 라인",
    "lyrics_n_lyric_lines": "가사 라인 수",
    "title_bracket_segments": "제목 괄호 수",
    "audio_rms_std": "에너지 변동",
    "tag_wide_ratio": "와이드샷 비율",
    "sync_cut_on_beat_ratio": "정박 컷 비율",
    "audio_onsets_per_sec": "온셋 밀도(/초)",
    "title_exclaim_count": "제목 느낌표",
    "title_len": "제목 길이",
    "duration_s": "곡 길이(초)",
    "upload_hour": "업로드 시각",
    "lyrics_text_frame_ratio": "자막 프레임 비율",
    "sync_cut_beat_offset_med_s": "컷-비트 오프셋(초)",
    "audio_peak_energy_ratio": "피크 위치(비율)",
    "lyrics_first_lyric_at_s": "첫 가사 시점(초)",
    "tag_lyrics_text_ratio": "가사 텍스트 씬 비율",
    "lyrics_compression_ratio": "가사 압축률(낮을수록 반복적)",
    "lyrics_title_first_s": "곡명 첫 등장(초)",
    "lyrics_title_count": "곡명 등장 라인 수",
    "lyrics_first_chorus_s": "첫 후렴 도달(초)",
    "sync_cut_on_line_ratio": "컷-가사라인 정렬률",
    "heat_slope_first_30s": "초반 30초 리텐션 기울기",
    "heat_peak_at_ratio": "리플레이 피크 위치(비율)",
    "heat_peak_value": "리플레이 피크 값",
}
NUMERIC = list(KO.keys())
BIN_KO = {"thumb_has_text": "썸네일에 텍스트 있음", "was_premiere": "프리미어 공개",
          "lyrics_has_hardsub": "하드자막 있음", "has_nico_link": "니코니코 링크",
          "title_has_mv_mark": "제목에 MV 표기", "title_has_emoji": "제목 이모지"}
CAT_KO = {"tag_mood_top": "장면 분위기(최빈)", "thumb_mood": "썸네일 분위기",
          "lyrics_topic_1": "가사 주제", "lyrics_sentiment": "가사 정서",
          "lyrics_addressee": "가사 화자", "lyrics_source": "가사 소스"}
ROW_KEYS = (["video_id", "title", "channel", "group", "view_count",
             "subscriber_count", "view_per_sub", "upload_date",
             "tag_mood_top", "lyrics_topic_1", "lyrics_sentiment",
             "lyrics_source", "thumb_has_text", "was_premiere"] + NUMERIC)


def merge_extra(rows, workdir):
    """신규 분석 jsonl(video_id 키)을 features 행에 병합."""
    extra = {}
    for name in ("lyrics_structure", "heatmap_features"):
        p = f"{workdir}/{name}.jsonl"
        if os.path.exists(p):
            for l in open(p, encoding="utf-8"):
                r = json.loads(l)
                extra.setdefault(r["video_id"], {}).update(r)
    for row in rows:
        for k, v in extra.get(row["video_id"], {}).items():
            row.setdefault(k, v)
    return rows


def compute_domain(rows, label, note, min_n=10):
    top = [r for r in rows if r["group"] == "top"]
    bot = [r for r in rows if r["group"] == "bottom"]
    numeric = []
    for col in NUMERIC:
        a = [r[col] for r in top if r.get(col) is not None]
        b = [r[col] for r in bot if r.get(col) is not None]
        if len(a) < min_n or len(b) < min_n:
            continue
        numeric.append({
            "id": col, "ko": KO[col],
            "medTop": round(float(np.median(a)), 3),
            "medBot": round(float(np.median(b)), 3),
            "delta": round(cliffs_delta(a, b), 3),
            "p": float(st.mannwhitneyu(a, b, alternative="two-sided").pvalue),
        })
    if numeric:
        qs = bh_fdr(np.array([r["p"] for r in numeric]))
        for r, q in zip(numeric, qs):
            r["q"] = round(float(q), 4)
            r["sig"] = bool(q < 0.05)
            del r["p"]
    numeric.sort(key=lambda r: -abs(r["delta"]))

    binary = []
    for col, ko in BIN_KO.items():
        na = sum(1 for r in top if r.get(col) is not None)
        nb = sum(1 for r in bot if r.get(col) is not None)
        if na < min_n or nb < min_n:
            continue
        ta = sum(1 for r in top if r.get(col) is True)
        tb = sum(1 for r in bot if r.get(col) is True)
        p = st.fisher_exact([[ta, na - ta], [tb, nb - tb]]).pvalue
        binary.append({"id": col, "ko": ko, "top": ta, "nTop": na,
                       "bot": tb, "nBot": nb, "p": round(float(p), 4)})
    binary.sort(key=lambda r: r["p"])

    categorical = []
    for col, ko in CAT_KO.items():
        ct = Counter(str(r[col]) for r in top if r.get(col) is not None)
        cb = Counter(str(r[col]) for r in bot if r.get(col) is not None)
        keys = [k for k, _ in (ct + cb).most_common(6)]
        if not keys:
            continue
        categorical.append({"id": col, "ko": ko, "keys": keys,
                            "top": [ct.get(k, 0) for k in keys],
                            "bot": [cb.get(k, 0) for k in keys]})

    rows_slim = [{k: r.get(k) for k in ROW_KEYS if k in r} for r in rows]
    return {"label": label, "note": note, "nTop": len(top), "nBot": len(bot),
            "numeric": numeric, "binary": binary, "categorical": categorical,
            "rows": rows_slim}


def load_vocaloid():
    rows = [json.loads(l) for l in
            open("work/features_table.jsonl", encoding="utf-8")]
    return merge_extra(rows, "work")


def load_kpop():
    out = []
    if not os.path.exists("work/kpop/sample.csv"):
        return out
    for r in csv.DictReader(open("work/kpop/sample.csv", encoding="utf-8")):
        p = f"data/{r['video_id']}/features.json"
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                row = json.load(f)
            row["group"] = r["group"]
            out.append(row)
    return merge_extra(out, "work/kpop")


def main():
    domains = {"vocaloid": compute_domain(
        load_vocaloid(), "보컬로이드 — 완결 (상·하위 각 25편)",
        "2025-04~2026-04 원본 프로듀서 채널 신곡. 본 연구의 확정 결과.")}
    kpop_rows = load_kpop()
    if kpop_rows:
        n = len(kpop_rows)
        domains["kpop"] = compute_domain(
            kpop_rows, f"K-pop — 진행 중 ({n}/50편 잠정)",
            "공식 아티스트/레이블 채널. 배치 진행분의 잠정 통계 — 기획사 규모 "
            "교란이 크고 표본 미완이라 참고용. 배치 완료 후 갱신됨.")
    heat_curves = None
    if os.path.exists("work/heatmap_curves.json"):
        with open("work/heatmap_curves.json", encoding="utf-8") as f:
            heat_curves = json.load(f)
    data = {"generated": datetime.date.today().isoformat(),
            "default": "vocaloid", "domains": domains,
            "heat_curves": heat_curves}

    with open("docs/reports/dashboard_template.html", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("/*__DATA__*/",
                        "const DATA = " + json.dumps(data, ensure_ascii=False) + ";")
    with open("docs/reports/dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)
    for k, d in domains.items():
        print(f"{k}: rows {len(d['rows'])} (top {d['nTop']}/bot {d['nBot']}), "
              f"numeric {len(d['numeric'])}")
    print(f"dashboard.html {len(html) // 1024}KB")


if __name__ == "__main__":
    main()
