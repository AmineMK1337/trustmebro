"""
tools/domain_analyzer.py
========================
LAYER 1 — Domain / URL Analysis
--------------------------------
Analyses a URL for structural and semantic red flags without making any
network requests.  Pure rule-based logic → fully explainable, zero latency.

Output schema:
    {
        "score": int,        # 0-100 suspicion score (higher = riskier)
        "reasons": [str],    # human-readable list of findings
    }
"""

import re
from urllib.parse import urlparse

from config.settings import (
    SUSPICIOUS_KEYWORDS,
    SUSPICIOUS_TLDS,
    TRUSTED_TLDS,
    TRUSTED_DOMAINS,
    DOMAIN_PENALTIES,
)
from utils.helpers import clamp


def analyze_domain(url: str) -> dict:
    """
    Evaluate the credibility signals embedded in a URL.

    Checks performed
    ────────────────
    1. Protocol — HTTP (insecure) vs HTTPS
    2. Trusted domain allowlist — known reputable outlets
    3. Trusted TLD bonus  (.gov, .edu, .org)
    4. Suspicious keyword presence in the hostname
    5. Suspicious / cheap TLD detection
    6. Subdomain depth (3+ levels suggest cloaking)
    7. Numeric subdomain pattern
    8. Hyphen spam in the domain name (e.g. free-real-news-today.com)

    Returns:
        dict with keys 'score' and 'reasons'
    """
    reasons: list[str] = []
    penalty: int = 0

    # ── Guard: handle empty / None input ──────────────────────────────────
    if not url or not isinstance(url, str):
        return {"score": 0, "reasons": ["No URL provided — domain analysis skipped."]}

    # Normalise: add scheme if missing so urlparse works correctly
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)
    hostname: str = parsed.netloc.lower().strip()

    # Remove port if present (e.g. example.com:8080)
    if ":" in hostname:
        hostname = hostname.split(":")[0]

    # ── 1. HTTPS check ─────────────────────────────────────────────────────
    if parsed.scheme == "http":
        penalty += DOMAIN_PENALTIES["no_https"]
        reasons.append("Site uses HTTP (not HTTPS) — connection is not encrypted.")

    # ── 2. Trusted domain allowlist ────────────────────────────────────────
    # Check if root domain matches a known trusted outlet
    root_domain = _get_root_domain(hostname)
    if root_domain in TRUSTED_DOMAINS:
        penalty += DOMAIN_PENALTIES["trusted_domain"]   # negative → reduces score
        reasons.append(f"Domain '{root_domain}' is a recognised reputable source.")
        # Return early — trusted domains need no further scrutiny
        return {"score": clamp(penalty), "reasons": reasons}

    # ── 3. Trusted TLD bonus ───────────────────────────────────────────────
    tld = _get_tld(hostname)
    if any(hostname.endswith(t) for t in TRUSTED_TLDS):
        penalty += DOMAIN_PENALTIES["trusted_tld"]
        reasons.append(f"TLD '{tld}' is generally associated with trusted institutions.")

    # ── 4. Suspicious keywords in hostname ────────────────────────────────
    found_keywords = [kw for kw in SUSPICIOUS_KEYWORDS if kw in hostname]
    if found_keywords:
        # Cap the penalty at 2 keyword hits to avoid over-penalising
        kw_penalty = min(len(found_keywords), 2) * DOMAIN_PENALTIES["suspicious_keyword"]
        penalty += kw_penalty
        reasons.append(
            f"Hostname contains suspicious keyword(s): {', '.join(found_keywords)}. "
            "Manipulative sites often use trust-signalling words in their domain."
        )

    # ── 5. Suspicious / low-quality TLD ───────────────────────────────────
    if any(hostname.endswith(t) for t in SUSPICIOUS_TLDS):
        penalty += DOMAIN_PENALTIES["suspicious_tld"]
        reasons.append(
            f"TLD '{tld}' is commonly associated with low-quality or spam websites."
        )

    # ── 6. Deep subdomain structure ───────────────────────────────────────
    parts = hostname.split(".")
    # e.g. news.real-truth.breaking.com has 4 parts → suspicious
    if len(parts) > 3:
        penalty += DOMAIN_PENALTIES["long_subdomain"]
        reasons.append(
            "Hostname has an unusually deep subdomain structure "
            f"({hostname}), which can be used to mimic legitimate sites."
        )

    # ── 7. Numeric subdomain (e.g. 192.real-news.com) ─────────────────────
    if parts and parts[0].isdigit():
        penalty += DOMAIN_PENALTIES["numeric_subdomain"]
        reasons.append(
            f"Subdomain starts with a number ('{parts[0]}'), a pattern common in bot-generated domains."
        )

    # ── 8. Hyphen spam ────────────────────────────────────────────────────
    hyphen_count = root_domain.count("-")
    if hyphen_count >= 3:
        penalty += DOMAIN_PENALTIES["hyphen_spam"]
        reasons.append(
            f"Domain name contains {hyphen_count} hyphens ('{root_domain}'), "
            "which is a common pattern in spammy or clickbait sites."
        )

    # ── Final output ───────────────────────────────────────────────────────
    if not reasons:
        reasons.append("No significant domain-level red flags detected.")

    return {"score": clamp(penalty), "reasons": reasons}


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

def _get_root_domain(hostname: str) -> str:
    """
    Extract the root domain (eTLD+1) from a hostname.
    Simple heuristic: last two dot-separated parts.
    e.g. 'news.breaking.example.co.uk' → 'example.co.uk'  (approx)
         'bbc.co.uk' → 'bbc.co.uk'
    """
    parts = hostname.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return hostname


def _get_tld(hostname: str) -> str:
    """Return the TLD (last dot-separated part) of a hostname."""
    parts = hostname.split(".")
    return f".{parts[-1]}" if parts else ""
