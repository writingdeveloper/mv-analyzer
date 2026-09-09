# Analyze My MV: local report workflow

The repository remains private. The public site is a research explorer and local JSON viewer,
not a hosted video-analysis service. Project collaborators have CLI access. Portfolio visitors
can use **Explore a sample report** without installing anything.

## Export an existing analysis — CPU and file IO only

```bash
mva report-export data/VIDEO_ID/features.json --out my-mv.json --benchmark-domain vocaloid
```

Use `all`, `vocaloid`, or `kpop` explicitly. A directory containing features.json is also accepted.
This command never downloads media, calls Ollama/Whisper, or starts GPU work. It preserves the
source file and optionally reads analysis_manifest.json. The tests prohibit socket connections.
Open `https://mv-analyzer.writingdeveloper.blog/?lang=en#/analyze` and select the JSON.
For Korean use `?lang=ko#/analyze`. The file is read in tab memory; it is not uploaded or saved in browser storage.
Navigating away or reloading clears the imported report. Cancel invalidates an unfinished import.

## New analysis — separate, explicit GPU permission required

```bash
mva analyze "YOUTUBE_URL" --lang ko --web-report my-mv.json --benchmark-domain kpop
```

The existing pipeline may download the requested video and run local models. Do not run this
command while GPU use is prohibited. `--skip-vlm` is not an offline report-export shortcut:
it still performs metadata/media/CPU stages. Prefer `report-export` for existing results.

## v2 report contract

v1 reports are deliberately rejected: regenerate from the source features with the current CLI.
A common JSON Schema and semantic checks validate feature ranges, uniqueness, reference scope,
SHA-256 identity, and numerical consistency in Python and the browser. The browser validator is
compiled at build time; production CSP does not allow unsafe-eval.

The reference is **Extreme Reference Corpus v2026.07**, not a representative market sample.
Reference-corpus percentile is not market ranking, future views, or a prediction of success.
The collection window is computed from the actual rows (full sample July 16–21, 2026).
The report records source features/corpus SHA-256 separately from measurement/export revisions.
A legacy manifest without a verifiable generated-features record is labeled **unverified**.
These checks establish internal consistency, not signed authenticity or independent accuracy.

PCA is fitted on reference rows only and uses the existing exploratory feature basis, including
experimental lyrics compression. Missing values are labeled. Below 60% measured PCA coverage,
score and display coordinates are withheld. The 2D/3D projection uses equal raw-score unit scales;
neighbor links use full standardized feature distance, not projected distance.
The sample demo is an in-corpus example, not out-of-sample validation.

## QA / maintainers

```bash
python scripts/build_report_contract.py --check
cd web
npm test -- --run
npm run typecheck
MVA_QA_PORT=4187 npm run test:e2e
PLAYWRIGHT_BASE_URL=https://mv-analyzer.writingdeveloper.blog npm run test:e2e
```

Browser regression uses Chromium SwiftShader software rendering, two workers, and the deployed
CSP even in local preview. Hardware GPU, ASR/VLM inference, new model A/B, and actual human visual
acceptance are separate gates and are not implied by these tests.


## Reason Engine

`mva reason-export` builds a portable `mv-analyzer-reason` document from an existing analysis without network, model or GPU work. `--favorites` uses the existing `talk profile` evidence but filters failed `motion_scene_*` experiments from personal-taste claims. Fewer than four analyzed favorites cannot produce a positive taste explanation; a high-variance favorite axis becomes an explicit `not_supported` claim when the target MV is distinctive on that axis.

`mva explain YOUTUBE_URL` does not introduce a second analyzer. It delegates to the existing `analyze.py`, receives its validated Analyze report, and then runs Reason Engine. Use `--output-lang ko|en` for deterministic terminal prose.

The Web viewer accepts either report v2 or Reason v1. Reason-only import intentionally omits PCA/raw-detail sections because those measurements are not duplicated into the portable Reason document. Import the source Analyze report when you want the full evidence dashboard.
