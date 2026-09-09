import copy
import json
from pathlib import Path

import pytest

from mv_analyzer.reason import (
    REASON_POLICY_ID,
    build_reason_document,
    render_claim,
    render_reason_summary,
    write_reason_document,
)
from mv_analyzer.reason_contract import validate_reason_document

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'web/e2e/fixtures/analyze-report.json'


def report():
    return json.loads(FIXTURE.read_text(encoding='utf-8'))


def test_reason_document_is_deterministic_and_links_source_fingerprints():
    r = report()
    a = build_reason_document(r, generated_at='2026-09-09T18:00:00Z')
    b = build_reason_document(copy.deepcopy(r), generated_at='2026-09-09T18:00:00Z')
    assert a == b
    assert a['kind'] == 'mv-analyzer-reason'
    assert a['schema_version'] == 1
    assert a['policy_id'] == REASON_POLICY_ID
    assert a['source_report']['source_features_sha256'] == r['pipeline']['source_features_sha256']
    assert a['source_report']['corpus_sha256'] == r['benchmark']['corpus_sha256']
    assert a['source_report']['benchmark_domain'] == r['benchmark']['domain']
    assert set(a['summary']) == {'distinctive', 'feel', 'taste'}
    validate_reason_document(a)


def test_distinctive_claims_only_use_tail_or_z_thresholds_and_real_evidence():
    doc = build_reason_document(report(), generated_at='2026-09-09T18:00:00Z')
    source_ids = {f['id'] for f in report()['features']}
    distinctive = [c for c in doc['claims'] if c['question'] == 'distinctive']
    assert distinctive
    for claim in distinctive:
        assert claim['support'] == 'supported'
        assert claim['claim_type'] == 'descriptive_difference'
        evidence = claim['evidence']
        assert len(evidence) == 1
        e = evidence[0]
        assert e['feature_id'] in source_ids
        assert abs(e['z']) >= 0.75 or e['reference_percentile'] >= 80 or e['reference_percentile'] <= 20
    # A near-median metric must not be promoted just because it exists.
    assert not any(c['evidence'][0]['feature_id'] == 'scene_cuts_per_minute' for c in distinctive)


def test_reason_engine_never_promotes_failed_motion_metrics_or_success_claims():
    r = report()
    r['features'].append({
        'id':'motion_scene_clip_ratio','labels':{'ko':'모션','en':'Motion clip ratio'},'category':'visual',
        'value':0.99,'z':3.0,'percentile':99.0,'reference_median':0.5,'reference_mean':0.5,
        'reference_std':0.16333333333333333,'reference_n':100,
    })
    # report contract does not know this synthetic extra feature's source policy, but Reason Engine must.
    doc = build_reason_document(r, validate_source=False, generated_at='2026-09-09T18:00:00Z')
    assert not any('motion_scene' in str(c) for c in doc['claims'])
    banned = {'success_prediction','causal_success','artistic_quality','psychology'}
    assert not any(c['claim_type'] in banned for c in doc['claims'])


def test_feel_claims_require_composed_measured_axes_and_keep_evidence_links():
    doc = build_reason_document(report(), generated_at='2026-09-09T18:00:00Z')
    feel = [c for c in doc['claims'] if c['question'] == 'feel' and c['support'] == 'supported']
    assert feel
    # Fixture has high close-up + low wide and high onset + peak-energy signals.
    ids = {c['id'] for c in feel}
    assert 'feel:closeup-focus' in ids
    assert 'feel:event-dense-audio' in ids
    for c in feel:
        assert len(c['evidence']) >= 2 or max(abs(e.get('z',0)) for e in c['evidence']) >= 1.5


def test_render_claim_is_deterministic_bilingual_and_does_not_invent_success_language():
    doc = build_reason_document(report(), generated_at='2026-09-09T18:00:00Z')
    claim = next(c for c in doc['claims'] if c['question'] == 'distinctive')
    en = render_claim(claim, 'en')
    ko = render_claim(claim, 'ko')
    assert en == render_claim(claim, 'en')
    assert ko == render_claim(claim, 'ko')
    assert en and ko and en != ko
    assert 'success probability' not in en.lower()
    assert '성공 확률' not in ko


def test_writer_is_atomic_and_validates(tmp_path):
    doc = build_reason_document(report(), generated_at='2026-09-09T18:00:00Z')
    out = tmp_path / 'reason.json'
    write_reason_document(out, doc)
    loaded = json.loads(out.read_text(encoding='utf-8'))
    assert loaded == doc
    assert not (tmp_path / 'reason.json.tmp').exists()


def test_invalid_reason_claim_without_evidence_is_rejected():
    doc = build_reason_document(report(), generated_at='2026-09-09T18:00:00Z')
    doc['claims'][0]['evidence'] = []
    with pytest.raises(ValueError):
        validate_reason_document(doc)


def test_render_reason_summary_prefers_composed_feel_before_raw_features():
    doc=build_reason_document(report(),generated_at='2026-09-09T18:00:00Z')
    rows=render_reason_summary(doc,'en')
    assert rows and rows[0]['id'].startswith('feel:')
    assert all(row['text'] for row in rows)
