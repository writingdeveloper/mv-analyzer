"""Evidence-backed Claim Engine over validated MV Analyzer reports."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .reason_contract import validate_reason_document

REASON_SCHEMA_VERSION = 1
REASON_KIND = "mv-analyzer-reason"
REASON_POLICY_ID = "reason-v1-z075-tail20-compose-v1"
DISTINCTIVE_Z = 0.75
DISTINCTIVE_HIGH_PCT = 80.0
DISTINCTIVE_LOW_PCT = 20.0
FAILED_EXPERIMENT_PREFIXES = ("motion_scene_",)


def _feature_map(report):
    return {row["id"]: row for row in report.get("features", []) if not row["id"].startswith(FAILED_EXPERIMENT_PREFIXES)}


def _feature_evidence(row):
    return {
        "kind": "feature", "feature_id": row["id"], "label": row["labels"], "value": row["value"],
        "z": row["z"], "reference_percentile": row["percentile"],
        "reference_median": row["reference_median"],
    }


def _is_distinctive(row):
    return abs(row["z"]) >= DISTINCTIVE_Z or row["percentile"] >= DISTINCTIVE_HIGH_PCT or row["percentile"] <= DISTINCTIVE_LOW_PCT


def _strength(row):
    return max(abs(row["z"]), abs(row["percentile"] - 50.0) / 25.0)


def _confidence(row):
    return "high" if abs(row["z"]) >= 1.0 or row["percentile"] >= 90 or row["percentile"] <= 10 else "medium"


def _distinctive_claims(report):
    rows = [row for row in _feature_map(report).values() if _is_distinctive(row)]
    rows.sort(key=lambda row: (-_strength(row), row["id"]))
    claims = []
    for row in rows:
        direction = "high" if row["z"] > 0 or row["percentile"] > 50 else "low"
        claims.append({
            "id": f"distinctive:{row['id']}:{direction}", "question": "distinctive",
            "claim_type": "descriptive_difference", "subject": row["category"], "direction": direction,
            "support": "supported", "confidence": _confidence(row), "scope": "reference_corpus",
            "text_key": f"reason.feature.{direction}", "evidence": [_feature_evidence(row)],
        })
    return claims


def _composed_claim(claim_id, subject, text_key, rows, confidence="medium"):
    return {
        "id": claim_id, "question": "feel", "claim_type": "measured_composition", "subject": subject,
        "direction": "mixed", "support": "supported", "confidence": confidence,
        "scope": "reference_corpus", "text_key": text_key,
        "evidence": [_feature_evidence(row) for row in rows],
    }


def _feel_claims(report):
    f = _feature_map(report)
    claims = []
    closeup, wide = f.get("tag_closeup_ratio"), f.get("tag_wide_ratio")
    if closeup and wide and closeup["z"] >= 0.6 and wide["z"] <= -0.6:
        claims.append(_composed_claim("feel:closeup-focus", "visual framing", "reason.feel.closeup_focus", [closeup, wide]))
    onsets, peak = f.get("audio_onsets_per_sec"), f.get("audio_peak_energy_ratio")
    if onsets and peak and onsets["z"] >= 0.75 and peak["z"] >= 0.75:
        claims.append(_composed_claim("feel:event-dense-audio", "audio intensity", "reason.feel.event_dense_audio", [onsets, peak], "high"))
    hook, first_cut = f.get("hook_cuts_first_15s"), f.get("sync_first_cut_s")
    if hook and first_cut and hook["z"] >= 0.75 and first_cut["percentile"] <= 20:
        claims.append(_composed_claim("feel:front-loaded-opening", "opening hook", "reason.feel.front_loaded", [hook, first_cut], "high"))
    cpm, median_shot = f.get("scene_cuts_per_minute"), f.get("scene_median_shot_len_s")
    if cpm and median_shot and cpm["z"] >= 0.5 and median_shot["z"] <= -0.5:
        claims.append(_composed_claim("feel:rapid-pacing", "editing rhythm", "reason.feel.rapid_pacing", [cpm, median_shot]))
    sat, bright = f.get("scene_avg_saturation"), f.get("scene_avg_brightness")
    if sat and bright and sat["z"] >= 0.6 and bright["z"] >= 0.6:
        claims.append(_composed_claim("feel:vivid-visuals", "visual appearance", "reason.feel.vivid_visuals", [sat, bright]))
    return claims


def build_reason_document(report, *, taste_profile=None, target_features=None, generated_at=None, validate_source=True):
    if validate_source:
        from .report_contract import validate_report
        validate_report(report)
    distinctive = _distinctive_claims(report)
    feel = _feel_claims(report)
    taste = []
    if taste_profile:
        from .taste_reason import build_taste_claims
        taste = build_taste_claims(report, taste_profile, target_features=target_features)
    claims = [*distinctive, *feel, *taste]
    doc = {
        "schema_version": REASON_SCHEMA_VERSION, "kind": REASON_KIND, "policy_id": REASON_POLICY_ID,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "video": {key: report["video"][key] for key in ("video_id", "title", "channel")},
        "source_report": {
            "schema_version": report["schema_version"],
            "source_features_sha256": report["pipeline"]["source_features_sha256"],
            "corpus_sha256": report["benchmark"]["corpus_sha256"],
            "benchmark_domain": report["benchmark"]["domain"],
        },
        "summary": {
            "distinctive": [c["id"] for c in distinctive[:4]],
            "feel": [c["id"] for c in feel[:4]],
            "taste": [c["id"] for c in taste[:6]],
        },
        "claims": claims,
        "limits": [
            "descriptive-reference-only", "not-a-success-prediction",
            *(["taste-profile-small-sample"] if taste_profile and int(taste_profile.get("n_videos") or 0) < 6 else []),
        ],
    }
    validate_reason_document(doc)
    return doc


def _first_feature(claim):
    return next((e for e in claim["evidence"] if e.get("kind") == "feature"), claim["evidence"][0])


def _label(evidence, locale):
    label = evidence.get("label")
    if isinstance(label, dict):
        return label.get(locale) or label.get("en") or evidence.get("feature_id", "feature")
    return evidence.get("feature_id") or evidence.get("favorite_value") or "feature"


def render_claim(claim, locale="en"):
    locale = "ko" if locale == "ko" else "en"
    key = claim["text_key"]
    evidence = claim["evidence"]
    first = _first_feature(claim)
    label = _label(first, locale)
    if key in {"reason.feature.high", "reason.feature.low"}:
        pct = first["reference_percentile"]
        if locale == "ko":
            direction = "높습니다" if key.endswith("high") else "낮습니다"
            return f"{label}은(는) 이 기준 코퍼스에서 상대적으로 {direction} (기준 코퍼스 백분위 {pct:.1f})."
        direction = "high" if key.endswith("high") else "low"
        return f"{label} is relatively {direction} in this reference corpus (reference percentile {pct:.1f})."
    feel_text = {
        "reason.feel.closeup_focus": {"en": "The visual framing leans toward close-ups rather than wide shots.", "ko": "화면 구성은 와이드 샷보다 클로즈업 쪽으로 기울어 있습니다."},
        "reason.feel.event_dense_audio": {"en": "The audio feels event-dense: onset activity and peak-energy concentration are both elevated.", "ko": "오디오는 사건 밀도가 높은 편입니다. 온셋 활동과 피크 에너지 집중도가 함께 높습니다."},
        "reason.feel.front_loaded": {"en": "The opening is front-loaded: it cuts frequently in the first 15 seconds and the first cut arrives early.", "ko": "도입부가 앞쪽에 집중되어 있습니다. 첫 15초 컷이 많고 첫 컷도 이르게 등장합니다."},
        "reason.feel.rapid_pacing": {"en": "The visual pacing is rapid: cuts are frequent and typical shots are short.", "ko": "시각적 페이스가 빠릅니다. 컷이 잦고 일반적인 샷 길이가 짧습니다."},
        "reason.feel.vivid_visuals": {"en": "The visual presentation is vivid, with both saturation and brightness elevated.", "ko": "채도와 밝기가 함께 높아 시각적으로 선명한 인상을 만듭니다."},
    }
    if key in feel_text:
        return feel_text[key][locale]
    profile = next((e for e in evidence if str(e.get("kind", "")).startswith("taste_profile")), evidence[-1])
    if key == "reason.taste.not_supported":
        if locale == "ko":
            return f"이 MV의 {label} 특성은 두드러지지만, 좋아하는 영상들에서는 이 축의 편차가 커서 현재 취향 이유로 지지되지 않습니다."
        return f"Although this MV is distinctive on {label}, that axis varies widely across your favorites, so it is not currently supported as a reason you like it."
    if key == "reason.taste.conventional":
        if locale == "ko":
            return f"좋아하는 영상들이 {label} 특성을 공유하지만 코퍼스에서도 흔해, 개인 취향 신호보다는 관습에 가깝습니다."
        return f"Your favorites share {label}, but it is also common in the corpus, so it is better treated as convention than a personal taste signal."
    if key == "reason.taste.insufficient":
        if locale == "ko":
            return f"{label}에서 취향 후보가 보이지만, 분석된 좋아하는 영상이 {profile.get('n_favorites', 0)}편뿐이라 아직 근거가 부족합니다."
        return f"There is an early taste pattern around {label}, but only {profile.get('n_favorites', 0)} analyzed favorites are available, so evidence is insufficient."
    if key == "reason.taste.signal":
        if locale == "ko":
            return f"{label}은(는) 좋아하는 영상에서 반복되는 패턴과 이 MV가 일치해, 현재 개인 취향 신호로 지지됩니다."
        return f"This MV aligns with a repeated pattern in your favorites around {label}, so it is currently supported as a personal taste signal."
    raise ValueError(f"unknown reason text key: {key}")


def write_reason_document(path, document):
    destination = Path(path)
    validate_reason_document(document)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(destination) + ".tmp")
    try:
        temp.write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        os.replace(temp, destination)
    finally:
        if temp.exists():
            temp.unlink()


def render_reason_summary(document, locale="en", limit=4):
    by_id = {claim["id"]: claim for claim in document.get("claims", [])}
    ordered = [*document.get("summary", {}).get("feel", []), *document.get("summary", {}).get("distinctive", []), *document.get("summary", {}).get("taste", [])]
    seen = set()
    lines = []
    for claim_id in ordered:
        if claim_id in seen or claim_id not in by_id:
            continue
        seen.add(claim_id)
        claim = by_id[claim_id]
        lines.append({"id": claim_id, "support": claim["support"], "confidence": claim["confidence"], "text": render_claim(claim, locale)})
        if len(lines) >= limit:
            break
    return lines
