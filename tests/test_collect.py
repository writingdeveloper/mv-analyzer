import pytest

from mv_analyzer.collect import filter_population, select_middle, select_sample


def row(vid, ch, ratio, subs=5000, dur=180, date="20251001"):
    return {"video_id": vid, "channel_id": ch, "view_per_sub": ratio,
            "subscriber_count": subs, "duration_s": dur, "upload_date": date,
            "view_count": int(ratio * subs), "width": 1920, "height": 1080}


def test_filter_population_rules():
    rows = [
        row("ok", "c1", 1.0),
        row("low_subs", "c2", 1.0, subs=500),          # 구독자 컷
        row("short", "c3", 1.0, dur=45),                # Shorts 컷
        row("old", "c4", 1.0, date="20240101"),         # 기간 밖
        row("future", "c5", 1.0, date="20260601"),      # 기간 밖(너무 최근)
        dict(row("vertical", "c6", 1.0), width=1080, height=1920),  # 세로형
        dict(row("no_ratio", "c7", 1.0), view_per_sub=None),
    ]
    out = filter_population(rows)
    assert [r["video_id"] for r in out] == ["ok"]


def test_filter_population_title_exclusions():
    rows = [
        row("ok2", "c1", 1.0),
        dict(row("remix", "c2", 1.0), title="曲名 (Chill REMIX)"),
        dict(row("cover", "c3", 1.0), title="曲名 歌ってみた"),
        dict(row("radio", "c4", 1.0), title="【音楽ラジオ】異世界転生"),
        dict(row("xfd", "c5", 1.0), title="アルバム クロスフェード"),
    ]
    out = filter_population(rows)
    assert [r["video_id"] for r in out] == ["ok2"]


def test_filter_population_require_mv_and_nfkc():
    rows = [
        dict(row("mv1", "c1", 1.0), title="ATEEZ - 'Lemon Drop' Official MV"),
        dict(row("mv2", "c2", 1.0), title="TWICE \"THIS IS FOR\" M/V"),
        dict(row("vlog", "c3", 1.0), title="SOMIN 피크닉 일상"),
        # NFKC 정규화 없으면 EXCLUDE(official audio)를 회피하는 장식 유니코드
        dict(row("fancy", "c4", 1.0), title="𝑶𝒇𝒇𝒊𝒄𝒊𝒂𝒍 𝑨𝒖𝒅𝒊𝒐 | 'SLAM DUNK'"),
    ]
    out = filter_population(rows, require_mv=True)
    assert [r["video_id"] for r in out] == ["mv1", "mv2"]
    # require_mv=False여도 장식 유니코드 Official Audio는 제외돼야 함
    out2 = filter_population(rows)
    assert "fancy" not in [r["video_id"] for r in out2]


def test_select_sample_extremes_and_cap():
    # 채널 cA가 상위 1~3위 독점 → 캡 2로 3위는 다음 채널에 양보
    rows = ([row(f"a{i}", "cA", 100 - i) for i in range(3)]      # 100, 99, 98
            + [row(f"m{i}", f"c{i}", 50 - i) for i in range(10)]  # 중간층
            + [row(f"z{i}", "cZ", 0.01 * (i + 1)) for i in range(3)])
    out = select_sample(rows, n=3, cap_per_channel=2)
    top_ids = [r["video_id"] for r in out["top"]]
    assert top_ids[:2] == ["a0", "a1"]
    assert top_ids[2].startswith("m")           # cA 3번째는 캡으로 제외
    bottom_ids = [r["video_id"] for r in out["bottom"]]
    assert bottom_ids[:2] == ["z0", "z1"]       # 비율 오름차순
    assert len(set(bottom_ids)) == 3


def test_select_sample_no_overlap():
    rows = [row(f"v{i}", f"c{i}", float(i + 1)) for i in range(10)]
    out = select_sample(rows, n=5, cap_per_channel=2)
    assert not set(r["video_id"] for r in out["top"]) & set(
        r["video_id"] for r in out["bottom"])


def test_ytdlp_jsonl_raises_on_failure(monkeypatch):
    from mv_analyzer import collect

    class FakeProc:
        returncode = 1
        stdout = ""
        stderr = "ERROR: boom"

    monkeypatch.setattr(collect.subprocess, "run", lambda *a, **k: FakeProc())
    with pytest.raises(RuntimeError, match="yt-dlp 실패"):
        collect._ytdlp_jsonl(["--version"])


def _fake_full_meta(vid):
    return {"id": vid, "title": "t", "channel_id": "c1",
            "channel_follower_count": 5000, "view_count": 1000,
            "duration": 180, "upload_date": "20250601",
            "width": 1920, "height": 1080}


def test_enumerate_channel_skips_failed_video(monkeypatch):
    """영상 1개의 전체 메타 조회 실패가 채널 전체를 중단시키지 않아야 함."""
    from mv_analyzer import collect

    flat_entries = [{"id": "vid1", "duration": 180},
                    {"id": "vid2", "duration": 180}]

    def fake_ytdlp_jsonl(args_list):
        if "--flat-playlist" in args_list:
            return flat_entries
        vid = args_list[-1].split("v=")[-1]
        if vid == "vid1":
            raise RuntimeError("yt-dlp 실패(rc=1): boom")
        return [_fake_full_meta(vid)]

    monkeypatch.setattr(collect, "_ytdlp_jsonl", fake_ytdlp_jsonl)
    rows = collect.enumerate_channel("https://www.youtube.com/channel/UCxxx")
    assert len(rows) == 1
    assert rows[0]["video_id"] == "vid2"
    assert rows[0]["channel_video_count"] == len(flat_entries)  # 채널 규모 프록시


# ---------- select_middle (Phase 4 — 중간층 표본) ----------
# view_per_sub 1..100, 채널 고유(캡 무관) — 40~60 백분위(선형보간) → [40.6, 60.4] → 41..60


def _middle_rows(n=100):
    return [row(f"v{i}", f"c{i}", float(i)) for i in range(1, n + 1)]


def test_select_middle_only_in_band():
    rows = _middle_rows()
    out = select_middle(rows, n=25, cap_per_channel=2)
    ratios = sorted(r["view_per_sub"] for r in out)
    assert ratios == [float(i) for i in range(41, 61)]  # 20개, 41~60


def test_select_middle_excludes_ids():
    rows = _middle_rows()
    exclude = {f"v{i}" for i in range(41, 51)}  # 밴드 하위 절반 제외
    out = select_middle(rows, n=25, cap_per_channel=2, exclude_ids=exclude)
    ids = {r["video_id"] for r in out}
    assert not ids & exclude
    assert ids == {f"v{i}" for i in range(51, 61)}


def test_select_middle_channel_cap():
    # 밴드(41~60) 전체를 한 채널로 몰아 캡 위반 여부 확인
    rows = [row(f"v{i}", "cA" if 41 <= i <= 60 else f"c{i}", float(i))
            for i in range(1, 101)]
    out = select_middle(rows, n=25, cap_per_channel=2)
    assert len(out) == 2  # cA 캡 2 → 밴드 20개 중 2개만 선택
    assert all(r["channel_id"] == "cA" for r in out)


def test_select_middle_orders_by_distance_to_median():
    rows = _middle_rows()
    out = select_middle(rows, n=25, cap_per_channel=2)
    median = 50.5  # percentile(50) of 1..100
    distances = [abs(r["view_per_sub"] - median) for r in out]
    assert distances == sorted(distances)
