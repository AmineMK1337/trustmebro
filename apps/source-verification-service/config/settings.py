"""
config/settings.py
==================
Central configuration for the Source Credibility Agent.
All thresholds, weights, and constants are defined here so the system
can be tuned without touching business logic — ideal for hackathon iterations.
"""

# ─────────────────────────────────────────────
# SCORING WEIGHTS  (must sum to 1.0)
# Each layer contributes a weighted share to the final 0-100 score.
# Adjust these to emphasise domain trust, content quality, or behaviour.
# ─────────────────────────────────────────────
WEIGHTS = {
    "domain":   0.35,   # URL / domain analysis
    "content":  0.45,   # LLM-based text analysis  ← highest weight: content is king
    "behavior": 0.20,   # Metadata / behavioural heuristics
}

# ─────────────────────────────────────────────
# RISK THRESHOLDS
# Final score → risk label mapping.
# Score represents SUSPICION level (higher = riskier).
# ─────────────────────────────────────────────
RISK_THRESHOLDS = {
    "low":    40,   # score < 40  → Low Risk  ✅
    "medium": 70,   # 40 ≤ score < 70 → Medium Risk ⚠️
    # score ≥ 70 → High Risk ❌
}

# ─────────────────────────────────────────────
# DOMAIN ANALYSIS SETTINGS
# ─────────────────────────────────────────────
SUSPICIOUS_KEYWORDS = [
    "news", "official", "secure", "real", "truth", "alert",
    "breaking", "leak", "insider", "verified", "confirm",
    "exposed", "hidden", "secret", "urgent", "warning",
]

# TLDs that are commonly abused for misinformation / spam
SUSPICIOUS_TLDS = [
    ".xyz", ".top", ".club", ".online", ".site",
    ".info", ".biz", ".tk", ".ml", ".ga", ".cf",
    ".buzz", ".click", ".link", ".live",
]

# Trusted TLDs — reduce suspicion score
TRUSTED_TLDS = [".gov", ".edu", ".org"]

# Well-known, generally reputable domains (hardcoded allowlist)
TRUSTED_DOMAINS = [
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
    "nytimes.com", "theguardian.com", "washingtonpost.com",
    "nature.com", "science.org", "who.int", "cdc.gov",
    "wikipedia.org", "britannica.com",
]

# Penalty points for domain anomalies (raw, before weighting)
DOMAIN_PENALTIES = {
    "no_https":            25,
    "suspicious_keyword":  15,   # per keyword found (capped)
    "suspicious_tld":      20,
    "long_subdomain":      10,   # subdomain has 3+ parts
    "numeric_subdomain":   15,   # e.g. 123.example.com
    "hyphen_spam":         10,   # 3+ hyphens in domain
    "trusted_domain":     -30,   # bonus — lower risk
    "trusted_tld":        -10,
}

# ─────────────────────────────────────────────
# CONTENT / TEXT ANALYSIS SETTINGS (Gemini LLM)
# ─────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Maximum characters of text sent to LLM (cost / latency control)
MAX_TEXT_LENGTH = 3000

# ─────────────────────────────────────────────
# BEHAVIORAL / METADATA SETTINGS
# ─────────────────────────────────────────────
BEHAVIOR_PENALTIES = {
    "bot_like_username":        20,
    "new_account":              15,   # account age < 30 days
    "high_post_frequency":      20,   # > 50 posts/day
    "no_profile_info":          10,
    "anonymous_source":         10,
    "recycled_content_flag":    15,
    "unverified_account":       10,
}

# Posts-per-day threshold above which we flag high frequency
HIGH_POST_FREQ_THRESHOLD = 50
NEW_ACCOUNT_DAYS_THRESHOLD = 30
