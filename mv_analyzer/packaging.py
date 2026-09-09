"""패키징 축: 제목 텍스트 특징 + 썸네일 VLM 태깅·색 통계."""
import re

import cv2

from mv_analyzer.vlm import THUMB_PROMPT, ask, parse_json

EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "\U00002B00-\U00002BFF\U0000FE0F]")
MV_MARK = re.compile(r"\bMV\b|Music Video|ミュージックビデオ|뮤직비디오", re.I)


def title_features(title):
    return {
        "title_len": len(title),
        "title_has_emoji": bool(EMOJI.search(title)),
        "title_bracket_segments": len(re.findall(r"【[^】]*】|\[[^\]]*\]", title)),
        "title_has_mv_mark": bool(MV_MARK.search(title)),
        "title_exclaim_count": title.count("!") + title.count("！"),
    }


def analyze_thumbnail(image_path):
    tag = parse_json(ask(image_path, THUMB_PROMPT))
    img = cv2.imread(image_path)
    if img is None:
        raise RuntimeError(f"썸네일 이미지 읽기 실패: {image_path}")
    hsv = cv2.cvtColor(cv2.resize(img, (320, 180)), cv2.COLOR_BGR2HSV)
    _, s, v = cv2.split(hsv)
    tag["thumb_brightness"] = round(float(v.mean()) / 255, 3)
    tag["thumb_saturation"] = round(float(s.mean()) / 255, 3)
    return tag
