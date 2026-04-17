# All schedule expressions are in UTC

# ── Primary: EC2 Backup Schedule ─────────────────────────────────────

resource "aws_cloudwatch_event_rule" "ec2_backup_schedule" {
  name                = "aws-backup-ec2-schedule"
  description         = "Nightly EBS snapshots for tagged EC2 instances"
  schedule_expression = "cron(0 2 * * ? *)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "ec2_backup_target" {
  rule      = aws_cloudwatch_event_rule.ec2_backup_schedule.name
  target_id = "BackupLambdaEC2"
  arn       = aws_lambda_function.backup_lambda.arn

  input = jsonencode({
    backup_type = "ec2"
  })
}

resource "aws_lambda_permission" "allow_eventbridge_ec2" {
  statement_id  = "AllowExecutionFromEventBridgeEC2"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backup_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ec2_backup_schedule.arn
}

# ── Primary: Cleanup Schedule ────────────────────────────────────────

resource "aws_cloudwatch_event_rule" "cleanup_schedule" {
  name                = "aws-backup-cleanup-schedule"
  description         = "Delete expired automated snapshots"
  schedule_expression = "cron(0 4 * * ? *)"
  state               = "ENABLED"
}

resource "aws_cloudwatch_event_target" "cleanup_target" {
  rule      = aws_cloudwatch_event_rule.cleanup_schedule.name
  target_id = "BackupLambdaCleanup"
  arn       = aws_lambda_function.backup_lambda.arn

  input = jsonencode({
    backup_type = "cleanup"
  })
}

resource "aws_lambda_permission" "allow_eventbridge_cleanup" {
  statement_id  = "AllowExecutionFromEventBridgeCleanup"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backup_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.cleanup_schedule.arn
}

# ── Expansion: RDS Backup Schedule ───────────────────────────────────

resource "aws_cloudwatch_event_rule" "rds_backup_schedule" {
  name                = "aws-backup-rds-schedule"
  description         = "Nightly RDS snapshots (expansion module)"
  schedule_expression = "cron(0 3 * * ? *)"
  state               = "DISABLED"
}

resource "aws_cloudwatch_event_target" "rds_backup_target" {
  rule      = aws_cloudwatch_event_rule.rds_backup_schedule.name
  target_id = "BackupLambdaRDS"
  arn       = aws_lambda_function.backup_lambda.arn

  input = jsonencode({
    backup_type = "rds"
  })
}

resource "aws_lambda_permission" "allow_eventbridge_rds" {
  statement_id  = "AllowExecutionFromEventBridgeRDS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backup_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.rds_backup_schedule.arn
}

# ── Expansion: S3 Backup Schedule ────────────────────────────────────

resource "aws_cloudwatch_event_rule" "s3_backup_schedule" {
  name                = "aws-backup-s3-schedule"
  description         = "Nightly S3 bucket sync (expansion module)"
  schedule_expression = "cron(0 1 * * ? *)"
  state               = "DISABLED"
}

resource "aws_cloudwatch_event_target" "s3_backup_target" {
  rule      = aws_cloudwatch_event_rule.s3_backup_schedule.name
  target_id = "BackupLambdaS3"
  arn       = aws_lambda_function.backup_lambda.arn

  input = jsonencode({
    backup_type = "s3"
  })
}

resource "aws_lambda_permission" "allow_eventbridge_s3" {
  statement_id  = "AllowExecutionFromEventBridgeS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.backup_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.s3_backup_schedule.arn
}