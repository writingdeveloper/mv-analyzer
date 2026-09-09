from mv_analyzer.lyrics import (asr_to_lines, char_ratio, clean_lyrics,
                                lyrics_features)


def test_char_ratio_korean():
    assert char_ratio("안녕하세요", "ko") == 1.0
    assert char_ratio("hello", "ko") == 0.0


def test_char_ratio_japanese():
    assert char_ratio("こんにちは", "ja") == 1.0
    assert char_ratio("バウムクーヘン", "ja") == 1.0  # 가타카나+장음
    assert char_ratio("終端の記憶", "ja") > 0.5      # 한자 포함
    assert char_ratio("hello!!", "ja") == 0.0


def test_clean_lyrics_filters_and_dedups():
    ocr = [
        {"t_s": 0, "text": "会いたくて\n@@noise@@"},
        {"t_s": 2, "text": "会いたくて"},          # 연속 중복 → 제거
        {"t_s": 4, "text": "君に届け"},
        {"t_s": 6, "text": "ab"},                  # 일어 비율 0 → 제거
    ]
    lines = clean_lyrics(ocr, lang="ja")
    assert [l["line"] for l in lines] == ["会いたくて", "君に届け"]
    assert lines[0]["t_s"] == 0


def test_clean_lyrics_korean_mode():
    ocr = [{"t_s": 10, "text": "만나고 싶어서\nAitakute"}]
    lines = clean_lyrics(ocr, lang="ko")
    assert [l["line"] for l in lines] == ["만나고 싶어서"]


def test_clean_lyrics_strips_lang_labels():
    ocr = [{"t_s": 0, "text": "일본어: 見捨てないで\nJapanese: 好きだよ"}]
    lines = clean_lyrics(ocr, lang="ja")
    assert [l["line"] for l in lines] == ["見捨てないで", "好きだよ"]


def test_asr_to_lines_keeps_native_and_drops_symbol_only():
    # 버그 수정: 영어 가사(sung English)는 K-pop/보컬로이드 모두에서 실가사이므로
    # 더 이상 환각으로 오분류해 버리지 않는다 — Latin 문자도 필터 통과 대상.
    # 순수 기호/무음 구간("...")만 계속 걸러진다.
    segs = [{"start": 12.3, "end": 15.0, "text": "会いたくて"},
            {"start": 20.0, "end": 22.0, "text": "..."},        # 언어문자 없음 → 제거
            {"start": 30.0, "end": 31.0, "text": "Thank you"},  # 영어 가사 → 유지
            {"start": 40.5, "end": 44.0, "text": "君に届け"}]
    lines = asr_to_lines(segs, lang="ja")
    assert [l["line"] for l in lines] == ["会いたくて", "Thank you", "君に届け"]
    assert lines[0]["t_s"] == 12


def test_asr_to_lines_keeps_english_line_under_korean_lang():
    # K-pop은 한글 가창 사이에 영어 가사 라인이 섞여 있는 경우가 흔하다 (진단 사례:
    # XG "GALA" 등 영어 위주 K-pop 곡). lang="ko"에서도 Latin 라인은 유지되어야 한다.
    segs = [{"start": 5.0, "end": 6.0, "text": "안녕하세요"},
            {"start": 10.0, "end": 12.0, "text": "I love you so much tonight"}]
    lines = asr_to_lines(segs, lang="ko")
    assert [l["line"] for l in lines] == ["안녕하세요", "I love you so much tonight"]


def test_asr_to_lines_collapses_consecutive_duplicates():
    # 반복구(non-consecutive chorus repeat)는 보존하되, 연속 중복(환각 방어)만 접는다.
    segs = [{"start": 1.0, "end": 2.0, "text": "会いたくて"},
            {"start": 2.0, "end": 3.0, "text": "会いたくて"},  # 연속 중복 → 제거
            {"start": 4.0, "end": 5.0, "text": "君に届け"},
            {"start": 6.0, "end": 7.0, "text": "会いたくて"}]  # 비연속 반복 → 유지(후렴)
    lines = asr_to_lines(segs, lang="ja")
    assert [l["line"] for l in lines] == ["会いたくて", "君に届け", "会いたくて"]


def test_asr_to_lines_drops_short_symbol_only_line():
    segs = [{"start": 1.0, "end": 2.0, "text": "!!"},
            {"start": 2.0, "end": 3.0, "text": "a"},   # MIN_LEN 미만
            {"start": 4.0, "end": 5.0, "text": "君に届け"}]
    lines = asr_to_lines(segs, lang="ja")
    assert [l["line"] for l in lines] == ["君に届け"]


def test_lyrics_features():
    lines = [{"t_s": 12, "line": "a"}, {"t_s": 20, "line": "b"}]
    f = lyrics_features(lines, duration_s=120.0)
    assert f == {"n_lyric_lines": 2, "first_lyric_at_s": 12,
                 "lyric_lines_per_min": 1.0}


def test_lyrics_features_empty():
    f = lyrics_features([], duration_s=120.0)
    assert f == {"n_lyric_lines": 0, "first_lyric_at_s": None,
                 "lyric_lines_per_min": 0.0}
