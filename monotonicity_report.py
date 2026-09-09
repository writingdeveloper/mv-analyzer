"""Phase 4 — 중간층 표본 단조성(dose-response) 확인 리포트.

docs/superpowers/specs/2026-07-21-paper-dataset-design.md §Phase 4.
work/features_table.jsonl(상·하위, 사이클 1)과 work/middle/features_table.jsonl
(중간층, 야간 배치 산출물)을 합쳐 사전 등록 6지표에 대해 하위<중간<상위 단조
경향을 검정한다. 중간층 배치가 아직 끝나지 않았으면 실행 전 명확히 실패한다.

핵심 로직(그룹핑·판정·리포트)은 mv_analyzer/monotonicity.py, 통계 코어
(trend_test)는 mv_analyzer/stats.py — 둘 다 유닛 테스트 대상.

usage:
  python monotonicity_report.py [--table work/features_table.jsonl]
                                 [--middle-table work/middle/features_table.jsonl]
                                 [--out docs/reports/2026-07-22-monotonicity.md]
  python monotonicity_report.py --selftest   # 합성 데이터로 파이프라인만 검증
"""
import argparse
import json
import os
import sys
import tempfile
from datetime import date

from mv_analyzer.monotonicity import run_analysis, render_report


def _load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(ln) for ln in f if ln.strip()]


def _generate(table, middle_table, out, generated=None):
    if not os.path.exists(table):
        print(f"오류: {table} 없음 — 사이클 1 배치(top/bottom)를 먼저 실행하세요",
              file=sys.stderr)
        return 1
    if not os.path.exists(middle_table):
        print(f"오류: {middle_table} 없음 — 중간층 야간 배치가 아직 완료되지 "
              "않았습니다 (scripts/run_middle_batch.ps1 실행 필요)", file=sys.stderr)
        return 1

    rows = _load_jsonl(table)
    bottom = [r for r in rows if r.get("group") == "bottom"]
    top = [r for r in rows if r.get("group") == "top"]
    middle = _load_jsonl(middle_table)
    if any(r.get("group") for r in middle):  # batch.py가 group 컬럼을 채웠으면 필터
        middle = [r for r in middle if r.get("group") == "middle"]

    if not bottom or not top or not middle:
        print(f"오류: 그룹 표본 부족 (하위 {len(bottom)} / 중간 {len(middle)} "
              f"/ 상위 {len(top)}) — 배치가 정상 종료했는지 확인하세요", file=sys.stderr)
        return 1

    results = run_analysis(bottom, middle, top)
    if not results:
        print("오류: 사전 등록 지표 중 검정 가능한 것이 없습니다 (표본 수 부족)",
              file=sys.stderr)
        return 1

    report = render_report(results, len(bottom), len(middle), len(top),
                           generated or date.today().isoformat())
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"리포트 → {out}")
    n_ok = sum(1 for r in results
              if r["q"] < 0.05 and r["median_order"] in ("증가", "감소"))
    print(f"단조성 성립 {n_ok}/{len(results)}")
    return 0


def _selftest():
    """실데이터(work/middle/features_table.jsonl) 없이 파이프라인 자체를 검증.

    scene_cuts_per_minute만 뚜렷한 단조 신호를 주고 나머지 5개 지표는 그룹 간
    구분 없는 합성 값으로 채워 '일부만 성립'하는 정상 케이스를 재현한다.
    """
    from mv_analyzer.monotonicity import METRICS

    rng_vals = {
        "bottom": [1, 2, 1, 3, 2],
        "middle": [10, 9, 11, 10, 12],
        "top": [20, 22, 19, 21, 20],
    }
    flat_vals = {"bottom": [5, 4, 6, 5, 4], "middle": [5, 6, 4, 5, 6],
                "top": [4, 5, 6, 5, 4]}

    def make_group_rows(group):
        vals_by_metric = {}
        for i, m in enumerate(METRICS):
            vals_by_metric[m] = (rng_vals if i == 0 else flat_vals)[group]
        n = len(next(iter(vals_by_metric.values())))
        return [{m: vals_by_metric[m][j] for m in METRICS} for j in range(n)]

    bottom = [dict(group="bottom", **r) for r in make_group_rows("bottom")]
    middle = [dict(group="middle", **r) for r in make_group_rows("middle")]
    top = [dict(group="top", **r) for r in make_group_rows("top")]

    with tempfile.TemporaryDirectory() as td:
        table = os.path.join(td, "features_table.jsonl")
        middle_table = os.path.join(td, "middle_features_table.jsonl")
        out = os.path.join(td, "monotonicity.md")
        with open(table, "w", encoding="utf-8") as f:
            for r in bottom + top:
                f.write(json.dumps(r) + "\n")
        with open(middle_table, "w", encoding="utf-8") as f:
            for r in middle:
                f.write(json.dumps(r) + "\n")

        # 누락 파일 케이스도 함께 확인 (야간 배치 완료 전 상태를 정직하게 실패)
        missing_rc = _generate(table, os.path.join(td, "does_not_exist.jsonl"), out)
        assert missing_rc == 1, "미완료 중간 테이블에서 실패해야 함"

        rc = _generate(table, middle_table, out, generated="2026-07-22(selftest)")
        assert rc == 0, "정상 입력에서는 성공해야 함"
        with open(out, encoding="utf-8") as f:
            report = f.read()
        assert METRICS[0] in report
        assert "단조성 성립" in report
        assert "하위 5" in report and "중간 5" in report and "상위 5" in report

    print("--selftest 통과: 파이프라인(로드→검정→BH-FDR→리포트 렌더) 정상, "
         "누락 파일 시 정직한 실패 확인")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="work/features_table.jsonl")
    ap.add_argument("--middle-table", default="work/middle/features_table.jsonl")
    ap.add_argument("--out", default="docs/reports/2026-07-22-monotonicity.md")
    ap.add_argument("--selftest", action="store_true",
                    help="합성 jsonl로 파이프라인 검증 — 실데이터·중간층 배치 불필요")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()
    return _generate(args.table, args.middle_table, args.out)


if __name__ == "__main__":
    sys.exit(main())
