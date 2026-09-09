# 툴링 리서치: 로컬 ASR·보컬 분리·구조 분석·VLM/OCR (2026-07-21)

파이프라인 차기 사이클을 위한 웹 리서치 종합 (병렬 리서치 에이전트 3종). 배경: K-pop 가사 표본 결손의 원인이 ASR 언어 필터로 확정된 시점에서, "필터 수정으로 충분한가, 스택 교체가 필요한가"를 판단하기 위해 수행.

## 즉시 적용된 것 (이번 커밋)

- **ASR 라인 필터 수정**: 한글/일문 문자비율 필터가 영어 가사를 오폐기 → 라틴 문자 포함 비율로 완화 + 연속 중복 접기(환각 방어). 근거: 2026 커뮤니티 합의는 "언어 문자비율 필터는 잘못된 환각 방어 — confidence 기반으로 대체" ([whisper Discussion #2378](https://github.com/openai/whisper/discussions/2378)). OCR 경로 필터는 스태프 크레딧 차단용으로 유지.
- K-pop 유효 표본 28→47 복구. 게이트 재판정: 여전히 FAIL (압축률 δ는 표본 확대 후 +0.32→+0.14로 축소 — 초기 신호는 소표본 잡음이었을 가능성).

## 차기 사이클 권장 (우선순위순)

### 1. ASR 재실행 레시피 (whisper 유지, 파라미터만 교정) — 야간 배치 1회

현행 `asr_worker.py`는 `language=<도메인 고정>` + 기본 파라미터. 2026 표준 레시피:

```python
model.transcribe(vocals,
    language=None,                    # 자동 감지 — ko 강제는 코드스위칭에 해로움
    task="transcribe",                # 번역 방지 (Discussion #1523)
    vad_filter=True,
    condition_on_previous_text=False, # 환각 전파(drift) 차단 — 음악에서 특히 중요
    hallucination_silence_threshold=2.0)
# 저장 스키마에 avg_logprob·no_speech_prob·compression_ratio 추가
# → 사후 환각 필터를 confidence 기반으로 전환 가능
```

주의: 파라미터 변경은 측정 일관성을 위해 **ASR 소스 전 영상(97편 중 ASR분) 일괄 재실행**과 함께만 적용할 것 — 일부만 재실행하면 교정 전/후 측정이 혼재된다. 잔존 실패 3편(비가사 내레이션·환각 반복·무검출)도 이 레시피로 재시도 가치 있음.

### 2. Qwen3-ASR-1.7B — 유력 교체 후보, A/B 게이트 후 결정

- 가창·BGM을 명시적 학습 대상으로 포함한 유일한 로컬 후보 (M4Singer WER 5.98%, BGM 풀송 en 14.6%; whisper 계열은 음악에서 열화 명시) — [기술 리포트](https://arxiv.org/html/2601.21337v1), [모델 카드](https://huggingface.co/Qwen/Qwen3-ASR-1.7B)
- 한국어·일본어 정식 지원(30개 언어), 자동 LID 97.9%로 코드스위칭 구조적 완화, Apache-2.0, FP16 ~5GB(16GB 여유), `pip install qwen-asr`, flash_attn 없이 Windows 구동 가능(예제 기준, 실설치 미검증)
- 타임스탬프는 별도 Qwen3-ForcedAligner-0.6B
- **전환 조건**: 소표본 A/B(현행 whisper 대비 WER·복구 세그먼트 수) 통과 + 전 영상 일괄 재전사(모델 혼재 금지)

### 3. 보컬 분리: audio-separator (BS-RoFormer) — A/B 필요

- demucs는 저활동 상태(원저자 개인 포크로 이관), RoFormer 계열이 SDR +3~4dB 우위 ([MVSEP 리더보드](https://mvsep.com/en/algorithms))
- `pip install "audio-separator[gpu]"` — UVR 모델 zoo 래핑, 활발 유지보수, VRAM ~5-6GB
- 단, 분리 품질 향상이 가사 WER 개선을 보장하지 않음 — 분리 아티팩트가 환각을 유발한 반례 있음 ([arXiv 2506.15514](https://arxiv.org/abs/2506.15514)). K-pop 샘플 일부로 WER A/B 후 결정.

### 4. 후렴/구조 검출: all-in-one-infer — 로드맵 항목 해결책

- 원본 `allin1`은 Windows 부적합(NATTEN 미지원·madmom 빌드 깨짐). `pip install all-in-one-infer`(openmirlab)가 Windows 명시 지원 + 컴파일 불필요, chorus/verse 라벨+타임스탬프 + beat/downbeat/bpm 동시 출력 → 로드맵의 "후렴 위치" feature와 비트 트래킹을 의존성 하나로 해결
- 소규모 프로젝트(~20 stars)이므로 자체 샘플 검증 필수. 대안: SongFormer(2025-10 SOTA, Linux만 검증 — 필요 시 4080 서버에서)

### 5. VLM/OCR — 교체 보류 (재현성)

- **씬 태깅 VLM**: Qwen3-VL:8b가 Ollama에 존재(OCRBench 864→905, VRAM 동급)하나, 현행 qwen2.5vl:7b 기준 블라인드 라벨러 검증(n=52)을 무효화하므로 **다음 사이클에 재검증과 함께** 전환 검토
- **가사 OCR**: PaddleOCR 3.x(PP-OCRv5)가 VLM 대비 속도 ~50배·동급 정확도로 차기 최우선 교체 후보 ([비교](https://modal.com/blog/8-top-open-source-ocr-models-compared)). EasyOCR은 유지보수 중단 확인 — 채택 금지
- **PySceneDetect**: 이미 최신(0.7) — 조치 불필요

## 판단 원칙 (이 리서치에서 재확인)

측정 도구 교체는 (1) 측정 일관성 — 코퍼스 전체 일괄 재처리와 함께만, (2) 신뢰도 재검증 — 블라인드 대조 재실시, (3) A/B 게이트 — 소표본 정량 비교 통과 후. 이번에 필터만 고치고 모델을 안 바꾼 것도 이 원칙 때문.
