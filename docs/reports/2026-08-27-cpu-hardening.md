# CPU-only hardening 및 다음 단계 — 2026-08-27

## 범위

이 작업은 다른 세션이 RTX 4080을 점유 중인 상태에서 수행했다. 따라서 Ollama
추론, demucs, faster-whisper CUDA, 모델 A/B 등 GPU 작업은 실행하지 않았다.
기존 `data/` 분석 결과는 읽기/QA 대상으로만 사용했고 재처리하지 않았다.

## 완료한 방어선

### 1. 측정 설정 단일 소스

`mv_analyzer/config.py`에 연구 결과를 바꾸는 핵심 설정을 모았다.

- scene threshold: 15.0
- VLM baseline: `qwen2.5vl:7b`
- ASR baseline: `large-v3`
- VAD: enabled
- `condition_on_previous_text`: enabled (현재 동작을 명시했을 뿐 변경하지 않음)

`mva config`로 현재 기준선을 즉시 확인할 수 있다. `config.py`는 provenance
fingerprint에도 포함되므로 향후 설정 변경이 manifest-backed artifact의 stale 판정에
반영된다.

### 2. DuckDB freshness

DuckDB는 JSON source of truth를 대체하지 않는 로컬 검색 캐시다.
`mv_analyzer/index_freshness.py`가 다음 입력을 fingerprint한다.

- `features.json`
- `lyrics_lines.json`
- `scenes.json`
- `scene_tags.json`
- index/derived-feature 코드

`mva index --check`로 freshness를 확인할 수 있고, `mva search`는 stale/missing
인덱스를 자동 재빌드한다. 실제 128편 코퍼스에서 legacy DB를 감지한 뒤
128 features / 5,039 lyric lines / 8,314 scenes로 재빌드하고 fresh 전환되는 것을
검증했다.

DB에는 로컬 가사 라인이 포함될 수 있으므로 `.duckdb`와 `.meta.json` sidecar는
gitignore하며 배포 데이터셋으로 취급하지 않는다.

### 3. 정식 통계 feature 정책

`mv_analyzer/feature_policy.py`가 기존 P5 가설검정 allowlist의 단일 소스다.

- `ext_*`
- `motion_*`

같은 실험 지표는 탐색/검색/유사도에는 사용할 수 있지만 별도 사전등록·신뢰성
게이트 전에는 기존 P5 가설검정에 자동 유입되지 않는다.

`mva stats-qa --table work/features_table.jsonl` 실제 결과:

- rows: 50
- top/bottom: 25 / 25
- formal missing: 0
- constant formal numeric: 0
- low-coverage feature/group pair: 0
- errors: 0

P5 리포트도 임시 출력 경로에서 재생성해 기존 10개 q<0.05 결과가 유지됨을 확인했다.

### 4. 공개 dataset invariant QA

`mva dataset-qa`가 공개 CSV의 구조와 표본 불변식을 검증한다.

- `features_50mv.csv`: 50 × 85, video_id 50 unique, top/bottom 25/25
- `features_100mv.csv`: 100 × 94, video_id 100 unique,
  top/bottom 50/50, Vocaloid/K-pop 50/50

현재 두 파일 모두 오류 0이다.

### 5. CI 확대

GitHub Actions는 이제 `master`뿐 아니라 모든 branch push와 PR에서 실행한다.
Python 3.12/3.13 matrix에서 다음을 검사한다.

1. Ruff F-only 정적 correctness 검사
2. tracked P5 input QA
3. 공개 dataset QA
4. fast CPU pytest suite

전체 Ruff 규칙은 현재 timezone/예외정책/스타일 등 기존 의도와 충돌할 수 있는
항목이 섞여 있으므로 일괄 적용하지 않았다. F-only는 undefined/unused import 및
명백한 f-string 오류처럼 동작 변경 위험이 낮은 correctness 규칙만 사용한다.

### 6. 설치형 CLI 의존성

CLI/server 도구이므로 OpenCV는 `opencv-python-headless`로 통일했다. 또한
`mva report` 및 `feature-structure`가 실제 사용하는 `matplotlib`을 기본 의존성에
추가했다.

### 7. 공유 GPU 보호

GPU busy guard의 VRAM 기준을 4GB에서 2GB로 낮췄다. 작은 VLM이 3GB 안팎으로
적재된 경우에도 다른 세션을 보호하기 위함이다. GPU usage 35% 기준은 유지한다.
이번 작업에서는 guard 코드만 수정했으며 GPU 상태 조회/추론은 실행하지 않았다.

## 다음 권장 작업

### P0 — GPU가 비었을 때 측정기 A/B

기존 128편 결과를 바로 갈아엎지 말고 소규모 고정 샘플에서 먼저 비교한다.

1. **ASR 설정 A/B**
   - baseline: VAD=true, `condition_on_previous_text=true`
   - candidate: VAD=true, `condition_on_previous_text=false`
   - 한국어/영어 및 일본어/영어 code-switch 구간을 반드시 포함
   - lyric recovery, hallucination, 반복 오류, 시간축 안정성 비교
2. **Qwen3-VL 후보 A/B**
   - 기존 52장 blind-label sample 사용
   - 후보 출력만 저장한 뒤 `mva evaluate-vlm candidate.json`으로 CPU 채점
   - baseline보다 정확도/κ가 개선된 field만 채택 근거로 인정
3. **Qwen3-ASR 후보 A/B**
   - 동일 audio subset, 동일 후처리 기준으로 Whisper baseline과 비교

모델/설정을 교체하기로 결정한 경우에만 pipeline version을 올리고 동일 코퍼스를
일관되게 재측정한다.

### P1 — 정식 음악 구조/후렴 검증

현재 `ext_lyrics_first_chorus_*`는 반복 가사 기반 proxy다. all-in-one 계열 등
음악구조 모델을 후보로 검증해 intro/verse/pre-chorus/chorus/bridge/outro의
시간축을 얻고, 시각 편집/색/에너지와 결합하는 것이 다음 연구 feature 우선순위다.

### P1 — motion 정식 채택 여부

현재 optical-flow motion은 opt-in 실험 측정기다. 합성 QA는 통과했지만 정식
코퍼스 feature로 사용하려면:

1. 사람이 고른 static / camera-motion / subject-motion 검증 샘플
2. sample_fps 및 static threshold 민감도 분석
3. 동일 128편 일괄 CPU 측정
4. 사전등록된 통계 분석

순서가 필요하다.

### P1 — 표본 증설

기존 로드맵의 group당 40+ 확대가 남아 있다. 측정기 버전을 먼저 고정한 뒤
표본을 늘리는 것이 맞다. 모델/측정기를 바꾸면서 표본까지 동시에 늘리면
측정 버전과 표본 효과가 섞인다.

### P2 — 검색 계층 스케일링

현재 128편에서는 `talk.py`가 JSON source를 직접 읽는 구조가 충분히 빠르다.
1,000편 이상이 되면 catalog/search/compare의 일부를 DuckDB query layer와
공유하되, keyframe path와 원본 timeline evidence는 JSON source에서 유지하는
하이브리드 구조를 검토한다.

### P2 — 전체 Ruff/typing

F-only 이후의 Ruff 항목과 정적 typing은 별도 리팩터링 브랜치에서 처리한다.
timezone 처리나 broad-exception 정책은 기존 수집/복구 동작을 바꿀 수 있으므로
연구 기능 변경과 섞지 않는다.

### 공개 전 결정 사항

- 라이선스 결정
- README/문서의 공개 범위 최종 점검
- 재현 가능한 최소 예제 데이터/명령 정의
- branch PR 검토 후 `master` merge

## 현재 결론

CPU 영역에서 즉시 필요한 구조·QA 개선은 대부분 완료됐다. 다음 큰 정확도 향상은
코드 정리보다 **GPU가 비었을 때의 ASR/VLM 측정기 A/B와 정식 음악 구조 검증**에서
나올 가능성이 가장 높다.
