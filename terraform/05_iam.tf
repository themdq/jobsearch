resource "aws_iam_role" "ecs-task-execution-role" {
  name               = "ecs_task_execution_role_prod"
  assume_role_policy = file("policies/ecs-role.json")
}

resource "aws_iam_role_policy" "ecs-task-execution-role-policy" {
  name   = "ecs_task_execution_role_policy"
  policy = file("policies/ecs-task-execution-policy.json")
  role   = aws_iam_role.ecs-task-execution-role.id
}

resource "aws_iam_role" "ecs-service-role" {
  name               = "ecs_service_role_prod"
  assume_role_policy = file("policies/ecs-role.json")
}

resource "aws_iam_role_policy" "ecs-service-role-policy" {
  name   = "ecs_service_role_policy"
  policy = file("policies/ecs-service-role-policy.json")
  role   = aws_iam_role.ecs-service-role.id
}

resource "aws_iam_role" "ecs_events_role" {
  name = "ecs-events-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Service = "events.amazonaws.com"
        },
        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_events_role_policy" {
  role       = aws_iam_role.ecs_events_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceEventsRole"
}
