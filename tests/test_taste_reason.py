import json
from pathlib import Path

from mv_analyzer.reason import build_reason_document, render_claim
from mv_analyzer.taste_reason import build_taste_claims

ROOT = Path(__file__).resolve().parents[1]
REPORT = json.loads((ROOT / 'web/e2e/fixtures/analyze-report.json').read_text(encoding='utf-8'))


def profile(n=6):
    return {
        'n_videos': n,
        'n_corpus': 132,
        'videos': [{'video_id': str(i), 'title': f'fav-{i}'} for i in range(n)],
        'missing': [],
        'numeric': [
            {'col': 'scene_cuts_per_minute', 'label': '분당 컷 수', 'n': n, 'median': 22, 'median_pct': 62,
             'min_pct': 10, 'max_pct': 97, 'spread_ratio': 0.9, 'verdict': '무관(편차 큼)', 'points': []},
            {'col': 'audio_lufs_i', 'label': '라우드니스(LUFS)', 'n': n, 'median': -8, 'median_pct': 85,
             'min_pct': 75, 'max_pct': 96, 'spread_ratio': 0.2, 'verdict': '특이점·높음', 'points': []},
            {'col': 'audio_bpm', 'label': 'BPM', 'n': n, 'median': 130, 'median_pct': 55,
             'min_pct': 45, 'max_pct': 65, 'spread_ratio': 0.1, 'verdict': '공통·관습', 'points': []},
            {'col': 'motion_scene_clip_ratio', 'label': '실제 움직임 씬 비율', 'n': n, 'median': 0.9,
             'median_pct': 90, 'min_pct': 80, 'max_pct': 98, 'spread_ratio': 0.1,
             'verdict': '특이점·높음', 'points': []},
        ],
        'categorical': [
            {'col': 'tag_mood_top', 'label': '지배적 무드', 'top': '활기', 'share': 0.83, 'corpus_share': 0.46,
             'n': n, 'verdict': '취향 신호', 'counts': {'활기': 5, '슬픔': 1}},
            {'col': 'tag_style_top', 'label': '작화 스타일', 'top': 'anime', 'share': 1.0, 'corpus_share': 0.72,
             'n': n, 'verdict': '관습', 'counts': {'anime': n}},
        ],
        'palette': None,
    }


def target_features():
    return {'tag_mood_top': '활기', 'tag_style_top': 'anime'}


def test_taste_claims_require_four_analyzed_favorites_for_positive_reason():
    claims = build_taste_claims(REPORT, profile(3), target_features=target_features())
    assert not any(c['support'] == 'supported' and c['claim_type'] == 'taste_signal' for c in claims)
    assert any(c['support'] == 'insufficient' for c in claims)


def test_taste_signal_confidence_scales_with_sample_size_and_motion_is_filtered():
    low = build_taste_claims(REPORT, profile(4), target_features=target_features())
    med = build_taste_claims(REPORT, profile(6), target_features=target_features())
    assert any(c['claim_type'] == 'taste_signal' and c['confidence'] == 'low' for c in low)
    assert any(c['claim_type'] == 'taste_signal' and c['confidence'] == 'medium' for c in med)
    assert not any('motion_scene' in str(c) for c in med)


def test_high_variance_axis_is_explicitly_not_supported_when_target_is_distinctive():
    r = json.loads(json.dumps(REPORT))
    f = next(x for x in r['features'] if x['id'] == 'scene_cuts_per_minute')
    f.update({'value': 35, 'z': 1.8, 'percentile': 95.0})
    claims = build_taste_claims(r, profile(6), target_features=target_features())
    c = next(c for c in claims if c['subject'] == 'scene_cuts_per_minute')
    assert c['support'] == 'contradicted'
    assert c['claim_type'] == 'not_supported'
    assert 'not currently supported' in render_claim(c, 'en')


def test_shared_convention_is_not_presented_as_personal_reason():
    claims = build_taste_claims(REPORT, profile(6), target_features=target_features())
    c = next(c for c in claims if c['subject'] == 'audio_bpm')
    assert c['claim_type'] == 'shared_but_conventional'
    assert c['support'] == 'insufficient'


def test_categorical_taste_signal_uses_explicit_target_feature_and_reason_document_includes_it():
    claims = build_taste_claims(REPORT, profile(6), target_features=target_features())
    mood = next(c for c in claims if c['subject'] == 'tag_mood_top')
    assert mood['support'] == 'supported' and mood['claim_type'] == 'taste_signal'
    doc = build_reason_document(
        REPORT,
        taste_profile=profile(6),
        target_features=target_features(),
        generated_at='2026-09-09T18:00:00Z',
    )
    assert mood['id'] in doc['summary']['taste']
