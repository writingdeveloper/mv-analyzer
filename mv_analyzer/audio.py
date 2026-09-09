"""오디오 특징: BPM·키·에너지 곡선 + 비트 타임스탬프 + ffmpeg ebur128 라우드니스."""
import re
import subprocess

import librosa
import numpy as np

MAJ = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def analyze_audio(audio_path):
    y, sr = librosa.load(audio_path, sr=22050, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    onsets = librosa.onset.onset_detect(y=y, sr=sr)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    best = max(
        [(float(np.corrcoef(np.roll(MAJ, k), chroma)[0, 1]), NOTES[k], "major") for k in range(12)]
        + [(float(np.corrcoef(np.roll(MIN, k), chroma)[0, 1]), NOTES[k], "minor") for k in range(12)]
    )
    rms = librosa.feature.rms(y=y)[0]
    cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    dur = len(y) / sr
    seg = int(10 * sr / 512)
    energy_curve = [round(float(rms[i:i + seg].mean()), 4) for i in range(0, len(rms), seg)]
    return {
        "duration_s": round(dur, 2),
        "bpm": round(float(np.atleast_1d(tempo)[0]), 1),
        "key": f"{best[1]} {best[2]}",
        "key_confidence": round(best[0], 3),
        "rms_mean": round(float(rms.mean()), 4),
        "rms_std": round(float(rms.std()), 4),
        "spectral_centroid_hz": round(float(cent.mean()), 0),
        "onsets_per_sec": round(len(onsets) / dur, 2),
        "energy_curve_10s": energy_curve,
        "peak_energy_at_s": int(np.argmax(energy_curve) * 10),
        "beat_times_s": [round(float(t), 3) for t in
                         librosa.frames_to_time(beats, sr=sr)],
    }


def measure_loudness(media_path):
    """ffmpeg ebur128 Summary에서 통합 라우드니스(I)와 LRA 추출."""
    proc = subprocess.run(
        ["ffmpeg", "-nostats", "-i", media_path,
         "-filter_complex", "ebur128", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    summary = proc.stderr.split("Summary:")[-1]
    i_m = re.search(r"I:\s*(-?[\d.]+)\s*LUFS", summary)
    lra_m = re.search(r"LRA:\s*(-?[\d.]+)\s*LU", summary)
    return {"lufs_i": float(i_m.group(1)) if i_m else None,
            "lra_lu": float(lra_m.group(1)) if lra_m else None}
