"""
tools/behavior_analyzer.py
==========================
LAYER 3 — Behavioural / Metadata Heuristics
--------------------------------------------
Evaluates the trustworthiness of the *source entity* (account, author,
publisher) using lightweight rule-based checks on metadata.

Accepted metadata fields (all optional):
    username         str   — account / author handle
    account_age_days int   — how old the account is in days
    posts_per_day    float — average posting frequency
    verified         bool  — is the account platform-verified?
    bio              str   — profile description
    followers        int   — follower count (if available)
    recycled_content bool  — flagged by upstream for content reuse
    anonymous        bool  — is the author anonymous?

Output schema:
    {
        "score":   int,    # 0-100 suspicion score
        "reasons": [str],  # human-readable findings
    }
"""

import re

from config.settings import (
    BEHAVIOR_PENALTIES,
    HIGH_POST_FREQ_THRESHOLD,
    NEW_ACCOUNT_DAYS_THRESHOLD,
)
from utils.helpers import clamp

# ─────────────────────────────────────────────────────────────────────────────
# Username patterns typical of bots / automated accounts
# ─────────────────────────────────────────────────────────────────────────────
_BOT_USERNAME_PATTERNS = [
    r"^\w+\d{6,}$",          # word followed by 6+ digits: user123456789
    r"^[a-z]{3,6}\d{4,}$",   # short word + 4+ digits: news2024
    r"^(bot|auto|feed|rss|alert)\w*",  # starts with 'bot', 'auto', etc.
    r"^[a-z0-9]{16,}$",       # 16+ lowercase alphanumeric (generated handle)
]


def analyze_behavior(metadata: dict | None) -> dict:
    """
    Evaluate the social / metadata signals of a content source.

    Args:
        metadata : dict of source metadata (see module docstring for fields).
                   Pass None or {} to skip behavioural analysis gracefully.

    Returns:
        dict with keys 'score' and 'reasons'.
    """
    if not metadata or not isinstance(metadata, dict):
        return {
            "score": 0,
            "reasons": ["No metadata provided — behavioural analysis skipped."],
        }

    reasons: list[str] = []
    penalty: int = 0

    # ── 1. Bot-like username ───────────────────────────────────────────────
    username = str(metadata.get("username", "")).strip()
    if username and _is_bot_username(username):
        penalty += BEHAVIOR_PENALTIES["bot_like_username"]
        reasons.append(
            f"Username '{username}' matches bot-like patterns "
            "(auto-generated handles often contain long digit strings)."
        )

    # ── 2. New account ─────────────────────────────────────────────────────
    age_days = metadata.get("account_age_days")
    if age_days is not None:
        try:
            age_days = int(age_days)
            if age_days < NEW_ACCOUNT_DAYS_THRESHOLD:
                penalty += BEHAVIOR_PENALTIES["new_account"]
                reasons.append(
                    f"Account is only {age_days} day(s) old. "
                    "Newly created accounts are disproportionately used to spread misinformation."
                )
        except (ValueError, TypeError):
            pass

    # ── 3. Abnormally high posting frequency ──────────────────────────────
    ppd = metadata.get("posts_per_day")
    if ppd is not None:
        try:
            ppd = float(ppd)
            if ppd > HIGH_POST_FREQ_THRESHOLD:
                penalty += BEHAVIOR_PENALTIES["high_post_frequency"]
                reasons.append(
                    f"Account posts ~{ppd:.0f} times per day — far above the human norm. "
                    "This is a strong indicator of automated or coordinated activity."
                )
        except (ValueError, TypeError):
            pass

    # ── 4. Unverified account ─────────────────────────────────────────────
    verified = metadata.get("verified")
    if verified is False:
        penalty += BEHAVIOR_PENALTIES["unverified_account"]
        reasons.append(
            "Account is not platform-verified. "
            "Unverified accounts cannot be confirmed as the entities they claim to represent."
        )

    # ── 5. Missing / empty bio / profile info ─────────────────────────────
    bio = str(metadata.get("bio", "")).strip()
    if not bio:
        penalty += BEHAVIOR_PENALTIES["no_profile_info"]
        reasons.append(
            "Account has no bio or profile description. "
            "Legitimate publishers and journalists typically maintain complete profiles."
        )

    # ── 6. Anonymous source flag ───────────────────────────────────────────
    if metadata.get("anonymous") is True:
        penalty += BEHAVIOR_PENALTIES["anonymous_source"]
        reasons.append(
            "Author / source is explicitly anonymous. "
            "Anonymity alone isn't disqualifying, but raises accountability concerns."
        )

    # ── 7. Recycled / duplicate content flag ──────────────────────────────
    if metadata.get("recycled_content") is True:
        penalty += BEHAVIOR_PENALTIES["recycled_content_flag"]
        reasons.append(
            "Content has been flagged as recycled or re-posted from an earlier date, "
            "which is a common tactic to make old news appear current."
        )

    # ── 8. Follower count heuristic (if provided) ─────────────────────────
    # Very low follower count + no verification + no bio = suspicious trio
    followers = metadata.get("followers")
    if followers is not None:
        try:
            followers = int(followers)
            if followers < 50 and not bio and verified is False:
                penalty += 10
                reasons.append(
                    f"Account has only {followers} follower(s) with no bio and is unverified — "
                    "consistent with a throwaway or sockpuppet account."
                )
        except (ValueError, TypeError):
            pass

    if not reasons:
        reasons.append("No behavioural red flags detected in the provided metadata.")

    return {"score": clamp(penalty), "reasons": reasons}


# ─────────────────────────────────────────────────────────────────────────────
# Internal helper
# ─────────────────────────────────────────────────────────────────────────────

def _is_bot_username(username: str) -> bool:
    """Return True if the username matches any known bot-like pattern."""
    username_lower = username.lower()
    return any(re.search(p, username_lower) for p in _BOT_USERNAME_PATTERNS)
