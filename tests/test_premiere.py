from mv_analyzer.premiere import build_pairs


def R(vid, ch, prem, date, dur=180, vps=1.0):
    return {"video_id": vid, "channel_id": ch, "was_premiere": prem,
            "upload_date": date, "duration_s": dur, "view_per_sub": vps}


def test_pairs_nearest_upload_date_within_channel():
    rows = [R("p1", "A", True, "20250601"),
            R("c1", "A", False, "20250520"),   # 12일 차 — 최근접
            R("c2", "A", False, "20250101")]   # 151일 차
    pairs = build_pairs(rows)
    assert len(pairs) == 1
    assert pairs[0][0]["video_id"] == "p1" and pairs[0][1]["video_id"] == "c1"


def test_control_used_once():
    rows = [R("p1", "A", True, "20250601"), R("p2", "A", True, "20250610"),
            R("c1", "A", False, "20250605")]
    pairs = build_pairs(rows)
    assert len(pairs) == 1  # 컨트롤 1개는 한 번만


def test_no_cross_channel_pairs():
    rows = [R("p1", "A", True, "20250601"), R("c1", "B", False, "20250601")]
    assert build_pairs(rows) == []


def test_max_days_cutoff():
    rows = [R("p1", "A", True, "20250601"), R("c1", "A", False, "20241001")]
    assert build_pairs(rows, max_days=180) == []
