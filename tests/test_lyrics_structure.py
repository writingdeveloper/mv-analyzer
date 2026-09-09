from mv_analyzer.lyrics_structure import (
    compression_ratio, cut_on_line_ratio, first_chorus_s,
    song_title_phrase, structure_features, title_in_lyrics,
)


def L(*pairs):
    return [{"t_s": t, "line": s} for t, s in pairs]


def test_compression_repetitive_lower_than_varied():
    rep = L(*[(i * 4, "사랑해 사랑해 오늘도 사랑해") for i in range(20)])
    var = L(*[(i * 4, f"서로 다른 문장 {i}번째 이야기 조각 {i*7}") for i in range(20)])
    assert compression_ratio(rep) < compression_ratio(var)


def test_song_title_phrase_strips_markers_and_artist():
    p = song_title_phrase("바움쿠헨 엔드롤 / 아마라 【Official MV】", "아마라")
    assert p == "바움쿠헨엔드롤"


def test_title_in_lyrics_first_hit_and_count():
    lines = L((0, "인트로"), (30, "가련한 바움쿠헨 엔드롤"), (60, "바움쿠헨 엔드롤!"))
    first, count = title_in_lyrics("바움쿠헨엔드롤", lines)
    assert first == 30 and count == 2


def test_first_chorus_is_first_reoccurrence():
    lines = L((0, "짧다"), (10, "후렴구 전체 가사 문장"), (20, "다른 가사"),
              (45, "후렴구 전체 가사 문장"))
    assert first_chorus_s(lines) == 45


def test_first_chorus_none_without_repeat():
    assert first_chorus_s(L((0, "가나다라마"), (10, "바사아자차"))) is None


def test_cut_on_line_ratio():
    # 컷 4개 중 라인 시작(10,20) ±0.5s 안에 2개
    assert cut_on_line_ratio([9.8, 20.3, 33.0, 50.0], [10, 20]) == 0.5


def test_structure_features_requires_min_lines():
    assert structure_features(L((0, "한 줄")), [1.0], "제목", "채널") is None


def test_song_title_phrase_no_separator_strips_channel_substring():
    # 구분자 없이 "채널명 + 곡명"이 붙어 있는 실제 케이스 — 폴백이 채널명을
    # 그대로 복귀시키지 않고, 정규화된 채널명 부분 문자열을 제거해야 한다.
    p = song_title_phrase("IVE 해야 (HEYA)", "IVE")
    assert p == "해야"


def test_song_title_phrase_no_separator_empty_after_channel_strip():
    # 채널명 제거 후 2자 미만이면 "" 반환
    p = song_title_phrase("IVE IVE", "IVE")
    assert p == ""
