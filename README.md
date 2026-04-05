# TrustMeBro

> AI-powered content verification platform addressing the trust crisis in digital media.

In today's digital age, photos, videos, and documents can be subtly altered, AI-generated, or entirely fabricated. TrustMeBro provides automated, transparent verification across three functional axes:

1. **Content Authenticity** — Detect AI-generated or tampered media using forensic analysis and machine learning
2. **Contextual Consistency** — Verify whether content is being used in a misleading context by analyzing narrative-vs-content alignment
3. **Source Credibility** — Assess the reliability of the originating account, URL, or domain using heuristic and indexed dataset checks

Every verification result includes a **trust rating**, **confidence score**, **status** (verified / suspicious / unverifiable), and a **human-readable explanation** so users understand *why* the AI reached its conclusion.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    CloudFront + WAF + API Gateway             │
└────────────┬──────────────────────────────────┬──────────────┘
             │                                  │
    ┌────────▼─────────┐             ┌──────────▼──────────┐
    │  Source Verify    │ ──Kafka──▶  │  Content Verify     │
    │  Service (HTTP)   │             │  Worker (Consumer)   │
    └────────┬─────────┘             └──────────┬──────────┘
             │                                  │
    ┌────────▼──────────────────────────────────▼──────────┐
    │              Amazon MSK (Kafka)                       │
    │  Topics: content-verification.requested               │
    │          content-verification.completed                │
    │          source-verification.audit                     │
    └──────────────────────────────────────────────────────┘
             │                                  │
    ┌────────▼─────────┐             ┌──────────▼──────────┐
    │  S3 + Kendra     │             │  Rekognition +       │
    │  (Source DB)      │             │  Bedrock + SageMaker │
    └──────────────────┘             └─────────────────────┘
```

## Active Services

| Service | Role | Port |
|---------|------|------|
| `source-verification-service` | HTTP API — checks source trust via Kendra + local credibility heuristics, escalates to Kafka | 8080 |
| `content-verification-service` | Kafka consumer — runs the full verification pipeline (authenticity, consistency, credibility) | 8082 |
| `kafka-service` | Bootstraps MSK topics, exposes health endpoint | 8081 |
| `web-ui` | Static frontend with visual trust result rendering | 3000 |
| `extension-ui` | Chrome extension (Manifest V3) popup for quick source checks | — |

## Quick Start

```bash
# 1. Install dependencies
pnpm install

# 2. Start local Kafka (requires Docker)
cd packages/kafka && docker compose up -d && cd ../..

# 3. Start all services
pnpm dev
```

The web UI will be available at `http://localhost:3000`. Enter a source URL to see the trust analysis.

## Verification Output

Every verification produces a structured result:

- **Trust Rating** — 0.0 to 1.0 composite score
- **Confidence Score** — how confident the system is in its assessment
- **Status** — `verified`, `suspicious`, or `unverifiable`
- **Explanation** — human-readable reasoning
- **Credibility Breakdown** — per-signal analysis with impact indicators
- **Content Verification** (async) — tamper score, synthetic media score, narrative consistency, historical consistency

## Target AWS Setup

- `CloudFront` + `WAF` + `API Gateway HTTP API`
- `ECS Fargate` for the microservices
- `ECS Service Connect` for private service-to-service networking
- `Amazon S3` for source datasets and evidence storage
- `Amazon Kendra` for source discovery
- `Amazon MSK` for Kafka
- `Amazon Rekognition` + `SageMaker` for media forensics
- `Amazon Bedrock` for narrative consistency analysis
- `Amazon Textract` for document extraction
- `Secrets Manager` for configuration and credentials
- `CloudWatch` for logs, metrics, and alarms

See `opus.md` for the architecture brief and `infra/aws/README.md` for the rollout scaffold.
