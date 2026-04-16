data "archive_file" "backup_lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/backup_lambda.zip"
}

resource "aws_lambda_function" "backup_lambda" {
  function_name = var.lambda_function_name
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "lambda_handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 900
  memory_size   = 512

  filename         = data.archive_file.backup_lambda_zip.output_path
  source_code_hash = data.archive_file.backup_lambda_zip.output_base64sha256

  environment {
    variables = {
      AWS_REGION            = var.aws_region
      BACKUP_BUCKET         = var.backup_bucket
      SNS_TOPIC_ARN         = var.sns_topic_arn
      BACKUP_RETENTION_DAYS = tostring(var.backup_retention_days)
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_logs,
    aws_iam_role_policy.backup_lambda_policy
  ]
}