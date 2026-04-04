from flask import request, jsonify
from app import app
import metrics


@app.route("/health", methods=["GET"])
def health():
    return jsonify(status="ok")


@app.route("/llm-health", methods=["GET"])
def llm_health():
    timeout = request.args.get("timeout", default=15, type=int)
    result = metrics.test_llm_connectivity(timeout=timeout)
    status_code = 200 if result.get("connected") else 503
    return jsonify(result), status_code

@app.route("/analyze", methods=["GET"])
def analyze():
    url = request.args.get("url")
    if not url:
        return jsonify(error="No URL provided"), 400
    try:
        domain = metrics.get_domain(url)
        domain_age = metrics.get_domain_age(domain)
        tranco_rank = metrics.get_tranco_rank(domain)
        html, screenshot = metrics.get_selenium_data(url)
        gemini_data = metrics.get_gemini_data(html, screenshot, domain)
        llm_report = metrics.get_gemini_human_report(html, domain, gemini_data)
        metadata = metrics.get_metadata(html)
        credibility_score = metrics.calculate_credibility_score(domain_age, tranco_rank, gemini_data, metadata)
        full_report = metrics.get_gemini_full_report(domain, domain_age, tranco_rank, gemini_data, metadata, credibility_score, llm_report)
        analysis_confidence = metrics.calculate_analysis_confidence(domain_age, tranco_rank, metadata, credibility_score)
        return jsonify(
            tranco_rank=tranco_rank,
            analysis_confidence=analysis_confidence,
            full_report=full_report
        )
    except RuntimeError as e:
        message = str(e)
        status_code = 502
        if "status 429" in message:
            status_code = 429
        return jsonify(error=message), status_code
    except Exception as e:
        return jsonify(error=f"Unexpected backend error: {str(e)}"), 500