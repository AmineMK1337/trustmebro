# TrustMeBro AWS Terraform

This folder provisions the AWS infrastructure for the current TrustMeBro platform.

## What It Creates

- a dedicated VPC with public and private subnets across two Availability Zones
- one public Application Load Balancer for `source-verification-service`
- one public Application Load Balancer for `context-verification-service`
- one ECS Fargate cluster
- four ECS services:
  - `source-verification-service`
  - `content-verification-service`
  - `context-verification-service`
  - `kafka-service`
- one private Amazon ECR repository per service
- CloudWatch log groups for all services
- Secrets Manager secrets for Kafka brokers and service API keys
- IAM roles for ECS execution, per-service task roles, and GitHub Actions OIDC deploys

## Service Mapping

### Public services

- `source-verification-service`
  - Flask API
  - port `8080`
  - public through its own ALB
  - health path: `/health`

- `context-verification-service`
  - Next.js app and API
  - port `3000`
  - public through its own ALB
  - health path: `/`

### Private services

- `content-verification-service`
  - Flask Kafka worker
  - port `8082`
  - private only

- `kafka-service`
  - Node service for Kafka bootstrap and health
  - port `8081`
  - private only

## Cloud Architecture

The deployed shape on AWS is:

1. Internet users reach two public ALBs in the public subnets.
2. One ALB forwards traffic to `source-verification-service` in private subnets.
3. The other ALB forwards traffic to `context-verification-service` in private subnets.
4. All four services run on ECS Fargate in the same cluster and private subnets.
5. `source-verification-service` performs source credibility checks and can publish deeper verification work to Kafka.
6. `content-verification-service` consumes Kafka jobs and publishes asynchronous content-analysis results.
7. `context-verification-service` serves the contextual-consistency UI and its `/api/verify` endpoint, calling Gemini, ImgBB, SerpApi, and article extraction services.
8. `kafka-service` ensures required Kafka topics exist and provides service-level health visibility around Kafka connectivity.
9. CloudWatch stores per-service logs, Secrets Manager provides runtime secrets, and GitHub Actions deploys through OIDC without long-lived AWS keys.

Important: this Terraform stack expects you to provide Kafka brokers through `var.kafka_brokers`. That should normally point to Amazon MSK or another managed Kafka cluster. Kafka infrastructure itself is not created in this pass.

## Files To Review

- [main.tf](c:/Users/user/Documents/Coding%20Projects/menacraft/infra/aws/main.tf)
- [variables.tf](c:/Users/user/Documents/Coding%20Projects/menacraft/infra/aws/variables.tf)
- [outputs.tf](c:/Users/user/Documents/Coding%20Projects/menacraft/infra/aws/outputs.tf)
- [deploy-aws.yml](c:/Users/user/Documents/Coding%20Projects/menacraft/.github/workflows/deploy-aws.yml)

## Required Terraform Inputs

You must provide:

- `github_repository`
- `kafka_brokers`
- `source_gemini_api_key`
- `content_gemini_api_key`
- `context_gemini_api_key`
- `context_imgbb_api_key`
- `context_serpapi_api_key`

You will usually also customize:

- `aws_region`
- `environment`
- `cors_origins`
- `api_certificate_arn`
- subnet CIDRs if needed

## Example terraform.tfvars

Create a local `terraform.tfvars` and do not commit it:

```hcl
aws_region              = "us-east-1"
project_name            = "trustmebro"
environment             = "prod"
github_repository       = "AmineMK1337/trustmebro"
github_branch           = "main"
cors_origins            = ["https://your-source-app-domain.com"]
kafka_brokers           = "b-1.example.kafka.us-east-1.amazonaws.com:9098,b-2.example.kafka.us-east-1.amazonaws.com:9098"
source_gemini_api_key   = "replace-me"
content_gemini_api_key  = "replace-me"
context_gemini_api_key  = "replace-me"
context_imgbb_api_key   = "replace-me"
context_serpapi_api_key = "replace-me"
api_certificate_arn     = "arn:aws:acm:us-east-1:123456789012:certificate/replace-me"
```

## Steps To Make It Work

### 1. Prepare remote Terraform state

Create:

- an S3 bucket for Terraform state
- a DynamoDB table for state locking

Then initialize Terraform, for example:

```bash
terraform -chdir=infra/aws init \
  -backend-config="bucket=your-terraform-state-bucket" \
  -backend-config="key=trustmebro/prod/terraform.tfstate" \
  -backend-config="region=us-east-1" \
  -backend-config="dynamodb_table=your-terraform-locks"
```

### 2. Supply variables

Create `terraform.tfvars` locally with your broker endpoints, API keys, repository name, and optional certificate ARN.

### 3. Review the plan

```bash
terraform -chdir=infra/aws plan
```

Check especially:

- VPC CIDRs
- ALB exposure
- ECS desired counts
- ECR repository names
- IAM role names
- public source/context ports

### 4. Apply the stack

```bash
terraform -chdir=infra/aws apply
```

After apply, keep these outputs:

- ECR repository URLs
- ECS cluster name
- ECS service names
- GitHub Actions role ARN
- source ALB DNS name
- context ALB DNS name

### 5. Wire GitHub Actions

Add these GitHub Actions repository variables:

- `AWS_REGION`
- `AWS_ROLE_TO_ASSUME`
- `ECS_CLUSTER`
- `ECS_SERVICE_SOURCE`
- `ECS_SERVICE_CONTENT`
- `ECS_SERVICE_CONTEXT`
- `ECS_SERVICE_KAFKA`
- `ECR_REPOSITORY_SOURCE`
- `ECR_REPOSITORY_CONTENT`
- `ECR_REPOSITORY_CONTEXT`
- `ECR_REPOSITORY_KAFKA`

Use these repository names:

- `source-verification-service`
- `content-verification-service`
- `context-verification-service`
- `kafka-service`

### 6. Build and deploy application images

Push to `main` or run the workflow manually. The workflow will:

- authenticate to AWS through OIDC
- build each service image
- push each image to ECR
- render ECS task definitions
- deploy the ECS services

### 7. Point your domains or clients

Use the ALB DNS outputs as your initial public endpoints.

- source API -> source ALB
- context web app and `/api/verify` -> context ALB

If `api_certificate_arn` is set, both ALBs will serve HTTPS on `443` and redirect HTTP to HTTPS.

### 8. Verify runtime health

Check:

- `http://<source-alb-dns>/health` or `https://<source-alb-dns>/health`
- `http://<context-alb-dns>/` or `https://<context-alb-dns>/`
- ECS service stability
- CloudWatch log groups under `/ecs/<project>-<env>/<service>`
- Kafka connectivity from `source-verification-service` and `content-verification-service`

## Security Notes

- ECS tasks run in private subnets without public IPs.
- Only the two ALBs are internet-facing.
- Runtime secrets come from Secrets Manager, not hardcoded task definitions.
- GitHub Actions uses OIDC instead of stored AWS access keys.
- Each ECS service gets its own task role for least privilege growth over time.

## Recommended Next Step

The next strong improvement would be to Terraform-manage Amazon MSK, Route 53, ACM certificate validation, and optionally AWS WAF so the entire production stack is versioned in one place.
