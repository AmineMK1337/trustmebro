variable "name_prefix" {
  description = "Prefix for the ECS cluster name"
  type        = string
}

variable "environment" {
  description = "Environment tag (e.g., dev, staging, prod)"
  type        = string
}

variable "enable_container_insights" {
  description = "Enable CloudWatch Container Insights"
  type        = bool
}

variable "capacity_providers" {
  description = "List of capacity providers to associate with the ECS cluster"
  type        = list(string)
}

variable "default_capacity_provider_strategy" {
  description = "Default strategy for placing tasks across capacity providers"
  type = list(object({
    capacity_provider = string
    weight            = number
    base              = number
  }))
}