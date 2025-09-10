# AWS Data Backup Pipeline - Testing Guide

## 🧪 **Testing Overview**

This guide provides comprehensive testing procedures for the AWS Data Backup Pipeline, including local testing, AWS environment testing, and production validation.

## 📋 **Testing Checklist**

### **Pre-Testing Requirements**
- [ ] Python 3.9+ installed
- [ ] AWS CLI configured
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Environment variables configured
- [ ] AWS credentials with appropriate permissions

## 🔧 **Local Testing (No AWS Costs)**

### **1. Basic Functionality Test**

```bash
# Run basic import and initialization test
python test_simple.py
```

**Expected Output:**
```
SUCCESS: boto3 imported successfully
SUCCESS: moto base module imported
SUCCESS: BackupManager imported successfully
SUCCESS: RestoreManager imported successfully

All imports successful! Ready for testing.
SUCCESS: BackupManager initialized successfully
SUCCESS: RestoreManager initialized successfully

Basic functionality test passed!
The backup pipeline is ready for deployment!
```

### **2. Unit Tests with Mocked Services**

Create a comprehensive test file:

```python
# tests/test_local.py
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from backup_manager import BackupManager
from restore_manager import RestoreManager

class TestBackupPipeline(unittest.TestCase):
    
    def setUp(self):
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['BACKUP_BUCKET'] = 'test-backup-bucket'
        os.environ['BACKUP_RETENTION_DAYS'] = '7'
    
    @patch('boto3.client')
    def test_backup_manager_init(self, mock_boto_client):
        """Test BackupManager initialization"""
        backup_manager = BackupManager()
        self.assertIsNotNone(backup_manager)
        self.assertEqual(backup_manager.region, 'us-east-1')
    
    @patch('boto3.client')
    def test_restore_manager_init(self, mock_boto_client):
        """Test RestoreManager initialization"""
        restore_manager = RestoreManager()
        self.assertIsNotNone(restore_manager)
        self.assertEqual(restore_manager.region, 'us-east-1')

if __name__ == '__main__':
    unittest.main()
```

Run the test:
```bash
python -m unittest tests.test_local -v
```

## 🚀 **AWS Environment Testing**

### **Phase 1: Setup Test Environment**

#### **1.1 Create Test Resources**

```bash
# Set variables
export TEST_INSTANCE_NAME="backup-test-instance"
export TEST_DB_NAME="backup-test-db"
export TEST_BUCKET_NAME="backup-test-bucket-$(date +%s)"

# Create test EC2 instance (t2.micro - free tier)
aws ec2 run-instances \
    --image-id ami-0abcdef1234567890 \
    --instance-type t2.micro \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$TEST_INSTANCE_NAME},{Key=Backup,Value=true},{Key=Environment,Value=test}]" \
    --query 'Instances[0].InstanceId' \
    --output text

# Create test RDS instance (db.t3.micro)
aws rds create-db-instance \
    --db-instance-identifier $TEST_DB_NAME \
    --db-instance-class db.t3.micro \
    --engine mysql \
    --master-username testuser \
    --master-user-password TestPass123! \
    --allocated-storage 20 \
    --tags Key=Backup,Value=true Key=Environment,Value=test

# Create test S3 bucket
aws s3 mb s3://$TEST_BUCKET_NAME
echo "Test content" | aws s3 cp - s3://$TEST_BUCKET_NAME/test-file.txt
```

#### **1.2 Deploy Backup Infrastructure**

```bash
# Run deployment script
chmod +x scripts/deploy.sh
./scripts/deploy.sh

# Verify deployment
aws lambda get-function --function-name aws-backup-pipeline
aws events describe-rule --name backup-pipeline-schedule
```

### **Phase 2: Functional Testing**

#### **2.1 Manual Backup Test**

```bash
# Trigger manual backup
aws lambda invoke \
    --function-name aws-backup-pipeline \
    --payload '{"backup_type":"full"}' \
    response.json

# Check response
cat response.json

# Expected response structure:
{
  "statusCode": 200,
  "body": "{\"timestamp\": \"2024-01-15T10:30:00\", \"summary\": {\"backup_status\": \"SUCCESS\"}}"
}
```

#### **2.2 Verify Backup Creation**

```bash
# Check EC2 snapshots
aws ec2 describe-snapshots \
    --owner-ids self \
    --filters "Name=tag:AutomatedBackup,Values=true" \
    --query 'Snapshots[*].[SnapshotId,Description,StartTime,State]' \
    --output table

# Check RDS snapshots
aws rds describe-db-snapshots \
    --snapshot-type manual \
    --query 'DBSnapshots[?contains(TagList[?Key==`AutomatedBackup`].Value, `true`)].[DBSnapshotIdentifier,SnapshotCreateTime,Status]' \
    --output table

# Check S3 backup bucket
aws s3 ls s3://aws-backup-pipeline-$(aws sts get-caller-identity --query Account --output text)/s3-backups/ --recursive
```

#### **2.3 Status Monitoring Test**

```bash
# Run status check
python scripts/check_backup_status.py --full-report

# Expected output sections:
# - Lambda Function Health
# - Backup Schedule Status  
# - Recent Backup Operations
# - Storage Utilization
# - Recent Logs
```

### **Phase 3: Disaster Recovery Testing**

#### **3.1 Test Backup Listing**

```python
# test_restore.py
import sys
import os
sys.path.insert(0, 'src')

from restore_manager import RestoreManager

def test_list_backups():
    restore_manager = RestoreManager()
    
    # List EC2 backups
    ec2_backups = restore_manager.list_available_backups('ec2')
    print(f"EC2 Backups: {len(ec2_backups.get('backups', {}).get('ec2', []))}")
    
    # List RDS backups
    rds_backups = restore_manager.list_available_backups('rds')
    print(f"RDS Backups: {len(rds_backups.get('backups', {}).get('rds', []))}")
    
    return ec2_backups, rds_backups

if __name__ == "__main__":
    test_list_backups()
```

```bash
python test_restore.py
```

#### **3.2 Test Backup Validation**

```python
# test_validation.py
import sys
sys.path.insert(0, 'src')

from restore_manager import RestoreManager

def test_backup_validation():
    restore_manager = RestoreManager()
    
    # Get recent backups
    backups = restore_manager.list_available_backups('ec2')
    
    if backups['success'] and backups['backups']['ec2']:
        snapshot_id = backups['backups']['ec2'][0]['snapshot_id']
        
        # Validate backup integrity
        validation = restore_manager.validate_backup_integrity('ec2', snapshot_id)
        print(f"Backup validation for {snapshot_id}: {validation}")
        
        return validation['valid']
    
    return False

if __name__ == "__main__":
    is_valid = test_backup_validation()
    print(f"Backup validation result: {'PASSED' if is_valid else 'FAILED'}")
```

## 📊 **Performance Testing**

### **Load Testing**

```bash
# Create multiple test instances for load testing
for i in {1..5}; do
    aws ec2 run-instances \
        --image-id ami-0abcdef1234567890 \
        --instance-type t2.micro \
        --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=load-test-$i},{Key=Backup,Value=true}]"
done

# Trigger backup and measure performance
time aws lambda invoke \
    --function-name aws-backup-pipeline \
    --payload '{"backup_type":"ec2"}' \
    load_test_response.json
```

### **Cost Analysis Testing**

```bash
# Monitor costs during testing
aws ce get-cost-and-usage \
    --time-period Start=2024-01-01,End=2024-01-31 \
    --granularity DAILY \
    --metrics BlendedCost \
    --group-by Type=DIMENSION,Key=SERVICE \
    --filter file://cost-filter.json

# cost-filter.json
{
  "Dimensions": {
    "Key": "SERVICE",
    "Values": ["Amazon Elastic Compute Cloud - Compute", "Amazon Simple Storage Service", "AWS Lambda"]
  }
}
```

## 🔍 **Monitoring and Alerting Tests**

### **CloudWatch Metrics Validation**

```bash
# Check custom metrics
aws cloudwatch get-metric-statistics \
    --namespace BackupPipeline \
    --metric-name BackupSuccess \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z \
    --period 3600 \
    --statistics Sum

# Check Lambda metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/Lambda \
    --metric-name Invocations \
    --dimensions Name=FunctionName,Value=aws-backup-pipeline \
    --start-time 2024-01-01T00:00:00Z \
    --end-time 2024-01-02T00:00:00Z \
    --period 3600 \
    --statistics Sum
```

### **SNS Notification Testing**

```bash
# Test SNS notifications
aws sns publish \
    --topic-arn $(aws sns list-topics --query 'Topics[?contains(TopicArn, `backup-notifications`)].TopicArn' --output text) \
    --message "Test backup notification" \
    --subject "Backup Pipeline Test"
```

## 🧹 **Cleanup and Teardown**

### **Test Resource Cleanup**

```bash
# Cleanup script
#!/bin/bash

echo "Cleaning up test resources..."

# Terminate test EC2 instances
aws ec2 describe-instances \
    --filters "Name=tag:Environment,Values=test" "Name=instance-state-name,Values=running" \
    --query 'Reservations[*].Instances[*].InstanceId' \
    --output text | xargs -r aws ec2 terminate-instances --instance-ids

# Delete test RDS instances
aws rds describe-db-instances \
    --query 'DBInstances[?contains(TagList[?Key==`Environment`].Value, `test`)].DBInstanceIdentifier' \
    --output text | xargs -r -I {} aws rds delete-db-instance --db-instance-identifier {} --skip-final-snapshot

# Delete test snapshots
aws ec2 describe-snapshots \
    --owner-ids self \
    --filters "Name=tag:Environment,Values=test" \
    --query 'Snapshots[*].SnapshotId' \
    --output text | xargs -r aws ec2 delete-snapshot --snapshot-id

# Delete test S3 buckets
aws s3 ls | grep backup-test-bucket | awk '{print $3}' | xargs -r -I {} aws s3 rb s3://{} --force

echo "Cleanup completed!"
```

## 📈 **Test Results Documentation**

### **Test Report Template**

```markdown
# Backup Pipeline Test Report

**Date:** 2024-01-15
**Tester:** [Your Name]
**Environment:** AWS Account [Account-ID]

## Test Summary
- **Total Tests:** 15
- **Passed:** 14
- **Failed:** 1
- **Success Rate:** 93.3%

## Test Results

### Local Testing
- [x] Basic functionality test - PASSED
- [x] Import validation - PASSED
- [x] Configuration loading - PASSED

### AWS Environment Testing
- [x] Infrastructure deployment - PASSED
- [x] Manual backup trigger - PASSED
- [x] EC2 snapshot creation - PASSED
- [x] RDS snapshot creation - PASSED
- [x] S3 backup replication - PASSED
- [x] Status monitoring - PASSED

### Disaster Recovery Testing
- [x] Backup listing - PASSED
- [x] Backup validation - PASSED
- [ ] Full restore test - FAILED (timeout issue)

### Performance Testing
- [x] Load testing (5 instances) - PASSED
- [x] Cost analysis - PASSED

## Issues Found
1. **Restore timeout:** Full restore test failed due to Lambda timeout
   - **Solution:** Increase Lambda timeout to 15 minutes
   - **Status:** Fixed

## Recommendations
1. Implement Step Functions for long-running restore operations
2. Add more granular error handling for network timeouts
3. Create automated test suite for CI/CD pipeline

## Cost Analysis
- **Testing Cost:** $2.45
- **Monthly Projected Cost:** $8.50
- **Cost per GB:** $0.032

## Conclusion
The backup pipeline is production-ready with 93.3% test success rate. One minor issue with restore timeouts has been identified and resolved.
```

## 🚀 **Continuous Testing**

### **Automated Test Script**

```bash
#!/bin/bash
# automated_test.sh

set -e

echo "Starting automated backup pipeline tests..."

# 1. Local tests
echo "Running local tests..."
python test_simple.py

# 2. AWS connectivity test
echo "Testing AWS connectivity..."
aws sts get-caller-identity

# 3. Backup functionality test
echo "Testing backup functionality..."
aws lambda invoke --function-name aws-backup-pipeline --payload '{}' test_response.json
cat test_response.json

# 4. Status check
echo "Running status check..."
python scripts/check_backup_status.py --days 1

# 5. Validation
echo "Validating recent backups..."
python test_validation.py

echo "All tests completed successfully!"
```

### **Scheduled Testing**

```bash
# Add to crontab for weekly testing
# 0 6 * * 0 /path/to/automated_test.sh >> /var/log/backup_tests.log 2>&1
```

## 📞 **Troubleshooting Test Issues**

### **Common Test Failures**

| Issue | Cause | Solution |
|-------|-------|----------|
| Import errors | Missing dependencies | `pip install -r requirements.txt` |
| AWS credential errors | Unconfigured AWS CLI | `aws configure` |
| Lambda timeout | Large backup operations | Increase timeout/memory |
| Permission denied | Insufficient IAM permissions | Update IAM policies |
| S3 access errors | Bucket doesn't exist | Run deployment script |

### **Debug Mode**

```bash
# Enable debug logging for troubleshooting
export LOG_LEVEL=DEBUG
python scripts/check_backup_status.py --full-report
```

---

**Next Steps:** After completing testing, review results and proceed with production deployment following the [Setup Guide](SETUP_GUIDE.md).