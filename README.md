# TrustMeBro

Team: `Binary Brains`

Presentation:
`https://canva.link/dhgvpo8umy0z5ne`

TrustMeBro is a multi-service content verification platform for checking social posts across four verification layers:

- source verification
- content verification
- context verification
- Kafka-backed orchestration

The current codebase combines Python Flask services, a Next.js app, a Node Kafka helper, and a browser extension prototype.

## Application Architecture

![Application Architecture](Application%20Architecture.png)

## Services

| Service | Runtime | Port | Role |
|---------|---------|------|------|
| `source-verification-service` | Python / Flask | `8080` | Adaptive source credibility service. Uses contextual-bandit + ReAct reasoning over domain/content/behavior layers, then can escalate downstream verification work to Kafka. |
| `content-verification-service` | Python / Flask | `8082` | Private worker that consumes Kafka jobs and produces content-verification results. |
| `context-verification-service` | Next.js | `3000` | Public web app and API for contextual consistency checks using Gemini, reverse image search, and linked-article extraction. |
| `kafka-service` | Node / Express | `8081` | Private Kafka bootstrap and health service for required topics. |
| `extension-ui` | Chrome extension + local Flask helper | `5000` local helper | Experimental browser extension flow for scraping posts and sending verification payloads. |

## Current Architecture

The app currently behaves like this:

1. `context-verification-service` exposes a web UI and `/api/verify` route for contextual consistency analysis.
2. `source-verification-service` can publish verification requests to Kafka when a source needs deeper review.
3. `content-verification-service` consumes Kafka messages, runs asynchronous verification, and publishes results back to Kafka.
4. `kafka-service` ensures required Kafka topics exist and provides a simple health endpoint.
5. `extension-ui` is a separate prototype path for scraping social content locally and sending it to a local helper backend.

## Source Verification Process

![Source Verification Process](Source%20Verification%20Process.png)

`source-verification-service` receives a source through `/verify`, runs the adaptive source agent flow (bandit + ReAct), returns a scored decision, and pushes non-verified cases to Kafka for deeper review.

The Source Credibility Agent evaluates online content using three layers: *URL structure, content analysis, and source behavior*, each contributing to a final score.
A contextual bandit policy and ReAct loop dynamically choose how much analysis is needed for each case.
It outputs a credibility score, risk level, and clear explanations, while continuously improving its decisions through feedback.
See [apps/source-verification-service/RL.md](apps/source-verification-service/RL.md) for implementation details.

## Content Verification Process

<img width="933" height="604" alt="image" src="https://github.com/user-attachments/assets/cb09c597-a6cf-4725-960d-64082f223a54" />

`content-verification-service` consumes Kafka verification jobs, runs the content pipeline, and publishes structured results back to Kafka.

## Context Verification Process

![Context Verification Process](Context%20Verification%20Process.png)

`context-verification-service` serves the web app and `/api/verify`, combining Gemini, reverse image search, and linked-article extraction to detect whether a post is being used in the right context.



## Repository Layout

```text
apps/
  source-verification-service/   Flask API for source checks
  content-verification-service/  Flask Kafka worker for content analysis
  context-verification-service/  Next.js app for contextual consistency
  kafka-service/                 Node service for Kafka bootstrap/health
  extension-ui/                  Chrome extension prototype

infra/aws/                       Terraform for AWS deployment
.github/workflows/               GitHub Actions deployment workflow
```

## Local Development

There is no single root command that correctly boots every service in the current repo, because the services use different runtimes.

### 1. Start Kafka locally

If you are using the local Kafka package:

```bash
cd packages/kafka
docker compose up -d
cd ../..
```

### 2. Run source-verification-service

```bash
cd apps/source-verification-service
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Runs on `http://localhost:8080`.

### 3. Run content-verification-service

```bash
cd apps/content-verification-service
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Runs on `http://localhost:8082`.

### 4. Run kafka-service

```bash
pnpm install
pnpm --filter kafka-service dev
```

Runs on `http://localhost:8081`.

### 5. Run context-verification-service

```bash
cd apps/context-verification-service
npm install
npm run dev
```

Runs on `http://localhost:3000`.

Required environment variables for the API route:

- `GEMINI_API_KEY`
- `IMGBB_API_KEY`
- `SERPAPI_API_KEY`

### 6. Optional extension flow

The extension prototype can use:

- `apps/extension-ui/content.js`
- `apps/extension-ui/app.py`

The local helper runs on `http://127.0.0.1:5000`.

## Important API Endpoints

### source-verification-service

- `GET /health`
- `POST /verify`

### content-verification-service

- `GET /health`

### context-verification-service

- `POST /api/verify`
- `GET /` for the web app

### kafka-service

- `GET /health`

## Docker

Each deployable service now has its own Dockerfile:

- [source-verification-service Dockerfile](apps/source-verification-service/Dockerfile)
- [content-verification-service Dockerfile](apps/content-verification-service/Dockerfile)
- [context-verification-service Dockerfile](apps/context-verification-service/Dockerfile)
- [kafka-service Dockerfile](apps/kafka-service/Dockerfile)

## AWS Deployment

Terraform for AWS is under [infra/aws](infra/aws).

At a high level, the AWS architecture is:

- a VPC with public and private subnets
- one public ALB for `source-verification-service`
- one public ALB for `context-verification-service`
- private ECS Fargate services for `content-verification-service` and `kafka-service`
- one private ECR repository per service
- Secrets Manager for runtime secrets
- CloudWatch log groups per service
- GitHub Actions deploying to ECS through OIDC

See [infra/aws/README.md](infra/aws/README.md) for provisioning and rollout details.
