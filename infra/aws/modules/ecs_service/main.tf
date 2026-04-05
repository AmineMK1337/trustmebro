resource "aws_ecs_service" "this" {
  name                              = "${var.name_prefix}-service"
  cluster                           = var.cluster_id
  task_definition                   = var.task_definition_arn
  launch_type                       = "FARGATE"
  desired_count                     = var.desired_count
  force_new_deployment              = var.force_new_deployment
  health_check_grace_period_seconds = var.health_check_grace_period_seconds
  enable_execute_command            = true

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = false
  }

  dynamic "load_balancer" {
    for_each = var.target_group_arn == null ? [] : [var.target_group_arn]
    content {
      target_group_arn = load_balancer.value
      container_name   = var.container_name
      container_port   = var.container_port
    }
  }

  deployment_controller {
    type = "ECS"
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = {
    Name        = "${var.name_prefix}-service"
    Environment = var.environment
  }
}
