resource "aws_iam_role" "lambda_exec_role" {
  name = "${var.lambda_function_name}-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic_logs" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "backup_lambda_policy" {
  name = "${var.lambda_function_name}-policy"
  role = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EC2SnapshotAccess"
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeSnapshots",
          "ec2:CreateSnapshot",
          "ec2:DeleteSnapshot",
          "ec2:CreateTags"
        ]
        Resource = "*"
      },
      {
        Sid    = "RDSBackupAccess"
        Effect = "Allow"
        Action = [
          "rds:DescribeDBInstances",
          "rds:DescribeDBSnapshots",
          "rds:CreateDBSnapshot",
          "rds:DeleteDBSnapshot",
          "rds:ListTagsForResource"
        ]
        Resource = "*"
      },
      {
        Sid    = "S3BackupAccess"
        Effect = "Allow"
        Action = [
          "s3:ListAllMyBuckets",
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetObject",
          "s3:PutObject",
          "s3:PutObjectTagging",
          "s3:CreateBucket",
          "s3:PutBucketVersioning",
          "s3:PutBucketLifecycleConfiguration",
          "s3:HeadBucket"
        ]
        Resource = "*"
      },
      {
        Sid    = "SNSPublishAccess"
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = var.sns_topic_arn != "" ? var.sns_topic_arn : "*"
      },
      {
        Sid    = "STSAccess"
        Effect = "Allow"
        Action = [
          "sts:GetCallerIdentity"
        ]
        Resource = "*"
      }
    ]
  })
}