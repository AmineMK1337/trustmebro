output "aws_region" {
  description = "AWS region used by the stack."
  value       = var.aws_region
}

output "ecr_repository_urls" {
  description = "Repository URLs for the service container images."
  value = {
    for name, repo in aws_ecr_repository.service :
    name => repo.repository_url
  }
}

output "ecs_cluster_name" {
  description = "ECS cluster name."
  value       = module.ecs.cluster_name
}

output "ecs_service_names" {
  description = "ECS service names keyed by app service."
  value = {
    for name, svc in module.ecs_service :
    name => svc.service_name
  }
}

output "source_api_alb_dns_name" {
  description = "Public DNS name for the source-verification service ALB."
  value       = module.source_alb.alb_dns_name
}

output "context_app_alb_dns_name" {
  description = "Public DNS name for the context-verification service ALB."
  value       = module.context_alb.alb_dns_name
}

output "github_actions_role_arn" {
  description = "IAM role ARN used by GitHub Actions OIDC deployments."
  value       = aws_iam_role.github_actions_deploy.arn
}

output "secret_arns" {
  description = "Secrets Manager secret ARNs used by the stack."
  value = {
    kafka_brokers          = aws_secretsmanager_secret.kafka_brokers.arn
    source_gemini_api_key  = aws_secretsmanager_secret.source_gemini_api_key.arn
    content_gemini_api_key = aws_secretsmanager_secret.content_gemini_api_key.arn
    context_gemini_api_key = aws_secretsmanager_secret.context_gemini_api_key.arn
    context_imgbb_api_key  = aws_secretsmanager_secret.context_imgbb_api_key.arn
    context_serpapi_api_key = aws_secretsmanager_secret.context_serpapi_api_key.arn
  }
  sensitive = true
}
