# Contributing to MV Analyzer

Thanks for improving MV Analyzer. The project is local-first and evidence-first:
measurement code, explanation claims, and UI wording should remain auditable.

## Development setup

```bash
python -m venv .venv
# activate the environment, then:
pip install -e ".[dev]"
cd web && npm ci
```

Optional GPU dependencies are deliberately separate:

```bash
pip install -e ".[gpu]"
```

Do not run or change GPU/model baselines merely to satisfy CPU tests.

## Before a pull request

```bash
pytest tests/ -q
ruff check '*.py' mv_analyzer tests scripts/build_report_contract.py --select F
python -m mv_analyzer dataset-qa
python scripts/build_report_contract.py --check
cd web
npm test -- --run
npm run typecheck
npm run build
npm run test:e2e
```

## Data and privacy rules

Do not commit downloaded video/audio, screenshots/keyframes from third-party MVs,
raw lyrics/subtitles/OCR text, cookies, signed URLs, local absolute paths, private
network addresses, or secrets. Public examples must pass the existing portable
report/reason safety contracts.

## Scientific claims

- Reference-corpus percentile is not a market percentile.
- Observational differences are not causal success effects.
- Failed/experimental measurements must not be promoted to formal claims.
- A Reason claim must retain its evidence, support state, and confidence level.

## OpenMontage boundary

OpenMontage is a separate AGPLv3 project. Do not copy or vendor upstream AGPL
source into MV Analyzer without an explicit license review. JSON interoperability
may remain separated from the external runtime.
