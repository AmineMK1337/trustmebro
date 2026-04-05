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
| `source-verification-service` | Python / Flask | `8080` | Public API for source credibility checks. Evaluates a source and can escalate downstream verification work to Kafka. |
| `content-verification-service` | Python / Flask | `8082` | Private worker that consumes Kafka jobs and produces content-verification results. |
| `context-verification-service` | Next.js | `3000` | Public web app and API for contextual consistency checks using Gemini, reverse image search, and linked-article extraction. |
| `kafka-service` | Node / Express | `8081` | Private Kafka bootstrap and health service for required topics. |
| `extension-ui` | Chrome extension + local Flask helper | `5000` local helper | Experimental browser extension flow for scraping posts and sending verification payloads. |

## Current Architecture

The app currently behaves like this:

1. `context-verification-service` exposes a web UI and `/api/verify` route for contextual consistency analysis.
2. `source-verification-service` exposes `/verify` and `/health` for source credibility checks.
3. `source-verification-service` can publish verification requests to Kafka when a source needs deeper review.
4. `content-verification-service` consumes Kafka messages, runs asynchronous verification, and publishes results back to Kafka.
5. `kafka-service` ensures required Kafka topics exist and provides a simple health endpoint.
6. `extension-ui` is a separate prototype path for scraping social content locally and sending it to a local helper backend.

## Content Verification Process

![Content Verification Process](Content%20Verification%20Process.png)

`content-verification-service` works as the asynchronous verification worker in the platform:

1. It consumes verification requests from Kafka.
2. It runs the content verification pipeline on the incoming payload.
3. It produces structured verification results back to Kafka.
4. It exposes `/health` so the platform can monitor worker readiness.

This service is designed for deeper media and content analysis after an upstream service decides a post needs more review.

## Source Verification Process

![Source Verification Process](Source%20Verification%20Process.png)

`source-verification-service` is the first credibility gate in the platform:

1. It receives a source URL or account identifier through `/verify`.
2. It runs the `SourceAgent`, which combines:
   domain analysis,
   content credibility analysis,
   and behavioral heuristics.
3. It returns a trust-oriented result with score, status, reasons, and detailed layer output.
4. If the source is not confidently verified, it escalates the request to Kafka for downstream analysis.

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

- [source-verification-service Dockerfile](c:/Users/user/Documents/Coding%20Projects/menacraft/apps/source-verification-service/Dockerfile)
- [content-verification-service Dockerfile](c:/Users/user/Documents/Coding%20Projects/menacraft/apps/content-verification-service/Dockerfile)
- [context-verification-service Dockerfile](c:/Users/user/Documents/Coding%20Projects/menacraft/apps/context-verification-service/Dockerfile)
- [kafka-service Dockerfile](c:/Users/user/Documents/Coding%20Projects/menacraft/apps/kafka-service/Dockerfile)

## AWS Deployment

Terraform for AWS is under [infra/aws](c:/Users/user/Documents/Coding%20Projects/menacraft/infra/aws).

At a high level, the AWS architecture is:

- a VPC with public and private subnets
- one public ALB for `source-verification-service`
- one public ALB for `context-verification-service`
- private ECS Fargate services for `content-verification-service` and `kafka-service`
- one private ECR repository per service
- Secrets Manager for runtime secrets
- CloudWatch log groups per service
- GitHub Actions deploying to ECS through OIDC

See [infra/aws/README.md](c:/Users/user/Documents/Coding%20Projects/menacraft/infra/aws/README.md) for provisioning and rollout details.
