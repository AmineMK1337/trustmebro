# TrustMeBro AWS Rollout

## Services

- `source-verification-service`: public ECS Fargate service behind API Gateway
- `content-verification-service`: private ECS Fargate worker consuming Kafka events
- `kafka-service`: private ECS Fargate service used for broker health and topic bootstrap
- `web-ui`: static container or S3 + CloudFront deployment
- `extension-ui`: distributed as a browser extension package that points to API Gateway

## Networking

- Public subnet resources:
  - Application Load Balancer if you want internal ALB to front ECS directly
  - NAT gateways if private workloads need outbound internet access
- Private subnet resources:
  - ECS services
  - Amazon MSK
  - Kendra access through IAM and VPC networking

## Public Entry

- CloudFront
- AWS WAF
- API Gateway HTTP API

## Data and Search

- Amazon S3 buckets for trusted source datasets and uploaded evidence
- Amazon Kendra index fed from S3 datasets

## Messaging

- Amazon MSK for Kafka topics:
  - `content-verification.requested`
  - `content-verification.completed`
  - `source-verification.audit`

## Secrets and Operations

- AWS Secrets Manager for runtime configuration
- CloudWatch Logs, metrics, dashboards, and alarms
- ECS Service Connect for private service discovery
