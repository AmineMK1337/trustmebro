# ECS Execution Role (used by ECS itself to run your tasks)
resource "aws_iam_role" "ecs_execution" {
  name = "${var.name_prefix}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "${var.name_prefix}-ecs-execution-role"
  }
}

resource "aws_iam_role_policy_attachment" "ecs_execution_policy" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Optional: Attach logging or secret access policies
resource "aws_iam_role_policy_attachment" "logs_policy" {
  count      = var.attach_cloudwatch_policy ? 1 : 0
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

resource "aws_iam_role_policy_attachment" "ssm_policy" {
  count      = var.attach_ssm_policy ? 1 : 0
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess"
}

# ECS Task Role (used by the app itself to access AWS resources)
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.name_prefix}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Effect = "Allow",
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "${var.name_prefix}-ecs-task-role"
  }
}

# Custom policies for task and execution roles
resource "aws_iam_role_policy" "custom_task_access" {
  count  = var.create_custom_task_policy ? 1 : 0
  name   = "${var.name_prefix}-custom-task-policy"
  role   = aws_iam_role.ecs_task_role.name
  policy = var.custom_task_policy_json
}

resource "aws_iam_role_policy" "custom_execution_access" {
  count  = var.create_custom_execution_policy ? 1 : 0
  name   = "${var.name_prefix}-custom-execution-policy"
  role   = aws_iam_role.ecs_execution.name
  policy = var.custom_execution_policy_json
}
