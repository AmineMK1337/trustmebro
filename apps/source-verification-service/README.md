# 🔍 Source Credibility Agent

A lightweight, modular, explainable AI system that evaluates the trustworthiness of online content using a **3-layer hybrid approach** — domain analysis, LLM-powered text evaluation (Gemini), and behavioural heuristics.

Built for hackathons. Zero heavy dependencies. Fully explainable.

---

## 🏗️ Architecture

```
source_credibility_agent/
│
├── agent/
│   └── source_agent.py        ← Main SourceAgent class (orchestrator)
│
├── tools/
│   ├── domain_analyzer.py     ← Layer 1: URL / domain structural analysis
│   ├── text_analyzer.py       ← Layer 2: Gemini LLM content analysis
│   └── behavior_analyzer.py   ← Layer 3: Metadata / behavioural heuristics
│
├── config/
│   └── settings.py            ← All thresholds, weights, constants
│
├── utils/
│   └── helpers.py             ← Scoring, formatting, shared utilities
│
├── examples/
│   └── run_examples.py        ← 5 demo scenarios (High / Medium / Low risk)
│
├── requirements.txt
└── README.md
```

### Layer Weight Distribution (configurable)

| Layer             | Default Weight | What it measures                        |
|-------------------|:--------------:|-----------------------------------------|
| 🌐 Domain Analysis | 35%           | URL structure, TLD, protocol, keywords |
| 📄 Content Analysis| 45%           | Manipulation, clickbait, sourcing       |
| 👤 Behavior Analysis| 20%          | Account age, frequency, bot patterns   |

---

## 🚀 Quick Start

### 1. Clone / copy the project

```bash
cd source_credibility_agent
```

### 2. (Optional) Set your Gemini API key

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

Without a key, Layer 2 automatically falls back to a rule-based text analyser.

### 3. Run the demo

```bash
python examples/run_examples.py
```

---

## 💻 Code Usage

```python
from agent.source_agent import SourceAgent

# Initialise (picks up GEMINI_API_KEY from env)
agent = SourceAgent(api_key="YOUR_KEY")  # or set env var

# Full 3-layer evaluation
result = agent.run(
    url="http://real-official-truth-news-alert.xyz/breaking",
    text="SHOCKING: They don't want you to know this SECRET!!",
    metadata={
        "username": "user8472916374",
        "account_age_days": 3,
        "posts_per_day": 120,
        "verified": False,
        "bio": "",
    }
)

# Output
print(result["score"])   # e.g. 82
print(result["risk"])    # "High"
print(result["reasons"]) # list of explanations
```

### Output Schema

```python
{
    "score": 82,          # 0-100 suspicion score (higher = riskier)
    "risk": "High",       # "Low" | "Medium" | "High"
    "reasons": [
        "[🌐 Domain] Site uses HTTP (not HTTPS)...",
        "[📄 Content (Gemini LLM)] Text uses emotionally charged language...",
        "[👤 Behavior] Username matches bot-like patterns...",
        # ...
    ],
    "details": {
        "domain_score": 70,
        "content_score": 88,
        "behavior_score": 65
    }
}
```

### Terminal Output

```
═══════════════════════════════════════════════════════
  ❌  Source Credibility: HIGH RISK (82/100)
═══════════════════════════════════════════════════════

  Layer Breakdown:
    • Domain Analysis   : 70/100
    • Content Analysis  : 88/100
    • Behavior Analysis : 65/100

  Reasons:
    – [🌐 Domain] Site uses HTTP (not HTTPS)
    – [🌐 Domain] Hostname contains suspicious keywords: real, official, truth
    – [📄 Content] Overall: Highly manipulative content with conspiracy signals
    – [👤 Behavior] Username matches bot-like patterns
    – [👤 Behavior] Account is only 3 days old
```

---

## ⚙️ Configuration

All thresholds and weights live in `config/settings.py`:

```python
# Layer weights (must sum to 1.0)
WEIGHTS = {
    "domain":   0.35,
    "content":  0.45,
    "behavior": 0.20,
}

# Risk thresholds
RISK_THRESHOLDS = {
    "low":    40,   # score < 40 → Low ✅
    "medium": 70,   # 40-69     → Medium ⚠️
    # ≥ 70            → High ❌
}
```

Override weights at runtime:

```python
agent = SourceAgent(weights={"domain": 0.5, "content": 0.3, "behavior": 0.2})
```

---

## 🧩 Multi-Agent Integration

The agent is designed to slot into a larger pipeline:

```python
# In a multi-agent orchestrator:
credibility_agent = SourceAgent(verbose=False)

def evaluate_article(article: dict) -> dict:
    return credibility_agent.run(
        url=article.get("url"),
        text=article.get("body"),
        metadata=article.get("author_metadata"),
    )
```

Individual layers can also be called independently:

```python
agent.check_domain("https://example.com")
agent.check_text("Some article text...")
agent.check_behavior({"username": "bot_123", "verified": False})
```

---

## 🧪 Risk Levels Explained

| Score | Risk   | Interpretation                                     |
|-------|--------|----------------------------------------------------|
| 0–39  | ✅ Low  | Source appears credible; no major red flags        |
| 40–69 | ⚠️ Medium | Some concerns; verify independently before trusting|
| 70–100| ❌ High  | Strong misinformation signals; treat with extreme caution |

---

## 🔑 Gemini API Key

Get yours free at: https://aistudio.google.com/app/apikey

The agent uses `gemini-2.0-flash` via direct HTTP (no SDK needed).
Without a key, a fully offline rule-based fallback is used automatically.

---

## 📜 License

MIT — free to use, modify, and distribute.
