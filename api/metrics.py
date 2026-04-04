import requests
from tranco import Tranco
from datetime import datetime
import datetime as dt
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json
import os
import time

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
GEMINI_TEST_MODE = os.getenv("GEMINI_TEST_MODE", "false").lower() in {"1", "true", "yes", "on"}

t = Tranco(cache=True, cache_dir=".tranco")
chrome_options = Options()
chrome_options.add_argument("--headless=new")  # Use the new headless mode introduced in Chrome 109
chrome_options.add_argument("--window-size=1920,1080")  # Set a common resolution
chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Prevent detection
chrome_options.add_argument("--disable-gpu")  # Disable GPU hardware acceleration
chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
chrome_options.add_argument("--remote-debugging-port=9222")  # Enable remote debugging

# Make the browser appear more like a real user
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
chrome_options.add_argument(f"user-agent={user_agent}")

_driver = None


def _get_driver():
    global _driver
    if _driver is not None:
        return _driver

    local_driver = os.path.join(os.path.dirname(__file__), "chromedriver")
    local_driver_exe = f"{local_driver}.exe"

    # Prefer a checked-in driver when present, otherwise let Selenium Manager resolve it.
    if os.path.isfile(local_driver):
        _driver = webdriver.Chrome(service=Service(local_driver), options=chrome_options)
    elif os.path.isfile(local_driver_exe):
        _driver = webdriver.Chrome(service=Service(local_driver_exe), options=chrome_options)
    else:
        _driver = webdriver.Chrome(options=chrome_options)

    return _driver

def get_domain(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def get_domain_age(domain):
    def _parse_datetime(value):
        if not value:
            return None

        if isinstance(value, list):
            for item in value:
                parsed = _parse_datetime(item)
                if parsed:
                    return parsed
            return None

        if not isinstance(value, str):
            return None

        for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=dt.UTC)
            except ValueError:
                continue

        try:
            iso_value = value.replace("Z", "+00:00")
            return datetime.fromisoformat(iso_value)
        except ValueError:
            return None

    url = f"https://who-dat.as93.net/{domain}"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        json_response = response.json()
        created_date = _parse_datetime(json_response.get("domain", {}).get("created_date"))
        if created_date:
            current_date = datetime.now(dt.UTC)
            domain_age = current_date.year - created_date.year
            return domain_age
    except requests.exceptions.RequestException:
        pass

    # Fallback: use RDAP registration event when who-dat is blocked.
    rdap_url = f"https://rdap.org/domain/{domain}"
    try:
        rdap_response = requests.get(rdap_url, timeout=15)
        rdap_response.raise_for_status()
        rdap_json = rdap_response.json()
        created_date = None
        for event in rdap_json.get("events", []):
            action = str(event.get("eventAction", "")).lower()
            if action == "registration":
                created_date = _parse_datetime(event.get("eventDate"))
                if created_date:
                    break

        if created_date:
            current_date = datetime.now(dt.UTC)
            domain_age = current_date.year - created_date.year
            return domain_age
    except requests.exceptions.RequestException:
        pass

    return None

def get_tranco_rank(domain):
    return t.list().rank(domain)

def get_selenium_data(url):
    if GEMINI_TEST_MODE:
        # In test mode, use requests to get HTML instead of Selenium
        try:
            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                },
            )
            response.raise_for_status()
            html = response.text
            # Create a minimal test screenshot (1x1 PNG)
            screenshot = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
            return html, screenshot
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to fetch URL {url}: {str(e)}")

    driver = _get_driver()
    driver.get(url)
    html = driver.page_source
    screenshot = driver.get_screenshot_as_base64()
    return html, screenshot


def _parse_llm_json_text(text):
    if not isinstance(text, str):
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None

    return None


def _normalize_gemini_output(raw_text):
    normalize_prompt = (
        "Convert the following content into a strict JSON object with exactly these keys: "
        "screenshot_notes, additional_notes, bias_justification, bias, sentiment_justification, sentiment, "
        "content_credibility_justification, content_credibility, publisher_reputation_justification, publisher_reputation. "
        "Rules: return JSON only, no markdown; sentiment must be -1, 0, or 1; content_credibility must be 0, 1, or 2; "
        "bias and publisher_reputation must be booleans.\n\n"
        f"Input content:\n{raw_text}"
    )

    normalize_payload = {
        "contents": [{"role": "user", "parts": [{"text": normalize_prompt}]}],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 700,
            "responseMimeType": "application/json",
        },
    }

    normalize_response = requests.post(
        GEMINI_URL,
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        json=normalize_payload,
        timeout=90,
    )
    if not normalize_response.ok:
        return None

    try:
        normalized_data = normalize_response.json()
        normalized_text = normalized_data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError, ValueError):
        return None

    return _parse_llm_json_text(normalized_text)


def get_gemini_human_report(html, domain, gemini_data):
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY or GOOGLE_API_KEY environment variable")

    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)
    page_text_sample = page_text[:5000]

    report_prompt = (
        "You are a media literacy assistant. Produce a concise human-readable report in plain text (no markdown). "
        "Write 6-10 short sentences. Include: source overview, likely bias, sentiment tone, credibility concerns, "
        "publisher reputation context, and a practical recommendation for a student/researcher. "
        "Use the structured analysis as anchor truth and avoid contradicting it.\n\n"
        f"Domain: {domain}\n"
        f"Structured analysis JSON: {json.dumps(gemini_data)}\n"
        f"Page text sample: {page_text_sample}"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": report_prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 350,
        },
    }

    response = requests.post(
        GEMINI_URL,
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    if not response.ok:
        error_details = None
        try:
            error_details = response.json()
        except ValueError:
            error_details = response.text[:300]
        raise RuntimeError(
            f"Gemini human-report request failed with status {response.status_code}: {error_details}"
        )

    response_data = response.json()
    try:
        report_text = response_data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError, ValueError):
        raise RuntimeError("Gemini returned an invalid response for the human-readable report")

    return report_text.strip()


def get_gemini_data(html, screenshot, domain):
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY or GOOGLE_API_KEY environment variable")

    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text()
    prompt = f"""You are a content quality expert.
You will be provided with a webpage's text content and a screenshot of the webpage, along with the domain of the webpage.
Your task is to analyze the text content and domain to provide a structured JSON response including the following metrics:
1. screenshot_notes (string): Provide any notes based on the screenshot of the webpage.
2. additional_notes (string): Provide any additional notes based on the text content and domain.
3. bias_justification (string): Indicate if the text is biased or unbiased. Provide a brief justification for your bias assessment. Bias can be political, religious, or any other form of bias.
4. bias (bool): Provide a single rating for the overall bias of the text (true, false) based on the justification provided.
5. sentiment_justification (string): Indicate the sentiment of the text (positive [1], negative [-1], neutral [0]). Provide a brief justification for your sentiment assessment. Sentiment can be positive, negative, or neutral. Information that is factual and unbiased should be rated as neutral.
6. sentiment (int): Provide a single rating for the overall sentiment of the text (-1, 0, 1) based on the justification provided.
7. content_credibility_justification (string): Assess the overall credibility of the content. Provide a brief justification for your content credibility assessment. Highly credible (2) means the content is well-written, informative, and engaging. Credible (1) means the content is somewhat informative but lacks depth or clarity. Not credible (0) means the content is poorly written, inaccurate, misleading, factually incorrect, or satirical. Any website that should not be included in research or a school paper should be rated as low quality (0).
8. content_credibility (int): Provide a single rating for the overall credibility of the content (not credible, credible, highly credible) based on the justification provided.
9. publisher_reputation_justification (string): Indicate whether the domain is associated with a well-known and reputable publisher. Provide a brief justification for your publisher reputation assessment. A reputable publisher is one that is well-known, respected, and has a history of producing accurate and reliable content.
10. publisher_reputation (bool): Provide a single rating for the publisher reputation (true, false) based on the justification provided.

Lean towards providing a conservative estimate for the metrics. It is better to underestimate than overestimate the quality of the content. Anything that is factually incorrect, misleading, or poorly written should be rated as low quality.
Provide the response strictly in JSON format. Do not include markdown code blocks or any additional text."""

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": f"{prompt}\n\nText:\n{page_text}\n\nDomain:\n{domain}"},
                    {
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": screenshot,
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 500,
            "responseMimeType": "application/json",
        },
    }

    response = requests.post(
        GEMINI_URL,
        params={"key": GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},      json=payload,
        timeout=120,
    )
    if not response.ok:
        error_details = None
        try:
            error_details = response.json()
        except ValueError:
            error_details = response.text[:300]
        raise RuntimeError(
            f"Gemini API request failed with status {response.status_code}: {error_details}"
        )

    response_data = response.json()
    content = response_data["candidates"][0]["content"]["parts"][0]["text"]

    parsed = _parse_llm_json_text(content)
    if parsed is not None:
        return parsed

    normalized = _normalize_gemini_output(content)
    if normalized is not None:
        return normalized

    raise RuntimeError("Gemini returned non-JSON content and normalization failed")


def test_llm_connectivity(timeout=15):
    started = time.time()

    if not GEMINI_API_KEY:
        return {
            "connected": False,
            "mode": "live",
            "model": GEMINI_MODEL,
            "status_code": None,
            "latency_ms": 0,
            "message": "Missing GEMINI_API_KEY or GOOGLE_API_KEY environment variable",
        }

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": "Respond with exactly: pong"}],
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 8,
        },
    }

    try:
        response = requests.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=timeout,
        )
    except requests.exceptions.RequestException as e:
        return {
            "connected": False,
            "mode": "live",
            "model": GEMINI_MODEL,
            "status_code": None,
            "latency_ms": int((time.time() - started) * 1000),
            "message": f"Gemini connectivity request failed: {str(e)}",
        }

    latency_ms = int((time.time() - started) * 1000)
    if not response.ok:
        error_details = None
        try:
            error_details = response.json()
        except ValueError:
            error_details = response.text[:300]
        return {
            "connected": False,
            "mode": "live",
            "model": GEMINI_MODEL,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "message": f"Gemini API request failed: {error_details}",
        }

    try:
        response_data = response.json()
        content = response_data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, ValueError, TypeError):
        content = None

    return {
        "connected": True,
        "mode": "live",
        "model": GEMINI_MODEL,
        "status_code": response.status_code,
        "latency_ms": latency_ms,
        "message": "Gemini connectivity check succeeded.",
        "response_preview": content,
    }

def get_metadata(html):
    soup = BeautifulSoup(html, "html.parser")
    # author
    # find any meta tag containing author in the name attribute (it can be author, article:author, etc.)
    author = soup.find("meta", attrs={"name": lambda x: x and "author" in x.lower()})
    if author:
        author = author["content"]
    else:
        author = None
    # date
    # find any meta tag containing date in the name attribute (it can be date, article:date, etc.)
    date = soup.find("meta", attrs={"name": lambda x: x and "date" in x.lower()})
    if date:
        date = date["content"]
    else:
        date = None
    return {
        "author": author,
        "date": date
    }

def calculate_credibility_score(domain_age, tranco_rank, ai_data, metadata):
    credibility_score = 0
    if not domain_age:
        return None

    if domain_age >= 10:
        credibility_score += 10
    elif domain_age >= 5:
        credibility_score += 5
    
    if tranco_rank >= 1:
        if tranco_rank <= 1000:
            credibility_score += 20
        elif tranco_rank <= 5000:
            credibility_score += 15
        elif tranco_rank <= 10000:
            credibility_score += 10
        elif tranco_rank <= 50000:
            credibility_score += 5
    
    if ai_data["content_credibility"] == 2:
        credibility_score += 30
    elif ai_data["content_credibility"] == 1:
        credibility_score += 15
    
    if not ai_data["bias"]:
        credibility_score += 10
    
    if ai_data["publisher_reputation"]:
        credibility_score += 20
    
    if metadata["author"]:
        credibility_score += 5
    
    if metadata["date"]:
        credibility_score += 5

    return credibility_score


def get_fake_assessment(credibility_score, ai_data):
    # Prefer final credibility score when available.
    if credibility_score is not None:
        credibility_score = max(0, min(100, int(credibility_score)))
        fake_percentage = 100 - credibility_score
        is_fake = fake_percentage >= 70
        return {
            "is_fake": is_fake,
            "fake_percentage": fake_percentage,
            "confidence_source": "credibility_score",
        }

    # Fallback: infer from AI metrics when score could not be computed.
    base = 50
    content_credibility = ai_data.get("content_credibility")
    if content_credibility == 2:
        base -= 30
    elif content_credibility == 1:
        base -= 10
    elif content_credibility == 0:
        base += 25

    if ai_data.get("bias"):
        base += 10
    else:
        base -= 5

    if ai_data.get("publisher_reputation"):
        base -= 15
    else:
        base += 5

    sentiment = ai_data.get("sentiment")
    if sentiment == -1:
        base += 5

    fake_percentage = max(0, min(100, int(base)))
    is_fake = fake_percentage >= 50
    return {
        "is_fake": is_fake,
        "fake_percentage": fake_percentage,
        "confidence_source": "ai_fallback",
    }


def calculate_analysis_confidence(domain_age, tranco_rank, metadata, credibility_score):
    """
    Calculate confidence percentage (0-100) based on available data signals.
    More data = higher confidence.
    """
    confidence = 0
    max_confidence = 100

    # Domain age: +20 if available
    if domain_age is not None:
        confidence += 20

    # Tranco rank: +20 if available and ranked (not -1)
    if tranco_rank is not None and tranco_rank > 0:
        confidence += 20

    # Metadata signals: +15 if author present, +15 if date present
    if metadata and metadata.get("author"):
        confidence += 15
    if metadata and metadata.get("date"):
        confidence += 15

    # Credibility score: +30 if available
    if credibility_score is not None:
        confidence += 30

    return min(confidence, max_confidence)


def get_gemini_full_report(domain, domain_age, tranco_rank, gemini_data, metadata, credibility_score, llm_report):
    """
    Generate a comprehensive analysis report with all key findings.
    """
    lines = []
    lines.append(f"[FULL CREDIBILITY REPORT FOR {domain.upper()}]\n")

    # Domain Signals
    lines.append("=== DOMAIN SIGNALS ===")
    if domain_age is not None:
        lines.append(f"Domain Age: {domain_age} years old")
    else:
        lines.append("Domain Age: Unable to resolve from WHOIS/RDAP")

    if tranco_rank and tranco_rank > 0:
        if tranco_rank <= 1000:
            rank_desc = "Very High (Top 1,000 globally)"
        elif tranco_rank <= 10000:
            rank_desc = "High (Top 10,000 globally)"
        elif tranco_rank <= 100000:
            rank_desc = "Medium (Top 100,000 globally)"
        else:
            rank_desc = f"Low (Rank {tranco_rank})"
        lines.append(f"Tranco Ranking: {rank_desc}")
    else:
        lines.append("Tranco Ranking: Not in top 100,000 (likely lower traffic)")

    # Metadata
    lines.append("\n=== ARTICLE METADATA ===")
    if metadata and metadata.get("author"):
        lines.append(f"Author Identified: {metadata['author']}")
    else:
        lines.append("Author Identified: No")

    if metadata and metadata.get("date"):
        lines.append(f"Publish Date Found: {metadata['date']}")
    else:
        lines.append("Publish Date Found: No")

    # AI Content Analysis
    lines.append("\n=== CONTENT ANALYSIS (AI-Powered) ===")
    
    credibility_level = {0: "Low", 1: "Medium", 2: "High"}.get(gemini_data.get("content_credibility"), "Unknown")
    lines.append(f"Content Credibility: {credibility_level}")
    if gemini_data.get("content_credibility_justification"):
        lines.append(f"  Reason: {gemini_data.get('content_credibility_justification')}")

    bias_status = "Detected" if gemini_data.get("bias") else "Not Detected"
    lines.append(f"Bias: {bias_status}")
    if gemini_data.get("bias_justification"):
        lines.append(f"  Details: {gemini_data.get('bias_justification')}")

    sentiment_map = {-1: "Negative", 0: "Neutral", 1: "Positive"}
    sentiment = sentiment_map.get(gemini_data.get("sentiment"), "Unknown")
    lines.append(f"Sentiment: {sentiment}")
    if gemini_data.get("sentiment_justification"):
        lines.append(f"  Details: {gemini_data.get('sentiment_justification')}")

    rep_status = "Reputable" if gemini_data.get("publisher_reputation") else "Not Well-Known"
    lines.append(f"Publisher Reputation: {rep_status}")
    if gemini_data.get("publisher_reputation_justification"):
        lines.append(f"  Details: {gemini_data.get('publisher_reputation_justification')}")

    # Scoring & Confidence
    lines.append("\n=== CREDIBILITY SCORING ===")
    if credibility_score is not None:
        lines.append(f"Overall Credibility Score: {int(credibility_score)} / 100")
    else:
        lines.append("Overall Credibility Score: Unable to compute (insufficient domain data)")

    confidence_pct = calculate_analysis_confidence(domain_age, tranco_rank, metadata, credibility_score)
    lines.append(f"Analysis Confidence: {confidence_pct}%")

    # Summary
    lines.append("\n=== EXPERT SUMMARY ===")
    lines.append(llm_report)

    return "\n".join(lines)


if __name__ == "__main__":
    url = "https://www.dhmo.org/facts.html"
    domain = get_domain(url)
    domain_age = get_domain_age(domain)
    print(domain_age)
    tranco_rank = get_tranco_rank(domain)
    print(tranco_rank)
    html, screenshot = get_selenium_data(url)
    ai_data = get_gemini_data(html, screenshot, domain)
    print(ai_data)
    metadata = get_metadata(html)
    print(metadata)
    credibility_score = calculate_credibility_score(domain_age, tranco_rank, ai_data, metadata)
    print(credibility_score)