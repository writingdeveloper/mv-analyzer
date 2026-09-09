import os
import subprocess

import pytest

from mv_analyzer.audio import analyze_audio, measure_loudness

PILOT_WAV = os.path.join("pilot", "audio.wav")


@pytest.fixture(scope="module")
def tone_wav(tmp_path_factory):
    """ffmpeg로 5초 440Hz 사인파 생성 — 결정적 테스트 입력."""
    p = str(tmp_path_factory.mktemp("audio") / "tone.wav")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    "sine=frequency=440:duration=5", "-ar", "22050", p],
                   check=True, capture_output=True)
    return p


def test_analyze_audio_keys_and_types(tone_wav):
    out = analyze_audio(tone_wav)
    for key in ["duration_s", "bpm", "key", "key_confidence", "rms_mean",
                "onsets_per_sec", "energy_curve_10s", "peak_energy_at_s",
                "beat_times_s"]:
        assert key in out, key
    assert abs(out["duration_s"] - 5.0) < 0.1
    assert isinstance(out["beat_times_s"], list)


def test_measure_loudness_sine(tone_wav):
    out = measure_loudness(tone_wav)
    assert out["lufs_i"] is not None and -30 < out["lufs_i"] < 0
    assert out["lra_lu"] is not None and out["lra_lu"] >= 0


@pytest.mark.slow
@pytest.mark.media
@pytest.mark.skipif(not os.path.exists(PILOT_WAV), reason="pilot 미디어 없음")
def test_pilot_regression():
    out = analyze_audio(PILOT_WAV)
    assert abs(out["bpm"] - 123.0) < 1.0           # 파일럿 실측값
    assert out["key"] == "D# minor"
    lufs = measure_loudness(PILOT_WAV)
    assert abs(lufs["lufs_i"] - (-9.9)) < 0.5       # 리포트 기재값 검증
