variable "aws_region" {
  description = "AWS region for the deployment."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for tagging and resource naming."
  type        = string
  default     = "trustmebro"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "prod"
}

variable "vpc_cidr" {
  description = "CIDR block for the application VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "azs" {
  description = "Availability zones used by the VPC."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets."
  type        = list(string)
  default     = ["10.42.1.0/24", "10.42.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets."
  type        = list(string)
  default     = ["10.42.11.0/24", "10.42.12.0/24"]
}

variable "github_repository" {
  description = "GitHub repository in owner/name format allowed to deploy through OIDC."
  type        = string
}

variable "github_branch" {
  description = "GitHub branch allowed to assume the deploy role."
  type        = string
  default     = "main"
}

variable "cors_origins" {
  description = "Allowed browser origins for the source-verification API."
  type        = list(string)
  default     = ["https://app.example.com"]
}

variable "kafka_brokers" {
  description = "Comma-separated Kafka bootstrap brokers. Point this at Amazon MSK or another managed Kafka cluster."
  type        = string
}

variable "source_gemini_api_key" {
  description = "Gemini API key for the source-verification service."
  type        = string
  sensitive   = true
}

variable "content_gemini_api_key" {
  description = "Gemini API key for the content-verification service."
  type        = string
  sensitive   = true
}

variable "context_gemini_api_key" {
  description = "Gemini API key for the context-verification service."
  type        = string
  sensitive   = true
}

variable "context_imgbb_api_key" {
  description = "ImgBB API key for context-verification reverse-image workflows."
  type        = string
  sensitive   = true
}

variable "context_serpapi_api_key" {
  description = "SerpApi key for context-verification reverse-image search."
  type        = string
  sensitive   = true
}

variable "source_image_tag" {
  description = "Initial image tag for the source-verification service."
  type        = string
  default     = "latest"
}

variable "content_image_tag" {
  description = "Initial image tag for the content-verification service."
  type        = string
  default     = "latest"
}

variable "context_image_tag" {
  description = "Initial image tag for the context-verification service."
  type        = string
  default     = "latest"
}

variable "kafka_image_tag" {
  description = "Initial image tag for the kafka-service."
  type        = string
  default     = "latest"
}

variable "source_desired_count" {
  description = "Desired ECS task count for the public source-verification API."
  type        = number
  default     = 2
}

variable "content_desired_count" {
  description = "Desired ECS task count for the private content-verification worker."
  type        = number
  default     = 1
}

variable "context_desired_count" {
  description = "Desired ECS task count for the private context-verification worker."
  type        = number
  default     = 1
}

variable "kafka_desired_count" {
  description = "Desired ECS task count for the private kafka bootstrap service."
  type        = number
  default     = 1
}

variable "source_cpu" {
  description = "CPU units for the source-verification task."
  type        = number
  default     = 512
}

variable "source_memory" {
  description = "Memory in MiB for the source-verification task."
  type        = number
  default     = 1024
}

variable "content_cpu" {
  description = "CPU units for the content-verification task."
  type        = number
  default     = 512
}

variable "content_memory" {
  description = "Memory in MiB for the content-verification task."
  type        = number
  default     = 1024
}

variable "context_cpu" {
  description = "CPU units for the context-verification task."
  type        = number
  default     = 512
}

variable "context_memory" {
  description = "Memory in MiB for the context-verification task."
  type        = number
  default     = 1024
}

variable "kafka_cpu" {
  description = "CPU units for the kafka-service task."
  type        = number
  default     = 512
}

variable "kafka_memory" {
  description = "Memory in MiB for the kafka-service task."
  type        = number
  default     = 1024
}

variable "api_certificate_arn" {
  description = "Optional ACM certificate ARN for HTTPS on the public ALB."
  type        = string
  default     = null
}

variable "alb_ingress_cidrs" {
  description = "CIDR blocks allowed to reach the public ALB."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}
