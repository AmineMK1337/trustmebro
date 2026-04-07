# Reinforcement Learning in Source Verification Service

## Overview

This agent uses reinforcement learning in a practical, lightweight form:

- A contextual bandit (LinUCB) learns which analysis layers to run.
- A ReAct-style loop executes selected layers step by step.
- A reward function updates the policy after each evaluation.

This design improves accuracy-cost tradeoffs without requiring a heavy deep RL stack.

## What "RL" means here

The current implementation is not full end-to-end PPO training by default. It is:

1. Online learning with a contextual bandit.
2. Reward-driven policy updates after each episode.
3. Episodic decision making over a small discrete action space.

In short: this is reinforcement learning, but in the bandit setting (single decision policy over context), combined with a sequential reasoning executor.

## Where it is implemented

- Policy and state featurization: `agent/bandit_policy.py`
- Reward design: `agent/reward.py`
- ReAct execution + policy update integration: `agent/react_agent.py`

## RL state (context)

The policy receives an 8-feature state vector (from `build_state`):

- has_url
- has_text
- has_metadata
- url_length_norm
- domain_prescore
- text_length_norm
- metadata_quality
- bias_term

These features summarize what evidence is available and how informative it may be.

## Action space

The bandit chooses one of 7 actions, where each action is a layer combination:

- domain-only
- content-only
- behavior-only
- domain+content
- domain+behavior
- content+behavior
- all-layers

This is the main RL decision: how much evidence to collect for a given input.

## Reward signal

The reward function (`compute_reward`) balances three objectives:

1. Accuracy
- Exact risk match: +1.00
- Adjacent risk match: +0.40
- Opposite-direction error: -1.00

2. Cost penalties
- Content layer (LLM call) used: -0.25
- Each extra layer after the first: -0.08

3. Efficiency bonus
- Correct with <=2 layers: +0.15

This drives the policy toward minimal-cost, sufficiently accurate decisions.

## Learning loop

For each evaluation episode (`AdaptiveAgent.evaluate`):

1. Build initial state from input.
2. Policy selects target layer set (`select_action`).
3. ReAct loop executes layers in priority order with early-stop gates.
4. Final score maps to risk label.
5. Reward is computed against provided or simulated ground truth.
6. Policy is updated (`policy.update`) using the observed reward.

If `learn=False`, the agent runs inference only and does not update the policy.

## Why this approach was chosen

- Fast to train online and cheap to run.
- Explicitly optimizes accuracy vs latency/API cost.
- Easy to inspect and explain (important for trust/safety workflows).
- Works well with sparse or partially available inputs.

## PPO-compatible upgrade path

The architecture in `agent/react_agent.py` is intentionally structured to be upgraded to full RL:

- state: observation vector
- action: discrete layer/control action
- reward: from `reward.py`
- done: episode termination

`CredibilityEnv` provides a gym-style interface (`reset`/`step`) so a PPO or DQN policy can replace the bandit when needed.

## Practical summary

The service currently uses contextual bandit RL in production-style logic, not deep neural RL by default. It still learns from reward feedback and adapts layer selection over time, while remaining interpretable and computationally lightweight.