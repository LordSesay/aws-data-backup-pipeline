variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "lambda_function_name" {
  description = "Name of the backup Lambda function"
  type        = string
  default     = "aws-data-backup-pipeline"
}

variable "backup_bucket" {
  description = "Centralized S3 backup bucket name"
  type        = string

  validation {
    condition     = length(var.backup_bucket) >= 3 && length(var.backup_bucket) <= 63
    error_message = "backup_bucket must be between 3 and 63 characters."
  }
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for backup notifications"
  type        = string
  default     = ""
}

variable "backup_retention_days" {
  description = "Retention period for backups"
  type        = number
  default     = 30

  validation {
    condition     = var.backup_retention_days > 0
    error_message = "backup_retention_days must be greater than 0."
  }
}