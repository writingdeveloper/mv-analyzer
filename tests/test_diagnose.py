from diagnose import extract_video_id, median, percentile_rank, verdict


def test_extract_video_id():
    assert extract_video_id("https://www.youtube.com/watch?v=vF0ZU2GQSzo") == "vF0ZU2GQSzo"
    assert extract_video_id("https://youtu.be/ctAMLdnQUfI") == "ctAMLdnQUfI"
    assert extract_video_id("g0JEUPfmu9c") == "g0JEUPfmu9c"


def test_median_and_percentile():
    assert median([1, 2, 3, 4]) == 2.5
    assert median([1, 2, 3]) == 2
    assert percentile_rank([1, 2, 3, 4], 5) == 100
    assert percentile_rank([1, 2, 3, 4], 0) == 0


def test_verdict_direction():
    # 상위 그룹이 큰 feature(+1): 중간점 이상이면 상위형
    assert verdict(20, med_top=24, med_bot=5, direction=+1) == "상위형"
    assert verdict(10, med_top=24, med_bot=5, direction=+1) == "하위형"
    # 상위 그룹이 작은 feature(-1): 중간점 이하이면 상위형
    assert verdict(2.0, med_top=1.5, med_bot=6.2, direction=-1) == "상위형"
    assert verdict(5.0, med_top=1.5, med_bot=6.2, direction=-1) == "하위형"
