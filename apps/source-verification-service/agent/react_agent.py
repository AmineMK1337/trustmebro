"""
agent/react_agent.py
====================
PHASE 2 — Adaptive Reasoning Agent (ReAct-style)
-------------------------------------------------
Transforms the original parallel execution model into a sequential,
self-directed reasoning loop that mirrors how a human analyst works:

    1. Look at the domain → form initial hypothesis
    2. Decide: is this already clear enough? Or do I need to read the text?
    3. Read the text → update hypothesis
    4. Decide: still uncertain? Do I need to check the author's behaviour?
    5. Make final call.

This "Reason → Act → Observe → Reason..." loop (ReAct) is more efficient
than running all three layers every time:
  • Easy cases (obvious spam or obvious Reuters) resolve in 1 step.
  • Hard cases (borderline tabloid) use all 3 layers.

The stopping policy is driven by the same ContextualBanditPolicy from
Phase 1 — every "should I continue?" decision is a bandit action,
so the agent keeps learning which signals warrant deeper investigation.

─────────────────────────────────────────────────────────────────────────
Architecture for future RL upgrade (BONUS)
─────────────────────────────────────────────────────────────────────────
The loop structure is intentionally PPO-compatible:
  • state   → observation vector (matches gym.Env.observation_space)
  • action  → discrete choice from {run_domain, run_content,
                                     run_behavior, stop_and_decide}
  • reward  → from reward.py
  • done    → bool (episode end)

To upgrade to PPO, replace _step_policy() with a neural policy network
and wrap AdaptiveAgent in a gym.Env subclass. The rest of the code
is unchanged.
─────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

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
from agent.bandit_policy     import ContextualBanditPolicy, build_state, ACTIONS
from agent.reward            import compute_reward, reward_breakdown, simulate_ground_truth
from utils.helpers           import clamp, score_to_risk, weighted_average
from config.settings         import WEIGHTS

# ─────────────────────────────────────────────────────────────────────────────
# ReAct action constants
# ─────────────────────────────────────────────────────────────────────────────

ACT_DOMAIN   = "run_domain"
ACT_CONTENT  = "run_content"
ACT_BEHAVIOR = "run_behavior"
ACT_STOP     = "stop_and_decide"

# Confidence thresholds for early stopping without bandit (rule-based gate)
STOP_HIGH_CONFIDENCE = 82   # score this high → clearly High Risk, stop
STOP_LOW_CONFIDENCE  = 12   # score this low  → clearly Low Risk, stop

MAX_STEPS = 4               # safety cap to prevent infinite loops


# ─────────────────────────────────────────────────────────────────────────────
# Episode state (tracks a single evaluation run)
# ─────────────────────────────────────────────────────────────────────────────

class EpisodeState:
    """
    Mutable state for one evaluation episode.

    Attributes
    ──────────
    layers_done       : set of layer names already executed
    layer_scores      : scores from completed layers {name: int}
    layer_reasons     : reasons from completed layers {name: [str]}
    uncertainty       : estimated uncertainty (0-1), high early, drops as layers run
    current_score     : running weighted score estimate
    steps             : number of ReAct steps taken
    reasoning_trace   : full human-readable log of each step
    """

    def __init__(self):
        self.layers_done:    set[str]         = set()
        self.layer_scores:   dict[str, int]   = {}
        self.layer_reasons:  dict[str, list]  = {}
        self.current_score:  int              = 50    # prior: medium suspicion
        self.uncertainty:    float            = 1.0   # starts fully uncertain
        self.steps:          int              = 0
        self.reasoning_trace: list[dict]      = []
        self._start_time:    float            = time.time()

    def add_layer_result(self, layer: str, score: int, reasons: list[str]) -> None:
        """Incorporate a new layer result and update running estimates."""
        self.layers_done.add(layer)
        self.layer_scores[layer]  = score
        self.layer_reasons[layer] = reasons

        # Recompute running score using static weights
        active = {k: v for k, v in self.layer_scores.items() if k in WEIGHTS}
        if active:
            self.current_score = weighted_average(active, WEIGHTS)

        # Uncertainty drops as we run more layers
        # Formula: starts at 1.0, each layer reduces it by ~0.3
        n = len(self.layers_done)
        self.uncertainty = max(1.0 - n * 0.32, 0.04)

    def log_step(
        self,
        step_num:   int,
        action:     str,
        observation: str,
        score_now:  int,
        reasoning:  str,
    ) -> None:
        """Append a reasoning step to the trace."""
        self.reasoning_trace.append({
            "step":        step_num,
            "action":      action,
            "observation": observation,
            "score":       score_now,
            "uncertainty": round(self.uncertainty, 3),
            "reasoning":   reasoning,
        })

    def to_bandit_state(
        self,
        url: str | None,
        text: str | None,
        metadata: dict | None,
    ) -> dict:
        """
        Build the bandit state vector from the current episode context.
        Includes live uncertainty and current score as extra signals.
        """
        state = build_state(url=url, text=text, metadata=metadata)
        # Inject dynamic features into the vector (overwrite last 2 slots)
        # vector[6] = metadata_quality, vector[7] = bias — keep those
        # We encode uncertainty into the domain_prescore slot if domain is done
        if "domain" in self.layers_done:
            state["vector"][4] = self.layer_scores["domain"] / 100.0
        state["uncertainty"] = self.uncertainty
        return state

    def elapsed_ms(self) -> int:
        return int((time.time() - self._start_time) * 1000)


# ─────────────────────────────────────────────────────────────────────────────
# AdaptiveAgent — the main public class
# ─────────────────────────────────────────────────────────────────────────────

class AdaptiveAgent:
    """
    ReAct-style adaptive credibility agent with contextual bandit learning.

    At each step the agent:
      1. THINKS — reasons about current certainty
      2. ACTS   — picks next layer to run OR stops
      3. OBSERVES — records the result
      4. UPDATES — feeds reward back to the bandit

    Parameters
    ──────────
    api_key       : Gemini API key for LLM-based content analysis.
    policy        : ContextualBanditPolicy instance. A fresh one is created
                    if not provided (useful for standalone use).
    verbose       : Print the ReAct trace after each evaluation.
    learn         : If True, the bandit updates after each evaluation.
                    Set False during pure inference / deployment.
    bandit_path   : Path to persist/restore the bandit's learned weights.
    max_steps     : Safety cap on the reasoning loop (default: 4).
    """

    def __init__(
        self,
        api_key:     str | None = None,
        policy:      ContextualBanditPolicy | None = None,
        verbose:     bool = True,
        learn:       bool = True,
        bandit_path: str | None = None,
        max_steps:   int = MAX_STEPS,
    ):
        self.api_key   = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.policy    = policy or ContextualBanditPolicy(
            alpha=0.5,
            persist_path=bandit_path,
        )
        self.verbose   = verbose
        self.learn     = learn
        self.max_steps = max_steps

        # Full history of all evaluations (for audit / training replay)
        self.eval_history: list[dict] = []

    # ─────────────────────────────────────────────────
    # Primary public method
    # ─────────────────────────────────────────────────

    def evaluate(
        self,
        url:          str | None = None,
        text:         str | None = None,
        metadata:     dict | None = None,
        ground_truth: str | None = None,  # "Low"/"Medium"/"High" if known
    ) -> dict:
        """
        Run a full adaptive evaluation episode.

        The agent sequentially selects and executes analysis layers,
        stopping when confident or when the step budget is exhausted.

        Args:
            url          : URL/domain to analyse.
            text         : Article/post body.
            metadata     : Author/account metadata dict.
            ground_truth : True risk label (enables bandit learning if known).
                           If None, the agent will simulate it from its own score.

        Returns:
            {
                "score":      int,
                "risk":       str,
                "reasons":    [str],
                "details":    dict,
                "trace":      [dict],        ← full ReAct reasoning steps
                "bandit_action": dict,       ← action selected by bandit
                "reward":     float | None,  ← reward (None if no ground truth)
                "steps_used": int,
                "elapsed_ms": int,
            }
        """

        episode = EpisodeState()

        # ── Build initial bandit state ────────────────────────────────────
        state = build_state(url=url, text=text, metadata=metadata)

        # ── Phase 1: Bandit selects which layer COMBINATION to target ─────
        # The bandit tells us the ideal set of layers for this input type.
        # Phase 2 then executes them sequentially (ReAct loop), stopping
        # early if confidence is reached before all selected layers run.
        bandit_action = self.policy.select_action(state)
        target_layers  = bandit_action["layers"]

        if self.verbose:
            self._print_header(bandit_action, url, text, metadata)

        # ── Phase 2: ReAct sequential execution loop ──────────────────────
        layer_queue = _build_queue(target_layers)  # ordered: domain → content → behavior

        for step_num in range(1, self.max_steps + 1):
            episode.steps = step_num

            if not layer_queue:
                # All selected layers done → stop
                self._log_step(episode, step_num, ACT_STOP, "All targeted layers completed.")
                break

            next_layer = layer_queue.pop(0)

            # ── THINK: should we stop early? ──────────────────────────────
            if _should_stop_early(episode, next_layer):
                reasoning = (
                    f"Score is {episode.current_score} with uncertainty "
                    f"{episode.uncertainty:.2f} — confidence is sufficient to decide."
                )
                self._log_step(episode, step_num, ACT_STOP, reasoning)
                if self.verbose:
                    _print_step(step_num, ACT_STOP, reasoning, episode.current_score)
                break

            # ── ACT: execute the selected layer ───────────────────────────
            act_name, result = self._execute_layer(next_layer, url, text, metadata)
            score   = result["score"]
            reasons = result["reasons"]

            episode.add_layer_result(next_layer, score, reasons)

            # ── OBSERVE: form reasoning about what we found ───────────────
            observation = _build_observation(next_layer, score, reasons)
            reasoning   = _build_reasoning(episode, next_layer, score)

            self._log_step(episode, step_num, act_name, reasoning, observation, score)

            if self.verbose:
                _print_step(step_num, act_name, reasoning, episode.current_score)

            # Check: did running this layer push us to a decision boundary?
            if _is_confident(episode) and not layer_queue:
                break

        # ── Finalise decision ─────────────────────────────────────────────
        final_score = episode.current_score
        risk        = score_to_risk(final_score)
        all_reasons = _aggregate_reasons(episode)

        result_dict = {
            "score":         final_score,
            "risk":          risk,
            "reasons":       all_reasons,
            "details": {
                "domain_score":   episode.layer_scores.get("domain",   "N/A"),
                "content_score":  episode.layer_scores.get("content",  "N/A"),
                "behavior_score": episode.layer_scores.get("behavior", "N/A"),
            },
            "trace":          episode.reasoning_trace,
            "bandit_action":  bandit_action,
            "steps_used":     episode.steps,
            "elapsed_ms":     episode.elapsed_ms(),
            "reward":         None,
        }

        # ── Phase 1: Compute reward and update bandit ─────────────────────
        if self.learn:
            # Use provided ground truth, or simulate from the score
            gt = ground_truth or simulate_ground_truth(final_score)
            rb = reward_breakdown(
                prediction=risk,
                ground_truth=gt,
                action=bandit_action,
                cost_info={
                    "llm_used":   "content" in episode.layers_done,
                    "n_layers":   len(episode.layers_done),
                    "latency_ms": episode.elapsed_ms(),
                },
            )
            result_dict["reward"]       = rb["total"]
            result_dict["reward_detail"] = rb

            updated_state = episode.to_bandit_state(url, text, metadata)
            self.policy.update(updated_state, bandit_action, rb["total"])

        # ── Print summary ─────────────────────────────────────────────────
        if self.verbose:
            self._print_summary(result_dict)

        self.eval_history.append(result_dict)
        return result_dict

    # ─────────────────────────────────────────────────
    # Batch evaluation
    # ─────────────────────────────────────────────────

    def evaluate_batch(self, inputs: list[dict]) -> list[dict]:
        """
        Evaluate a list of inputs. Each input is a dict with optional keys:
            url, text, metadata, ground_truth

        The bandit learns from each example in sequence.
        """
        return [self.evaluate(**inp) for inp in inputs]

    # ─────────────────────────────────────────────────
    # Monitoring
    # ─────────────────────────────────────────────────

    def bandit_stats(self) -> dict:
        """Return learning statistics from the bandit policy."""
        return self.policy.stats()

    def print_trace(self, result: dict) -> None:
        """Pretty-print the ReAct reasoning trace from a result dict."""
        print("\n  📋 REASONING TRACE")
        print("  " + "─" * 50)
        for step in result.get("trace", []):
            print(f"  Step {step['step']}: [{step['action']}]")
            print(f"    Score: {step['score']} | Uncertainty: {step['uncertainty']}")
            print(f"    Reasoning: {step['reasoning']}")
            if step.get("observation"):
                print(f"    Observation: {step['observation'][:100]}...")
            print()

    # ─────────────────────────────────────────────────
    # Internal — layer execution
    # ─────────────────────────────────────────────────

    def _execute_layer(
        self,
        layer:    str,
        url:      str | None,
        text:     str | None,
        metadata: dict | None,
    ) -> tuple[str, dict]:
        """
        Dispatch to the correct analysis function.
        Returns (act_name, result_dict).
        """
        if layer == "domain":
            if not url:
                return ACT_DOMAIN, {"score": 0, "reasons": ["No URL provided."]}
            return ACT_DOMAIN, analyze_domain(url)

        elif layer == "content":
            if not text:
                return ACT_CONTENT, {"score": 0, "reasons": ["No text provided."]}
            return ACT_CONTENT, analyze_text(text, api_key=self.api_key)

        elif layer == "behavior":
            if not metadata:
                return ACT_BEHAVIOR, {"score": 0, "reasons": ["No metadata provided."]}
            return ACT_BEHAVIOR, analyze_behavior(metadata)

        return ACT_STOP, {"score": 0, "reasons": ["Unknown layer."]}

    # ─────────────────────────────────────────────────
    # Internal — logging helpers
    # ─────────────────────────────────────────────────

    def _log_step(
        self,
        episode:     EpisodeState,
        step_num:    int,
        action:      str,
        reasoning:   str,
        observation: str = "",
        score:       int = -1,
    ) -> None:
        episode.log_step(
            step_num=step_num,
            action=action,
            observation=observation,
            score_now=score if score >= 0 else episode.current_score,
            reasoning=reasoning,
        )

    def _print_header(
        self,
        action:   dict,
        url:      str | None,
        text:     str | None,
        metadata: dict | None,
    ) -> None:
        has = ", ".join(filter(None, [
            "url" if url else "",
            "text" if text else "",
            "metadata" if metadata else "",
        ]))
        print(f"\n{'═' * 58}")
        print(f"  🤖  AdaptiveAgent — ReAct Evaluation")
        print(f"  Inputs: {has}")
        print(f"  Bandit action: {action['label']}")
        print(f"{'═' * 58}")

    def _print_summary(self, result: dict) -> None:
        score  = result["score"]
        risk   = result["risk"]
        icon   = {"Low": "✅", "Medium": "⚠️", "High": "❌"}.get(risk, "?")
        reward = result.get("reward")
        rb     = result.get("reward_detail", {})

        print(f"\n{'─' * 58}")
        print(f"  {icon}  VERDICT: {risk.upper()} RISK  ({score}/100)")
        print(f"  Steps used : {result['steps_used']}")
        print(f"  Layers run : {list(result['details'].keys())}")
        print(f"  Elapsed    : {result['elapsed_ms']} ms")
        if reward is not None:
            print(f"  Reward     : {reward:+.3f}  ({rb.get('label','')})")
        print(f"{'─' * 58}")


# ─────────────────────────────────────────────────────────────────────────────
# Internal — ReAct logic helpers (pure functions — easy to test in isolation)
# ─────────────────────────────────────────────────────────────────────────────

def _build_queue(target_layers: list[str]) -> list[str]:
    """
    Return layers in execution priority order:
    domain first (fast, free) → behavior → content (slowest / most expensive).

    Running domain first gives a fast pre-signal; if it's clearly bad,
    the stop-early logic kicks in before we spend on LLM.
    """
    priority = {"domain": 0, "behavior": 1, "content": 2}
    return sorted(target_layers, key=lambda l: priority.get(l, 99))


def _should_stop_early(episode: EpisodeState, next_layer: str) -> bool:
    """
    Rule-based early stopping gate.

    Stop if:
    a) Score is already extremely high (clearly High Risk) and we haven't
       started content analysis — no need to confirm with LLM.
    b) Score is already extremely low (clearly Low Risk) after domain check.
    c) Only 1 layer has run but uncertainty is very low (shouldn't happen,
       but included as a safety net).

    Note: the bandit already decided the target layers; this is just a
    confidence gate that can override its plan if evidence is overwhelming.
    """
    if not episode.layers_done:
        return False   # Haven't run anything yet — never stop before first layer

    # Only apply fast-exit after at least one layer
    if episode.current_score >= STOP_HIGH_CONFIDENCE:
        return True    # Already very suspicious — don't need more evidence

    if episode.current_score <= STOP_LOW_CONFIDENCE:
        return True    # Already very clean — save LLM cost

    return False


def _is_confident(episode: EpisodeState) -> bool:
    """Return True if the agent has high enough confidence to stop."""
    return episode.uncertainty < 0.1 or (
        episode.current_score >= STOP_HIGH_CONFIDENCE or
        episode.current_score <= STOP_LOW_CONFIDENCE
    )


def _build_observation(layer: str, score: int, reasons: list[str]) -> str:
    """Build a one-line observation summary from a layer result."""
    top_reason = reasons[0] if reasons else "No notable findings."
    return f"{layer.capitalize()} layer: score={score}. {top_reason}"


def _build_reasoning(episode: EpisodeState, layer: str, score: int) -> str:
    """
    Generate a human-readable reasoning statement for the current step.
    This is the 'Thought' part of Thought → Action → Observation.
    """
    n_done = len(episode.layers_done)
    current = episode.current_score
    unc = episode.uncertainty

    if n_done == 1:
        direction = "suspicious" if score > 50 else "credible"
        return (
            f"First signal ({layer}) shows {direction} patterns (score={score}). "
            f"Uncertainty is high ({unc:.2f}) — continuing analysis."
        )
    elif n_done == 2:
        change = abs(current - score)
        if change > 20:
            return (
                f"{layer.capitalize()} analysis shifted the score significantly "
                f"(Δ={change}). Updating estimate to {current}."
            )
        else:
            return (
                f"{layer.capitalize()} analysis corroborates earlier finding. "
                f"Score stable at ~{current}."
            )
    else:
        return (
            f"All selected layers executed. Final score: {current}. "
            f"Uncertainty reduced to {unc:.2f}."
        )


def _aggregate_reasons(episode: EpisodeState) -> list[str]:
    """Flatten all layer reasons into a single labelled list."""
    icons = {"domain": "🌐 Domain", "content": "📄 Content", "behavior": "👤 Behavior"}
    result = []
    for layer in ["domain", "content", "behavior"]:
        if layer in episode.layer_reasons:
            for r in episode.layer_reasons[layer]:
                result.append(f"[{icons[layer]}] {r}")
    return result


def _print_step(step: int, action: str, reasoning: str, score: int) -> None:
    """Print one ReAct step in a clean format."""
    print(f"\n  Step {step} › {action}")
    print(f"    💭 {reasoning}")
    print(f"    📊 Running score: {score}/100")


# ─────────────────────────────────────────────────────────────────────────────
# Bonus: gym.Env-compatible wrapper stub (PPO upgrade path)
# ─────────────────────────────────────────────────────────────────────────────

class CredibilityEnv:
    """
    Gym-compatible environment wrapper for PPO/DQN upgrades.

    To upgrade from bandit to PPO:
        1. Replace ContextualBanditPolicy with a neural policy network
           (e.g. stable-baselines3 PPO)
        2. Wrap AdaptiveAgent in this class
        3. Use standard RL training loop: collect → compute advantage → update

    This stub documents the interface without adding a gym dependency.
    """

    def __init__(self, agent: AdaptiveAgent, dataset: list[dict]):
        """
        Args:
            agent   : AdaptiveAgent instance.
            dataset : List of {url, text, metadata, ground_truth} dicts.
        """
        self.agent   = agent
        self.dataset = dataset
        self._idx    = 0

    def reset(self) -> list[float]:
        """Start a new episode. Returns initial observation vector."""
        inp = self.dataset[self._idx % len(self.dataset)]
        self._current = inp
        from agent.bandit_policy import build_state
        state = build_state(
            url=inp.get("url"),
            text=inp.get("text"),
            metadata=inp.get("metadata"),
        )
        return state["vector"]

    def step(self, action_id: int) -> tuple[list[float], float, bool, dict]:
        """
        Execute one action.

        Returns:
            (next_observation, reward, done, info)
        """
        from agent.bandit_policy import ACTIONS, build_state
        from agent.reward import compute_reward

        action = ACTIONS[action_id]
        result = self.agent.evaluate(
            url=self._current.get("url"),
            text=self._current.get("text"),
            metadata=self._current.get("metadata"),
            ground_truth=self._current.get("ground_truth"),
        )
        reward = result.get("reward", 0.0)
        self._idx += 1
        done = True   # one episode per article (episodic)
        state = build_state(
            url=self._current.get("url"),
            text=self._current.get("text"),
            metadata=self._current.get("metadata"),
        )
        return state["vector"], reward, done, result
