# mv-analyzer

[English](README.md) | **한국어**

**MV Analyzer는 뮤직비디오를 숫자로 끝내지 않습니다. 영상을 측정하고 비교한 뒤 “그래서 왜 이런 느낌이고, 나는 왜 이 영상을 좋아할 수 있는가?”를 근거와 함께 설명합니다.** 화면·편집·음향·가사·동기화·도입부·패키징 분석은 **100% 로컬**에서 수행하고, 숫자는 자연어 설명을 검증하는 evidence layer로 남깁니다.

> **상태**: 연구 사이클 1 완료 (보컬로이드, N=50) + K-pop 재현 (N=50). **논문 초안 완료** — 영어 IMRaD 본문 + 한국어 리포트: [`docs/paper/paper.md`](docs/paper/paper.md) · [`docs/paper/paper.ko.md`](docs/paper/paper.ko.md). raw provenance를 보존하는 연구 원본 저장소는 **비공개**로 유지하며, 공개 `writingdeveloper/mv-analyzer` 저장소는 `scripts/build_public_release.py`가 생성한 감사 가능한 **clean-history** source tree만 배포한다. [`docs/open-source-readiness.md`](docs/open-source-readiness.md)와 [`docs/open-source-release.md`](docs/open-source-release.md) 참조.


## Reason Engine — 차트보다 먼저 “그래서 왜?”

Analyze report v2는 이제 deterministic **Reason Engine**의 근거 계층이다. Claim Engine이 자연어를 만들기 **전에** 어떤 주장이 지지되는지, 반박되는지, 아직 근거가 부족한지를 결정한다. LLM이 없어도 설명이 가능하며, 구조화된 근거에 없는 이유를 LLM이 임의로 추가하는 구조가 아니다.

질문은 세 가지로 분리한다.

- **이 MV의 특징이 뭔데?** — reference corpus 대비 차이.
- **왜 이런 느낌이 나는 건데?** — 구도·페이스·오디오 밀도·도입부 등 여러 측정축의 조합.
- **내가 왜 좋아할 수 있는 건데?** — 명시적으로 지정한 로컬 favorite 목록과 비교. favorite에서 편차가 큰 축은 취향 이유로 만들지 않고 **현재 지지되지 않음**이라고 표시한다.

이미 분석한 결과는 GPU·네트워크 없이:

```bash
mva reason-export data/VIDEO_ID --out reason.json --benchmark-domain vocaloid
```

개인 favorite 목록 연결:

```bash
mva reason-export data/VIDEO_ID --out reason.json --favorites work/favorites_queue.txt --data data
```

새 URL은 기존 로컬 분석기를 그대로 거친 뒤 Reason Engine으로:

```bash
mva explain "https://www.youtube.com/watch?v=..." --lang ko --benchmark-domain vocaloid --out reason.json
```

공개 Analyze 화면은 Analyze report JSON과 portable Reason JSON을 모두 받을 수 있다. report를 열면 같은 버전의 reference/feel claim을 브라우저에서 재구성하고, **그래서 왜?**를 PCA와 원시 feature보다 먼저 보여준다.

## Web Research Explorer — 주력 인터페이스

이 프로젝트의 **주력 배포 화면은 Web UI**다. 분석·QA·재현은 Python/`mva`가 담당하고, 브라우저는 공개 안전성 검사를 통과한 정적 JSON snapshot만 읽는다.

- 배포: **https://mv-analyzer.writingdeveloper.blog/**
- 영어 포트폴리오 링크: **https://mv-analyzer.writingdeveloper.blog/?lang=en**
- 언어: 브라우저 언어 자동 감지 + 전역 **KO / EN** 전환 + 선택 저장 + `?lang=en|ko` 공유 링크. 한 개의 동일한 연구 snapshot을 두 언어 UI가 사용한다.
- 주요 화면: Overview · Discover · MV Space · Compare · **Analyze** · Samples · Methodology
- MV Space 3D: Three.js 기반 **Data Constellation** — PCA 좌표를 왜곡하지 않고 glow, 근접 이웃 연결, focus camera, PC1/2/3 설명분산을 시각화
- 정적 배포이므로 Ollama/GPU/로컬 파일시스템/사설 네트워크는 Web에 노출하지 않는다.

로컬 실행:

```bash
pip install -e .
mva web-export --out web/public/data
cd web
npm ci
npm run dev
```

### Analyze My MV — 로컬 분석 리포트 사용

무거운 분석은 사용자 PC에서 그대로 실행한다. 로컬 CLI가 공개 안전성이 보장된 JSON 리포트를 만든 뒤, 배포된 **Analyze** 화면에서 그 파일을 직접 연다. 공개 Web 앱은 리포트를 서버로 업로드하지 않고 현재 브라우저 탭의 메모리에서만 읽는다.

```bash
pip install -e .
mva analyze "https://www.youtube.com/watch?v=..." --web-report my-mv.json
```

뷰어: **https://mv-analyzer.writingdeveloper.blog/#/analyze** · 영어: **https://mv-analyzer.writingdeveloper.blog/?lang=en#/analyze**

비교 기준은 **Extreme Reference Corpus v2026.07**이라는 극단 그룹 연구 표본이다. 따라서 percentile은 **reference-corpus percentile**이며 시장 전체 백분위나 성공 확률이 아니다. 휴대용 report에는 원본 미디어, 가사/OCR 원문, 로컬 경로, 쿠키/헤더, 서명된 미디어 URL을 넣지 않는다.

유지보수자 production 배포는 clean worktree에서 아래 helper를 사용한다. 현재 HEAD SHA가 public manifest에 자동 기록된다.

```bash
python deploy_web.py --prod
```

배포 후 브라우저 QA는 같은 Playwright 회귀 suite를 production에 직접 실행한다. 이 경우 로컬 preview server는 시작하지 않는다.

```bash
cd web
PLAYWRIGHT_BASE_URL=https://mv-analyzer.writingdeveloper.blog npm run test:e2e
```

PowerShell:

```powershell
cd web
$env:PLAYWRIGHT_BASE_URL = "https://mv-analyzer.writingdeveloper.blog"
npm run test:e2e
```

## 기존 분석 결과 활용 (GPU·네트워크 없이)

```bash
mva report-export data/VIDEO_ID/features.json --out my-mv.json --benchmark-domain all
```

[사용 흐름·v2 리포트 전환·개인정보·해석 한계](docs/analyze-my-mv.md).
Analyze의 샘플 결과는 설치 없이 확인할 수 있고, 공개 오픈소스 CLI는 로컬에서 Analyze/Reason 파일을 생성할 수 있으며,
이미 분석한 결과를 내보낼 때 새 GPU 분석은 필요하지 않습니다. v1 파일은 최신 CLI로 다시 내보내세요.


## 오픈소스 릴리스 방식

MV Analyzer 소스 코드는 **Apache License 2.0**으로 공개한다. 데이터와 제3자/모델 라이선스는 코드 라이선스와 분리하여 [`DATA_LICENSE.md`](DATA_LICENSE.md), [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md), [`NOTICE`](NOTICE)에 기록한다.

private provenance repo는 연구 원본을 보존하고, 공개 `writingdeveloper/mv-analyzer`에는 **clean-history sanitized tree**만 배포한다. 따라서 운영 로그, raw population snapshot, 썸네일 OCR 원문, 개인 경로, pilot 산출물, base64 legacy report가 공개 저장소에 포함되지 않는다.

```bash
python scripts/build_public_release.py --out dist/public-release
python scripts/audit_public_release.py dist/public-release
```

## 연구 질문

> 2025-04~2026-04 원본 프로듀서 채널 공개 보컬로이드 MV 중, 조회수/구독자수 비율 상위 극단 25편과 하위 극단 25편은 음향·가사·화면·패키징에서 어떻게 다른가?

## 핵심 발견 (사이클 1)

전체 리포트: [`docs/reports/2026-07-16-p5-report.md`](docs/reports/2026-07-16-p5-report.md) · 인터랙티브 대시보드: `docs/reports/dashboard.html` · 제작 체크리스트: [`docs/reports/mv-production-checklist.md`](docs/reports/mv-production-checklist.md)

| 신호 | 상위 그룹 | 하위 그룹 | Cliff's δ |
|---|---|---|---|
| 분당 컷 수 | 23.9 | 5.5 | +0.72 |
| 샷 길이 중앙값 | 1.5초 | 6.2초 | −0.79 |
| 첫 15초 컷 수 | 5 | 2 | +0.57 |
| 씬당 등장인물 | 1.24 | 0.95 | +0.46 |
| 썸네일 텍스트 있음 | 9/25 | 24/25 | p<0.0001 |
| 프리미어 공개 | 13/25 | 4/25 | p=0.016 |

상·하위 **공통**이라 인기 요인이 아닌 것(장르 관습): 가사 주제(이별)·부정 정서·1인칭 독백, 곡 길이, 라우드니스, 업로드 요일·시각.

**주의**: 극단 그룹 설계의 상관관계이지 인과가 아님. 빠른 컷·작화량은 제작 투자 규모의 프록시일 수 있음. 채널 다작 교란(δ −0.75)이 문서화돼 있으며 통제 재분석 예정. **[2026-07-21 갱신]** 프리미어 공개 행은 사이클 1 원 결과를 그대로 유지하지만, 채널 내 매칭 재분석에서 프리미어 효과는 소멸했다(55쌍, Wilcoxon p=0.46, 배율 중앙값 1.07×) — 원 결과(13/25 vs 4/25)는 채널 수준 교란으로 보인다. 자세한 내용은 [`docs/reports/2026-07-21-premiere-matching.md`](docs/reports/2026-07-21-premiere-matching.md) 참조.

## 파이프라인 (전부 로컬, 외부 API 없음)

| 단계 | 도구 |
|---|---|
| 수집·메타데이터 | yt-dlp + ffmpeg (deno JS 런타임) |
| 씬 경계/컷 리듬/색감 | PySceneDetect 0.7 (ContentDetector t=15) + OpenCV |
| 오디오 (BPM·키·LUFS·에너지·비트) | librosa 0.11 + ffmpeg ebur128 |
| 장면 의미 태깅 | Ollama `qwen2.5vl:7b`, temperature 0, 고정 어휘 |
| 가사 — 하드자막 OCR | 동일 VLM, 하단 30% 크롭 0.5fps |
| 가사 — ASR 폴백 | demucs 보컬 분리 + faster-whisper large-v3 |
| 가사 주제/감정 태깅 | Ollama 텍스트 호출, 고정 어휘 |

GPU 단계는 절대 동시 실행하지 않음 (16GB VRAM): ASR은 별도 프로세스로 실행하고, 직전에 VLM 모델을 명시적으로 언로드.

## 사용법

일반 탐색의 권장 진입점은 위 Web Research Explorer다. 설치형 `mva` CLI는 분석·QA·snapshot 생성용 엔진이며, 기존 `python analyze.py ...` 등 루트 스크립트도 그대로 호환된다.

```bash
# CPU 기본 기능 설치 (GPU ASR/VLM은 별도 환경 유지)
pip install -e .

# 환경/데이터 QA — 모델 추론이나 CUDA를 실행하지 않음
mva doctor
mva config                         # 현재 측정 모델/threshold 확인
mva status
mva qa --tests
mva stats-qa --table work/features_table.jsonl

# 읽기 전용 로컬 인덱스 + feature-space 탐색
mva index
mva index --check                  # source fingerprint 기준 freshness 확인
mva search <검색어> --limit 50      # 제목·가사·씬 태그 DuckDB 검색
mva similar <video_id> --limit 10
mva benchmark <video_id>
mva outliers --limit 10
mva motion <video.mp4|video_id>       # CPU optical-flow 실험 측정기
mva motion-scenes <video_id>          # 씬별 움직임 3분류 (정지 이미지 / 정지 일러스트+카메라워크 / 실제 움직임)
mva motion-scenes-batch               # 코퍼스 전체 → data/<id>/motion_scenes.json + work/experiments/motion/
mva caption-scan                      # YouTube 자막 트랙 가용성 스캔 (네트워크만, 가사 본문 미수집)
mva motion-label                      # 모션 3분류 사람 라벨 게이트용 층화 표본·스트립 생성 (블라인드)
mva motion-label-score                # 채워진 라벨 시트를 정답키와 대조 (일치율·Cohen's kappa)
mva evaluate-vlm --baseline           # 기존 VLM vs 블라인드 라벨 CPU 재채점
mva evaluate-vlm candidate.json       # 후보 모델 출력 A/B 채점

# MV 1편 분석 / 진단
mva analyze <YouTube URL> --lang ja|ko
mva analyze <YouTube URL> --web-report my-mv.json --benchmark-domain all|vocaloid|kpop
mva diagnose <YouTube URL>

# 분석 결과 대화 계층
mva talk list
mva talk show <id>
mva talk timeline <id>
mva talk at <id> <초>
mva talk search <검색어>
mva talk compare <id> <id> ...
mva talk profile --list work/favorites.txt   # 취향 목록의 공통 형질을 코퍼스 백분위·색 팔레트와 함께 (특이점/공통/관습/무관)
mva talk export <id>                         # OpenMontage 호환 분석 JSON → work/exports/ (openmontage-reference-lab --from-analysis 입력)
mva talk sanitize <vision.json> --typography abstract   # 레퍼런스 고유 요소(자막 띠·필러박스·화면 글자) 제거한 생성용 변형
mva gen-frames <id> --clean-source <무자막 id>           # 생성용 참조 프레임 (무자막 판본에서 재추출 + 필러박스 제거)
mva talk export <id> --keyframes <dir>                  # 그 프레임 세트를 꽂아 내보내기 (I2VA 첫 프레임)

# 표본/배치/리포트
mva collect discover --queries work/queries.txt --out work/channels_candidates.csv
mva batch
mva report
mva dashboard
mva trend --report
```

`analyze`는 앞으로 `analysis_manifest.json`에 git commit, pipeline schema, 단계별 fingerprint를 기록한다. 기존 legacy 산출물은 자동 재처리하지 않으며, **manifest가 있는 산출물 중 코드 fingerprint가 바뀐 단계만** 명시적으로 `mva analyze ... --refresh-stale`을 줬을 때 재생성한다. 손상된 JSON 캐시는 재실행 시 자동 복구된다.

통합 `mva` CLI는 Windows 자식 Python에 UTF-8을 자동 적용한다. 루트 스크립트를 직접 실행할 때는 기존처럼 `PYTHONUTF8=1`을 권장한다. GPU 단계는 Ollama VLM / demucs / faster-whisper를 순차 실행하는 기존 원칙을 유지한다. GPU 산출물 재생성이 필요한 분석은 시작 전 busy guard를 통과해야 하며, 다른 세션이 2GB+ VRAM 또는 35%+ GPU를 사용 중이면 기본적으로 중단한다 (`--force-gpu-busy`로만 명시적 우회). CPU QA(`mva qa`, `mva index`, `mva search`, `mva similar`, `mva benchmark`, `mva outliers`)는 GPU를 사용하지 않는다. DuckDB는 JSON 원본을 대체하지 않는 로컬 캐시이며, 새 분석/수정으로 source fingerprint가 바뀌면 `mva search`가 자동 재빌드한다. 인덱스에는 로컬 가사 라인이 포함될 수 있으므로 `.duckdb`와 sidecar는 gitignore되며 공유/커밋하지 않는다.

## 데이터셋

[`dataset/features_100mv.csv`](dataset/features_100mv.csv) — 공개본은 보컬로이드+K-pop 100편 × **93개 공개-safe 컬럼**이다. private provenance 원본의 썸네일 OCR 원문 1개 컬럼은 의도적으로 제외한다. [`dataset/features_50mv.csv`](dataset/features_50mv.csv)는 50편 × **84개 공개-safe 컬럼**이다. [데이터 사전](dataset/README.md) 참조. 미디어·가사/OCR 원문은 배포하지 않는다.

## 연구 과정 (완료된 사이클)

1. ✅ **P1 — 표본 설계** (2026-07-15): [스펙](docs/superpowers/specs/2026-07-15-p1-sample-design-design.md) — 모집단·정규화(조회/구독)·극단 그룹·제외 규칙
2. ✅ **P2 — 파이프라인** (2026-07-16): 단일 CLI 분석기 + 수집기, 파일럿 대비 검증 게이트 2단계 ([게이트1](docs/superpowers/specs/2026-07-15-p2-validation.md) · [게이트2](docs/superpowers/specs/2026-07-16-p2-validation-gate2.md) · [유효성 검토](docs/superpowers/specs/2026-07-16-features-validity-review.md))
3. ✅ **P3 — ASR** (2026-07-16): 원본 채널 2/2편에서 하단 크롭 OCR 실패(전면 타이포/영어 자막) → demucs+whisper 도입·재검증
4. ✅ **P4 — 배치** (2026-07-16): 50/50 성공 (이어하기 배치 드라이버, Ollama/VRAM 순차화, YouTube 봇 차단 대응)
5. ✅ **P5 — 통계** (2026-07-16): Mann-Whitney U + Cliff's δ + BH-FDR, 효과크기 랭킹, 교란 점검

## 신뢰성 보강 로드맵

CPU-only 구조/QA 고도화와 남은 GPU 게이트는 [`2026-08-27-cpu-hardening.md`](docs/reports/2026-08-27-cpu-hardening.md)에 정리했다.

- [x] **채널 다작 교란 통제 재분석** (2026-07-17): log-매칭 쌍대 Wilcoxon — 유의 10개 전원 유지 (`docs/reports/2026-07-17-confound-reanalysis.md`)
- [x] **측정 정확도 검증** (2026-07-17): VLM 태깅 vs 독립 라벨러 블라인드 대조 — 유의 결론 10개 중 9개는 결정론적 측정기 기반, 인물 수는 ρ0.80 통과, mood/shot_type은 가중 하향 (`2026-07-17-measurement-reliability.md`)
- [x] 가사 저작물 git 이력 제거 (저작권) + CI(GitHub Actions) 구축
- [ ] 표본 증설 (그룹당 40편+ → 중간 효과 검출)
- [x] **타 도메인 재현** (2026-07-21): K-pop 50/50 완주 — 보컬로이드 대비 도메인 비교 리포트 (`docs/reports/2026-07-21-domain-comparison.md`)
- [x] **신규 분석 3종** (2026-07-21): 프리미어 채널 내 매칭 · 가사 구조 · 히트맵 리텐션(`docs/reports/2026-07-21-heatmap-retention.md`) — 사전등록 게이트 **FAIL**(기준: q<0.05 & |δ|≥0.33, 또는 매칭 p<0.05 — 충족 결과 없음 → 재기획 복귀, `docs/reports/2026-07-21-new-analyses-gate.md`)
- [x] **측정 수정: ASR 가사 언어필터 버그** (2026-07-21): `asr_to_lines`가 sung English 라인을 환각으로 오분류해 K-pop 표본 대량 탈락시키던 버그 수정(라틴 문자 포함 + 연속중복 접기) → K-pop 유효 표본 28→47/50 복구(보컬로이드는 47/50로 변동 없음). 게이트 재판정 결과도 **FAIL**(동일 기준, 충족 결과 없음) — 상세: `docs/reports/2026-07-21-lyrics-structure.md`
- [x] **중간층 표본 / 단조성** (2026-07-22): 보컬로이드 40~60 백분위 중간층 그룹 추가(하위25/중간25/상위25) — 사전 등록 편집 리듬 지표 **6/6** 전부 단조 dose-response gradient 성립(Kendall τ, 전부 q<0.005; 예: 분당 컷 5.5→17.5→23.9) ([리포트](docs/reports/2026-07-22-monotonicity.md))
- [x] **색 다양성/시각 변동 파생 feature**: 기존 씬 산출물에서 밝기·채도 표준편차, 색 변화 평균/P90, 고유색 비율을 GPU 없이 DuckDB 인덱스에 파생
- [x] **CPU optical-flow motion 측정기**: 샷 내부 움직임 평균/중앙값/P90/static ratio를 opt-in으로 측정; 기존 128편 결과에는 자동 혼합하지 않음
- [x] **통계 feature 정책/입력 QA**: 정식 P5 allowlist를 중앙화하고 `ext_*`/`motion_*` 실험 지표는 기존 가설검정에 자동 혼합하지 않음; 실제 50편 표는 top/bottom 25/25, 결측 정책 오류 0
- [x] **DuckDB freshness 추적**: 데이터/파생 코드 fingerprint sidecar + 검색 시 stale 자동 재빌드
- [x] **CI 연구 방어선**: Python 3.12/3.13 모든 브랜치 push에서 pytest + Ruff F-only + P5 입력표 QA + 공개 CSV dataset invariant QA 실행
- [ ] 정식 음악 구조 모델 기반 후렴 위치(all-in-one-infer 등) — 현재 반복 가사 기반 `ext_lyrics_first_chorus_*` 프록시는 제공
- [x] **씬별 움직임 3분류** (2026-09-02): Farneback flow의 평균 크기·분산으로 씬을 정지 이미지 / 정지 일러스트+팬·줌 / 실제 움직임으로 분류(`motion_scene_*`, 실험 접두사). 순차 디코딩으로 편당 수십 초
- [x] **모션 3분류 사람 라벨 게이트 (2026-09-03): 미통과** — 블라인드 45건 대조 일치율 0.556 · κ 0.333 (기준 0.75 / 0.60). 임계값·모델을 바꿔도 상한이 3분류 0.667 · 2분류 0.733이라 통과 불가. 단 `motion_clip` 정밀도 1.000(재현율 0.484)으로 **단측 지표**로는 유효. `motion_scene_*`는 가설검정 미편입 확정, 상·하위 그룹 탐색치 중 정지 비율 행은 철회 ([리포트](docs/reports/2026-09-03-motion-gate.md))
- [x] **자막 트랙 가용성 스캔** (2026-09-02): 128편 중 수동 자막 76편, 원곡 언어 트랙 50편(ja 14/77 · ko 36/51). 가사 결손 12편 중 7편 복구 가능, ASR 58편 중 32편 승급 가능 — 가사 출처 `cc` 도입은 전 코퍼스 재실행 규칙 대상이라 별도 결정
- [x] **생성용 프롬프트 변형** (2026-09-03): `talk sanitize`가 비전 시맨틱스에서 자막 띠·필러박스·화면 가사를 절 단위로 걷어내고(49샷 중 82절), 글자에 기대는 서술은 형태 서술로 치환. reference-lab 재실행에서 산물 언급 96→0, H3 ready 49/49
- [x] **생성용 참조 프레임** (2026-09-03): I2VA는 이미지를 첫 프레임으로 쓰므로 서술만 정리해선 부족하다 — 키프레임 49장 중 29장에 남아 있던 필러박스와 팬자막을, `gen-frames`가 무자막 판본에서 같은 시각의 프레임을 재추출하고 띠를 깎아 제거(MV 자체 타이포그래피는 보존)
- [x] **취향 프로파일 / 제작 브리지** (2026-09-02): `talk profile`이 목록 공통 형질을 코퍼스 백분위로 특이점·공통·관습·무관으로 가르고 색 팔레트 편차를 냄; `talk export`가 OpenMontage 호환 JSON을 내보내 `openmontage-reference-lab --from-analysis`로 H3 프롬프트 단계까지 연결 (코드 의존 없음, AGPL 경계 유지)

## 트렌드 모니터링 런북

- **가벼운 추적 (수 분)**: `python trend_snapshot.py` — 표본 50편 현재 조회수 스냅샷, `--report`로 성장 비교. 분기 1회.
- **전체 갱신 (하룻밤)**: 분기마다 enumerate(date 창 이동) → sample → batch → p5_report — 메타 변화 추적. 이전 결과는 `docs/reports/`에 날짜별 보존.

## pilot/ (최초 검증 산출물)

`report.md` · `meta.json` · `scenes.json`+`keyframes/` · `audio_features.json` · `scene_tags.json` · `lyrics_ocr.json`→`lyrics_clean.txt` · 분석 스크립트 4종. 대상: 바움쿠헨 엔드롤 / 아마라 (vF0ZU2GQSzo).

## 라이선스

소스 코드는 **Apache License 2.0**이다. 공개 데이터셋은 [`DATA_LICENSE.md`](DATA_LICENSE.md)를 따르며, 프로젝트가 권리를 보유한 selection/파생 측정치는 CC BY 4.0으로 제공하되 제3자 권리는 포함하지 않는다. 의존성·모델은 각자 라이선스를 유지하며 [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md)에 정리한다.
