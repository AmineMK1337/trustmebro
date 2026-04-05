from __future__ import annotations


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))


def _normalize_score(score: float) -> float:
    return round(_clamp(score) / 100, 2)


def _build_reasons(message: dict) -> list[str]:
    reasons: list[str] = []
    narrative = str(message.get("narrative") or "").strip()
    content_type = str(message.get("contentType") or "mixed").strip().lower()
    source = str(message.get("source") or "").strip()

    if source:
        reasons.append(f"Source `{source}` triggered asynchronous content verification.")
    if narrative:
        reasons.append("Narrative text was supplied and included in the content-risk scoring.")
    else:
        reasons.append("No narrative text was provided, so scoring relied on metadata-only heuristics.")

    if content_type in {"image", "video", "document"}:
        reasons.append(f"Content type `{content_type}` was weighted for authenticity-sensitive review.")
    else:
        reasons.append(f"Content type `{content_type}` was treated as mixed media for baseline analysis.")

    metadata = message.get("metadata")
    if isinstance(metadata, dict) and metadata:
        reasons.append("Supplemental metadata was present and increased confidence in the result.")

    return reasons


def run_verification_pipeline(message: dict) -> dict:
    narrative = str(message.get("narrative") or "").strip()
    content_type = str(message.get("contentType") or "mixed").strip().lower()
    metadata = message.get("metadata")

    tamper_score = 35 if content_type in {"image", "video", "document"} else 20
    synthetic_media_score = 30 if content_type in {"image", "video"} else 15
    narrative_consistency_score = 25 if narrative else 10
    historical_consistency_score = 20 if isinstance(metadata, dict) and metadata else 12

    weighted_score = round(
        (tamper_score * 0.35)
        + (synthetic_media_score * 0.30)
        + (narrative_consistency_score * 0.20)
        + (historical_consistency_score * 0.15),
        2,
    )

    final_trust_rating = round(1 - _normalize_score(weighted_score), 2)

    if weighted_score < 35:
        status = "verified"
    elif weighted_score < 65:
        status = "suspicious"
    else:
        status = "unverifiable"

    return {
        "submissionId": message.get("postId") or "unknown-submission",
        "source": message.get("source"),
        "status": status,
        "finalTrustRating": final_trust_rating,
        "confidenceScore": 0.72 if narrative or metadata else 0.58,
        "tamperScore": round(_normalize_score(tamper_score), 2),
        "syntheticMediaScore": round(_normalize_score(synthetic_media_score), 2),
        "narrativeConsistencyScore": round(_normalize_score(narrative_consistency_score), 2),
        "historicalConsistencyScore": round(_normalize_score(historical_consistency_score), 2),
        "reasoning": _build_reasons(message),
    }
