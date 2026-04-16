# AWS Data Backup Pipeline

## Overview

This project is an evolving AWS-based backup and disaster recovery platform designed to protect critical infrastructure across EC2, RDS, and S3.

The current implementation focuses on:

- Automated snapshot creation for EC2 and RDS
- S3 data backup into a centralized backup bucket
- Lifecycle policies for cost optimization (Glacier / Deep Archive)
- Restore workflows for disaster recovery scenarios
- SNS notifications for backup status

This project is being actively expanded toward a production-grade architecture that includes:

- Event-driven scheduling (EventBridge + Lambda)
- Cross-region backup replication
- Infrastructure as Code (Terraform)
- Centralized logging and monitoring
- Compliance and reporting automation

## Current Architecture (Implemented)

- Python Backup Manager (boto3)
- EC2 Snapshot Automation
- RDS Snapshot Automation
- S3 Backup Copy Process
- Backup S3 Bucket with Lifecycle Policies
- SNS Notifications

## Target Architecture (In Progress)

- EventBridge → Scheduled backup triggers
- AWS Lambda → Serverless execution layer
- S3 Cross-Region Replication → Disaster recovery
- CloudWatch → Logging and alerting
- Terraform → Infrastructure provisioning
- IAM Roles → Least privilege security model

## Features

- ✅ **Automated EC2 Snapshot Creation**
- ✅ **RDS Database Backups**
- ✅ **S3 Backup Copy into Centralized Backup Bucket**
- ✅ **Lifecycle Management** (S3 → Glacier → Deep Archive)
- ✅ **Backup Verification & Validation**
- ✅ **Disaster Recovery Restore Workflows**
- ✅ **SNS Backup Notifications**

**Planned Enhancement:**
- Implement native S3 Cross-Region Replication (CRR)

## Example Output

Backup Execution Result:

```json
{
  "ec2_snapshots_created": 2,
  "rds_snapshots_created": 1,
  "s3_objects_copied": 145,
  "status": "SUCCESS"
}
```

## Testing Coverage

- Backup workflow execution
- S3 backup validation
- Cleanup and lifecycle logic
- Restore functionality

Tests are located in `/tests` directory.

## Prerequisites

- AWS CLI configured with appropriate permissions
- Python 3.9+
- Terraform (optional, for infrastructure as code)
- AWS Account with the following services enabled:
  - Lambda
  - S3
  - EC2
  - RDS
  - CloudWatch
  - SNS

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/LordSesay/aws-data-backup-pipeline.git
cd aws-data-backup-pipeline
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and region
```

### 3. Set Environment Variables

```bash
cp .env.example .env
# Edit .env with your specific configuration
```

### 4. Deploy Infrastructure

```bash
# Using the deployment script
./scripts/deploy.sh

# Or manually deploy Lambda functions
python scripts/deploy_lambda.py
```

### 5. Test the Pipeline

```bash
# Run backup test
python tests/test_backup_pipeline.py

# Check backup status
python scripts/check_backup_status.py
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | Target AWS region | `us-east-1` |
| `BACKUP_BUCKET` | S3 bucket for backups | `aws-backup-pipeline-{account-id}` |
| `SNS_TOPIC_ARN` | SNS topic for notifications | Required |
| `BACKUP_RETENTION_DAYS` | Days to retain backups | `30` |
| `GLACIER_TRANSITION_DAYS` | Days before moving to Glacier | `7` |

### Backup Schedule

Configure backup schedules in `config/backup_schedule.json`:

```json
{
  "ec2_snapshots": "cron(0 2 * * ? *)",
  "rds_backups": "cron(0 3 * * ? *)",
  "s3_sync": "cron(0 1 * * ? *)"
}
```

## Usage Examples

### Manual Backup Trigger

```python
from src.backup_manager import BackupManager

# Initialize backup manager
backup_mgr = BackupManager()

# Backup specific EC2 instance
backup_mgr.backup_ec2_instance('i-1234567890abcdef0')

# Backup RDS database
backup_mgr.backup_rds_database('my-database')
```

### Restore Operations

```python
from src.restore_manager import RestoreManager

# Initialize restore manager
restore_mgr = RestoreManager()

# Restore EC2 from snapshot
restore_mgr.restore_ec2_from_snapshot('snap-1234567890abcdef0')

# Restore RDS from backup
restore_mgr.restore_rds_from_backup('my-database', '2024-01-15')
```

## Monitoring & Alerts

- **SNS Notifications**: Email/SMS alerts for backup failures
- **CloudWatch Logs**: Backup operation logging
- **Cost Tracking**: Monthly backup cost reports

## Security Considerations

- **IAM Roles**: Least privilege access for Lambda functions
- **Encryption**: All backups encrypted at rest and in transit
- **Access Logging**: CloudTrail integration for audit trails
- **Network Security**: VPC endpoints for secure communication

## Cost Optimization

- **Intelligent Tiering**: Automatic transition to cheaper storage classes
- **Lifecycle Policies**: Automated deletion of old backups
- **Centralized Backup Storage**: Strategic bucket placement to minimize transfer costs
- **Monitoring**: Cost alerts and optimization recommendations

## Troubleshooting

### Common Issues

1. **Lambda Timeout**: Increase timeout in `src/lambda_config.py`
2. **Permission Errors**: Check IAM roles in `docs/iam_policies.json`
3. **Storage Costs**: Review lifecycle policies in `config/s3_lifecycle.json`

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python src/backup_manager.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: [sesay.malcolm.dev@gmail.com]
- 🐛 Issues: [GitHub Issues](https://github.com/LordSesay/aws-data-backup-pipeline/issues)
- 📖 Documentation: [Wiki](https://github.com/LordSesay/aws-data-backup-pipeline/wiki)

## Acknowledgments

- AWS Documentation and Best Practices
- Community contributions and feedback
- Open source libraries and tools used in this project
