"""파이프라인 측정 설정의 단일 소스.

연구 결과에 영향을 주는 값은 이 파일에서 관리한다. 값을 바꾸면 provenance
fingerprint가 바뀌어 manifest-backed 산출물은 --refresh-stale 대상이 된다.
"""

SCENE_THRESHOLD = 15.0
VLM_MODEL = "qwen2.5vl:7b"
WHISPER_MODEL = "large-v3"

# 현재 검증된 ASR 기준선. 후보 설정은 GPU A/B 게이트 전에는 여기서 바꾸지 않는다.
ASR_VAD_FILTER = True
ASR_CONDITION_ON_PREVIOUS_TEXT = True


def as_dict():
    return {
        "scene_threshold": SCENE_THRESHOLD,
        "vlm_model": VLM_MODEL,
        "whisper_model": WHISPER_MODEL,
        "asr_vad_filter": ASR_VAD_FILTER,
        "asr_condition_on_previous_text": ASR_CONDITION_ON_PREVIOUS_TEXT,
    }
