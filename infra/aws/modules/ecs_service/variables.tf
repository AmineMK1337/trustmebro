variable "name_prefix" {
  description = "Prefix for ECS service name"
  type        = string
}

variable "cluster_id" {
  description = "ID of the ECS cluster"
  type        = string
}

variable "task_definition_arn" {
  description = "ARN of the ECS task definition"
  type        = string
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "security_group_ids" {
  description = "List of security group IDs"
  type        = list(string)
}

variable "environment" {
  description = "Environment (e.g., dev, prod)"
  type        = string
}

variable "target_group_arn" {
  description = "Optional ARN of the ALB target group"
  type        = string
  default     = null
}

variable "container_name" {
  description = "Name of the container that the ALB will route traffic to"
  type        = string
}

variable "container_port" {
  description = "Container port exposed to ALB"
  type        = number
}

variable "force_new_deployment" {
  description = "Whether to force a new task deployment of the service"
  type        = bool
  default     = false
}

variable "health_check_grace_period_seconds" {
  description = "Seconds to wait before checking the health of a new task"
  type        = number
  default     = null
}
