# AWS Data Backup Pipeline - Complete Setup Guide

## 🚀 Quick Start (5 Minutes)

### Prerequisites Checklist

- [ ] AWS Account with administrative access
- [ ] AWS CLI installed and configured
- [ ] Python 3.9+ installed
- [ ] Git installed

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/LordSesay/aws-data-backup-pipeline.git
cd aws-data-backup-pipeline

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (use your preferred editor)
notepad .env  # Windows
# nano .env   # Linux/Mac
```

**Required Environment Variables:**
```bash
AWS_REGION=us-east-1
BACKUP_BUCKET=aws-backup-pipeline-your-account-id
SNS_TOPIC_ARN=arn:aws:sns:us-east-1:123456789012:backup-notifications
BACKUP_RETENTION_DAYS=30
```

### 3. Deploy Infrastructure

```bash
# Make deployment script executable (Linux/Mac)
chmod +x scripts/deploy.sh

# Run deployment
./scripts/deploy.sh

# For Windows, use PowerShell or run commands manually
```

### 4. Test the Setup

```bash
# Run backup status check
python scripts/check_backup_status.py --full-report

# Test backup functionality
python -m pytest tests/ -v
```

## 📋 Detailed Setup Instructions

### Step 1: AWS Account Preparation

#### 1.1 Create IAM User (Recommended)

```bash
# Create IAM user for backup operations
aws iam create-user --user-name backup-pipeline-user

# Create access key
aws iam create-access-key --user-name backup-pipeline-user
```

#### 1.2 Attach Required Policies

```bash
# Attach AWS managed policies
aws iam attach-user-policy \
    --user-name backup-pipeline-user \
    --policy-arn arn:aws:iam::aws:policy/AmazonEC2FullAccess

aws iam attach-user-policy \
    --user-name backup-pipeline-user \
    --policy-arn arn:aws:iam::aws:policy/AmazonRDSFullAccess

aws iam attach-user-policy \
    --user-name backup-pipeline-user \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Attach custom backup policy
aws iam put-user-policy \
    --user-name backup-pipeline-user \
    --policy-name BackupPipelinePolicy \
    --policy-document file://docs/iam_policies.json
```

### Step 2: Environment Configuration

#### 2.1 AWS CLI Configuration

```bash
# Configure AWS CLI with backup user credentials
aws configure --profile backup-pipeline
# Enter Access Key ID, Secret Access Key, Region, and Output format

# Set environment variable to use profile
export AWS_PROFILE=backup-pipeline
```

#### 2.2 Environment Variables Setup

Create `.env` file with your specific configuration:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=backup-pipeline

# Backup Configuration
BACKUP_BUCKET=aws-backup-pipeline-$(aws sts get-caller-identity --query Account --output text)
BACKUP_RETENTION_DAYS=30
GLACIER_TRANSITION_DAYS=7

# Notification Configuration
SNS_TOPIC_ARN=  # Will be created during deployment

# Logging Configuration
LOG_LEVEL=INFO
```

### Step 3: Infrastructure Deployment

#### 3.1 Manual Deployment Steps

If the automated script fails, follow these manual steps:

**Create S3 Backup Bucket:**
```bash
# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BACKUP_BUCKET="aws-backup-pipeline-${ACCOUNT_ID}"

# Create bucket
aws s3 mb s3://${BACKUP_BUCKET}

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket ${BACKUP_BUCKET} \
    --versioning-configuration Status=Enabled

# Set lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
    --bucket ${BACKUP_BUCKET} \
    --lifecycle-configuration file://config/s3_lifecycle.json
```

**Create SNS Topic:**
```bash
# Create SNS topic
SNS_TOPIC_ARN=$(aws sns create-topic \
    --name backup-pipeline-notifications \
    --query TopicArn --output text)

# Subscribe to email notifications
aws sns subscribe \
    --topic-arn ${SNS_TOPIC_ARN} \
    --protocol email \
    --notification-endpoint your-email@domain.com
```

**Deploy Lambda Function:**
```bash
# Create deployment package
cd src
zip -r ../backup-pipeline.zip . -x "*.pyc" "__pycache__/*"
cd ..

# Create IAM role for Lambda
aws iam create-role \
    --role-name BackupPipelineLambdaRole \
    --assume-role-policy-document file://docs/lambda-trust-policy.json

# Attach policies
aws iam attach-role-policy \
    --role-name BackupPipelineLambdaRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam put-role-policy \
    --role-name BackupPipelineLambdaRole \
    --policy-name BackupPipelinePolicy \
    --policy-document file://docs/iam_policies.json

# Create Lambda function
aws lambda create-function \
    --function-name aws-backup-pipeline \
    --runtime python3.9 \
    --role arn:aws:iam::${ACCOUNT_ID}:role/BackupPipelineLambdaRole \
    --handler backup_manager.lambda_handler \
    --zip-file fileb://backup-pipeline.zip \
    --timeout 900 \
    --memory-size 512 \
    --environment Variables="{BACKUP_BUCKET=${BACKUP_BUCKET},SNS_TOPIC_ARN=${SNS_TOPIC_ARN}}"
```

**Set up CloudWatch Events:**
```bash
# Create EventBridge rule
aws events put-rule \
    --name backup-pipeline-schedule \
    --schedule-expression "cron(0 2 * * ? *)" \
    --description "Daily backup pipeline execution"

# Add Lambda permission
aws lambda add-permission \
    --function-name aws-backup-pipeline \
    --statement-id backup-pipeline-schedule \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:${AWS_REGION}:${ACCOUNT_ID}:rule/backup-pipeline-schedule

# Add target to rule
aws events put-targets \
    --rule backup-pipeline-schedule \
    --targets "Id"="1","Arn"="arn:aws:lambda:${AWS_REGION}:${ACCOUNT_ID}:function:aws-backup-pipeline"
```

### Step 4: Configuration Customization

#### 4.1 Backup Schedule Configuration

Edit `config/backup_schedule.json` to customize:

- Backup frequency and timing
- Resource filters and tags
- Retention policies
- Notification preferences

#### 4.2 Resource Tagging Strategy

Tag your resources for selective backup:

```bash
# Tag EC2 instances for backup
aws ec2 create-tags \
    --resources i-1234567890abcdef0 \
    --tags Key=Backup,Value=true Key=Environment,Value=production

# Tag RDS instances for backup
aws rds add-tags-to-resource \
    --resource-name arn:aws:rds:us-east-1:123456789012:db:mydb \
    --tags Key=Backup,Value=true
```

### Step 5: Testing and Validation

#### 5.1 Run Initial Tests

```bash
# Test backup functionality
python tests/test_backup_pipeline.py

# Check system status
python scripts/check_backup_status.py --full-report

# Test manual backup
python -c "
from src.backup_manager import BackupManager
bm = BackupManager()
result = bm.run_full_backup()
print(result)
"
```

#### 5.2 Validate Backup Creation

```bash
# Check EC2 snapshots
aws ec2 describe-snapshots --owner-ids self \
    --filters "Name=tag:AutomatedBackup,Values=true"

# Check RDS snapshots
aws rds describe-db-snapshots --snapshot-type manual \
    --query 'DBSnapshots[?contains(TagList[?Key==`AutomatedBackup`].Value, `true`)]'

# Check S3 backup bucket
aws s3 ls s3://your-backup-bucket/s3-backups/ --recursive
```

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Issue 1: Lambda Timeout Errors

**Symptoms:** Lambda function times out during backup operations

**Solutions:**
```bash
# Increase Lambda timeout
aws lambda update-function-configuration \
    --function-name aws-backup-pipeline \
    --timeout 900

# Increase memory allocation
aws lambda update-function-configuration \
    --function-name aws-backup-pipeline \
    --memory-size 1024
```

#### Issue 2: Permission Denied Errors

**Symptoms:** IAM permission errors in Lambda logs

**Solutions:**
```bash
# Check IAM role policies
aws iam list-attached-role-policies --role-name BackupPipelineLambdaRole
aws iam get-role-policy --role-name BackupPipelineLambdaRole --policy-name BackupPipelinePolicy

# Update IAM policies if needed
aws iam put-role-policy \
    --role-name BackupPipelineLambdaRole \
    --policy-name BackupPipelinePolicy \
    --policy-document file://docs/iam_policies.json
```

#### Issue 3: S3 Bucket Access Issues

**Symptoms:** Cannot create or access backup bucket

**Solutions:**
```bash
# Check bucket policy
aws s3api get-bucket-policy --bucket your-backup-bucket

# Verify bucket exists and is accessible
aws s3 ls s3://your-backup-bucket/

# Check bucket region
aws s3api get-bucket-location --bucket your-backup-bucket
```

#### Issue 4: SNS Notification Issues

**Symptoms:** Not receiving backup notifications

**Solutions:**
```bash
# Check SNS topic subscriptions
aws sns list-subscriptions-by-topic --topic-arn your-sns-topic-arn

# Test SNS publishing
aws sns publish \
    --topic-arn your-sns-topic-arn \
    --message "Test notification" \
    --subject "Backup Pipeline Test"

# Confirm email subscription
# Check your email for confirmation message
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Set debug environment variable
export LOG_LEVEL=DEBUG

# Run backup with debug logging
python src/backup_manager.py

# Check CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/aws-backup-pipeline
aws logs get-log-events \
    --log-group-name /aws/lambda/aws-backup-pipeline \
    --log-stream-name latest-stream-name
```

## 📊 Monitoring Setup

### CloudWatch Dashboard

Create a custom dashboard for monitoring:

```bash
# Create dashboard JSON configuration
cat > dashboard.json << 'EOF'
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations", "FunctionName", "aws-backup-pipeline"],
          [".", "Errors", ".", "."],
          [".", "Duration", ".", "."]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "Backup Pipeline Metrics"
      }
    }
  ]
}
EOF

# Create dashboard
aws cloudwatch put-dashboard \
    --dashboard-name BackupPipelineMonitoring \
    --dashboard-body file://dashboard.json
```

### CloudWatch Alarms

Set up critical alarms:

```bash
# Backup failure alarm
aws cloudwatch put-metric-alarm \
    --alarm-name backup-pipeline-failures \
    --alarm-description "Alert on backup failures" \
    --metric-name Errors \
    --namespace AWS/Lambda \
    --statistic Sum \
    --period 300 \
    --threshold 1 \
    --comparison-operator GreaterThanOrEqualToThreshold \
    --dimensions Name=FunctionName,Value=aws-backup-pipeline \
    --alarm-actions your-sns-topic-arn

# High cost alarm
aws cloudwatch put-metric-alarm \
    --alarm-name backup-storage-cost \
    --alarm-description "Alert on high backup costs" \
    --metric-name EstimatedCharges \
    --namespace AWS/Billing \
    --statistic Maximum \
    --period 86400 \
    --threshold 100 \
    --comparison-operator GreaterThanThreshold \
    --dimensions Name=Currency,Value=USD \
    --alarm-actions your-sns-topic-arn
```

## 🔄 Maintenance Tasks

### Regular Maintenance Checklist

**Weekly:**
- [ ] Review backup success rates
- [ ] Check storage costs and utilization
- [ ] Validate recent backup integrity

**Monthly:**
- [ ] Test disaster recovery procedures
- [ ] Review and update retention policies
- [ ] Update IAM policies if needed
- [ ] Check for AWS service updates

**Quarterly:**
- [ ] Conduct full DR test
- [ ] Review and optimize costs
- [ ] Update documentation
- [ ] Security audit and compliance check

### Backup Validation Script

```bash
#!/bin/bash
# backup_validation.sh

echo "🔍 Validating backup integrity..."

# Check recent snapshots
python scripts/check_backup_status.py --days 1

# Test restore capability (non-destructive)
python -c "
from src.restore_manager import RestoreManager
rm = RestoreManager()
backups = rm.list_available_backups('ec2')
if backups['success'] and backups['backups']['ec2']:
    snapshot_id = backups['backups']['ec2'][0]['snapshot_id']
    validation = rm.validate_backup_integrity('ec2', snapshot_id)
    print(f'Backup validation: {validation}')
"

echo "✅ Validation complete"
```

## 📞 Support and Resources

### Getting Help

1. **Check Documentation**: Review all files in the `docs/` directory
2. **Run Diagnostics**: Use `check_backup_status.py --full-report`
3. **Check Logs**: Review CloudWatch logs for detailed error information
4. **GitHub Issues**: Report bugs or request features

### Useful Commands Reference

```bash
# Quick status check
python scripts/check_backup_status.py

# Manual backup trigger
aws lambda invoke --function-name aws-backup-pipeline response.json

# List recent backups
aws ec2 describe-snapshots --owner-ids self --max-items 10
aws rds describe-db-snapshots --snapshot-type manual --max-items 10

# Check costs
aws ce get-cost-and-usage --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity MONTHLY --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE

# Update Lambda function
cd src && zip -r ../backup-pipeline.zip . && cd ..
aws lambda update-function-code \
    --function-name aws-backup-pipeline \
    --zip-file fileb://backup-pipeline.zip
```

---

**Next Steps:** After completing setup, review the [Architecture Documentation](ARCHITECTURE.md) and [Study Notes](STUDY_NOTES.md) for deeper understanding of the system.