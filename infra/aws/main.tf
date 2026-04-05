provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  services = {
    source-verification-service = {
      port          = 8080
      cpu           = var.source_cpu
      memory        = var.source_memory
      desired_count = var.source_desired_count
      image_tag     = var.source_image_tag
      public        = true
      health_path   = "/health"
      environment = [
        { name = "PORT", value = "8080" },
        { name = "CORS_ORIGINS", value = join(",", var.cors_origins) },
        { name = "CONTENT_VERIFICATION_TOPIC", value = "content-verification.requested" }
      ]
      secrets = [
        { name = "KAFKA_BROKERS", value_from = aws_secretsmanager_secret.kafka_brokers.arn },
        { name = "GEMINI_API_KEY", value_from = aws_secretsmanager_secret.source_gemini_api_key.arn }
      ]
    }
    content-verification-service = {
      port          = 8082
      cpu           = var.content_cpu
      memory        = var.content_memory
      desired_count = var.content_desired_count
      image_tag     = var.content_image_tag
      public        = false
      health_path   = "/health"
      environment = [
        { name = "PORT", value = "8082" },
        { name = "INPUT_TOPIC", value = "content-verification.requested" },
        { name = "OUTPUT_TOPIC", value = "content-verification.completed" },
        { name = "CONSUMER_GROUP", value = "content-verification-service-group" }
      ]
      secrets = [
        { name = "KAFKA_BROKERS", value_from = aws_secretsmanager_secret.kafka_brokers.arn },
        { name = "GEMINI_API_KEY", value_from = aws_secretsmanager_secret.content_gemini_api_key.arn }
      ]
    }
    context-verification-service = {
      port          = 3000
      cpu           = var.context_cpu
      memory        = var.context_memory
      desired_count = var.context_desired_count
      image_tag     = var.context_image_tag
      public        = true
      health_path   = "/"
      environment = [
        { name = "PORT", value = "3000" },
        { name = "HOSTNAME", value = "0.0.0.0" },
        { name = "NODE_ENV", value = "production" }
      ]
      secrets = [
        { name = "GEMINI_API_KEY", value_from = aws_secretsmanager_secret.context_gemini_api_key.arn },
        { name = "IMGBB_API_KEY", value_from = aws_secretsmanager_secret.context_imgbb_api_key.arn },
        { name = "SERPAPI_API_KEY", value_from = aws_secretsmanager_secret.context_serpapi_api_key.arn }
      ]
    }
    kafka-service = {
      port          = 8081
      cpu           = var.kafka_cpu
      memory        = var.kafka_memory
      desired_count = var.kafka_desired_count
      image_tag     = var.kafka_image_tag
      public        = false
      health_path   = "/health"
      environment = [
        { name = "PORT", value = "8081" }
      ]
      secrets = [
        { name = "KAFKA_BROKERS", value_from = aws_secretsmanager_secret.kafka_brokers.arn }
      ]
    }
  }
}

module "vpc" {
  source = "./modules/vpc"

  name_prefix          = local.name_prefix
  vpc_cidr             = var.vpc_cidr
  azs                  = var.azs
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
}

module "ecs" {
  source      = "./modules/ecs"
  name_prefix = local.name_prefix
  environment = var.environment

  enable_container_insights = true

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy = [
    {
      capacity_provider = "FARGATE"
      weight            = 1
      base              = 1
    }
  ]
}

module "iam" {
  source                    = "./modules/iam"
  name_prefix               = local.name_prefix
  attach_cloudwatch_policy  = false
  attach_ssm_policy         = false
  create_custom_task_policy = false

  create_custom_execution_policy = true
  custom_execution_policy_json = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/${local.name_prefix}/*:*"
      },
      {
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue",
          "kms:Decrypt"
        ],
        Resource = [
          aws_secretsmanager_secret.kafka_brokers.arn,
          aws_secretsmanager_secret.source_gemini_api_key.arn,
          aws_secretsmanager_secret.content_gemini_api_key.arn,
          aws_secretsmanager_secret.context_gemini_api_key.arn,
          aws_secretsmanager_secret.context_imgbb_api_key.arn,
          aws_secretsmanager_secret.context_serpapi_api_key.arn
        ]
      }
    ]
  })
}

resource "aws_ecr_repository" "service" {
  for_each = local.services

  name                 = each.key
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = merge(local.common_tags, {
    Name = each.key
  })
}

resource "aws_cloudwatch_log_group" "service" {
  for_each = local.services

  name              = "/ecs/${local.name_prefix}/${each.key}"
  retention_in_days = 30
  tags              = local.common_tags
}

resource "aws_secretsmanager_secret" "kafka_brokers" {
  name                    = "${local.name_prefix}/shared/kafka-brokers"
  recovery_window_in_days = 7
  tags                    = local.common_tags
}

resource "aws_secretsmanager_secret_version" "kafka_brokers" {
  secret_id     = aws_secretsmanager_secret.kafka_brokers.id
  secret_string = var.kafka_brokers
}

resource "aws_secretsmanager_secret" "source_gemini_api_key" {
  name                    = "${local.name_prefix}/source/gemini-api-key"
  recovery_window_in_days = 7
  tags                    = local.common_tags
}

resource "aws_secretsmanager_secret_version" "source_gemini_api_key" {
  secret_id     = aws_secretsmanager_secret.source_gemini_api_key.id
  secret_string = var.source_gemini_api_key
}

resource "aws_secretsmanager_secret" "content_gemini_api_key" {
  name                    = "${local.name_prefix}/content/gemini-api-key"
  recovery_window_in_days = 7
  tags                    = local.common_tags
}

resource "aws_secretsmanager_secret_version" "content_gemini_api_key" {
  secret_id     = aws_secretsmanager_secret.content_gemini_api_key.id
  secret_string = var.content_gemini_api_key
}

resource "aws_secretsmanager_secret" "context_gemini_api_key" {
  name                    = "${local.name_prefix}/context/gemini-api-key"
  recovery_window_in_days = 7
  tags                    = local.common_tags
}

resource "aws_secretsmanager_secret_version" "context_gemini_api_key" {
  secret_id     = aws_secretsmanager_secret.context_gemini_api_key.id
  secret_string = var.context_gemini_api_key
}

resource "aws_secretsmanager_secret" "context_imgbb_api_key" {
  name                    = "${local.name_prefix}/context/imgbb-api-key"
  recovery_window_in_days = 7
  tags                    = local.common_tags
}

resource "aws_secretsmanager_secret_version" "context_imgbb_api_key" {
  secret_id     = aws_secretsmanager_secret.context_imgbb_api_key.id
  secret_string = var.context_imgbb_api_key
}

resource "aws_secretsmanager_secret" "context_serpapi_api_key" {
  name                    = "${local.name_prefix}/context/serpapi-api-key"
  recovery_window_in_days = 7
  tags                    = local.common_tags
}

resource "aws_secretsmanager_secret_version" "context_serpapi_api_key" {
  secret_id     = aws_secretsmanager_secret.context_serpapi_api_key.id
  secret_string = var.context_serpapi_api_key
}

module "alb_sg" {
  source = "./modules/security-group"

  name   = "${local.name_prefix}-alb-sg"
  vpc_id = module.vpc.vpc_id

  ingress_rules = concat(
    [
      {
        from_port   = 80
        to_port     = 80
        protocol    = "tcp"
        cidr_blocks = var.alb_ingress_cidrs
      }
    ],
    var.api_certificate_arn != null ? [
      {
        from_port   = 443
        to_port     = 443
        protocol    = "tcp"
        cidr_blocks = var.alb_ingress_cidrs
      }
    ] : []
  )
}

module "source_service_sg" {
  source = "./modules/security-group"

  name   = "${local.name_prefix}-source-sg"
  vpc_id = module.vpc.vpc_id

  ingress_rules = [
    {
      from_port       = local.services["source-verification-service"].port
      to_port         = local.services["source-verification-service"].port
      protocol        = "tcp"
      cidr_blocks     = []
      security_groups = [module.alb_sg.security_group_id]
    }
  ]
}

module "content_service_sg" {
  source = "./modules/security-group"

  name   = "${local.name_prefix}-content-sg"
  vpc_id = module.vpc.vpc_id
}

module "context_service_sg" {
  source = "./modules/security-group"

  name   = "${local.name_prefix}-context-sg"
  vpc_id = module.vpc.vpc_id

  ingress_rules = [
    {
      from_port       = local.services["context-verification-service"].port
      to_port         = local.services["context-verification-service"].port
      protocol        = "tcp"
      cidr_blocks     = []
      security_groups = [module.alb_sg.security_group_id]
    }
  ]
}

module "kafka_service_sg" {
  source = "./modules/security-group"

  name   = "${local.name_prefix}-kafka-sg"
  vpc_id = module.vpc.vpc_id
}

module "source_alb" {
  source = "./modules/alb"

  name_prefix        = "${local.name_prefix}-source"
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  security_group_ids = [module.alb_sg.security_group_id]
  target_port        = local.services["source-verification-service"].port
  health_check_path  = local.services["source-verification-service"].health_path
  certificate_arn    = var.api_certificate_arn
  environment        = var.environment
}

module "context_alb" {
  source = "./modules/alb"

  name_prefix        = "${local.name_prefix}-context"
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  security_group_ids = [module.alb_sg.security_group_id]
  target_port        = local.services["context-verification-service"].port
  health_check_path  = local.services["context-verification-service"].health_path
  certificate_arn    = var.api_certificate_arn
  environment        = var.environment
}

resource "aws_iam_role" "service_task_role" {
  for_each = local.services

  name = "${local.name_prefix}-${each.key}-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Action = "sts:AssumeRole",
        Effect = "Allow",
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-${each.key}-task-role"
  })
}

module "task_definition" {
  for_each = local.services
  source   = "./modules/task-definition"

  family                   = "${local.name_prefix}-${each.key}"
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  container_name           = each.key
  image                    = "${aws_ecr_repository.service[each.key].repository_url}:${each.value.image_tag}"
  container_port           = each.value.port
  region                   = var.aws_region
  execution_role_arn       = module.iam.ecs_execution_role_arn
  task_role_arn            = aws_iam_role.service_task_role[each.key].arn
  log_group_name           = aws_cloudwatch_log_group.service[each.key].name
  environment              = each.value.environment
  secrets                  = each.value.secrets
  readonly_root_filesystem = true
}

module "ecs_service" {
  for_each = local.services
  source   = "./modules/ecs_service"

  name_prefix                       = "${local.name_prefix}-${each.key}"
  cluster_id                        = module.ecs.cluster_id
  task_definition_arn               = module.task_definition[each.key].task_definition_arn
  desired_count                     = each.value.desired_count
  private_subnet_ids                = module.vpc.private_subnet_ids
  security_group_ids                = each.key == "source-verification-service" ? [module.source_service_sg.security_group_id] : (each.key == "content-verification-service" ? [module.content_service_sg.security_group_id] : (each.key == "context-verification-service" ? [module.context_service_sg.security_group_id] : [module.kafka_service_sg.security_group_id]))
  environment                       = var.environment
  target_group_arn                  = each.key == "source-verification-service" ? module.source_alb.target_group_arn : (each.key == "context-verification-service" ? module.context_alb.target_group_arn : null)
  container_name                    = each.key
  container_port                    = each.value.port
  force_new_deployment              = true
  health_check_grace_period_seconds = each.value.public ? 60 : null
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

data "aws_iam_policy_document" "github_oidc_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:ref:refs/heads/${var.github_branch}"]
    }
  }
}

data "aws_iam_policy_document" "github_deploy" {
  statement {
    effect    = "Allow"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:CompleteLayerUpload",
      "ecr:DescribeImages",
      "ecr:DescribeRepositories",
      "ecr:GetDownloadUrlForLayer",
      "ecr:InitiateLayerUpload",
      "ecr:PutImage",
      "ecr:UploadLayerPart"
    ]
    resources = [for repo in aws_ecr_repository.service : repo.arn]
  }

  statement {
    effect = "Allow"
    actions = [
      "ecs:DescribeServices",
      "ecs:DescribeTaskDefinition",
      "ecs:RegisterTaskDefinition",
      "ecs:UpdateService"
    ]
    resources = ["*"]
  }

  statement {
    effect = "Allow"
    actions = [
      "iam:PassRole"
    ]
    resources = concat(
      [module.iam.ecs_execution_role_arn],
      [for role in aws_iam_role.service_task_role : role.arn]
    )
  }
}

resource "aws_iam_role" "github_actions_deploy" {
  name               = "${local.name_prefix}-github-actions-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_oidc_assume_role.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy" "github_actions_deploy" {
  name   = "${local.name_prefix}-github-actions-deploy"
  role   = aws_iam_role.github_actions_deploy.id
  policy = data.aws_iam_policy_document.github_deploy.json
}
