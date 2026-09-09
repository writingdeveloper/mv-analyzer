from mv_analyzer.sync import sync_features


def make_scenes(cut_times, duration=120.0):
    """cut_times: 씬 경계 시각 리스트 → scenes dict 생성 헬퍼."""
    bounds = [0.0] + list(cut_times) + [duration]
    rows = [{"scene": i, "start_s": bounds[i], "end_s": bounds[i + 1]}
            for i in range(len(bounds) - 1)]
    return {"summary": {"duration_s": duration,
                        "cuts_per_minute": round(len(rows) / (duration / 60), 1)},
            "scenes": rows}


def test_cuts_exactly_on_beats():
    # 비트 0.5s 간격, 컷이 정확히 비트 위에
    audio = {"beat_times_s": [i * 0.5 for i in range(240)],
             "peak_energy_at_s": 60, "duration_s": 120.0}
    scenes = make_scenes([10.0, 20.0, 30.0])
    f = sync_features(scenes, audio, [])
    assert f["cut_beat_offset_med_s"] == 0.0
    assert f["cut_on_beat_ratio"] == 1.0
    assert f["first_cut_s"] == 10.0


def test_cuts_off_beat():
    audio = {"beat_times_s": [float(i) for i in range(120)],  # 1s 간격
             "peak_energy_at_s": 60, "duration_s": 120.0}
    scenes = make_scenes([10.5, 20.5])  # 비트에서 0.5s 어긋남
    f = sync_features(scenes, audio, [])
    assert f["cut_beat_offset_med_s"] == 0.5
    assert f["cut_on_beat_ratio"] == 0.0


def test_cut_accel_at_peak():
    # 피크(60s) ±10s 창에 컷 4개 = 12컷/min, 전체 6컷/120s = 3컷/min → 4.0배
    audio = {"beat_times_s": [], "peak_energy_at_s": 60, "duration_s": 120.0}
    scenes = make_scenes([52.0, 55.0, 58.0, 61.0, 90.0, 100.0])
    f = sync_features(scenes, audio, [])
    assert f["cut_accel_at_peak"] == 4.0


def test_first_lyric_passthrough_and_empty_beats():
    audio = {"beat_times_s": [], "peak_energy_at_s": 0, "duration_s": 60.0}
    scenes = make_scenes([5.0], duration=60.0)
    f = sync_features(scenes, audio, [{"t_s": 8, "line": "x"}])
    assert f["first_lyric_at_s"] == 8
    assert f["cut_beat_offset_med_s"] is None
    assert f["cut_on_beat_ratio"] is None


def test_beats_per_cut():
    audio = {"beat_times_s": [], "peak_energy_at_s": 0, "duration_s": 120.0,
             "bpm": 123.0}
    scenes = make_scenes([10.0, 20.0])  # summary cuts_per_minute = 1.5
    f = sync_features(scenes, audio, [])
    assert f["beats_per_cut"] == round(123.0 / 1.5, 1)  # 82.0


def test_beats_per_cut_none_when_bpm_missing():
    audio = {"beat_times_s": [], "peak_energy_at_s": 0, "duration_s": 120.0}
    scenes = make_scenes([10.0])
    f = sync_features(scenes, audio, [])
    assert f["beats_per_cut"] is None
