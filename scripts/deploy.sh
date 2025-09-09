#!/bin/bash

# AWS Data Backup Pipeline Deployment Script
# This script deploys the backup pipeline to AWS Lambda

set -e

echo "🚀 Starting AWS Data Backup Pipeline Deployment..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

# Get AWS account ID and region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

echo "📋 Deployment Details:"
echo "   Account ID: $ACCOUNT_ID"
echo "   Region: $REGION"

# Create deployment package
echo "📦 Creating deployment package..."
mkdir -p dist
cd src
zip -r ../dist/backup-pipeline.zip . -x "*.pyc" "__pycache__/*"
cd ..

# Create IAM role for Lambda
echo "🔐 Creating IAM role..."
aws iam create-role \
    --role-name BackupPipelineLambdaRole \
    --assume-role-policy-document file://docs/lambda-trust-policy.json \
    --description "Role for AWS Backup Pipeline Lambda functions" \
    2>/dev/null || echo "   Role already exists"

# Attach policies
aws iam attach-role-policy \
    --role-name BackupPipelineLambdaRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam put-role-policy \
    --role-name BackupPipelineLambdaRole \
    --policy-name BackupPipelinePolicy \
    --policy-document file://docs/iam_policies.json

# Wait for role propagation
echo "⏳ Waiting for IAM role propagation..."
sleep 10

# Create Lambda function
echo "⚡ Creating Lambda function..."
aws lambda create-function \
    --function-name aws-backup-pipeline \
    --runtime python3.9 \
    --role arn:aws:iam::$ACCOUNT_ID:role/BackupPipelineLambdaRole \
    --handler backup_manager.lambda_handler \
    --zip-file fileb://dist/backup-pipeline.zip \
    --timeout 900 \
    --memory-size 512 \
    --description "Automated AWS resource backup pipeline" \
    --environment Variables="{BACKUP_BUCKET=aws-backup-pipeline-$ACCOUNT_ID,AWS_REGION=$REGION}" \
    2>/dev/null || {
        echo "   Function exists, updating code..."
        aws lambda update-function-code \
            --function-name aws-backup-pipeline \
            --zip-file fileb://dist/backup-pipeline.zip
    }

# Create CloudWatch Events rule for scheduling
echo "⏰ Setting up scheduled execution..."
aws events put-rule \
    --name backup-pipeline-schedule \
    --schedule-expression "cron(0 2 * * ? *)" \
    --description "Daily backup pipeline execution"

# Add permission for CloudWatch Events to invoke Lambda
aws lambda add-permission \
    --function-name aws-backup-pipeline \
    --statement-id backup-pipeline-schedule \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:$REGION:$ACCOUNT_ID:rule/backup-pipeline-schedule \
    2>/dev/null || echo "   Permission already exists"

# Add Lambda target to CloudWatch Events rule
aws events put-targets \
    --rule backup-pipeline-schedule \
    --targets "Id"="1","Arn"="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:aws-backup-pipeline"

# Create SNS topic for notifications
echo "📧 Setting up notifications..."
SNS_TOPIC_ARN=$(aws sns create-topic --name backup-pipeline-notifications --query TopicArn --output text)
echo "   SNS Topic ARN: $SNS_TOPIC_ARN"

# Update Lambda environment with SNS topic
aws lambda update-function-configuration \
    --function-name aws-backup-pipeline \
    --environment Variables="{BACKUP_BUCKET=aws-backup-pipeline-$ACCOUNT_ID,AWS_REGION=$REGION,SNS_TOPIC_ARN=$SNS_TOPIC_ARN}"

echo "✅ Deployment completed successfully!"
echo ""
echo "📋 Next Steps:"
echo "   1. Subscribe to SNS topic for notifications:"
echo "      aws sns subscribe --topic-arn $SNS_TOPIC_ARN --protocol email --notification-endpoint your-email@domain.com"
echo ""
echo "   2. Test the pipeline:"
echo "      aws lambda invoke --function-name aws-backup-pipeline --payload '{}' response.json"
echo ""
echo "   3. Monitor execution:"
echo "      aws logs describe-log-groups --log-group-name-prefix /aws/lambda/aws-backup-pipeline"