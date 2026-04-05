output "task_definition_arn" {
  description = "The full ARN of the ECS task definition"
  value       = aws_ecs_task_definition.this.arn
}

output "task_definition_family" {
  description = "The family of the ECS task definition"
  value       = aws_ecs_task_definition.this.family
}

output "revision" {
  description = "The revision of the ECS task definition"
  value       = aws_ecs_task_definition.this.revision
}