# Source Credibility Agent — Decision-Making Architecture

## Overview

The Source Credibility Agent is a **3-layer hybrid system** designed to evaluate the trustworthiness of online content. Each layer independently analyzes a different signal of credibility, produces a score (0–100), and provides human-readable reasons. The final verdict is a weighted average of all active layers.

---

## The Three Decision Layers

### Layer 1: Domain / URL Analysis (35% weight)
**What:** Structural and semantic red flags in the URL itself.  
**How:** Rule-based pattern matching — no network calls, instant response.

**Checks performed:**
1. Protocol security (HTTP vs HTTPS)
2. Trusted domain allowlist (e.g., reuters.com, bbc.com)
3. Trusted TLD bonus (.gov, .edu, .org)
4. Suspicious keywords in hostname (e.g., "official", "truth", "alert")
5. Suspicious/cheap TLDs (.xyz, .top, .club)
6. Deep subdomain structures (3+ levels = cloaking flag)
7. Numeric subdomains (bot patterns)
8. Hyphen spam (3+ hyphens = clickbait signal)

**Output:**
```python
{
    "score": 0-100,  # higher = riskier
    "reasons": [...]
}
```

**Example:**
- ✅ `https://bbc.com/news/article123` → score 0 (recognized reputable source)
- ❌ `http://real-official-truth-news-alert.xyz/breaking` → score 85 (HTTP, suspicious TLD, keyword spam, hyphens)

---

### Layer 2: Content / Text Analysis (45% weight — highest)
**What:** The article/post body itself — emotional tone, factual grounding, manipulation tactics.  
**How:** LLM-powered (Gemini) with rule-based fallback for offline mode.

**Gemini evaluates:**
1. **Emotional manipulation** — Fear, anger, outrage language
2. **Clickbait / exaggeration** — Hyperbole, ALL CAPS, extraordinary claims
3. **Factual grounding** — Cites sources, named experts, specific data vs. vague phrases
4. **Conspiracy signals** — Hidden agendas, unverified conspiracies
5. **Sensationalism** — Dramatization beyond facts

**Rule-based fallback checks:**
- Clickbait patterns (e.g., "you won't believe", "shocking", excessive punctuation)
- Emotional language (e.g., "destroy", "outrage", "evil")
- Weak sourcing (e.g., "sources say", "allegedly", "some experts")
- Conspiracy terms (e.g., "cover-up", "false flag", "plandemic")
- ALL-CAPS ratio (>15% is flagged)

**Output:**
```python
{
    "score": 0-100,
    "reasons": [...],
    "llm_used": bool,        # Gemini called or rule-based?
    "raw_response": str      # raw LLM output for debugging
}
```

**Example:**
- ✅ Cited sources, named experts, balanced tone, specific data → score ~20
- ❌ "SHOCKING AGENDA the ELITES don't want you to know + no sources" → score ~80+

---

### Layer 3: Behavioral / Metadata Heuristics (20% weight)
**What:** Signals about the *source entity* (account, author, publisher).  
**How:** Rule-based pattern matching on metadata fields.

**Checks performed:**
1. Bot-like username patterns (e.g., "user123456789", "news2024")
2. Account age (< 30 days = risky)
3. Posting frequency (> 50 posts/day = bot-like)
4. Verification status (unverified = higher suspicion)
5. Profile completeness (no bio = red flag)
6. Follower count heuristics (very low + no bio + unverified = sockpuppet)
7. Anonymous source flag
8. Recycled/reposted content

**Output:**
```python
{
    "score": 0-100,
    "reasons": [...]
}
```

**Example:**
- ✅ Verified account, 16 years old, 21M followers, full bio → score 0
- ❌ Username "user8472916374", 3 days old, 120 posts/day, no bio → score 65+

**⚠️ Note:** This layer requires *external data* (social API, platform metadata). From a URL alone, it cannot be inferred.

---

## Decision Flow

```
Input: url, text, metadata (any or all)
  ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Domain Analysis                                │
│ (always runs if URL provided)                            │
│ → score₁, reasons₁                                       │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Content Analysis                               │
│ (runs if text provided)                                 │
│ → score₂, reasons₂                                       │
│ [Uses Gemini if API key available, else rule-based]     │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Behavioral Analysis                            │
│ (runs if metadata provided)                             │
│ → score₃, reasons₃                                       │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ Weighted Score Aggregation                              │
│                                                         │
│ Only ACTIVE layers (those that ran) contribute.        │
│ Remaining weight redistributed proportionally.         │
│                                                         │
│ final_score = weighted_average(                         │
│     {layer: score},                                     │
│     weights={domain: 0.35, content: 0.45, behavior: 0.20}
│ )                                                       │
│                                                         │
│ final_score = clamp(int(round(result)), 0, 100)        │
└─────────────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────────────┐
│ Risk Classification                                     │
│                                                         │
│ if final_score < 40:        → "Low" ✅                  │
│ if 40 ≤ final_score < 70:   → "Medium" ⚠️               │
│ if final_score ≥ 70:        → "High" ❌                 │
└─────────────────────────────────────────────────────────┘
  ↓
Output: {score, risk, reasons, details}
```

---

## Weighted Score Aggregation (The Decision Algorithm)

The agent combines layer scores using **proportional weighting**:

```python
def weighted_average(scores: dict, weights: dict) -> int:
    # Only ACTIVE layers contribute
    active = {k: v for k, v in scores.items() if v != -1}
    
    # Redistribute weight proportionally
    total_weight = sum(weights[k] for k in active)
    weighted_sum = sum(active[k] * weights[k] for k in active)
    
    final = weighted_sum / total_weight
    return clamp(int(round(final)), 0, 100)
```

**Example 1: All three layers run**
```
domain_score = 50, content_score = 70, behavior_score = 60
weights = {domain: 0.35, content: 0.45, behavior: 0.20}

final = (50×0.35 + 70×0.45 + 60×0.20) / (0.35+0.45+0.20)
      = (17.5 + 31.5 + 12.0) / 1.0
      = 61
      → "Medium" risk
```

**Example 2: Only domain and content layers (no metadata)**
```
domain_score = 50, content_score = 70, behavior_score = -1 (skipped)
active = {domain: 50, content: 70}
total_weight = 0.35 + 0.45 = 0.80  # behavior weight dropped

final = (50×0.35 + 70×0.45) / 0.80
      = (17.5 + 31.5) / 0.80
      = 49 / 0.80
      = 61.25 ≈ 61
      → "Medium" risk
```

Key insight: **Missing layers don't penalize the score — their weight is redistributed.**

---

## Configuration: Tuning Weights

All thresholds and weights live in `config/settings.py`:

```python
# Default layer weights (sum to 1.0)
WEIGHTS = {
    "domain":   0.35,
    "content":  0.45,  # highest = content is king
    "behavior": 0.20,
}

# Risk thresholds
RISK_THRESHOLDS = {
    "low":    40,   # score < 40
    "medium": 70,   # 40 ≤ score < 70
}
```

**Why these weights?**
- **Domain (35%): Early signal** — If the URL smells wrong, that matters.
- **Content (45%): Highest** — What's actually written is the strongest indicator.
- **Behavior (20%): Contextual** — Who posted it matters, but can often be unavailable.

**Override at runtime:**
```python
agent = SourceAgent(weights={
    "domain":   0.5,
    "content":  0.3,
    "behavior": 0.2
})
```

---

## Real-World Decision Examples

### Example A: Highly Suspicious URL + Clickbait Text + Bot Account
```
URL: http://real-official-truth-alert.xyz/breaking
Text: "SHOCKING! They DON'T want you to know this SECRET!!!..."
Metadata: username="user8472916374", account_age_days=3, posts_per_day=120

Layer 1 (Domain):   score 85 (HTTP, keywords, suspicious TLD, hyphens)
Layer 2 (Content):  score 88 (all-caps, clickbait, conspiracy language)
Layer 3 (Behavior): score 65 (bot username, new account, high frequency)

Final Score: (85×0.35 + 88×0.45 + 65×0.20) = (29.75 + 39.6 + 13) = 82.35 ≈ 82

Risk: ❌ HIGH
Recommendation: Do not trust this source.
```

### Example B: Reputable URL + Factual Text + Verified Account
```
URL: https://reuters.com/world/...
Text: "Reuters reported on Wednesday... citing official sources..."
Metadata: username="Reuters_Official", verified=True, followers=21M, account_age_days=5840

Layer 1 (Domain):   score 0 (trusted domain → early return)
Layer 2 (Content):  score 15 (named sources, balanced tone, no emotional language)
Layer 3 (Behavior): score 0 (verified, huge following, old account)

Final Score: (0×0.35 + 15×0.45 + 0×0.20) = (0 + 6.75 + 0) = 6.75 ≈ 7

Risk: ✅ LOW
Recommendation: This is a credible source.
```

### Example C: Good URL + No Text + Unknown Account
```
URL: https://example.org/article
Text: (None)
Metadata: username="john_smith", account_age_days=45, posts_per_day=3

Layer 1 (Domain):   score 0 (HTTPS, .org TLD = trusted)
Layer 2 (Content):  -1 (skipped, no text)
Layer 3 (Behavior): score 12 (reasonable activity, but no profile details)

Active layers: {domain: 0, behavior: 12}
total_weight = 0.35 + 0.20 = 0.55
final = (0×0.35 + 12×0.20) / 0.55 = 2.4 / 0.55 ≈ 4.4 ≈ 4

Risk: ✅ LOW
Recommendation: Data is limited. URL is trustworthy; account is normal.
```

---

## Key Design Principles

1. **Explainability** — Every score comes with reasons. No black box.
2. **Independence** — Layers are independent; each can be called alone.
3. **Graceful degradation** — Missing inputs (e.g., no text) don't break the pipeline; layers are skipped.
4. **Proportional weighting** — Missing layers don't penalize; their weight redistributes.
5. **Offline-first** — Domain and behavioral layers work without network. Content layer has a rule-based fallback.
6. **Configurability** — Weights and thresholds are all in `config/settings.py` for quick iteration.

---

## When to Trust Each Layer

| Layer | Best For | Limitations |
|-------|----------|------------|
| **Domain** | Quick URL screening | Can't detect well-crafted phishing sites |
| **Content** | Detecting manipulation tactics | Needs actual article text; useless for headlines only |
| **Behavior** | Spotting bot/coordinated accounts | Requires platform metadata; unavailable from URL alone |

**Recommendation:** Always run **all three layers** when possible for maximum accuracy.

---

## Future Enhancements (ReAct Chain)

A ReAct chain could add **conditional reasoning**:
- "Domain score is high → definitely run content analysis."
- "Domain is trusted → consider skipping content analysis (cost/speed tradeoff)."
- "No metadata available → ask user or skip behavior layer explicitly."

This would make decisions more adaptive and efficient.
