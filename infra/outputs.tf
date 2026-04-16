output "lambda_function_name" {
  value = aws_lambda_function.backup_lambda.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.backup_lambda.arn
}

output "ec2_backup_rule_name" {
  value = aws_cloudwatch_event_rule.ec2_backup_schedule.name
}

output "cleanup_rule_name" {
  value = aws_cloudwatch_event_rule.cleanup_schedule.name
}

output "rds_backup_rule_name" {
  value = aws_cloudwatch_event_rule.rds_backup_schedule.name
}

output "s3_backup_rule_name" {
  value = aws_cloudwatch_event_rule.s3_backup_schedule.name
}
