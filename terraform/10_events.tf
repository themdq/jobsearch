resource "aws_cloudwatch_event_rule" "scrape_jobs_hourly" {
  name                = "scrape-jobs-hourly"
  schedule_expression = "${var.scrape_schedule}"
}

resource "aws_cloudwatch_event_target" "scrape_jobs_target" {
  rule      = aws_cloudwatch_event_rule.scrape_jobs_hourly.name
  target_id = "scrape-jobs-run"
  arn       = aws_ecs_cluster.production.arn
  role_arn  = aws_iam_role.ecs_events_role.arn

  ecs_target {
    launch_type        = "FARGATE"
    task_definition_arn = aws_ecs_task_definition.scrape_jobs.arn
    task_count         = 1

    network_configuration {
      subnets          = [aws_subnet.public-subnet-1.id, aws_subnet.public-subnet-2.id]
      security_groups  = [aws_security_group.ecs-fargate.id]
      assign_public_ip = true
    }
  }
}