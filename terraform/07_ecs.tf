resource "aws_ecs_cluster" "production" {
  name = "${var.ecs_cluster_name}-cluster"
}

locals {
  container_definitions = templatefile(
    "${path.module}/templates/django_app.json.tpl",
    {
      docker_image_url_django = var.docker_image_url_django
      docker_image_url_nginx  = var.docker_image_url_nginx
      region                  = var.region
      rds_db_name             = var.rds_db_name
      rds_username            = var.rds_username
      rds_password            = var.rds_password
      rds_hostname            = aws_db_instance.production.address
      database_engine         = var.database_engine
      google_api_key          = var.google_api_key
      google_cx               = var.google_cx
      django_secret_key       = var.django_secret_key
      django_debug            = var.django_debug
      django_log_level        = var.django_log_level
      django_allowed_hosts    = var.django_allowed_hosts
    }
  )
}

resource "aws_ecs_task_definition" "app" {
  family                   = "django-app"
  network_mode             = "awsvpc" # Required for Fargate
  requires_compatibilities = ["FARGATE"]
  cpu                      = "${var.fargate_cpu}"
  memory                   = "${var.fargate_memory}"
  execution_role_arn       = aws_iam_role.ecs-task-execution-role.arn
  task_role_arn            = aws_iam_role.ecs-task-execution-role.arn
  container_definitions    = local.container_definitions
  depends_on               = [aws_db_instance.production]
  volume {
    name = "efs-volume"
    efs_volume_configuration {
      file_system_id          = aws_efs_file_system.efs.id
      root_directory          = "/"
      transit_encryption      = "ENABLED"
      transit_encryption_port = 2049
      authorization_config {
        access_point_id = aws_efs_access_point.app_access_point.id
        iam             = "ENABLED"
      }
    }
  }
}


resource "aws_ecs_service" "production" {
  name            = "${var.ecs_cluster_name}-service"
  cluster         = aws_ecs_cluster.production.id
  task_definition = aws_ecs_task_definition.app.arn
  launch_type     = "FARGATE"
  desired_count   = var.app_count
  network_configuration {
    subnets          = [aws_subnet.public-subnet-1.id, aws_subnet.public-subnet-2.id]
    security_groups  = [aws_security_group.ecs-fargate.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_alb_target_group.default-target-group.arn
    container_name   = "nginx"
    container_port   = 80
  }
}

resource "aws_ecs_task_definition" "django_migration" {
  family                = "django-migration-task"
  network_mode          = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                   = var.fargate_cpu
  memory                = var.fargate_memory
  execution_role_arn    = aws_iam_role.ecs-task-execution-role.arn

  container_definitions = jsonencode([
    {
      name  = "django-migration-container"
      image = var.docker_image_url_django
      environment: [
        {
            "name": "DATABASE_ENGINE",
            "value": var.database_engine
        },
        {
            "name": "DATABASE_NAME",
            "value": var.rds_db_name
        },
        {
            "name": "DATABASE_USERNAME",
            "value": var.rds_username
        },
        {
            "name": "DATABASE_PASSWORD",
            "value": var.rds_password
        },
        {
            "name": "DATABASE_HOST",
            "value": aws_db_instance.production.address
        },
        {
            "name": "DATABASE_PORT",
            "value": "5432"
        }
      ],
      # Run migrations as the command
      command = ["python", "manage.py", "migrate"]

      # Add log configuration for CloudWatch
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/django-app"
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      }

      # Other required configurations go here...
      portMappings = [
        {
          containerPort = 8000
        }
      ]
    }
  ])
}


resource "aws_ecs_task_definition" "django_collectstatic" {
  family                = "django-collectstatic-task"
  network_mode          = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                   = var.fargate_cpu
  memory                = var.fargate_memory
  execution_role_arn    = aws_iam_role.ecs-task-execution-role.arn
  task_role_arn         = aws_iam_role.ecs-task-execution-role.arn
  volume {
    name = "efs-volume"
    efs_volume_configuration {
      file_system_id          = aws_efs_file_system.efs.id
      root_directory          = "/"
      transit_encryption      = "ENABLED"
      transit_encryption_port = 2049
      authorization_config {
        access_point_id = aws_efs_access_point.app_access_point.id
        iam             = "ENABLED"
      }
    }
  }
  container_definitions = jsonencode([
    {
      name  = "django-collectstatic-container"
      image = var.docker_image_url_django
      linuxParameters = {
        user = "1000:1000"
      },
      # Run collectstatic as the command
      command = ["python", "manage.py", "collectstatic", "--no-input", "-v", "3"]

      mountPoints = [
        {
          sourceVolume = "efs-volume",
          containerPath = "/efs/staticfiles/",
          readOnly = false
        }
      ]

      # Add log configuration for CloudWatch
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "/ecs/django-app"
          awslogs-region        = var.region
          awslogs-stream-prefix = "ecs"
        }
      }

      # Other required configurations go here...
      portMappings = [
        {
          containerPort = 8000
        }
      ]
    }
  ])
}

resource "aws_ecs_task_definition" "scrape_jobs" {
  family                   = "scrape-jobs-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.fargate_cpu
  memory                   = var.fargate_memory
  execution_role_arn       = aws_iam_role.ecs-task-execution-role.arn
  task_role_arn            = aws_iam_role.ecs-task-execution-role.arn

  container_definitions = jsonencode([
    {
      name  = "scrape-jobs"
      image = var.docker_image_url_django

      command = ["python", "manage.py", "scrape_jobs"]

      environment: [
        {
          name  = "DATABASE_ENGINE"
          value = var.database_engine
        },
        {
          name  = "DATABASE_NAME"
          value = var.rds_db_name
        },
        {
          name  = "DATABASE_USERNAME"
          value = var.rds_username
        },
        {
          name  = "DATABASE_PASSWORD"
          value = var.rds_password
        },
        {
          name  = "DATABASE_HOST"
          value = aws_db_instance.production.address
        },
        {
          name  = "DATABASE_PORT"
          value = "5432"
        },
        {
          name  = "GOOGLE_API_KEY"
          value = var.google_api_key
        },
        {
          name  = "GOOGLE_CX"
          value = var.google_cx
        }
      ],

      logConfiguration = {
        logDriver = "awslogs",
        options = {
          awslogs-group         = "/ecs/scrape-jobs"
          awslogs-region        = var.region
          awslogs-stream-prefix = "scrape"
        }
      }
    }
  ])
}


resource "aws_efs_file_system" "efs" {
  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }
}

resource "aws_efs_access_point" "app_access_point" {
  file_system_id = aws_efs_file_system.efs.id
  posix_user {
    uid = 1000
    gid = 1000
  }
  root_directory {
    path = "/efs"
    creation_info {
      owner_uid   = 1000
      owner_gid   = 1000
      permissions = "755"
    }
  }
}

resource "aws_efs_mount_target" "efs_mount" {
  count           = length([aws_subnet.public-subnet-1.id, aws_subnet.public-subnet-2.id])
  file_system_id  = aws_efs_file_system.efs.id
  subnet_id       = [aws_subnet.public-subnet-1.id, aws_subnet.public-subnet-2.id][count.index]
  security_groups = [aws_security_group.efs_sg.id]
}