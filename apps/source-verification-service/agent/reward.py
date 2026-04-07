"""
agent/reward.py
===============
PHASE 1 — Reward Function
--------------------------
Translates evaluation outcomes into a scalar reward signal that guides
the contextual bandit's learning.

Design Philosophy
─────────────────
The reward function must balance THREE competing objectives:

  1. ACCURACY   — did we correctly classify the source's risk level?
  2. COST       — did we avoid expensive LLM API calls when unnecessary?
  3. EFFICIENCY — did we run only the layers we actually needed?

This mirrors real-world trade-offs: a news verification system that
calls Gemini on every single article is expensive and slow; one that
never uses LLM analysis misses nuanced manipulation signals.

Reward Structure
────────────────
  Base accuracy reward:
    +1.00  exact risk-level match (Low/Medium/High)
    +0.40  adjacent match (predicted Medium, truth was Low or High)
    -1.00  wrong direction (predicted Low, truth was High, or vice versa)

  Cost penalties (subtracted):
    -0.25  if content layer (LLM) was called   → API cost
    -0.08  per additional layer beyond the first → latency cost

  Efficiency bonus:
    +0.15  if used fewer than 3 layers AND got the right answer
           (encourages the bandit to find minimal sufficient layer sets)

  Range: approximately [-1.33, +1.15]
  The bandit learns to maximise expected reward across many evaluations.

Ground Truth
────────────
In production, ground truth comes from:
  • Human fact-checker labels
  • Later correction flags from downstream systems
  • Aggregated community signals
  • Cross-validation against known misinformation databases

For hackathon / simulation, pass the ground_truth parameter directly.
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# Reward constants (configurable for ablation studies)
# ─────────────────────────────────────────────────────────────────────────────

REWARD_EXACT_MATCH      = +1.00   # predicted risk == true risk
REWARD_ADJACENT_MATCH   = +0.40   # off by one level (Medium↔Low or Medium↔High)
REWARD_WRONG_DIRECTION  = -1.00   # Low↔High mismatch (worst case)

COST_CONTENT_LAYER      = -0.25   # Gemini API call penalty
COST_EXTRA_LAYER        = -0.08   # per layer beyond the first
BONUS_MINIMAL_CORRECT   = +0.15   # used ≤2 layers and still got it right

# Risk levels as an ordered scale (used to compute adjacency)
_RISK_ORDER = {"Low": 0, "Medium": 1, "High": 2}


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def compute_reward(
    prediction:   str,
    ground_truth: str,
    action:       dict,
    cost_info:    dict | None = None,
) -> float:
    """
    Compute the scalar reward for one evaluation step.

    Args:
        prediction   : Risk level predicted by the agent ("Low"/"Medium"/"High").
        ground_truth : True risk level (from human label or simulation).
        action       : The action dict chosen by the bandit
                       e.g. {"id": 6, "layers": ["domain","content","behavior"], ...}
        cost_info    : Optional dict with runtime cost details:
                       {
                           "llm_used":    bool,   # was Gemini called?
                           "latency_ms":  float,  # total wall time
                           "n_layers":    int,     # layers actually executed
                       }

    Returns:
        float: scalar reward signal.

    Side Effects:
        None — this is a pure function.
    """
    # ── 1. Accuracy component ─────────────────────────────────────────────
    accuracy_reward = _accuracy_reward(prediction, ground_truth)

    # ── 2. Cost component ─────────────────────────────────────────────────
    layers   = action.get("layers", [])
    n_layers = len(layers)

    cost = 0.0
    # Penalise LLM usage (expensive API call)
    used_llm = (cost_info or {}).get("llm_used", "content" in layers)
    if used_llm:
        cost += COST_CONTENT_LAYER

    # Penalise each layer beyond the first (latency)
    extra_layers = max(n_layers - 1, 0)
    cost += extra_layers * COST_EXTRA_LAYER

    # ── 3. Efficiency bonus ───────────────────────────────────────────────
    efficiency_bonus = 0.0
    correct = (prediction == ground_truth)
    if correct and n_layers <= 2:
        efficiency_bonus = BONUS_MINIMAL_CORRECT

    # ── 4. Combine ────────────────────────────────────────────────────────
    total = accuracy_reward + cost + efficiency_bonus

    return round(total, 4)


def compute_reward_batch(evaluations: list[dict]) -> list[float]:
    """
    Compute rewards for a batch of evaluations.

    Each evaluation dict must contain:
        prediction, ground_truth, action
    Optionally: cost_info

    Returns: list of scalar rewards (same order as input).
    """
    return [
        compute_reward(
            prediction=e["prediction"],
            ground_truth=e["ground_truth"],
            action=e["action"],
            cost_info=e.get("cost_info"),
        )
        for e in evaluations
    ]


def reward_breakdown(
    prediction:   str,
    ground_truth: str,
    action:       dict,
    cost_info:    dict | None = None,
) -> dict:
    """
    Return a detailed breakdown of the reward components.
    Useful for debugging and logging.

    Returns:
        {
            "total":            float,
            "accuracy":         float,
            "cost":             float,
            "efficiency_bonus": float,
            "label":            str,      # human description
        }
    """
    layers   = action.get("layers", [])
    n_layers = len(layers)

    accuracy = _accuracy_reward(prediction, ground_truth)

    used_llm = (cost_info or {}).get("llm_used", "content" in layers)
    cost  = (COST_CONTENT_LAYER if used_llm else 0.0)
    cost += max(n_layers - 1, 0) * COST_EXTRA_LAYER

    correct = (prediction == ground_truth)
    eff     = BONUS_MINIMAL_CORRECT if (correct and n_layers <= 2) else 0.0

    total = accuracy + cost + eff

    # Human-readable label
    match_type = _match_type(prediction, ground_truth)
    label = (
        f"{match_type} | layers={','.join(layers)} | "
        f"llm={'yes' if used_llm else 'no'} | "
        f"reward={total:+.3f}"
    )

    return {
        "total":            round(total, 4),
        "accuracy":         round(accuracy, 4),
        "cost":             round(cost, 4),
        "efficiency_bonus": round(eff, 4),
        "label":            label,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _accuracy_reward(prediction: str, ground_truth: str) -> float:
    """Map accuracy type to reward value."""
    mt = _match_type(prediction, ground_truth)
    return {
        "exact":    REWARD_EXACT_MATCH,
        "adjacent": REWARD_ADJACENT_MATCH,
        "wrong":    REWARD_WRONG_DIRECTION,
    }[mt]


def _match_type(prediction: str, ground_truth: str) -> str:
    """
    Classify the accuracy of a prediction:
        "exact"    — perfect match
        "adjacent" — off by one risk level
        "wrong"    — opposite ends (Low vs High)
    """
    p = _RISK_ORDER.get(prediction, 1)
    g = _RISK_ORDER.get(ground_truth, 1)
    diff = abs(p - g)
    if diff == 0:
        return "exact"
    elif diff == 1:
        return "adjacent"
    else:
        return "wrong"


# ─────────────────────────────────────────────────────────────────────────────
# Simulation helpers (for training / demo without real ground truth)
# ─────────────────────────────────────────────────────────────────────────────

def simulate_ground_truth(score: int) -> str:
    """
    Derive a simulated ground truth from a suspicion score.
    Use this in demos / unit tests when you don't have human labels.

    Mirrors the same thresholds as config/settings.RISK_THRESHOLDS.
    """
    if score < 40:
        return "Low"
    elif score < 70:
        return "Medium"
    else:
        return "High"
