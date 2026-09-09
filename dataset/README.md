# MV 특징 데이터셋 — 2개 도메인 (2026-07)

## features_100mv.csv — 2개 도메인 확장 (N=100, 2026-07-21)

보컬로이드 50편 + K-pop 50편의 정량 특징 테이블. `domain` 컬럼에서 도메인 구분.
Canonical private research table: 94 columns. The generated public-release copy removes the raw `thumb_text_content` OCR field and therefore contains 93 columns.

### 표본 설계 요약
- **보컬로이드**: 조회수/구독자 비율 상위 극단 25편(top) + 하위 극단 25편(bottom) — 선택 편향 주의(하단 참조)
- **K-pop**: 조회수/구독자 비율 상위 극단 25편(top) + 하위 극단 25편(bottom) — 선택 편향 주의(하단 참조)
- 참고: 그룹은 극단치 표본만 포함; 중위권 표본은 별도 수집 예정(본 파일 미포함)

---

## features_50mv.csv — 보컬로이드 (N=50, 2026-07)

유튜브 보컬로이드 오리지널 MV 상·하위 극단 50편의 정량 특징 테이블.
Canonical private research table: 85 columns. The generated public-release copy removes `thumb_text_content` and contains 84 columns.

## 표본 설계

- 모집단: 2025-04~2026-04 원본 프로듀서 채널 공개 신곡 (171채널 열거 → 필터 후 540편)
- 그룹: `group` 컬럼 — 조회수/구독자수 비율 상위 극단 25편(top) / 하위 극단 25편(bottom)
- 필터: 구독자 1,000+, 60~600초, 세로형 제외, 비-MV 콘텐츠 제목 휴리스틱 제외, 채널당 최대 2편
- 알려진 제외: 구독자수 비공개 채널(22편), 혼합 콘텐츠 채널 1곳

## 측정 방법 (100% 로컬)

| 축 | 컬럼 프리픽스 | 도구 |
|---|---|---|
| 화면 | `scene_*` | PySceneDetect 0.7 (ContentDetector t=15) + OpenCV |
| 음향 | `audio_*` | librosa 0.11 + ffmpeg ebur128 |
| 장면 의미 | `tag_*` | Qwen2.5-VL 7B (temperature 0, 고정 어휘) |
| 가사 | `lyrics_*` | 하드자막 VLM OCR(≥8라인 시) 또는 demucs+faster-whisper ASR — `lyrics_source` 참조 |
| 패키징 | `thumb_*`, `title_*` | 썸네일 VLM + 제목 파싱 |
| 교차 동기화 | `sync_*`, `hook_*` | 씬×비트 파생 계산 |

**2026-07-21 ASR 필터 수정**: `lyrics_source='asr'`인 경우 ASR 신뢰도 필터 재기준선 적용(threshold=15로 상향). K-pop 가사 커버리지: 47/50(94%).

---

## 주요 컬럼 사전

### 신규 파생 컬럼 (features_100mv.csv)
- `lyrics_compression_ratio`: 가사 텍스트 압축률 (반복 감지)
- `lyrics_title_first_s`: 제목 첫 언급 시간(초)
- `lyrics_title_count`: 제목 반복 횟수
- `lyrics_first_chorus_s`: 첫 후렴 시작 시간(초)
- `sync_cut_on_line_ratio`: 라인 시작점 정렬 비율(컷×가사 동기화)
- `heat_slope_first_30s`: 처음 30초 에너지 기울기(히트맵)
- `heat_peak_at_ratio`: 에너지 피크 위치(영상 진행률, 히트맵)
- `heat_peak_value`: 에너지 피크 값(정규화, 히트맵)

### 기존 주요 컬럼
- `view_per_sub`: 수집 시점(`collected_at`) 조회수/구독자수 — 그룹 구분 기준
- `scene_cuts_per_minute`, `scene_median_shot_len_s`: 편집 리듬 (최대 판별력)
- `hook_cuts_first_15s`, `hook_energy_first_10s_ratio`: 도입부 훅
- `sync_beats_per_cut`, `sync_cut_on_beat_ratio`: 컷-비트 정렬
- `tag_mood_top`: 8범주 고정 어휘(행복·슬픔·긴장·평온·활기·어둠·신비·분노)
- `lyrics_topic_1/2`: 8범주(사랑·이별·자기긍정·어둠/절망·희망·일상·메타/음악·판타지)
- `lyrics_has_hardsub`: OCR 텍스트 프레임 비율 ≥ 0.1 여부

## 주의사항

- 조회수·구독자수는 2026-07-16 스냅샷 — 시점 의존
- VLM 태깅은 temperature 0으로 재현 가능하나 모델(qwen2.5vl:7b) 의존
- 상관 데이터임 — 인과 해석 금지. 분석 리포트: `../docs/reports/2026-07-16-p5-report.md`
- 원 데이터는 YouTube 공개 메타데이터와 파생 측정치만 포함 (영상 원본 미포함)

### 히트맵 선택 편향 (heat_* 컬럼)
`heat_*` 컬럼(열정도 기반 파생)은 완전 표본 미포함:
- **보컬로이드**: 상위 극단 25편 중 24편, 하위 극단 25편 중 4편(총 28/50)
- **K-pop**: 상위 극단 25편 중 25편, 하위 극단 25편 중 21편(총 46/50)

히트맵 분석은 이 부분표본에서만 유효.

## 재현

```
python collect.py discover|enumerate|sample   # 표본 수집
python batch.py                               # 50편 분석 (GPU, ~8h)
python p5_report.py                           # 통계 리포트
```

## 구조 QA

공개 CSV의 행/열 수, video_id 유일성, group/domain 균형은 다음 명령으로 검증한다.

```bash
mva dataset-qa
```

이 검사는 GitHub Actions의 Python 3.12/3.13 matrix에서도 실행된다.


## 공개 릴리스 데이터 권리

공개 source release는 `scripts/build_public_release.py`로 생성하며 원본 영상·음원·썸네일·가사/자막 원문·OCR 원문을 포함하지 않습니다. 프로젝트가 권리를 보유하는 선택·배열·주석·파생 측정치에는 `DATA_LICENSE.md`의 CC BY 4.0 조건을 적용하지만, YouTube 식별자·제목·채널명 등 제3자 메타데이터나 underlying media에 대한 권리를 부여하지 않습니다.

이 데이터는 extreme-group 관찰 표본이며 시장 전체 백분위나 성공 예측 데이터셋이 아닙니다.
