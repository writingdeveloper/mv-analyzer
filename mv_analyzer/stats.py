"""공용 통계 헬퍼 — 효과크기(Cliff's δ)와 다중비교 보정(BH-FDR).

p5_report.py에서 추출 (2026-07-21). 신규 분석 3종과 리포트 스크립트가 공유.
"""
import numpy as np
from scipy import stats


def cliffs_delta(a, b):
    """Cliff's delta — U 통계량에서 유도: d = 2U/(n1·n2) - 1."""
    u = stats.mannwhitneyu(a, b, alternative="two-sided").statistic
    return 2 * u / (len(a) * len(b)) - 1


def bh_fdr(pvals):
    """Benjamini-Hochberg q값."""
    n = len(pvals)
    order = np.argsort(pvals)
    q = np.empty(n)
    prev = 1.0
    for rank_from_end, idx in enumerate(reversed(order)):
        rank = n - rank_from_end
        prev = min(prev, pvals[idx] * n / rank)
        q[idx] = prev
    return q


def magnitude(d):
    d = abs(d)
    if d < 0.147:
        return "무시"
    if d < 0.33:
        return "작음"
    if d < 0.474:
        return "중간"
    return "큼"


def trend_test(groups):
    """순서형 그룹 간 단조 경향 검정 (Phase 4 §단조성 확인).

    groups: 오름차순으로 의미가 매겨진 그룹들의 값 리스트 (예: [bottom, middle, top]).
    설치된 scipy에 scipy.stats.jonckheere(-terpstra)가 있으면 그것을 사용,
    없으면 그룹 순위(0,1,2,...)와 값 사이 Kendall's tau(양측)로 대체
    (2026-07-21 기준 scipy 1.18에는 미존재 — 항상 폴백 경로).

    반환: {"stat": float, "p": float, "method": str}
    """
    jt_fn = getattr(stats, "jonckheere", None) or getattr(stats, "jonckheere_terpstra", None)
    if jt_fn is not None:
        res = jt_fn(*groups)
        return {"stat": float(res.statistic), "p": float(res.pvalue),
                "method": "jonckheere-terpstra"}

    ranks, vals = [], []
    for gi, g in enumerate(groups):
        ranks.extend([gi] * len(g))
        vals.extend(g)
    tau, p = stats.kendalltau(ranks, vals)
    return {"stat": float(tau), "p": float(p), "method": "kendall_tau"}
