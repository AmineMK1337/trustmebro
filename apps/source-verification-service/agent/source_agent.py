"""
agent/source_agent.py
=====================
SourceAgent — Main Orchestration Class
---------------------------------------
Coordinates the three analysis layers, aggregates scores using configurable
weights, and produces the final structured verdict.

This class is designed to be:
  • Standalone  — call run() with any combination of url/text/metadata
  • Composable  — embed inside a larger multi-agent pipeline
  • Explainable — every score comes with traceable reasons

Usage:
    from agent.source_agent import SourceAgent

    agent = SourceAgent(api_key="YOUR_GEMINI_KEY")
    result = agent.run(
        url="http://real-official-news-alert.xyz/breaking",
        text="SHOCKING: They don't want you to know this secret...",
        metadata={"username": "user28374628", "verified": False}
    )
"""

import os
import sys

# ── Path fix so the agent works when run from any working directory ──────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.domain_analyzer import analyze_domain
from tools.text_analyzer import analyze_text
from tools.behavior_analyzer import analyze_behavior
from config.settings import WEIGHTS
from utils.helpers import clamp, score_to_risk, format_summary, weighted_average


class SourceAgent:
    """
    Hybrid, 3-layer Source Credibility Agent.

    Layers
    ──────
    1. Domain / URL Analysis    → structural and semantic URL signals
    2. Content / Text Analysis  → LLM-based (Gemini) content evaluation
    3. Behavioural Heuristics   → account/metadata pattern detection

    Each layer returns an independent score (0-100) and a list of reasons.
    The final score is a configurable weighted average of all active layers.

    Parameters
    ──────────
    api_key   : Gemini API key for Layer 2. Falls back to GEMINI_API_KEY env var.
    weights   : Override default layer weights (must be a dict with keys
                'domain', 'content', 'behavior' that sum to 1.0).
    verbose   : If True, prints the formatted summary to stdout on each run.
    """

    def __init__(
        self,
        api_key: str | None = None,
        weights: dict | None = None,
        verbose: bool = True,
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.weights = weights or WEIGHTS
        self.verbose = verbose

        # Validate weights sum to ~1.0
        total = sum(self.weights.values())
        if not (0.99 <= total <= 1.01):
            raise ValueError(
                f"Layer weights must sum to 1.0, got {total:.3f}. "
                f"Received: {self.weights}"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def run(
        self,
        url: str | None = None,
        text: str | None = None,
        metadata: dict | None = None,
    ) -> dict:
        """
        Run the full credibility evaluation pipeline.

        Args:
            url      : The URL / domain to analyse.
            text     : The article or post body to evaluate.
            metadata : Dict of account/author metadata (see behavior_analyzer).

        Returns:
            {
                "score":   int,               # 0-100 suspicion score
                "risk":    "Low"|"Medium"|"High",
                "reasons": [str],             # aggregated findings
                "details": {
                    "domain_score":   int,
                    "content_score":  int,
                    "behavior_score": int,
                }
            }
        """

        all_reasons: list[str] = []
        layer_scores = {"domain": -1, "content": -1, "behavior": -1}

        # ── Layer 1: Domain analysis ─────────────────────────────────────
        if url:
            domain_result = analyze_domain(url)
            layer_scores["domain"] = domain_result["score"]
            _label_reasons(all_reasons, domain_result["reasons"], "🌐 Domain")
        else:
            all_reasons.append("🌐 Domain: No URL provided — layer skipped.")

        # ── Layer 2: Content analysis ────────────────────────────────────
        if text:
            content_result = analyze_text(text, api_key=self.api_key)
            layer_scores["content"] = content_result["score"]
            source = "Gemini LLM" if content_result.get("llm_used") else "Rule-based"
            _label_reasons(all_reasons, content_result["reasons"], f"📄 Content ({source})")
        else:
            all_reasons.append("📄 Content: No text provided — layer skipped.")

        # ── Layer 3: Behavioural heuristics ──────────────────────────────
        if metadata:
            behavior_result = analyze_behavior(metadata)
            layer_scores["behavior"] = behavior_result["score"]
            _label_reasons(all_reasons, behavior_result["reasons"], "👤 Behavior")
        else:
            all_reasons.append("👤 Behavior: No metadata provided — layer skipped.")

        # ── Weighted final score ─────────────────────────────────────────
        active_scores = {k: v for k, v in layer_scores.items() if v != -1}
        final_score = weighted_average(active_scores, self.weights)
        risk = score_to_risk(final_score)

        result = {
            "score": final_score,
            "risk":  risk,
            "reasons": all_reasons,
            "details": {
                "domain_score":   layer_scores["domain"]   if layer_scores["domain"]   != -1 else "N/A",
                "content_score":  layer_scores["content"]  if layer_scores["content"]  != -1 else "N/A",
                "behavior_score": layer_scores["behavior"] if layer_scores["behavior"] != -1 else "N/A",
            },
        }

        if self.verbose:
            print(format_summary(result))

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Convenience: run individual layers without full pipeline
    # ─────────────────────────────────────────────────────────────────────────

    def check_domain(self, url: str) -> dict:
        """Run only Layer 1 (domain analysis)."""
        return analyze_domain(url)

    def check_text(self, text: str) -> dict:
        """Run only Layer 2 (content analysis)."""
        return analyze_text(text, api_key=self.api_key)

    def check_behavior(self, metadata: dict) -> dict:
        """Run only Layer 3 (behavioral heuristics)."""
        return analyze_behavior(metadata)

    def __repr__(self) -> str:
        return (
            f"SourceAgent(weights={self.weights}, "
            f"gemini={'configured' if self.api_key else 'not configured'}, "
            f"verbose={self.verbose})"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helper
# ─────────────────────────────────────────────────────────────────────────────

def _label_reasons(
    target: list,
    reasons: list[str],
    label: str,
) -> None:
    """Prefix each reason with a layer label and append to the target list."""
    for r in reasons:
        target.append(f"[{label}] {r}")
