variable "name_prefix" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "security_group_ids" {
  type = list(string)
}

variable "target_port" {
  type    = number
  default = 80
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "health_check_path" {
  description = "HTTP path used by the target group health check."
  type        = string
  default     = "/health"
}

variable "certificate_arn" {
  description = "Optional ACM certificate ARN for HTTPS listeners."
  type        = string
  default     = null
}
