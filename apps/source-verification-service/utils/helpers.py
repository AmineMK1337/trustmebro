"""
utils/helpers.py
================
Shared utility functions used across all layers of the agent.
Kept small and dependency-free for hackathon portability.
"""

from config.settings import RISK_THRESHOLDS


def clamp(value: int, min_val: int = 0, max_val: int = 100) -> int:
    """Clamp an integer to [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def score_to_risk(score: int) -> str:
    """
    Convert a numeric suspicion score (0-100) to a human-readable risk label.

    Score represents RISK / SUSPICION level:
      0-39  → Low
      40-69 → Medium
      70+   → High
    """
    if score < RISK_THRESHOLDS["low"]:
        return "Low"
    elif score < RISK_THRESHOLDS["medium"]:
        return "Medium"
    else:
        return "High"


def risk_emoji(risk: str) -> str:
    """Return a visual emoji for a given risk level."""
    return {"Low": "✅", "Medium": "⚠️", "High": "❌"}.get(risk, "❓")


def format_summary(result: dict) -> str:
    """
    Render a clean, human-readable summary of the agent's output.
    This is what gets printed to the terminal for quick inspection.
    """
    score = result["score"]
    risk  = result["risk"]
    emoji = risk_emoji(risk)
    reasons = result.get("reasons", [])
    details = result.get("details", {})

    lines = [
        "",
        "=" * 55,
        f"  {emoji}  Source Credibility: {risk.upper()} RISK ({score}/100)",
        "=" * 55,
        "",
        "  Layer Breakdown:",
        f"    • Domain Analysis   : {details.get('domain_score',  'N/A')}/100",
        f"    • Content Analysis  : {details.get('content_score', 'N/A')}/100",
        f"    • Behavior Analysis : {details.get('behavior_score','N/A')}/100",
        "",
        "  Reasons:",
    ]

    if reasons:
        for r in reasons:
            lines.append(f"    – {r}")
    else:
        lines.append("    – No specific issues detected.")

    lines += ["", "=" * 55, ""]
    return "\n".join(lines)


def weighted_average(scores: dict, weights: dict) -> int:
    """
    Compute a weighted average score given a dict of layer scores
    and a dict of weights (weights must sum to 1.0).

    Only layers that actually ran (score != -1) contribute.
    Remaining weight is redistributed proportionally.
    """
    active = {k: v for k, v in scores.items() if v != -1}
    if not active:
        return 0

    total_weight = sum(weights[k] for k in active)
    if total_weight == 0:
        return 0

    weighted_sum = sum(active[k] * weights[k] for k in active)
    raw = weighted_sum / total_weight
    return clamp(int(round(raw)))
