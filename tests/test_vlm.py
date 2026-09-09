from mv_analyzer.vlm import LYRICS_PROMPT, ask_text, parse_json


def test_parse_json_extracts_object():
    text = '앞설명 {"mood": "행복", "num_characters": 2} 뒷말'
    assert parse_json(text) == {"mood": "행복", "num_characters": 2}


def test_parse_json_multiline():
    text = '{\n "shot_type": "closeup",\n "style": "anime"\n}'
    assert parse_json(text)["shot_type"] == "closeup"


def test_parse_json_invalid_returns_raw():
    assert parse_json("JSON 없음") == {"raw": "JSON 없음"}
    assert parse_json("{깨진 json")["raw"] == "{깨진 json"


def test_lyrics_prompt_has_fixed_vocab():
    assert "사랑" in LYRICS_PROMPT and "이별" in LYRICS_PROMPT
    assert "긍정" in LYRICS_PROMPT and "부정" in LYRICS_PROMPT and "양가" in LYRICS_PROMPT
    assert "1인칭 독백" in LYRICS_PROMPT and "2인칭 대상" in LYRICS_PROMPT
    assert "topics" in LYRICS_PROMPT and "sentiment" in LYRICS_PROMPT
    assert "addressee" in LYRICS_PROMPT


def test_ask_text_is_importable():
    assert callable(ask_text)
