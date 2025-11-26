[
  {
    "name": "django-app",
    "image": "${docker_image_url_django}",
    "essential": true,
    "cpu": 10,
    "memory": 512,
    "portMappings": [
      {
        "containerPort": 8000,
        "protocol": "tcp"
      }
    ],
    "command": [
      "gunicorn",
      "-w", "3",
      "-b", "0.0.0.0:8000",
      "jobsearch.wsgi:application"
    ],
    "environment": [
      {
        "name": "DATABASE_ENGINE",
        "value": "${database_engine}"
      },
      {
        "name": "DATABASE_NAME",
        "value": "${rds_db_name}"
      },
      {
        "name": "DATABASE_USERNAME",
        "value": "${rds_username}"
      },
      {
        "name": "DATABASE_PASSWORD",
        "value": "${rds_password}"
      },
      {
        "name": "DATABASE_HOST",
        "value": "${rds_hostname}"
      },
      {
        "name": "DATABASE_PORT",
        "value": "5432"
      },
      {
        "name" : "GOOGLE_API_KEY",
        "value": "${google_api_key}"
      },
      {
        "name" : "GOOGLE_CX",
        "value": "${google_cx}"
      },
      {
        "name" : "DJANGO_SECRET_KEY",
        "value": "${django_secret_key}"
      },
      {
        "name" : "DEBUG",
        "value": "${django_debug}"
      },
      {
        "name" : "DJANGO_LOGLEVEL",
        "value": "${django_log_level}"
      },
      {
        "name" : "DJANGO_ALLOWED_HOSTS",
        "value": "${django_allowed_hosts}"
      }
  ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/django-app",
        "awslogs-region": "${region}",
        "awslogs-stream-prefix": "django-app-log-stream"
      }
    },
    "mountPoints": [
      {
        "containerPath": "/efs/staticfiles/",
        "sourceVolume": "efs-volume",
        "readOnly": false

      }
    ]
  },
  {
    "name": "nginx",
    "image": "${docker_image_url_nginx}",
    "essential": true,
    "cpu": 10,
    "memory": 128,
    "portMappings": [
      {
        "containerPort": 80,
        "protocol": "tcp"
      }
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/nginx",
        "awslogs-region": "${region}",
        "awslogs-stream-prefix": "nginx-log-stream"
      }
    },
    "mountPoints": [
      {
        "containerPath": "/efs/staticfiles/",
        "sourceVolume": "efs-volume",
        "readOnly": false

      }
    ]
  }
]
