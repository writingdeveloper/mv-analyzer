"""프리미어 효과 — 같은 채널 내 프리미어/비프리미어 영상 매칭.

채널 수준 교란(팬덤 규모·제작 수준)을 채널 내 비교로 통제한다.
스펙 1-C 참조.
"""
from collections import defaultdict
from datetime import datetime


def _days(a, b):
    return abs((datetime.strptime(a, "%Y%m%d")
                - datetime.strptime(b, "%Y%m%d")).days)


def build_pairs(rows, max_days=180):
    """각 프리미어 영상을 같은 채널의 최근접(업로드일 차, 동률이면 길이 차)
    비프리미어와 짝. 컨트롤 재사용 금지, 업로드일 차 > max_days 쌍 제외."""
    by_ch = defaultdict(list)
    for r in rows:
        if r.get("view_per_sub") and r.get("upload_date") \
                and r.get("duration_s") is not None:
            by_ch[r["channel_id"]].append(r)
    pairs = []
    for ch_rows in by_ch.values():
        premieres = [r for r in ch_rows if r.get("was_premiere")]
        controls = [r for r in ch_rows if not r.get("was_premiere")]
        used = set()
        for p in premieres:
            best, best_key = None, None
            for c in controls:
                if c["video_id"] in used:
                    continue
                key = (_days(p["upload_date"], c["upload_date"]),
                       abs(p["duration_s"] - c["duration_s"]))
                if best is None or key < best_key:
                    best, best_key = c, key
            if best is not None and best_key[0] <= max_days:
                used.add(best["video_id"])
                pairs.append((p, best))
    return pairs
