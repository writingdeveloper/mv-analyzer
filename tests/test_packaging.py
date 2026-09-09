import subprocess


from mv_analyzer.packaging import analyze_thumbnail, title_features


def test_title_features_basic():
    f = title_features("バウムクーヘン・エンドロール / アマラ feat. 初音ミク")
    assert f["title_len"] == len("バウムクーヘン・エンドロール / アマラ feat. 初音ミク")
    assert f["title_has_emoji"] is False
    assert f["title_has_mv_mark"] is False


def test_title_features_marks():
    f = title_features("【MV】天使の翼🕊 / P名 feat. 可不!!")
    assert f["title_has_emoji"] is True
    assert f["title_bracket_segments"] == 1
    assert f["title_has_mv_mark"] is True
    assert f["title_exclaim_count"] == 2


def test_analyze_thumbnail_color_only(tmp_path, monkeypatch):
    """VLM은 mock, 색 통계만 실검증 — 회색 단색 이미지."""
    img = str(tmp_path / "t.jpg")
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                    "color=c=gray:s=64x36:d=1", "-frames:v", "1", img],
                   check=True, capture_output=True)
    monkeypatch.setattr("mv_analyzer.packaging.ask",
                        lambda path, prompt: '{"style": "anime", "mood": "차분"}')
    out = analyze_thumbnail(img)
    assert out["style"] == "anime"
    assert 0.4 < out["thumb_brightness"] < 0.6   # gray ≈ 0.5
    assert out["thumb_saturation"] < 0.05
