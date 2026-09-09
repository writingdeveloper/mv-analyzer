"""음향×화면 교차 동기화 파생 feature. 입력은 기존 산출물 dict — 추가 분석 없음."""
import numpy as np

ON_BEAT_TOL_S = 0.1   # 컷이 비트 위로 간주되는 허용 오차
PEAK_WIN_S = 10.0     # 에너지 피크 주변 창 (±)


def sync_features(scenes, audio, lyric_lines):
    rows = scenes["scenes"]
    duration = float(scenes["summary"]["duration_s"])
    cuts = [r["start_s"] for r in rows[1:]]  # 첫 씬 시작(0s)은 컷이 아님
    beats = audio.get("beat_times_s") or []

    if cuts and beats:
        offsets = [min(abs(c - b) for b in beats) for c in cuts]
        offset_med = round(float(np.median(offsets)), 3)
        on_beat = round(sum(o <= ON_BEAT_TOL_S for o in offsets) / len(offsets), 3)
    else:
        offset_med, on_beat = None, None

    peak = audio.get("peak_energy_at_s")
    accel = None
    if peak is not None and cuts and duration:
        lo, hi = peak - PEAK_WIN_S, peak + PEAK_WIN_S
        win_len_min = (min(hi, duration) - max(lo, 0.0)) / 60
        win_rate = sum(lo <= c <= hi for c in cuts) / win_len_min if win_len_min else 0
        overall = len(cuts) / (duration / 60)
        accel = round(win_rate / overall, 2) if overall else None

    bpm = audio.get("bpm")
    cpm = scenes["summary"].get("cuts_per_minute")
    return {
        "cut_beat_offset_med_s": offset_med,
        "cut_on_beat_ratio": on_beat,
        "cut_accel_at_peak": accel,
        "first_cut_s": cuts[0] if cuts else None,
        "first_lyric_at_s": lyric_lines[0]["t_s"] if lyric_lines else None,
        "beats_per_cut": round(bpm / cpm, 1) if bpm and cpm else None,
    }
