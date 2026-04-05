variable "name_prefix" {
  description = "Prefix for naming IAM roles"
  type        = string
}

variable "attach_cloudwatch_policy" {
  description = "Attach CloudWatchLogsFullAccess to ECS execution role"
  type        = bool
  default     = false
}

variable "attach_ssm_policy" {
  description = "Attach AmazonSSMReadOnlyAccess to ECS execution role"
  type        = bool
  default     = false
}

variable "create_custom_task_policy" {
  description = "Whether to create a custom task role policy"
  type        = bool
  default     = false
}

variable "custom_task_policy_json" {
  description = "Custom task role policy JSON"
  type        = string
  default     = ""
}

variable "create_custom_execution_policy" {
  description = "Whether to create a custom execution role policy"
  type        = bool
  default     = false
}

variable "custom_execution_policy_json" {
  description = "Custom execution role policy JSON"
  type        = string
  default     = ""
}
