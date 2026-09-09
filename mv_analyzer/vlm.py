"""Ollama VLM 클라이언트: 이미지 질의, JSON 파싱, 프롬프트 상수."""
import base64
import json
import re
import time
import urllib.request

from .config import VLM_MODEL

DEFAULT_MODEL = VLM_MODEL
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

SCENE_PROMPT = """이 이미지는 뮤직비디오의 한 장면이다. 다음 JSON만 출력하라(설명 금지):
{"setting": "장소/배경 한 구절", "num_characters": 숫자, "shot_type": "closeup|medium|wide",
"style": "anime|live_action|3dcg|motion_graphics|mixed", "mood": "행복|슬픔|긴장|평온|활기|어둠|신비|분노 중 하나",
"has_lyrics_text": true/false, "visual_elements": ["눈에 띄는 요소 최대 3개"]}"""

SUB_PROMPT = """이 이미지는 영상 하단부 크롭이다. 화면에 보이는 자막/가사 텍스트를 그대로 출력하라.
한국어와 일본어가 함께 있으면 둘 다 출력. 텍스트가 없으면 NONE만 출력. 다른 설명 금지."""

THUMB_PROMPT = """이 이미지는 유튜브 뮤직비디오의 썸네일이다. 다음 JSON만 출력하라(설명 금지):
{"style": "anime|live_action|3dcg|motion_graphics|mixed", "num_characters": 숫자,
"has_text": true/false, "text_content": "보이는 텍스트 그대로(없으면 빈 문자열)",
"mood": "행복|슬픔|긴장|평온|활기|어둠|신비|분노 중 하나", "composition": "구도 한 구절(예: 인물 클로즈업, 풍경 와이드)"}"""

LYRICS_TOPICS = ["사랑", "이별", "자기긍정", "어둠/절망", "희망",
                 "일상", "메타/음악", "판타지"]
LYRICS_SENTIMENTS = ["긍정", "부정", "양가", "중립"]
LYRICS_ADDRESSEES = ["1인칭 독백", "2인칭 대상", "3인칭 관찰"]

# 주의: 어휘 목록을 JSON 틀 안에 "값1|값2" 형태로 넣으면 모델이 플레이스홀더를
# 그대로 반향한다(실측). 목록은 틀 밖 규칙으로 제시할 것.
LYRICS_PROMPT = f"""다음은 뮤직비디오의 가사다. 아래 규칙에 따라 JSON만 출력하라(설명 금지):
- topics: 다음 목록에서 가장 맞는 것을 1~2개 고른 배열 — {", ".join(LYRICS_TOPICS)}
- sentiment: {", ".join(LYRICS_SENTIMENTS)} 중 하나
- addressee: {", ".join(LYRICS_ADDRESSEES)} 중 하나
출력 형식 예시: {{"topics": ["희망"], "sentiment": "긍정", "addressee": "1인칭 독백"}}

가사:
"""


def _generate(payload):
    """Ollama /api/generate 공통 요청(재시도 3회, 5초 backoff)."""
    body = json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())["response"].strip()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(5)


def ask(image_path, prompt, model=DEFAULT_MODEL):
    """이미지 1장 + 프롬프트를 Ollama에 보내고 응답 텍스트를 반환."""
    with open(image_path, "rb") as f:
        img64 = base64.b64encode(f.read()).decode()
    return _generate({
        "model": model, "prompt": prompt, "images": [img64],
        "stream": False, "options": {"temperature": 0, "num_predict": 300},
    })


def ask_text(prompt, model=DEFAULT_MODEL):
    """텍스트 전용 Ollama 질의 (이미지 없음). ask()와 동일한 재시도 정책."""
    return _generate({
        "model": model, "prompt": prompt,
        "stream": False, "options": {"temperature": 0, "num_predict": 300},
    })


def unload(model=DEFAULT_MODEL):
    """Ollama 적재 모델 즉시 언로드(VRAM 반환). 서버 미기동 등 실패는 무시.

    ASR(demucs/whisper) 직전에 호출 — 이전 영상의 VLM 모델이 keep_alive로
    잔류 적재된 채 ASR이 겹치면 VRAM 충돌로 Ollama가 죽을 수 있다(배치 실측).
    """
    body = json.dumps({"model": model, "prompt": "", "stream": False,
                       "keep_alive": 0}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30):
            pass
    except Exception:
        pass


def parse_json(text):
    """응답 텍스트에서 첫 JSON 오브젝트를 추출. 실패 시 {"raw": text}."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {"raw": text}
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return {"raw": text}
