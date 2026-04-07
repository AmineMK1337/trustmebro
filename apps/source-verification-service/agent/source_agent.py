"""
agent/source_agent.py
=====================
SourceAgent — Upgraded Main Orchestration Class
------------------------------------------------
Original: parallel 3-layer execution with static weights.
Upgrade:  optional bandit-driven layer selection (Phase 1).

Backwards compatible — existing code using SourceAgent.run() is unchanged.
Pass `use_bandit=True` to enable adaptive layer selection.

Usage (original):
    agent = SourceAgent(api_key="KEY")
    result = agent.run(url=..., text=..., metadata=...)

Usage (adaptive / Phase 1):
    agent = SourceAgent(api_key="KEY", use_bandit=True)
    result = agent.run(url=..., text=..., metadata=..., ground_truth="High")

For the full Phase 2 ReAct loop, use AdaptiveAgent (react_agent.py).
"""

import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from tools.domain_analyzer   import analyze_domain
from tools.text_analyzer     import analyze_text
from tools.behavior_analyzer import analyze_behavior
from config.settings         import WEIGHTS
from utils.helpers           import clamp, score_to_risk, format_summary, weighted_average


class SourceAgent:
    """
    Hybrid, 3-layer Source Credibility Agent.

    Modes
    ------
    Static (default): run all available layers with fixed WEIGHTS.
    Adaptive:         use ContextualBanditPolicy to select layers dynamically.

    Parameters
    ----------
    api_key     : Gemini API key for Layer 2.
    weights     : Override default layer weights (ignored in bandit mode).
    verbose     : Print formatted summary after each run.
    use_bandit  : Enable Phase 1 bandit-driven layer selection.
    bandit_path : Path to persist bandit weights across restarts.
    """

    def __init__(
        self,
        api_key:     str | None = None,
        weights:     dict | None = None,
        verbose:     bool = True,
        use_bandit:  bool = False,
        bandit_path: str | None = None,
    ):
        self.api_key    = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.weights    = weights or WEIGHTS
        self.verbose    = verbose
        self.use_bandit = use_bandit

        if not use_bandit:
            total = sum(self.weights.values())
            if not (0.99 <= total <= 1.01):
                raise ValueError(
                    f"Layer weights must sum to 1.0, got {total:.3f}."
                )

        self._policy = None
        if use_bandit:
            from agent.bandit_policy import ContextualBanditPolicy
            self._policy = ContextualBanditPolicy(persist_path=bandit_path)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def run(
        self,
        url:          str | None = None,
        text:         str | None = None,
        metadata:     dict | None = None,
        ground_truth: str | None = None,
    ) -> dict:
        """
        Run the credibility evaluation pipeline.

        In static mode: runs all available layers with fixed weights.
        In bandit mode: bandit selects which layers to run, then learns.
        """
        if self.use_bandit and self._policy:
            return self._run_bandit(url, text, metadata, ground_truth)
        else:
            return self._run_static(url, text, metadata)

    # -------------------------------------------------------------------------
    # Static execution (original behaviour — unchanged)
    # -------------------------------------------------------------------------

    def _run_static(self, url, text, metadata):
        all_reasons  = []
        layer_scores = {"domain": -1, "content": -1, "behavior": -1}

        if url:
            r = analyze_domain(url)
            layer_scores["domain"] = r["score"]
            _label_reasons(all_reasons, r["reasons"], "🌐 Domain")
        else:
            all_reasons.append("🌐 Domain: No URL provided — layer skipped.")

        if text:
            r = analyze_text(text, api_key=self.api_key)
            layer_scores["content"] = r["score"]
            src = "Gemini LLM" if r.get("llm_used") else "Rule-based"
            _label_reasons(all_reasons, r["reasons"], f"📄 Content ({src})")
        else:
            all_reasons.append("📄 Content: No text provided — layer skipped.")

        if metadata:
            r = analyze_behavior(metadata)
            layer_scores["behavior"] = r["score"]
            _label_reasons(all_reasons, r["reasons"], "👤 Behavior")
        else:
            all_reasons.append("👤 Behavior: No metadata provided — layer skipped.")

        active      = {k: v for k, v in layer_scores.items() if v != -1}
        final_score = weighted_average(active, self.weights)
        risk        = score_to_risk(final_score)

        result = {
            "score":   final_score,
            "risk":    risk,
            "reasons": all_reasons,
            "details": {
                "domain_score":   layer_scores["domain"]   if layer_scores["domain"]   != -1 else "N/A",
                "content_score":  layer_scores["content"]  if layer_scores["content"]  != -1 else "N/A",
                "behavior_score": layer_scores["behavior"] if layer_scores["behavior"] != -1 else "N/A",
            },
            "bandit": None,
        }

        if self.verbose:
            print(format_summary(result))
        return result

    # -------------------------------------------------------------------------
    # Bandit-driven execution (Phase 1)
    # -------------------------------------------------------------------------

    def _run_bandit(self, url, text, metadata, ground_truth):
        from agent.bandit_policy import build_state
        from agent.reward        import reward_breakdown, simulate_ground_truth

        t0    = time.time()
        state = build_state(url=url, text=text, metadata=metadata)
        action = self._policy.select_action(state)
        target_layers = action["layers"]

        all_reasons  = []
        layer_scores = {"domain": -1, "content": -1, "behavior": -1}

        if "domain" in target_layers and url:
            r = analyze_domain(url)
            layer_scores["domain"] = r["score"]
            _label_reasons(all_reasons, r["reasons"], "🌐 Domain")

        if "content" in target_layers and text:
            r = analyze_text(text, api_key=self.api_key)
            layer_scores["content"] = r["score"]
            src = "Gemini LLM" if r.get("llm_used") else "Rule-based"
            _label_reasons(all_reasons, r["reasons"], f"📄 Content ({src})")

        if "behavior" in target_layers and metadata:
            r = analyze_behavior(metadata)
            layer_scores["behavior"] = r["score"]
            _label_reasons(all_reasons, r["reasons"], "👤 Behavior")

        active      = {k: v for k, v in layer_scores.items() if v != -1}
        final_score = weighted_average(active, WEIGHTS) if active else 50
        risk        = score_to_risk(final_score)

        gt = ground_truth or simulate_ground_truth(final_score)
        rb = reward_breakdown(
            prediction=risk,
            ground_truth=gt,
            action=action,
            cost_info={
                "llm_used":   "content" in target_layers,
                "n_layers":   len(target_layers),
                "latency_ms": int((time.time() - t0) * 1000),
            },
        )
        self._policy.update(state, action, rb["total"])

        result = {
            "score":   final_score,
            "risk":    risk,
            "reasons": all_reasons,
            "details": {
                "domain_score":   layer_scores["domain"]   if layer_scores["domain"]   != -1 else "N/A",
                "content_score":  layer_scores["content"]  if layer_scores["content"]  != -1 else "N/A",
                "behavior_score": layer_scores["behavior"] if layer_scores["behavior"] != -1 else "N/A",
            },
            "bandit": {
                "action":        action["label"],
                "layers":        action["layers"],
                "reward":        rb["total"],
                "reward_detail": rb,
            },
        }

        if self.verbose:
            print(format_summary(result))
            print(f"  🎰 Bandit: action='{action['label']}'  reward={rb['total']:+.3f}")

        return result

    # -------------------------------------------------------------------------
    # Convenience methods
    # -------------------------------------------------------------------------

    def check_domain(self, url: str) -> dict:
        return analyze_domain(url)

    def check_text(self, text: str) -> dict:
        return analyze_text(text, api_key=self.api_key)

    def check_behavior(self, metadata: dict) -> dict:
        return analyze_behavior(metadata)

    def bandit_stats(self) -> dict | None:
        return self._policy.stats() if self._policy else None

    def __repr__(self) -> str:
        mode = "adaptive/bandit" if self.use_bandit else "static"
        return (
            f"SourceAgent(mode={mode}, "
            f"gemini={'yes' if self.api_key else 'no'}, "
            f"verbose={self.verbose})"
        )


def _label_reasons(target: list, reasons: list[str], label: str) -> None:
    for r in reasons:
        target.append(f"[{label}] {r}")
