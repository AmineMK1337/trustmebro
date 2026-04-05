"""
examples/run_examples.py
========================
Demonstration of the Source Credibility Agent with four realistic scenarios:

  1. HIGH RISK   — Suspicious misinformation-style source
  2. MEDIUM RISK — Borderline tabloid-style source
  3. LOW RISK    — Reputable news outlet
  4. DOMAIN ONLY — URL check with no text or metadata
  5. TEXT ONLY   — Pure content analysis (no URL)

Run from the project root:
    python examples/run_examples.py
Or with your Gemini key:
    GEMINI_API_KEY=your_key python examples/run_examples.py
"""

import os
import sys

# Ensure imports resolve from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.source_agent import SourceAgent


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def run_example(title: str, agent: SourceAgent, **kwargs) -> dict:
    """Print a titled banner and run the agent with the provided inputs."""
    print("\n" + "▓" * 60)
    print(f"  EXAMPLE: {title}")
    print("▓" * 60)
    return agent.run(**kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# Sample data
# ─────────────────────────────────────────────────────────────────────────────

HIGH_RISK_URL = "http://real-official-truth-news-alert.xyz/breaking-story"

HIGH_RISK_TEXT = (
    "BREAKING!!! They DON'T want you to know this SECRET!! "
    "SHOCKING new evidence EXPOSES the TRUTH about the HIDDEN AGENDA "
    "that the mainstream media has been COVERING UP for years!! "
    "Sources say the ELITE are planning something HORRIFYING and you MUST "
    "act NOW before it's too late!!! SHARE this before they DELETE it!!!! "
    "Insiders claim that a massive cover-up is underway and crisis actors "
    "were involved. Wake up people — this is a false flag operation!!"
)

HIGH_RISK_METADATA = {
    "username":        "user8472916374",   # bot-like pattern
    "account_age_days": 3,                 # brand-new account
    "posts_per_day":   120,               # impossibly high
    "verified":        False,
    "bio":             "",                 # empty profile
    "followers":       12,
    "recycled_content": True,
    "anonymous":       True,
}

# ────────────────────────────────────────────────────────────────────────────

MEDIUM_RISK_URL = "https://breaking-news-today.info/article/123"

MEDIUM_RISK_TEXT = (
    "Sources close to the government say the new policy could affect "
    "millions of people. Many experts believe the decision was rushed, "
    "and some insiders are reportedly furious. The announcement has "
    "sent shockwaves across the country, with many citizens outraged. "
    "Allegedly, key data was withheld from the public report."
)

MEDIUM_RISK_METADATA = {
    "username":        "newsreporter_2024",
    "account_age_days": 45,
    "posts_per_day":   8,
    "verified":        False,
    "bio":             "Independent journalist covering politics.",
    "followers":       320,
    "recycled_content": False,
    "anonymous":       False,
}

# ────────────────────────────────────────────────────────────────────────────

LOW_RISK_URL = "https://reuters.com/world/us/federal-reserve-holds-rates-2025"

LOW_RISK_TEXT = (
    "The Federal Reserve held its benchmark interest rate steady on Wednesday, "
    "keeping the federal funds rate in the 5.25%-5.50% range for the fifth "
    "consecutive meeting. Fed Chair Jerome Powell said in a press conference "
    "that while inflation has eased significantly from its 2022 peak of 9.1%, "
    "the central bank needs 'greater confidence' that price increases are "
    "sustainably moving toward its 2% target before cutting rates. "
    "The decision was unanimous among voting members of the FOMC."
)

LOW_RISK_METADATA = {
    "username":        "Reuters_Official",
    "account_age_days": 5840,   # 16 years old
    "posts_per_day":   15,
    "verified":        True,
    "bio":             "Reuters — Award-winning international news organisation.",
    "followers":       21000000,
    "recycled_content": False,
    "anonymous":       False,
}

# ────────────────────────────────────────────────────────────────────────────

DOMAIN_ONLY_URL = "http://secure-official-verified-news.top/leaked-documents"

TEXT_ONLY_CONTENT = (
    "Scientists at Harvard Medical School published findings in the New England "
    "Journal of Medicine showing that regular exercise reduces cardiovascular "
    "disease risk by 35%. The randomised controlled trial followed 12,000 "
    "participants over 10 years. Lead author Dr Sarah Chen said the results "
    "were 'robust across all age groups and demographics'."
)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Initialise agent — picks up GEMINI_API_KEY from env automatically
    agent = SourceAgent(verbose=True)

    print("\n" + "═" * 60)
    print("  SOURCE CREDIBILITY AGENT — DEMO RUN")
    print(f"  Gemini: {'✅ configured' if agent.api_key else '⚠️  not configured (rule-based fallback)'}")
    print("═" * 60)

    # ── Example 1: Full pipeline — HIGH RISK ─────────────────────────────
    r1 = run_example(
        "Full Pipeline — HIGH RISK (Misinformation)",
        agent,
        url=HIGH_RISK_URL,
        text=HIGH_RISK_TEXT,
        metadata=HIGH_RISK_METADATA,
    )

    # ── Example 2: Full pipeline — MEDIUM RISK ───────────────────────────
    r2 = run_example(
        "Full Pipeline — MEDIUM RISK (Tabloid-style)",
        agent,
        url=MEDIUM_RISK_URL,
        text=MEDIUM_RISK_TEXT,
        metadata=MEDIUM_RISK_METADATA,
    )

    # ── Example 3: Full pipeline — LOW RISK ──────────────────────────────
    r3 = run_example(
        "Full Pipeline — LOW RISK (Reuters)",
        agent,
        url=LOW_RISK_URL,
        text=LOW_RISK_TEXT,
        metadata=LOW_RISK_METADATA,
    )

    # ── Example 4: Domain-only check ─────────────────────────────────────
    r4 = run_example(
        "Domain-Only Check",
        agent,
        url=DOMAIN_ONLY_URL,
    )

    # ── Example 5: Text-only analysis ─────────────────────────────────────
    r5 = run_example(
        "Text-Only Analysis (Scientific article)",
        agent,
        text=TEXT_ONLY_CONTENT,
    )

    # ── Summary table ─────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("  RESULTS SUMMARY")
    print("═" * 60)
    examples = [
        ("HIGH RISK source",   r1),
        ("MEDIUM RISK source", r2),
        ("LOW RISK source",    r3),
        ("Domain-only",        r4),
        ("Text-only",          r5),
    ]
    for label, r in examples:
        risk  = r["risk"]
        score = r["score"]
        icon  = {"Low": "✅", "Medium": "⚠️", "High": "❌"}.get(risk, "?")
        print(f"  {icon}  {label:<25}  Score: {score:>3}/100  Risk: {risk}")
    print("═" * 60 + "\n")

    return {
        "high_risk":   r1,
        "medium_risk": r2,
        "low_risk":    r3,
        "domain_only": r4,
        "text_only":   r5,
    }


if __name__ == "__main__":
    main()
