# Credibility Backend - Website Analysis Library

A Python backend library that analyzes website credibility using LLM-powered content analysis, domain age metrics, traffic rankings, and metadata extraction.

## Overview

This backend library evaluates website trustworthiness by:
- Extracting page content and screenshots via Selenium
- Analyzing content bias, sentiment, and credibility using Google Gemini AI
- Checking domain age via WHOIS/RDAP
- Retrieving traffic rankings from Tranco
- Generating comprehensive credibility reports
- Computing confidence percentages based on available data

## Prerequisites

- **Python 3.12+** (verify with `python --version`)
- **Poetry** (Python package manager)
- **Google Gemini API Key** (for LLM analysis)
- **Chrome/Chromium browser** (for Selenium)

## Installation

### 1. Files Required

Ensure you have these files in your project directory:
```
credibility/
├── api/
│   └── metrics.py          # Core analysis module
├── .env                    # Environment variables
├── pyproject.toml          # Poetry configuration
├── poetry.lock             # Locked dependencies
└── test_urls.py            # URL testing script
```

### 2. Install Dependencies

```bash
# Install Python dependencies using Poetry
python -m poetry install
```

If Poetry is not found:
```bash
python -m pip install poetry
```

### 3. Set Environment Variables

Create or edit `.env` file in project root:

```env
# Required: Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Specify Gemini model (default: gemini-2.5-flash)
GEMINI_MODEL=gemini-2.5-flash
```

To get a Gemini API key:
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Copy and paste into `.env`

## Quick Start - Testing URLs

### Test Without LLM (Fast, No Quota Used)

Test core features: domain extraction, Tranco ranking, domain age, metadata scraping.

```bash
# Test default URLs
python -m poetry run python test_urls.py

# Test specific URL
python -m poetry run python test_urls.py "https://www.wikipedia.org"

# Test multiple URLs
python -m poetry run python test_urls.py "https://www.wikipedia.org" "https://www.bbc.com" "https://www.goal.com"
```

**Output includes:**
- Domain name
- Tranco traffic rank
- Domain age (years)
- Analysis confidence %
- HTML/screenshot lengths
- Metadata (author, date found)

### Test With LLM (Full Analysis)

Includes Gemini AI bias/sentiment/credibility analysis (requires API quota).

```bash
# Test with LLM enabled
python -m poetry run python test_urls.py --with-llm "https://www.wikipedia.org"

# Multiple URLs with LLM
python -m poetry run python test_urls.py --with-llm "https://www.wikipedia.org" "https://www.goal.com"
```

**LLM Output includes:**
- Credibility score (0-100)
- Content credibility assessment
- Bias detection (true/false)
- Sentiment analysis (positive/neutral/negative)
- Publisher reputation
- Full multi-section report

## Python Usage

Import and use the core functions directly:

```python
import sys
sys.path.insert(0, 'api')
import metrics

# Extract domain from URL
domain = metrics.get_domain('https://www.wikipedia.org')
print(f"Domain: {domain}")  # Output: wikipedia.org

# Get Tranco rank
rank = metrics.get_tranco_rank(domain)
print(f"Tranco Rank: {rank}")  # Output: 28 (lower = more popular)

# Get domain age
age = metrics.get_domain_age(domain)
print(f"Domain Age: {age} years")  # Output: 25 years

# Get page HTML and screenshot
html, screenshot_b64 = metrics.get_selenium_data('https://www.wikipedia.org')
print(f"HTML length: {len(html)} chars")
print(f"Screenshot: {len(screenshot_b64)} chars (base64 PNG)")

# Extract metadata (author, date)
metadata = metrics.get_metadata(html)
print(f"Author: {metadata.get('author')}")
print(f"Date: {metadata.get('date')}")

# Calculate analysis confidence
confidence = metrics.calculate_analysis_confidence(
    domain_age=age,
    tranco_rank=rank,
    metadata=metadata,
    credibility_score=None
)
print(f"Analysis Confidence: {confidence}%")

# Get Gemini LLM analysis (requires API key and quota)
gemini_data = metrics.get_gemini_data(html, screenshot_b64, domain)
print(f"Bias: {gemini_data.get('bias')}")
print(f"Content Credibility: {gemini_data.get('content_credibility')}")
```

## Core Functions Reference

### Domain & Ranking
- `get_domain(url)` → Returns domain name
- `get_tranco_rank(domain)` → Returns global traffic rank (1-1M+)
- `get_domain_age(domain)` → Returns years since registration

### Scraping & Metadata
- `get_selenium_data(url)` → Returns (html, screenshot_base64)
- `get_metadata(html)` → Returns {"author": str, "date": str}

### Analysis
- `get_gemini_data(html, screenshot, domain)` → LLM analysis object
  - Returns: bias, sentiment, content_credibility, publisher_reputation, justifications
- `get_gemini_human_report(html, domain, gemini_data)` → Readable text summary
- `get_gemini_full_report(...)` → Multi-section comprehensive report
- `calculate_credibility_score(domain_age, tranco_rank, ai_data, metadata)` → 0-100 score
- `calculate_analysis_confidence(domain_age, tranco_rank, metadata, credibility_score)` → 0-100%

## Understanding Results

### Tranco Rank
The global traffic ranking of the domain:
- **1-1,000:** Extremely popular (top 0.1% of websites)
- **1,001-10,000:** Very popular (top 1%)
- **10,001-100,000:** Popular (top 10%)
- **100,001-1,000,000:** Well-known
- **1,000,000+:** Smaller/niche sites or unranked
- **None/null:** Website not ranked by Tranco

### Analysis Confidence (0-100%)
How confident the analysis is based on available data signals:
- **80-100%:** High confidence (domain age + rank + credibility score + metadata all available)
- **50-79%:** Medium confidence (most signals available)
- **Below 50%:** Low confidence (limited data available)

### Credibility Score (0-100)
With LLM analysis:
- **80-100:** Highly credible source
- **60-79:** Generally credible
- **40-59:** Mixed credibility signals
- **20-39:** Low credibility
- **0-19:** Likely fake/unreliable

## Troubleshooting

### Issue: Poetry command not found

**Solution:** Use `python -m poetry` instead:
```bash
python -m poetry install
python -m poetry run python test_urls.py
```

### Issue: "No Chrome/Chromium found"

**Solution:** Install Chrome or configure Selenium to use your browser path.

### Issue: GEMINI_API_KEY error

**Solution:** 
1. Ensure `.env` file exists in project root
2. Add valid `GEMINI_API_KEY` to `.env`
3. Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Issue: "Quota exceeded" (429 error)

**Solution:** 
1. Gemini free-tier limits 20 requests/day per model
2. Wait 24 hours for quota reset, OR
3. Upgrade to paid plan in [Google AI Console](https://aistudio.google.com), OR
4. Create new Google Cloud project for fresh quota

### Issue: SSL Certificate Verification Failed

**Solution:** This is expected for some websites. The backend uses requests with browser-like headers to handle this.

### Issue: Analysis fails with "Gemini API error"

**Solution:** 
1. Check your GEMINI_API_KEY is valid
2. Verify internet connectivity to Gemini API
3. Check if API quota is exceeded (use `python -m poetry run python test_urls.py` to test without LLM)
4. Try a different URL if the current one is blocked

## Performance Notes

- First request may take 10-20 seconds (Selenium browser initialization)
- Subsequent requests take 30-60 seconds (depending on page size)
- LLM analysis adds 5-15 seconds
- Keep browser open to reuse session for faster requests

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | Yes | - | Google Gemini API key |
| `GOOGLE_API_KEY` | No | - | Alternative to GEMINI_API_KEY |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | Gemini model version to use |

## License

This project is part of the Credibility research tool.
