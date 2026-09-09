"""Translate existing talk.profile() evidence into explicit taste claims."""
from __future__ import annotations

FAILED_EXPERIMENT_PREFIXES = ("motion_scene_",)


def _feature_map(report):
    return {row["id"]: row for row in report.get("features", [])}


def _distinctive(row):
    return abs(float(row.get("z", 0))) >= 0.75 or row.get("percentile", 50) >= 80 or row.get("percentile", 50) <= 20


def _confidence(n):
    return "medium" if n >= 6 else "low"


def _feature_evidence(row):
    return {
        "kind": "feature", "feature_id": row["id"], "label": row["labels"],
        "value": row["value"], "z": row["z"],
        "reference_percentile": row["percentile"], "reference_median": row["reference_median"],
    }


def build_taste_claims(report, taste_profile, *, target_features=None):
    if not taste_profile:
        return []
    target_features = target_features or {}
    n_videos = int(taste_profile.get("n_videos") or 0)
    fmap = _feature_map(report)
    claims = []
    for item in taste_profile.get("numeric") or []:
        col = str(item.get("col") or "")
        if not col or col.startswith(FAILED_EXPERIMENT_PREFIXES):
            continue
        target = fmap.get(col)
        if not target:
            continue
        verdict = item.get("verdict")
        profile_evidence = {
            "kind": "taste_profile", "feature_id": col, "n_favorites": n_videos,
            "profile_verdict": verdict, "favorite_median": item.get("median"),
            "favorite_median_percentile": item.get("median_pct"),
            "favorite_min_percentile": item.get("min_pct"),
            "favorite_max_percentile": item.get("max_pct"),
            "spread_ratio": item.get("spread_ratio"),
        }
        evidence = [_feature_evidence(target), profile_evidence]
        if verdict == "무관(편차 큼)" and _distinctive(target):
            claims.append({
                "id": f"taste:{col}:not-supported", "question": "taste", "claim_type": "not_supported",
                "subject": col, "direction": "mixed", "support": "contradicted",
                "confidence": _confidence(n_videos), "scope": "taste_profile",
                "text_key": "reason.taste.not_supported", "evidence": evidence,
            })
        elif verdict == "공통·관습":
            claims.append({
                "id": f"taste:{col}:conventional", "question": "taste",
                "claim_type": "shared_but_conventional", "subject": col, "direction": "match",
                "support": "insufficient", "confidence": _confidence(n_videos), "scope": "taste_profile",
                "text_key": "reason.taste.conventional", "evidence": evidence,
            })
        elif verdict in {"특이점·높음", "특이점·낮음", "공통"}:
            wanted = "high" if verdict == "특이점·높음" else "low" if verdict == "특이점·낮음" else "match"
            aligned = ((wanted == "high" and target["percentile"] >= 70) or
                       (wanted == "low" and target["percentile"] <= 30) or wanted == "match")
            if aligned:
                support = "supported" if n_videos >= 4 else "insufficient"
                claims.append({
                    "id": f"taste:{col}:signal", "question": "taste", "claim_type": "taste_signal",
                    "subject": col, "direction": wanted, "support": support, "confidence": _confidence(n_videos),
                    "scope": "taste_profile",
                    "text_key": "reason.taste.signal" if support == "supported" else "reason.taste.insufficient",
                    "evidence": evidence,
                })
    for item in taste_profile.get("categorical") or []:
        col = str(item.get("col") or "")
        if not col or col.startswith(FAILED_EXPERIMENT_PREFIXES):
            continue
        target_value = target_features.get(col)
        if target_value is None or str(target_value) != str(item.get("top")):
            continue
        profile_evidence = {
            "kind": "taste_profile_category", "feature_id": col, "n_favorites": n_videos,
            "profile_verdict": item.get("verdict"), "favorite_value": item.get("top"),
            "favorite_share": item.get("share"), "corpus_share": item.get("corpus_share"),
        }
        if item.get("verdict") == "취향 신호":
            support = "supported" if n_videos >= 4 else "insufficient"
            claims.append({
                "id": f"taste:{col}:signal", "question": "taste", "claim_type": "taste_signal",
                "subject": col, "direction": "match", "support": support, "confidence": _confidence(n_videos),
                "scope": "taste_profile",
                "text_key": "reason.taste.signal" if support == "supported" else "reason.taste.insufficient",
                "evidence": [profile_evidence],
            })
        elif item.get("verdict") == "관습":
            claims.append({
                "id": f"taste:{col}:conventional", "question": "taste",
                "claim_type": "shared_but_conventional", "subject": col, "direction": "match",
                "support": "insufficient", "confidence": _confidence(n_videos), "scope": "taste_profile",
                "text_key": "reason.taste.conventional", "evidence": [profile_evidence],
            })
    return claims
