"""표본 수집: 채널 발굴(discover) → 모집단 열거(enumerate) → 극단 표본 추출(sample).

스펙 §2~§4: 구독자 1,000+ / 업로드 2025-04~2026-04 / Shorts 제외 /
view_per_sub 상·하위 각 25편 / 채널당 최대 2편.
"""
import json
import re
import subprocess
import unicodedata

import numpy as np

from mv_analyzer.download import slim_meta, ytdlp_cmd

# 스펙 §2 제외 조건(커버·리믹스·리마스터·라이브·인스트)의 제목 휴리스틱.
# 오리지널 MV가 아닌 콘텐츠 유형(라디오·XFD·예고편)도 함께 배제.
EXCLUDE_TITLE = re.compile(
    r"remix|リミックス|arrange|アレンジ|cover|カバー|歌ってみた|"
    r"instrumental|インスト|off\s*vocal|カラオケ|karaoke|remaster|"
    r"リマスター|ライブ|\blive\b|クロスフェード|xfd|trailer|予告|teaser|"
    r"ティザー|ラジオ|radio|mmd|talk|対談|インタビュー|interview|"
    r"メイキング|making|behind|tour|ツアー|試聴|digest|\breel\b|"
    r"anniversary|visualizer|session|発表会|解説|\bdj\b|performance|"
    r"つくってみた|studio\s*film|(dance|acoustic|piano|band|かわいい)\s*ver|"
    r"official\s*audio|メドレー|medley|全曲紹介|東方|touhou|mix\b|"
    r"を出します|\btr\.\s*\d|album\s*(preview|announcement)|"
    r"full\s*album|"
    # K-pop 도메인 비-MV 유형
    r"직캠|fancam|안무|choreograph|dance\s*practice|무대|stage\s*mix|"
    r"lyric\s*video|리릭\s*비디오|콘서트|concert|응원법|비하인드|"
    r"교차편집|자컨|challenge|챌린지|reaction|리액션", re.I)


# K-pop 등 공식 채널 도메인용 포지티브 필터 — MV 표기가 제목에 있어야 함.
# (보컬로이드는 MV 표기가 없는 원제가 많아 기본 비활성)
MV_MARKER = re.compile(
    r"\bM/?V\b|official\s*(music\s*)?video|music\s*video|뮤직\s*비디오", re.I)


def filter_population(rows, min_subs=1000, min_dur=60, max_dur=600,
                      date_from="20250401", date_to="20260401",
                      require_mv=False):
    out = []
    for r in rows:
        if r.get("view_per_sub") is None:
            continue
        if (r.get("subscriber_count") or 0) < min_subs:
            continue
        dur = r.get("duration_s") or 0
        if not (min_dur <= dur <= max_dur):
            continue
        d = r.get("upload_date") or ""
        if not (date_from <= d <= date_to):
            continue
        w, h = r.get("width"), r.get("height")
        if w and h and h > w:  # 세로형(Shorts) 제외
            continue
        # NFKC 정규화 — 장식 유니코드("𝑶𝒇𝒇𝒊𝒄𝒊𝒂𝒍")의 정규식 회피 차단
        title = unicodedata.normalize("NFKC", r.get("title") or "")
        if EXCLUDE_TITLE.search(title):
            continue
        if require_mv and not MV_MARKER.search(title):
            continue
        out.append(r)
    return out


def _pick(rows_sorted, n, cap):
    picked, per_ch = [], {}
    for r in rows_sorted:
        ch = r["channel_id"]
        if per_ch.get(ch, 0) >= cap:
            continue
        picked.append(r)
        per_ch[ch] = per_ch.get(ch, 0) + 1
        if len(picked) == n:
            break
    return picked

def select_sample(rows, n=25, cap_per_channel=2):
    by_ratio = sorted(rows, key=lambda r: r["view_per_sub"], reverse=True)
    top = _pick(by_ratio, n, cap_per_channel)
    top_ids = {r["video_id"] for r in top}
    rest = [r for r in reversed(by_ratio) if r["video_id"] not in top_ids]
    bottom = _pick(rest, n, cap_per_channel)
    return {"top": top, "bottom": bottom}


def select_middle(rows, n=25, cap_per_channel=2, lo_pct=40, hi_pct=60,
                  exclude_ids=frozenset()):
    """중간층 표본 추출 (Phase 4 §단조성 확인) — view_per_sub 40~60 백분위.

    백분위·중앙값은 FULL rows 목록의 view_per_sub 분포 기준(결정론적,
    numpy.percentile 선형보간). 밴드 내에서 중앙값과 가까운 순으로 정렬 후
    기존 _pick 채널당 상한 로직 재사용.
    """
    vals = [r["view_per_sub"] for r in rows if r.get("view_per_sub") is not None]
    if not vals:
        return []
    lo = np.percentile(vals, lo_pct)
    hi = np.percentile(vals, hi_pct)
    median = np.percentile(vals, 50)
    band = [r for r in rows
            if r.get("view_per_sub") is not None
            and lo <= r["view_per_sub"] <= hi
            and r["video_id"] not in exclude_ids]
    band_sorted = sorted(band, key=lambda r: abs(r["view_per_sub"] - median))
    return _pick(band_sorted, n, cap_per_channel)


# ---------- CLI 백엔드 (네트워크) ----------

def _ytdlp_jsonl(args_list):
    proc = subprocess.run(ytdlp_cmd() + args_list, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp 실패(rc={proc.returncode}): {proc.stderr[-500:]}")
    return [json.loads(ln) for ln in proc.stdout.splitlines() if ln.strip()]


def discover_channels(queries, per_query=50):
    """검색 쿼리들로 후보 채널 수집 (채널 발굴 전용 — 표본 아님, 스펙 §3-1)."""
    seen = {}
    for q in queries:
        entries = _ytdlp_jsonl(["--flat-playlist", "--dump-json", "--",
                                f"ytsearch{per_query}:{q}"])
        for e in entries:
            cid = e.get("channel_id")
            if cid and cid not in seen:
                seen[cid] = {"channel_id": cid, "channel": e.get("channel"),
                             "channel_url": e.get("channel_url"),
                             "found_via": q}
    return list(seen.values())


def enumerate_channel(channel_url, date_from="20250401", date_to="20260401"):
    """채널 업로드 전체 flat 덤프 → 기간 후보만 전체 메타 조회 → slim rows."""
    flat = _ytdlp_jsonl(["--flat-playlist", "--dump-json", "--",
                         channel_url.rstrip("/") + "/videos"])
    rows = []
    for e in flat:
        vid = e.get("id")
        if not vid:
            continue
        dur = e.get("duration") or 0
        if dur and not (60 <= dur <= 600):  # flat 단계 저비용 필터
            continue
        try:
            full = _ytdlp_jsonl(["--dump-json", "--no-download", "--",
                                 f"https://www.youtube.com/watch?v={vid}"])
        except RuntimeError as e:
            print(f"    영상 {vid} 메타 실패 — 건너뜀: {e}", flush=True)
            continue
        if not full:
            continue
        r = slim_meta(full[0])
        d = r.get("upload_date") or ""
        if d and d < date_from:
            break  # 채널 videos 탭은 최신순 — 기간 이전에 도달하면 중단
        if date_from <= d <= date_to:
            rows.append(r)
    channel_video_count = len(flat)
    for r in rows:
        r["channel_video_count"] = channel_video_count
    return rows
