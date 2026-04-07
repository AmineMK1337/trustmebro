"""
agent/bandit_policy.py
======================
PHASE 1 — Contextual Bandit Policy (LinUCB)
--------------------------------------------
Learns which combination of analysis layers to execute — and at what
weights — for each type of input, balancing accuracy vs. cost/latency.

Algorithm: LinUCB (Linear Upper Confidence Bound)
-------------------------------------------------
LinUCB is the gold standard for contextual bandits because it:
  • Handles continuous state features (unlike tabular ε-greedy)
  • Has provable regret bounds
  • Adapts naturally as the input distribution shifts
  • Is computationally lightweight (matrix ops only, no neural net)

Core idea:
  For each action a, maintain a ridge-regression model θ_a that
  predicts expected reward given context x.  Add an exploration bonus
  proportional to the uncertainty (confidence ellipsoid radius).

    score(a) = θ_a · x  +  α * sqrt(x^T A_a⁻¹ x)
               ───────────   ───────────────────────
               exploitation       exploration

Select action = argmax(score).
After observing reward r, update:
    A_a ← A_a + x·x^T
    b_a ← b_a + r·x
    θ_a ← A_a⁻¹ · b_a

Epsilon-Greedy fallback is also included for simpler use / ablation.

State vector (8 features):
    [has_url, has_text, has_metadata,
     url_length_norm, domain_prescore,
     text_length_norm, metadata_quality,
     bias_term]

Action space (7 discrete actions):
    0: ["domain"]
    1: ["content"]
    2: ["behavior"]
    3: ["domain", "content"]
    4: ["domain", "behavior"]
    5: ["content", "behavior"]
    6: ["domain", "content", "behavior"]   ← most informative, most expensive
"""

import json
import math
import os
import random
import time
from typing import Literal

# ─────────────────────────────────────────────────────────────────────────────
# Action space definition
# ─────────────────────────────────────────────────────────────────────────────

ACTIONS: list[dict] = [
    {"id": 0, "layers": ["domain"],                        "label": "domain-only"},
    {"id": 1, "layers": ["content"],                       "label": "content-only"},
    {"id": 2, "layers": ["behavior"],                      "label": "behavior-only"},
    {"id": 3, "layers": ["domain", "content"],             "label": "domain+content"},
    {"id": 4, "layers": ["domain", "behavior"],            "label": "domain+behavior"},
    {"id": 5, "layers": ["content", "behavior"],           "label": "content+behavior"},
    {"id": 6, "layers": ["domain", "content", "behavior"], "label": "all-layers"},
]

N_ACTIONS = len(ACTIONS)
N_FEATURES = 8          # dimensionality of state vector (including bias)


# ─────────────────────────────────────────────────────────────────────────────
# State featurisation
# ─────────────────────────────────────────────────────────────────────────────

def build_state(
    url: str | None = None,
    text: str | None = None,
    metadata: dict | None = None,
    domain_prescore: float = 0.0,  # fast, cheap pre-check score (0–1)
) -> dict:
    """
    Convert raw inputs into a structured state dict used by the bandit.

    The state captures what data is available and rough quality signals
    so the bandit can decide intelligently which layers are worth running.

    Args:
        url            : The URL string (if any).
        text           : Article / post body (if any).
        metadata       : Source metadata dict (if any).
        domain_prescore: A normalised 0–1 score from a fast domain check.
                         Pass 0.0 if unavailable (will be estimated from URL).

    Returns:
        dict with human-readable keys AND a 'vector' key (list[float])
        ready for the LinUCB model.
    """
    has_url      = 1.0 if url else 0.0
    has_text     = 1.0 if text else 0.0
    has_metadata = 1.0 if metadata else 0.0

    # URL length normalised to [0, 1] — very long URLs can be suspicious
    url_length_norm = min(len(url) / 200.0, 1.0) if url else 0.0

    # Text length on log scale, normalised — more text → richer signal
    text_len = len(text) if text else 0
    text_length_norm = min(math.log1p(text_len) / math.log1p(5000), 1.0)

    # Metadata quality: count of non-null, non-empty fields
    if metadata:
        filled = sum(1 for v in metadata.values() if v not in (None, "", False))
        meta_quality = min(filled / 8.0, 1.0)  # 8 known fields max
    else:
        meta_quality = 0.0

    # Domain prescore: caller can pass result of a fast regex check
    prescore = float(domain_prescore) if domain_prescore else (
        _fast_domain_prescore(url) if url else 0.0
    )

    vector = [
        has_url,
        has_text,
        has_metadata,
        url_length_norm,
        prescore,
        text_length_norm,
        meta_quality,
        1.0,            # bias term — always 1, lets model learn intercepts
    ]

    return {
        "has_url":          bool(has_url),
        "has_text":         bool(has_text),
        "has_metadata":     bool(has_metadata),
        "url_length_norm":  url_length_norm,
        "domain_prescore":  prescore,
        "text_length_norm": text_length_norm,
        "metadata_quality": meta_quality,
        "vector":           vector,
    }


def _fast_domain_prescore(url: str) -> float:
    """
    Rapid, regex-free domain suspicion pre-check (no imports from tools).
    Used when the caller hasn't already run analyze_domain.
    Returns a value in [0, 1].
    """
    url_lower = url.lower()
    score = 0.0
    if url_lower.startswith("http://"):
        score += 0.25
    suspicious_tlds = [".xyz", ".top", ".club", ".online", ".site", ".buzz", ".tk"]
    if any(url_lower.endswith(t) or (t + "/") in url_lower for t in suspicious_tlds):
        score += 0.3
    # Keyword signals
    hot_words = ["breaking", "truth", "real", "official", "secure", "alert"]
    hits = sum(w in url_lower for w in hot_words)
    score += min(hits * 0.1, 0.3)
    hyphens = url_lower.count("-")
    score += min(hyphens * 0.05, 0.15)
    return min(score, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# LinUCB model (one per action)
# ─────────────────────────────────────────────────────────────────────────────

class _LinUCBArm:
    """
    Single LinUCB arm — one per action.

    Maintains ridge-regression parameters:
        A  : d×d feature covariance matrix (identity-initialised)
        b  : d×1 reward accumulator
        theta: A⁻¹·b — the estimated reward coefficients
    """

    def __init__(self, n_features: int, alpha: float):
        self.alpha = alpha
        d = n_features
        # A starts as identity → regularises early (data-free) estimates
        self.A = [[1.0 if i == j else 0.0 for j in range(d)] for i in range(d)]
        self.b = [0.0] * d
        self._theta = [0.0] * d
        self._A_inv = self.A[:]   # will be updated lazily
        self._dirty = True        # flag: recompute A_inv before next select

    def update(self, x: list[float], reward: float) -> None:
        """Rank-1 update of A and b given observed reward."""
        d = len(x)
        # A ← A + x·x^T
        for i in range(d):
            for j in range(d):
                self.A[i][j] += x[i] * x[j]
        # b ← b + r·x
        for i in range(d):
            self.b[i] += reward * x[i]
        self._dirty = True

    def score(self, x: list[float]) -> float:
        """
        Compute UCB score for context x:
            θ·x  +  α * sqrt(x^T A⁻¹ x)
        """
        if self._dirty:
            self._A_inv = _invert(self.A)
            self._theta = _mat_vec(self._A_inv, self.b)
            self._dirty = False

        exploit = _dot(self._theta, x)
        # Uncertainty: x^T A⁻¹ x
        A_inv_x = _mat_vec(self._A_inv, x)
        variance = max(_dot(x, A_inv_x), 0.0)
        explore  = self.alpha * math.sqrt(variance)
        return exploit + explore


# ─────────────────────────────────────────────────────────────────────────────
# Contextual Bandit Policy (public class)
# ─────────────────────────────────────────────────────────────────────────────

class ContextualBanditPolicy:
    """
    LinUCB-based contextual bandit for dynamic layer selection.

    The policy learns which subset of analysis layers to run for each
    type of input, trading off accuracy against API cost and latency.

    Parameters
    ──────────
    alpha       : Exploration parameter. Higher → more exploration.
                  Typical range: 0.1 (greedy) to 2.0 (very exploratory).
    algorithm   : "linucb" (default) or "epsilon_greedy"
    epsilon     : Exploration probability for epsilon-greedy.
    persist_path: If set, policy weights are saved/loaded here so learning
                  survives across process restarts.
    """

    def __init__(
        self,
        alpha: float = 0.5,
        algorithm: Literal["linucb", "epsilon_greedy"] = "linucb",
        epsilon: float = 0.15,
        persist_path: str | None = None,
    ):
        self.alpha     = alpha
        self.algorithm = algorithm
        self.epsilon   = epsilon
        self.persist_path = persist_path

        # One arm per action
        self._arms = [_LinUCBArm(N_FEATURES, alpha) for _ in range(N_ACTIONS)]

        # ε-greedy counters (also used as fallback)
        self._counts  = [0] * N_ACTIONS   # times each action was selected
        self._values  = [0.0] * N_ACTIONS # mean reward per action

        # Full audit trail
        self.history: list[dict] = []
        self._step = 0

        if persist_path and os.path.exists(persist_path):
            self._load(persist_path)

    # ─────────────────────────────────────────────────
    # Core API
    # ─────────────────────────────────────────────────

    def select_action(self, state: dict) -> dict:
        """
        Choose which layers to execute given the current input context.

        Args:
            state : Output of build_state().

        Returns:
            One of the ACTIONS dicts, e.g.:
            {"id": 6, "layers": ["domain","content","behavior"], "label": "all-layers"}
        """
        x = state["vector"]

        if self.algorithm == "linucb":
            action_id = self._linucb_select(x)
        else:
            action_id = self._epsilon_greedy_select()

        self._step += 1
        return ACTIONS[action_id]

    def update(self, state: dict, action: dict, reward: float) -> None:
        """
        Incorporate the observed reward and improve the model.

        Args:
            state  : Same state dict passed to select_action.
            action : The action dict returned by select_action.
            reward : Scalar reward from reward.compute_reward().
        """
        x         = state["vector"]
        action_id = action["id"]

        # Update LinUCB arm
        self._arms[action_id].update(x, reward)

        # Update ε-greedy stats (used as fallback and for monitoring)
        n = self._counts[action_id]
        self._counts[action_id]  = n + 1
        self._values[action_id] += (reward - self._values[action_id]) / (n + 1)

        # Log
        self.history.append({
            "step":      self._step,
            "action":    action["label"],
            "layers":    action["layers"],
            "reward":    round(reward, 4),
            "timestamp": time.strftime("%H:%M:%S"),
        })

        if self.persist_path:
            self._save(self.persist_path)

    def best_action_so_far(self) -> dict:
        """Return the action with highest mean reward seen so far."""
        best_id = max(range(N_ACTIONS), key=lambda i: self._values[i])
        return {**ACTIONS[best_id], "mean_reward": round(self._values[best_id], 4)}

    def stats(self) -> dict:
        """Summary statistics for monitoring / debugging."""
        return {
            "algorithm":  self.algorithm,
            "total_steps": self._step,
            "action_counts": {
                ACTIONS[i]["label"]: self._counts[i] for i in range(N_ACTIONS)
            },
            "mean_rewards": {
                ACTIONS[i]["label"]: round(self._values[i], 4) for i in range(N_ACTIONS)
            },
        }

    # ─────────────────────────────────────────────────
    # Internal — LinUCB
    # ─────────────────────────────────────────────────

    def _linucb_select(self, x: list[float]) -> int:
        scores = [arm.score(x) for arm in self._arms]
        return scores.index(max(scores))

    # ─────────────────────────────────────────────────
    # Internal — Epsilon-Greedy
    # ─────────────────────────────────────────────────

    def _epsilon_greedy_select(self) -> int:
        if random.random() < self.epsilon:
            return random.randint(0, N_ACTIONS - 1)   # explore
        return self._values.index(max(self._values))   # exploit

    # ─────────────────────────────────────────────────
    # Persistence (JSON, no pickle — portable)
    # ─────────────────────────────────────────────────

    def _save(self, path: str) -> None:
        """Persist bandit state to JSON so learning survives restarts."""
        data = {
            "counts":  self._counts,
            "values":  self._values,
            "step":    self._step,
            # Arms: save A and b matrices (theta recomputed on load)
            "arms": [
                {"A": arm.A, "b": arm.b}
                for arm in self._arms
            ],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self, path: str) -> None:
        """Restore bandit state from JSON checkpoint."""
        try:
            with open(path) as f:
                data = json.load(f)
            self._counts = data["counts"]
            self._values = data["values"]
            self._step   = data["step"]
            for i, arm_data in enumerate(data["arms"]):
                self._arms[i].A     = arm_data["A"]
                self._arms[i].b     = arm_data["b"]
                self._arms[i]._dirty = True
        except Exception as e:
            print(f"[BanditPolicy] Warning: could not load checkpoint: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Pure-Python linear algebra (no numpy — hackathon-safe)
# ─────────────────────────────────────────────────────────────────────────────

def _dot(a: list[float], b: list[float]) -> float:
    return sum(ai * bi for ai, bi in zip(a, b))


def _mat_vec(M: list[list[float]], v: list[float]) -> list[float]:
    """Multiply matrix M by vector v."""
    return [_dot(row, v) for row in M]


def _invert(M: list[list[float]]) -> list[list[float]]:
    """
    Gauss-Jordan matrix inversion (in-place on a copy).
    O(d³) — fine for d=8. For larger d, swap in numpy.
    """
    d = len(M)
    # Augment M with identity
    aug = [M[i][:] + [1.0 if i == j else 0.0 for j in range(d)] for i in range(d)]
    for col in range(d):
        # Partial pivot
        pivot = max(range(col, d), key=lambda r: abs(aug[r][col]))
        aug[col], aug[pivot] = aug[pivot], aug[col]
        diag = aug[col][col]
        if abs(diag) < 1e-12:
            # Singular → return identity (safe fallback, early in training)
            return [[1.0 if i == j else 0.0 for j in range(d)] for i in range(d)]
        aug[col] = [x / diag for x in aug[col]]
        for row in range(d):
            if row != col:
                factor = aug[row][col]
                aug[row] = [aug[row][k] - factor * aug[col][k] for k in range(2 * d)]
    return [row[d:] for row in aug]
