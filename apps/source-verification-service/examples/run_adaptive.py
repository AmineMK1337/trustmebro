"""
examples/run_adaptive.py
========================
Full demonstration of Phase 1 (Contextual Bandit) + Phase 2 (ReAct Agent).

Sections:
  A. Phase 1 demo  — SourceAgent with use_bandit=True
     Shows the bandit selecting layers, getting rewards, learning over time.

  B. Phase 2 demo  — AdaptiveAgent (ReAct loop)
     Shows sequential step-by-step reasoning with early stopping.

  C. Learning simulation — 10 articles, bandit improves over iterations.

  D. Bandit stats   — action selection distribution after training.

Run:
    python examples/run_adaptive.py
Or with Gemini:
    GEMINI_API_KEY=your_key python examples/run_adaptive.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.source_agent  import SourceAgent
from agent.react_agent   import AdaptiveAgent
from agent.bandit_policy import ContextualBanditPolicy, build_state
from agent.reward        import reward_breakdown, compute_reward_batch


# ─────────────────────────────────────────────────────────────────────────────
# Test data set — 5 articles with known ground truth labels
# ─────────────────────────────────────────────────────────────────────────────

ARTICLES = [
    {
        "label":        "Obvious misinformation",
        "ground_truth": "High",
        "url":          "http://real-official-truth-alert.xyz/breaking",
        "text": (
            "BREAKING!!! THEY DON'T WANT YOU TO KNOW!!! "
            "SHOCKING secret EXPOSED by brave insiders! "
            "Cover-up CONFIRMED by sources!! Share before deleted!!!"
        ),
        "metadata": {
            "username": "user847291637",
            "account_age_days": 2,
            "posts_per_day": 200,
            "verified": False,
            "bio": "",
            "followers": 5,
            "recycled_content": True,
            "anonymous": True,
        },
    },
    {
        "label":        "Reuters article",
        "ground_truth": "Low",
        "url":          "https://reuters.com/world/economy/fed-holds-rates-2025",
        "text": (
            "The Federal Reserve held interest rates steady at its May meeting, "
            "citing continued progress on inflation. Fed Chair Jerome Powell said "
            "policymakers need more data before considering cuts. "
            "The decision was unanimous."
        ),
        "metadata": {
            "username": "Reuters_Breaking",
            "account_age_days": 5000,
            "posts_per_day": 20,
            "verified": True,
            "bio": "Reuters official breaking news account.",
            "followers": 22000000,
        },
    },
    {
        "label":        "Borderline tabloid",
        "ground_truth": "Medium",
        "url":          "https://breaking-news-today.info/story/456",
        "text": (
            "Sources close to the White House claim the president is 'furious' "
            "about the latest scandal. Insiders say the situation is 'out of control'. "
            "Many experts reportedly believe this could end his presidency. "
            "Allegedly, key emails were withheld."
        ),
        "metadata": {
            "username": "political_insider_2024",
            "account_age_days": 60,
            "posts_per_day": 15,
            "verified": False,
            "bio": "Independent political commentary.",
            "followers": 800,
        },
    },
    {
        "label":        "Scientific article",
        "ground_truth": "Low",
        "url":          "https://nature.com/articles/exercise-heart-2025",
        "text": (
            "A randomised controlled trial published in Nature Medicine found "
            "that 150 minutes of moderate exercise weekly reduces cardiovascular "
            "mortality by 28% (HR 0.72, 95% CI 0.61-0.85, p<0.001). "
            "Dr. Sarah Chen, the lead author, stated the effect was consistent "
            "across age groups and demographics."
        ),
        "metadata": {
            "username": "NatureMedicine",
            "account_age_days": 3650,
            "posts_per_day": 3,
            "verified": True,
            "bio": "Nature Medicine — peer-reviewed research.",
            "followers": 500000,
        },
    },
    {
        "label":        "Suspicious crypto news",
        "ground_truth": "High",
        "url":          "http://cryptoalert-insider-news.buzz/pump",
        "text": (
            "URGENT: Bitcoin is about to EXPLODE 10000%!! "
            "Hidden signals confirm massive pump incoming! "
            "Anonymous whale sources confirm: buy NOW before it's too late! "
            "This information is being suppressed by the banks!!!"
        ),
        "metadata": {
            "username": "crypto_alert_bot_9912",
            "account_age_days": 7,
            "posts_per_day": 80,
            "verified": False,
            "bio": "",
            "followers": 20,
            "recycled_content": True,
            "anonymous": True,
        },
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# A. PHASE 1 DEMO — SourceAgent with bandit
# ─────────────────────────────────────────────────────────────────────────────

def demo_phase1():
    print("\n" + "█" * 60)
    print("  PHASE 1 — Contextual Bandit (SourceAgent, use_bandit=True)")
    print("█" * 60)

    agent = SourceAgent(verbose=True, use_bandit=True)

    for article in ARTICLES[:3]:
        print(f"\n{'▓' * 55}")
        print(f"  Article: {article['label']}  (truth={article['ground_truth']})")
        print("▓" * 55)

        result = agent.run(
            url=article.get("url"),
            text=article.get("text"),
            metadata=article.get("metadata"),
            ground_truth=article["ground_truth"],
        )

        # Show bandit details
        b = result.get("bandit", {})
        if b:
            print(f"  📊 Layers selected : {b['layers']}")
            print(f"  🏆 Reward          : {b['reward']:+.3f}")
            print(f"  📝 Breakdown       : {b['reward_detail']['label']}")

    print("\n  🎰 Bandit stats after 3 articles:")
    stats = agent.bandit_stats()
    for action, count in stats["action_counts"].items():
        mean_r = stats["mean_rewards"][action]
        if count > 0:
            print(f"    {action:<30} selected={count}  mean_reward={mean_r:+.3f}")


# ─────────────────────────────────────────────────────────────────────────────
# B. PHASE 2 DEMO — AdaptiveAgent ReAct loop
# ─────────────────────────────────────────────────────────────────────────────

def demo_phase2():
    print("\n" + "█" * 60)
    print("  PHASE 2 — ReAct Sequential Reasoning (AdaptiveAgent)")
    print("█" * 60)

    agent = AdaptiveAgent(verbose=True, learn=True)

    for article in ARTICLES:
        print(f"\n{'▓' * 55}")
        print(f"  Article: {article['label']}  (truth={article['ground_truth']})")
        print("▓" * 55)

        result = agent.evaluate(
            url=article.get("url"),
            text=article.get("text"),
            metadata=article.get("metadata"),
            ground_truth=article["ground_truth"],
        )

        # Print trace
        agent.print_trace(result)
        print(f"  ⏱  Steps used: {result['steps_used']} / 4")
        print(f"  🔍 Layers run: {list(result['details'].keys())}")


# ─────────────────────────────────────────────────────────────────────────────
# C. LEARNING SIMULATION — 10 rounds, watch bandit improve
# ─────────────────────────────────────────────────────────────────────────────

def demo_learning_curve():
    print("\n" + "█" * 60)
    print("  LEARNING SIMULATION — 10 iterations (Phase 1)")
    print("█" * 60)
    print("  Watching bandit learn optimal layer selection over time...\n")

    policy = ContextualBanditPolicy(alpha=0.5)
    import random; random.seed(42)

    cumulative_reward = 0.0

    for i, article in enumerate(ARTICLES * 2, 1):   # 10 total
        state = build_state(
            url=article.get("url"),
            text=article.get("text"),
            metadata=article.get("metadata"),
        )

        action = policy.select_action(state)

        # Simulate: all-layers gives most accurate result
        simulated_score = 80 if article["ground_truth"] == "High" else (
            50 if article["ground_truth"] == "Medium" else 15
        )
        from utils.helpers import score_to_risk
        prediction = score_to_risk(simulated_score)

        rb = reward_breakdown(
            prediction=prediction,
            ground_truth=article["ground_truth"],
            action=action,
        )
        policy.update(state, action, rb["total"])
        cumulative_reward += rb["total"]

        print(
            f"  [{i:02d}] {article['label'][:28]:<28} "
            f"action={action['label']:<22} "
            f"reward={rb['total']:+.2f}  "
            f"cumulative={cumulative_reward:+.2f}"
        )

    print("\n  Final bandit action preferences:")
    stats = policy.stats()
    for action, mean_r in sorted(
        stats["mean_rewards"].items(), key=lambda x: -x[1]
    ):
        count = stats["action_counts"][action]
        bar   = "█" * max(0, int((mean_r + 1.5) * 10))
        print(f"    {action:<30} {bar}  mean={mean_r:+.3f}  n={count}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    gemini = bool(os.environ.get("GEMINI_API_KEY"))
    print(f"\n{'═' * 60}")
    print(f"  ADAPTIVE SOURCE CREDIBILITY AGENT — DEMO")
    print(f"  Gemini: {'✅ configured' if gemini else '⚠️  offline (rule-based fallback)'}")
    print(f"{'═' * 60}")

    demo_phase1()
    demo_phase2()
    demo_learning_curve()

    print(f"\n{'═' * 60}")
    print(f"  DEMO COMPLETE")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
