import json

import pytest

from mv_analyzer import prompt_sanitize as ps


def test_strip_field_removes_only_the_artifact_clause():
    out, removed = ps.strip_field(
        "thick black outlines, flat cel colors, subtitle band present at bottom; mint palette.")
    assert out == "thick black outlines, flat cel colors, mint palette."
    assert [r[0] for r in removed] == ["subtitle"]


def test_strip_field_drops_whole_pillarbox_sentence():
    out, removed = ps.strip_field(
        "Wide, logo dead-center; flat depth. "
        "4:3 picture pillarboxed inside the 16:9 frame with black bars left and right.")
    assert out == "Wide, logo dead-center; flat depth."
    assert {r[0] for r in removed} == {"pillarbox"}


def test_strip_field_keeps_untouched_text_identical():
    src = "Static, eye level; shallow depth."
    assert ps.strip_field(src) == (src, [])


def test_dead_field_keeps_original_and_flags_rewrite():
    shot = {"shot_number": 3, "subject": "Korean subtitle band.", "camera": "Static"}
    out, audit = ps.sanitize_shot(shot)
    assert out["subject"] == shot["subject"], "필드가 통째로 산물이면 지우지 않고 표시만"
    assert audit["needs_rewrite"] == ["subject"]
    assert all(r["applied"] is False for r in audit["removed"])


def test_abstract_typography_converts_content_to_shape():
    assert ps.abstract_typography("giant white kanji characters flank her head.")[0] == \
        "giant white kanji-like glyph shapes flank her head."
    # 글자가 아닌 '일본어' 언급은 건드리지 않는다
    assert ps.abstract_typography("vertical Japanese speech bubbles on the right.")[1] == 0


def test_sanitize_reports_rules_and_text_dependence():
    payload = {"shots": [
        {"shot_number": 1, "visual_style": "flat cel colors, subtitle band at bottom.",
         "spatial_framing": "Wide, logo dead-center. 4:3 picture pillarboxed with black bars."},
        {"shot_number": 2, "subject": "girl with giant white kanji characters beside her.",
         "camera": "Push In"},
    ]}
    clean, rep = ps.sanitize(payload, typography="abstract")
    assert rep["n_shots"] == 2 and rep["n_shots_changed"] == 1
    assert rep["removed_by_rule"] == {"subtitle": 1, "pillarbox": 1}
    assert rep["text_dependent"] == [2] and rep["n_text_clauses"] == 1
    assert rep["n_typography_abstracted"] == 1
    assert "kanji-like glyph shapes" in clean["shots"][1]["subject"]
    assert clean["_sanitize"]["typography"] == "abstract"


def test_sanitize_file_keeps_loader_shape(tmp_path):
    src = tmp_path / "x.vision.json"
    src.write_text(json.dumps({"shots": [
        {"shot_number": 1, "subject": "a girl", "camera": "Static",
         "visual_style": "flat cel, subtitle band at bottom."}]}), encoding="utf-8")
    out, rep = ps.sanitize_file(str(src))
    assert out.endswith("x.gen.json")
    payload = json.loads(open(out, encoding="utf-8").read())
    # reference-lab load_vision_semantics는 dict + shots 배열만 요구한다
    assert isinstance(payload, dict) and isinstance(payload["shots"], list)
    assert payload["shots"][0]["shot_number"] == 1
    assert rep["removed_by_rule"] == {"subtitle": 1}


def test_sanitize_file_rejects_bad_shape(tmp_path):
    bad = tmp_path / "b.json"
    bad.write_text(json.dumps({"nope": 1}), encoding="utf-8")
    with pytest.raises(ValueError):
        ps.sanitize_file(str(bad))


def test_video_id_masking_leaves_long_options_alone():
    """11자 옵션(--keyframes)이 video_id 마스킹에 걸려 삼켜지던 회귀."""
    import talk as talk_cli

    from mv_analyzer.cli import VIDEO_ID_ARG as CLI_RX
    for rx in (talk_cli.VIDEO_ID_ARG, CLI_RX):
        assert rx.fullmatch("-FX7yWRFw9Y"), "하이픈으로 시작하는 video_id는 계속 가려야 한다"
        assert not rx.fullmatch("--keyframes")
        assert not rx.fullmatch("--typography")
    assert talk_cli._mask_ids(["export", "-FX7yWRFw9Y", "--keyframes", "d"])[2] == "--keyframes"
