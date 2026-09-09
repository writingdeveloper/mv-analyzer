import json

import pytest

from mv_analyzer.music_structure import normalize_label, normalize_structure, run_music_structure


def test_normalize_label_handles_common_variants():
    assert normalize_label("Chorus") == "chorus"
    assert normalize_label("pre_chorus") == "pre-chorus"
    assert normalize_label("Pre-Chorus") == "pre-chorus"
    assert normalize_label("inst") == "unknown"


def test_normalize_structure_summarizes_chorus():
    out = normalize_structure({
        "bpm": 120,
        "segments": [
            {"start": 0.0, "end": 10.0, "label": "intro"},
            {"start": 10.0, "end": 30.0, "label": "verse"},
            {"start": 30.0, "end": 50.0, "label": "chorus"},
            {"start": 50.0, "end": 70.0, "label": "bridge"},
            {"start": 70.0, "end": 100.0, "label": "chorus"},
        ],
    })
    assert out["duration_s"] == 100.0
    assert out["first_chorus_s"] == 30.0
    assert out["chorus_count"] == 2
    assert out["chorus_duration_ratio"] == 0.5
    assert out["bpm"] == 120.0


def test_normalize_structure_rejects_invalid_segment():
    with pytest.raises(ValueError, match="end must be greater"):
        normalize_structure({"segments": [{"start": 5, "end": 4, "label": "verse"}]})


def test_runner_checks_gpu_before_external_command(tmp_path):
    calls = []

    def guard():
        calls.append("guard")
        raise RuntimeError("GPU busy")

    def runner(*args, **kwargs):
        calls.append("runner")
        raise AssertionError("runner must not be called")

    with pytest.raises(RuntimeError, match="GPU busy"):
        run_music_structure(tmp_path / "x.wav", tmp_path / "out.json", gpu_guard=guard,
                            command_runner=runner, executable="all-in-one-infer")
    assert calls == ["guard"]


def test_runner_normalizes_external_json(tmp_path):
    audio = tmp_path / "song.wav"
    audio.write_bytes(b"fake")
    dest = tmp_path / "candidate.json"

    def runner(cmd, **kwargs):
        out_dir = tmp_path / "struct"
        assert cmd[-2:] == ["-o", str(out_dir)]
        out_dir.mkdir()
        (out_dir / "song.json").write_text(json.dumps({
            "bpm": 100,
            "segments": [{"start": 0, "end": 10, "label": "chorus"}],
        }), encoding="utf-8")
        class R:
            returncode = 0
            stdout = ""
            stderr = ""
        return R()

    out = run_music_structure(audio, dest, gpu_guard=lambda: None,
                              command_runner=runner, executable="all-in-one-infer",
                              temp_dir=tmp_path / "struct")
    assert out["first_chorus_s"] == 0.0
    assert json.loads(dest.read_text(encoding="utf-8"))["chorus_count"] == 1
