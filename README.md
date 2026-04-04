# Credibility Backend - Website Analysis Service

A Python Flask backend service that analyzes website credibility using LLM-powered content analysis, domain age metrics, traffic rankings, and metadata extraction.

## Overview

This backend service evaluates website trustworthiness by:
- Extracting page content and screenshots via Selenium
- Analyzing content bias, sentiment, and credibility using Google Gemini AI
- Checking domain age via WHOIS/RDAP
- Retrieving traffic rankings from Tranco
- Generating comprehensive credibility reports
- Computing confidence percentages based on available data

## Prerequisites

- **Python 3.12+** (verify with `python --version`)
- **Poetry** (Python package manager)
- **Google Gemini API Key** (for live analysis)
- **Chrome/Chromium browser** (for Selenium)

## Installation

### 1. Clone or Copy Files

Ensure you have these files in your project directory:
```
credibility/
├── api/
│   ├── app.py
│   ├── metrics.py
│   └── routes.py
├── .env
├── pyproject.toml
├── poetry.lock
└── test_routes.py
```

### 2. Install Dependencies

```bash
# Install Python dependencies using Poetry
python -m poetry install
```

If Poetry is not recognized, ensure it's installed:
```bash
python -m pip install poetry
```

### 3. Set Environment Variables

Create or edit `.env` file in the project root:

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

## Running the Backend

### Start the Flask Server

```bash
# Using Poetry
python -m poetry run flask --app api/app --debug run --port=8080

# Or activate venv first, then run
.\.venv\Scripts\Activate.ps1  # PowerShell on Windows
poetry run flask --app api/app --debug run --port=8080
```

The server will start at `http://localhost:8080`

## Testing Websites

### 1. Quick Health Check

```bash
curl http://localhost:8080/health
```

Response:
```json
{"status": "ok"}
```

### 2. Check LLM Connectivity

```bash
curl http://localhost:8080/llm-health
```

Response (live mode):
```json
{
  "connected": true,
  "mode": "live",
  "model": "gemini-2.5-flash",
  "status_code": 200,
  "latency_ms": 1234
}
```

### 3. Analyze a Website

**Basic Request:**
```bash
curl "http://localhost:8080/analyze?url=https://www.goal.com"
```

**Response Fields:**
- `tranco_rank` - Global traffic ranking (lower is more popular)
- `analysis_confidence` - Confidence percentage (0-100%) based on available data
- `full_report` - Comprehensive multi-section analysis report with all metrics

### 4. Run Test Suite

```bash
# Run all endpoints smoke tests
python -m poetry run python test_routes.py
```

This tests:
- `/health` endpoint
- `/llm-health` endpoint (Gemini API connectivity)
- `/analyze` endpoint with a sample URL

## Testing the Backend

### Quick Terminal Testing

Test all endpoints directly from your terminal without writing code:

#### 1. Health Check
```bash
# Test if backend is running
curl http://localhost:8080/health
```
**Expected:**
```json
{"status": "ok"}
```

#### 2. LLM Connectivity
```bash
# Verify Gemini API is reachable
curl http://localhost:8080/llm-health
```
**Expected:**
```json
{"connected": true, "mode": "live", "status_code": 200, "latency_ms": 1234}
```

#### 3. Analyze a Website (Basic)
```bash
# Analyze a live website - replace URL with any website
curl "http://localhost:8080/analyze?url=https://www.goal.com/en/news/sample-article"
```

#### 4. Analyze Multiple Websites (Loop)

**PowerShell:**
```powershell
$urls = @(
  "https://www.goal.com",
  "https://www.bbc.com",
  "https://www.wikipedia.org"
)

foreach ($url in $urls) {
  Write-Host "Testing: $url"
  $uri = "http://localhost:8080/analyze?url=$url"
  $response = Invoke-WebRequest -Uri $uri -UseBasicParsing
  $json = $response.Content | ConvertFrom-Json
  Write-Host "  Tranco Rank: $($json.tranco_rank)"
  Write-Host "  Confidence: $($json.analysis_confidence)%"
  Write-Host ""
}
```

**Bash/Linux:**
```bash
# Test multiple URLs
for url in "https://www.goal.com" "https://www.bbc.com" "https://www.wikipedia.org"; do
  echo "Testing: $url"
  curl -s -G http://localhost:8080/analyze --data-urlencode "url=$url" | \
    python -m json.tool | grep -E "tranco_rank|analysis_confidence"
  echo ""
done
```

#### 5. Get Full Report Only

**PowerShell:**
```powershell
$url = "https://www.goal.com/en/news/article"
$response = curl -s "http://localhost:8080/analyze?url=$url" | ConvertFrom-Json
Write-Host $response.full_report
```

**Bash/Linux:**
```bash
url="https://www.goal.com/en/news/article"
curl -s "http://localhost:8080/analyze?url=$url" | python -c "import sys, json; print(json.load(sys.stdin)['full_report'])"
```

#### 6. Extract Specific Fields

**Get Tranco Rank:**
```bash
# Windows PowerShell
curl http://localhost:8080/analyze?url=https://www.goal.com | ConvertFrom-Json | Select-Object -ExpandProperty tranco_rank

# Bash/Linux
curl -s "http://localhost:8080/analyze?url=https://www.goal.com" | python -c "import sys, json; print(json.load(sys.stdin)['tranco_rank'])"
```

**Get Confidence Score:**
```bash
# Windows PowerShell
curl http://localhost:8080/analyze?url=https://www.goal.com | ConvertFrom-Json | Select-Object -ExpandProperty analysis_confidence

# Bash/Linux
curl -s "http://localhost:8080/analyze?url=https://www.goal.com" | python -c "import sys, json; print(json.load(sys.stdin)['analysis_confidence'])"
```

### Comprehensive Testing Methods

#### Step 1: Run Automated Tests
```bash
# Run smoke tests for all endpoints
python -m poetry run python test_routes.py
```

This tests:
- `/health` - Basic connectivity
- `/llm-health` - Gemini API reach
- `/analyze` - Full analysis pipeline

#### Step 2: Test in Python REPL

```bash
# Start interactive Python
python -m poetry run python
```

Then paste this code:
```python
import sys
sys.path.insert(0, 'api')
from app import app

client = app.test_client()

# Test health
print("=" * 50)
print("Testing /health")
r = client.get('/health')
print(f"Status: {r.status_code}")
print(f"Response: {r.get_json()}\n")

# Test LLM health
print("=" * 50)
print("Testing /llm-health")
r = client.get('/llm-health')
print(f"Status: {r.status_code}")
data = r.get_json()
print(f"Connected: {data.get('connected')}")
print(f"Latency: {data.get('latency_ms')}ms\n")

# Test analyze
print("=" * 50)
print("Testing /analyze")
url = 'https://www.goal.com/en/news/article'
r = client.get('/analyze', query_string={'url': url})
print(f"Status: {r.status_code}")
data = r.get_json()
print(f"Tranco Rank: {data.get('tranco_rank')}")
print(f"Confidence: {data.get('analysis_confidence')}%")
print(f"Report (first 500 chars): {data.get('full_report', '')[:500]}...")
```

#### Step 3: One-Liner Tests

**Check if backend is running:**
```bash
curl http://localhost:8080/health && echo "Backend is UP" || echo "Backend is DOWN"
```

**Get all three fields from /analyze:**
```bash
curl -s "http://localhost:8080/analyze?url=https://www.goal.com" | python -m json.tool
```

**Format analyze response as table:**
```bash
curl -s "http://localhost:8080/analyze?url=https://www.goal.com" | python -c "
import sys, json
d = json.load(sys.stdin)
print(f'Tranco Rank: {d[\"tranco_rank\"]}')
print(f'Confidence: {d[\"analysis_confidence\"]}%')
print(f'Report: {d[\"full_report\"][:200]}...')
"
```

## API Endpoints

### `GET /health`
Simple health check.
- **Response:** `{"status": "ok"}`

### `GET /llm-health`
Check Gemini API connectivity.
- **Query Parameters:** 
  - `timeout=15` (seconds, optional)
- **Response:** Connection status and latency

### `GET /analyze`
Perform full website credibility analysis.
- **Query Parameters:**
  - `url` (required) - Full website URL to analyze
  - Example: `/analyze?url=https://example.com/article`
- **Response:** 
  - `tranco_rank` - Traffic ranking
  - `analysis_confidence` - Confidence percentage (0-100%)
  - `full_report` - Comprehensive multi-section analysis

## Example Usage

### Python
```python
import requests

url = "https://www.goal.com/en/news/some-article"
response = requests.get(f"http://localhost:8080/analyze?url={url}")
data = response.json()

print(f"Tranco Rank: {data['tranco_rank']}")
print(f"Analysis Confidence: {data['analysis_confidence']}%")
print(f"\nFull Report:\n{data['full_report']}")
```

### JavaScript/Fetch
```javascript
const url = "https://www.goal.com/en/news/some-article";
const response = await fetch(`http://localhost:8080/analyze?url=${encodeURIComponent(url)}`);
const data = await response.json();

console.log(`Tranco Rank: ${data.tranco_rank}`);
console.log(`Analysis Confidence: ${data.analysis_confidence}%`);
console.log(data.full_report);
```

### cURL
```bash
curl -G http://localhost:8080/analyze \
  --data-urlencode "url=https://www.goal.com/en/news/some-article"
```

## Backend Response Example

```json
{
  "tranco_rank": 4521,
  "analysis_confidence": 75,
  "full_report": "[DOMAIN SIGNALS]\nDomain Age: 8 years\nTraffic Ranking: Top 5000 globally\n\n[ARTICLE METADATA]\nAuthor: John Doe\nPublish Date: 2024-03-15\n\n[CONTENT ANALYSIS]\n- Content Credibility: High\n- Bias Detected: False\n- Sentiment: Neutral\n... (continues with comprehensive analysis)"
}
```

## Understanding the Response

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

### Full Report
Multi-section comprehensive analysis including:
- **DOMAIN SIGNALS:** Age, traffic rank, registration details
- **ARTICLE METADATA:** Author, publish date, last modified date
- **CONTENT ANALYSIS:** Credibility assessment, bias detection, sentiment analysis, publisher reputation
- **CREDIBILITY SCORING:** Detailed scoring breakdown
- **EXPERT SUMMARY:** AI-generated human-readable summary

## Troubleshooting

### Issue: Poetry command not found

**Solution:** Use `python -m poetry` instead:
```bash
python -m poetry install
python -m poetry run flask --app api/app run
```

### Issue: "No Chrome/Chromium found"

**Solution:** Install Chrome or configure Selenium to use your browser path.

### Issue: GEMINI_API_KEY error

**Solution:** 
1. Ensure `.env` file exists in project root
2. Add valid `GEMINI_API_KEY` to `.env`
3. Get a key from [Google AI Studio](https://aistudio.google.com/app/apikey)

### Issue: SSL Certificate Verification Failed

**Solution:** This is expected for some websites. The backend uses requests with browser-like headers to handle this.

### Issue: Analysis fails with "Gemini API error"

**Solution:** 
1. Check your GEMINI_API_KEY is valid
2. Verify internet connectivity to Gemini API
3. Check if API quota is exceeded
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

## Support

For issues or questions about the backend service, check:
1. `.env` configuration
2. API key validity
3. Browser/Chrome installation
4. Network connectivity to Gemini API
