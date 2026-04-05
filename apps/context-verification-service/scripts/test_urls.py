import argparse
import sys
import time

sys.path.insert(0, "api")
import metrics  # noqa: E402


def test_one_url(url: str, with_llm: bool) -> dict:
    started = time.time()
    result = {
        "url": url,
        "ok": False,
        "error": None,
    }

    try:
        domain = metrics.get_domain(url)
        tranco_rank = metrics.get_tranco_rank(domain)
        domain_age = metrics.get_domain_age(domain)
        html, screenshot = metrics.get_selenium_data(url)
        metadata = metrics.get_metadata(html)
        confidence = metrics.calculate_analysis_confidence(
            domain_age=domain_age,
            tranco_rank=tranco_rank,
            metadata=metadata,
            credibility_score=None,
        )

        result.update(
            {
                "ok": True,
                "domain": domain,
                "tranco_rank": tranco_rank,
                "domain_age": domain_age,
                "analysis_confidence": confidence,
                "has_author": bool(metadata.get("author")),
                "has_date": bool(metadata.get("date")),
                "html_length": len(html),
                "screenshot_bytes_est": len(screenshot),
            }
        )

        if with_llm:
            try:
                gemini_data = metrics.get_gemini_data(html, screenshot, domain)
                llm_report = metrics.get_gemini_human_report(html, domain, gemini_data)
                credibility_score = metrics.calculate_credibility_score(
                    domain_age=domain_age,
                    tranco_rank=tranco_rank,
                    ai_data=gemini_data,
                    metadata=metadata,
                )
                full_report = metrics.get_gemini_full_report(
                    domain=domain,
                    domain_age=domain_age,
                    tranco_rank=tranco_rank,
                    gemini_data=gemini_data,
                    metadata=metadata,
                    credibility_score=credibility_score,
                    llm_report=llm_report,
                )
                confidence = metrics.calculate_analysis_confidence(
                    domain_age=domain_age,
                    tranco_rank=tranco_rank,
                    metadata=metadata,
                    credibility_score=credibility_score,
                )
                
                # Get final credibility decision
                decision = metrics.get_credibility_decision(
                    domain_age=domain_age,
                    tranco_rank=tranco_rank,
                    gemini_data=gemini_data,
                    credibility_score=credibility_score,
                    analysis_confidence=confidence,
                    metadata=metadata,
                )

                result.update(
                    {
                        "analysis_confidence": confidence,
                        "credibility_score": credibility_score,
                        "full_report_preview": full_report[:500],
                        "is_credible": decision["is_credible"],
                        "credibility_decision": decision["reasoning"],
                        "decision_confidence": decision["confidence"],
                        "llm_ok": True,
                    }
                )
            except Exception as llm_exc:
                result.update(
                    {
                        "llm_ok": False,
                        "llm_error": str(llm_exc),
                    }
                )

    except Exception as exc:
        result["error"] = str(exc)

    result["elapsed_sec"] = round(time.time() - started, 2)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Test multiple URLs directly via metrics.py")
    parser.add_argument(
        "urls",
        nargs="*",
        help="URLs to test. If omitted, a default list is used.",
    )
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Also run Gemini analysis (requires API key and available quota).",
    )
    args = parser.parse_args()

    urls = args.urls or [
        "https://www.wikipedia.org",
        "https://www.bbc.com",
        "https://www.goal.com",
    ]

    print(f"Testing {len(urls)} URL(s) | with_llm={args.with_llm}\n")

    passed = 0
    for idx, url in enumerate(urls, start=1):
        print(f"[{idx}/{len(urls)}] {url}")
        out = test_one_url(url, with_llm=args.with_llm)

        if out["ok"]:
            passed += 1
            print("  status: PASS")
            print(f"  domain: {out.get('domain')}")
            print(f"  tranco_rank: {out.get('tranco_rank')}")
            print(f"  domain_age: {out.get('domain_age')}")
            print(f"  analysis_confidence: {out.get('analysis_confidence')}%")
            print(f"  has_author: {out.get('has_author')} | has_date: {out.get('has_date')}")
            print(f"  html_length: {out.get('html_length')} | screenshot_len: {out.get('screenshot_bytes_est')}")
            if args.with_llm:
                if out.get("llm_ok"):
                    print("  llm_status: PASS")
                    print(f"  credibility_score: {out.get('credibility_score')}")
                    credible = "CREDIBLE ✓" if out.get('is_credible') else "NOT CREDIBLE ✗"
                    print(f"  credibility_decision: {credible}")
                    print(f"  decision_reasoning: {out.get('credibility_decision')}")
                    print(f"  decision_confidence: {out.get('decision_confidence')}%")
                    print(f"  full_report_preview: {out.get('full_report_preview')}")
                else:
                    print("  llm_status: FAIL")
                    print(f"  llm_error: {out.get('llm_error')}")
        else:
            print("  status: FAIL")
            print(f"  error: {out.get('error')}")

        print(f"  elapsed: {out.get('elapsed_sec')}s\n")

    print("=" * 60)
    print(f"Completed: {passed}/{len(urls)} passed")


if __name__ == "__main__":
    main()
