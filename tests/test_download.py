import datetime
import re


from mv_analyzer.download import slim_meta

FAKE_META = {
    "id": "abc123", "title": "곡명 / P명 feat. 미쿠",
    "channel": "P채널", "channel_id": "UCxxx", "channel_follower_count": 5000,
    "view_count": 10000, "like_count": 500, "comment_count": 50,
    "upload_date": "20251103", "duration": 200, "width": 1920, "height": 1080,
    "fps": 30, "tags": ["初音ミク", "VOCALOID"], "categories": ["Music"],
    "chapters": [{"start_time": 0, "title": "イントロ"}],
    "description": "作詞作曲: P名\nニコニコ: https://www.nicovideo.jp/watch/sm123",
    "heatmap": [{"start_time": 0, "end_time": 5, "value": 0.8}],
    "live_status": "not_live", "release_timestamp": 1762128000,
    "timestamp": 1762135023,
}


def test_slim_meta_core_fields():
    m = slim_meta(FAKE_META)
    assert m["video_id"] == "abc123"
    assert m["subscriber_count"] == 5000
    assert m["view_per_sub"] == 2.0
    assert m["aspect_ratio"] == round(1920 / 1080, 3)
    assert m["has_chapters"] is True
    assert m["has_nico_link"] is True
    assert m["has_heatmap"] is True
    assert m["upload_weekday"] == 0  # 2025-11-03 = 월요일
    assert m["upload_hour"] == datetime.datetime.fromtimestamp(1762135023).hour
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", m["collected_at"])


def test_slim_meta_missing_fields():
    m = slim_meta({"id": "x", "title": "t", "view_count": 100, "duration": 60})
    assert m["subscriber_count"] is None
    assert m["view_per_sub"] is None
    assert m["has_chapters"] is False
    assert m["has_nico_link"] is False
    assert m["upload_weekday"] is None
    assert m["upload_hour"] is None


def test_slim_meta_missing_view_count():
    """view_count 결측(구독자 비공개 등) 시 0으로 둔갑하지 않고 None 유지."""
    m = slim_meta({"id": "x", "title": "t", "channel_follower_count": 5000,
                   "duration": 60})
    assert m["view_count"] is None
    assert m["view_per_sub"] is None
    assert m["like_per_view"] is None
