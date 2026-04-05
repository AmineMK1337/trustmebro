"""
tools/text_analyzer.py
======================
LAYER 2 — Content / Text Credibility Analysis (LLM-powered)
-------------------------------------------------------------
Sends article text to Google Gemini and asks it to evaluate:
  • Emotional manipulation
  • Clickbait / exaggerated claims
  • Lack of factual grounding / verifiable sources
  • Conspiracy language
  • Sensationalism

The LLM returns a structured JSON response that we parse into a score
and a list of human-readable findings.

If no API key is supplied, a rule-based fallback kicks in so the agent
still works in offline / demo mode.

Output schema:
    {
        "score":       int,     # 0-100 suspicion score
        "reasons":     [str],   # findings from LLM
        "llm_used":    bool,    # True if Gemini was called
        "raw_response": str,    # raw LLM output (for debugging)
    }
"""

import json
import os
import re
import urllib.request
import urllib.error

from config.settings import GEMINI_MODEL, GEMINI_API_URL, MAX_TEXT_LENGTH
from utils.helpers import clamp

# ─────────────────────────────────────────────────────────────────────────────
# PROMPT TEMPLATE  (visible & documented as required by the spec)
# ─────────────────────────────────────────────────────────────────────────────
CREDIBILITY_PROMPT = """You are an expert fact-checker and media analyst specialising in misinformation detection.

Analyse the following text and evaluate it across FIVE dimensions:

1. **Emotional Manipulation** — Does the text use fear, anger, or outrage to influence the reader rather than inform?
2. **Clickbait / Exaggeration** — Does the headline or body use hyperbolic language, ALL CAPS, or make extraordinary claims without proportionate evidence?
3. **Factual Grounding** — Does the text cite verifiable sources, named experts, or specific data? Or does it rely on vague phrases like "sources say" or "many people believe"?
4. **Conspiracy Language** — Does the text promote hidden agendas, unverified conspiracies, or discredit mainstream institutions without evidence?
5. **Sensationalism** — Is the language neutral and balanced, or does it dramatise events beyond what the facts support?

TEXT TO ANALYSE:
\"\"\"
{text}
\"\"\"

Respond ONLY with a valid JSON object in this exact format (no markdown, no extra text):
{{
  "suspicion_score": <integer 0-100>,
  "findings": [
    "<finding 1>",
    "<finding 2>"
  ],
  "summary": "<one sentence overall assessment>"
}}

Where suspicion_score means:
  0-30  = credible, balanced, well-sourced
  31-60 = some concerns (emotional language, weak sourcing)
  61-100 = high risk (manipulation, clickbait, conspiracy signals)
"""

# ─────────────────────────────────────────────────────────────────────────────
# Public function
# ─────────────────────────────────────────────────────────────────────────────

def analyze_text(text: str, api_key: str | None = None) -> dict:
    """
    Analyse the credibility of a piece of text.

    Args:
        text    : The article / post body to evaluate.
        api_key : Gemini API key. Falls back to env var GEMINI_API_KEY,
                  then to the offline rule-based analyser.

    Returns:
        dict with keys: score, reasons, llm_used, raw_response
    """
    if not text or not isinstance(text, str) or len(text.strip()) < 20:
        return {
            "score": 0,
            "reasons": ["No text provided — content analysis skipped."],
            "llm_used": False,
            "raw_response": "",
        }

    # Truncate to keep LLM costs low
    truncated = text.strip()[:MAX_TEXT_LENGTH]

    # Resolve API key from argument → environment variable
    key = api_key or os.environ.get("GEMINI_API_KEY", "")

    if key:
        return _call_gemini(truncated, key)
    else:
        # No API key → rule-based fallback (demo / offline mode)
        return _rule_based_fallback(truncated)


# ─────────────────────────────────────────────────────────────────────────────
# Gemini API call
# ─────────────────────────────────────────────────────────────────────────────

def _call_gemini(text: str, api_key: str) -> dict:
    """
    Send text to Gemini and parse the structured JSON response.
    Uses only the standard library (urllib) — no httpx / requests required.
    """
    url = GEMINI_API_URL.format(model=GEMINI_MODEL) + f"?key={api_key}"
    prompt = CREDIBILITY_PROMPT.format(text=text)

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,       # low temperature → deterministic analysis
            "maxOutputTokens": 512,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        return _error_result(f"Gemini API HTTP error {e.code}: {error_body[:200]}")
    except Exception as e:
        return _error_result(f"Gemini API call failed: {str(e)}")

    return _parse_gemini_response(raw)


def _parse_gemini_response(raw: str) -> dict:
    """
    Extract the JSON payload from Gemini's response envelope and build
    the standard layer output dict.
    """
    try:
        outer = json.loads(raw)
        # Navigate the Gemini response structure
        candidates = outer.get("candidates", [])
        if not candidates:
            return _error_result("Gemini returned no candidates.")

        content_text = (
            candidates[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )

        # The model might wrap JSON in ```json ... ``` — strip fences
        content_text = re.sub(r"```(?:json)?", "", content_text).strip().rstrip("`").strip()

        parsed = json.loads(content_text)

        score    = clamp(int(parsed.get("suspicion_score", 50)))
        findings = parsed.get("findings", [])
        summary  = parsed.get("summary", "")

        reasons = findings if findings else ["LLM returned no specific findings."]
        if summary:
            reasons.insert(0, f"Overall: {summary}")

        return {
            "score":        score,
            "reasons":      reasons,
            "llm_used":     True,
            "raw_response": content_text,
        }

    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
        return _error_result(f"Failed to parse Gemini response: {e}\nRaw: {raw[:300]}")


# ─────────────────────────────────────────────────────────────────────────────
# Rule-based offline fallback
# ─────────────────────────────────────────────────────────────────────────────

# Patterns that signal low-quality / manipulative content
_CLICKBAIT_PATTERNS = [
    r"\b(you won't believe|shocking|mind-blowing|jaw-dropping|unbelievable)\b",
    r"\b(they don't want you to know|the truth about|wake up|open your eyes)\b",
    r"\b(BREAKING|URGENT|ALERT|EXCLUSIVE)\b",
    r"!{2,}",          # multiple exclamation marks
    r"\?{2,}",         # multiple question marks
]

_EMOTIONAL_PATTERNS = [
    r"\b(outrage|fury|horrifying|terrifying|disgusting|shameful|evil)\b",
    r"\b(destroy|crush|annihilate|expose|attack|fight back)\b",
    r"\b(they|them|elites|globalists|deep state|mainstream media)\b",
]

_WEAK_SOURCING_PATTERNS = [
    r"\b(sources say|some people|many experts|insiders claim|rumours suggest)\b",
    r"\b(apparently|allegedly|reportedly|it is said|word is)\b",
]

_CONSPIRACY_PATTERNS = [
    r"\b(conspiracy|cover-?up|hidden agenda|false flag|new world order)\b",
    r"\b(plandemic|hoax|fabricated|staged|crisis actor)\b",
]

ALL_CAPS_RATIO_THRESHOLD = 0.15  # >15% uppercase words is a red flag


def _rule_based_fallback(text: str) -> dict:
    """
    Offline heuristic content analyser.
    Used when no Gemini API key is available.
    Scans for known linguistic patterns of low-credibility content.
    """
    reasons: list[str] = []
    penalty: int = 0
    text_lower = text.lower()

    # ── Clickbait ──────────────────────────────────────────────────────────
    clickbait_hits = sum(
        1 for p in _CLICKBAIT_PATTERNS if re.search(p, text, re.IGNORECASE)
    )
    if clickbait_hits:
        penalty += min(clickbait_hits * 12, 30)
        reasons.append(
            f"Text contains {clickbait_hits} clickbait / sensationalism pattern(s) "
            "(e.g. 'you won't believe', excessive punctuation, ALL-CAPS alerts)."
        )

    # ── Emotional manipulation ─────────────────────────────────────────────
    emotional_hits = sum(
        1 for p in _EMOTIONAL_PATTERNS if re.search(p, text_lower)
    )
    if emotional_hits:
        penalty += min(emotional_hits * 10, 25)
        reasons.append(
            f"Text uses emotionally charged language ({emotional_hits} pattern(s)) "
            "that may be designed to provoke rather than inform."
        )

    # ── Weak sourcing ──────────────────────────────────────────────────────
    weak_src_hits = sum(
        1 for p in _WEAK_SOURCING_PATTERNS if re.search(p, text_lower)
    )
    if weak_src_hits:
        penalty += min(weak_src_hits * 8, 20)
        reasons.append(
            "Text relies on vague attribution phrases (e.g. 'sources say', "
            "'some experts') rather than named, verifiable sources."
        )

    # ── Conspiracy language ────────────────────────────────────────────────
    conspiracy_hits = sum(
        1 for p in _CONSPIRACY_PATTERNS if re.search(p, text_lower)
    )
    if conspiracy_hits:
        penalty += min(conspiracy_hits * 15, 30)
        reasons.append(
            f"Text contains {conspiracy_hits} conspiracy-related term(s). "
            "This is a strong indicator of low-credibility content."
        )

    # ── ALL-CAPS ratio ─────────────────────────────────────────────────────
    words = text.split()
    if words:
        caps_ratio = sum(1 for w in words if w.isupper() and len(w) > 2) / len(words)
        if caps_ratio > ALL_CAPS_RATIO_THRESHOLD:
            penalty += 15
            reasons.append(
                f"{caps_ratio:.0%} of words are in ALL CAPS — "
                "a common tactic to convey false urgency."
            )

    if not reasons:
        reasons.append(
            "No significant content red flags detected by rule-based analysis. "
            "(Tip: supply a GEMINI_API_KEY for deeper LLM analysis.)"
        )

    return {
        "score":        clamp(penalty),
        "reasons":      reasons,
        "llm_used":     False,
        "raw_response": "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Error helper
# ─────────────────────────────────────────────────────────────────────────────

def _error_result(message: str) -> dict:
    """Return a neutral score with an error message when LLM call fails."""
    return {
        "score":        30,   # neutral-ish — don't unfairly penalise on API errors
        "reasons":      [f"[Content analysis error] {message}"],
        "llm_used":     False,
        "raw_response": "",
    }
