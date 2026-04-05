variable "family" {
  description = "The name of the task definition family"
  type        = string
}

variable "cpu" {
  description = "The number of CPU units used by the task"
  type        = number
}

variable "memory" {
  description = "The amount of memory (in MiB) used by the task"
  type        = number
}

variable "container_name" {
  description = "The name of the container within the task"
  type        = string
}

variable "image" {
  description = "The container image to use"
  type        = string
}

variable "container_port" {
  description = "The port on the container to expose"
  type        = number
}

variable "execution_role_arn" {
  description = "The ARN of the IAM role that grants permissions for ECS to pull images and publish logs"
  type        = string
}

variable "task_role_arn" {
  description = "The ARN of the IAM role that the container can assume to interact with AWS services"
  type        = string
}

variable "region" {
  description = "AWS region where the ECS service is deployed (used for logs)"
  type        = string
}

variable "log_group_name" {
  description = "CloudWatch log group name for the container"
  type        = string
}

variable "environment" {
  description = "Environment variables injected into the container"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "secrets" {
  description = "Secrets Manager or SSM secrets injected into the container"
  type = list(object({
    name       = string
    value_from = string
  }))
  default = []
}

variable "readonly_root_filesystem" {
  description = "Whether the container filesystem should be mounted read-only"
  type        = bool
  default     = true
}
