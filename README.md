# AWS Data Backup Pipeline

## Problem Statement

Organizations face critical challenges in data protection and disaster recovery:
- **Data Loss Risk**: Critical business data stored across multiple AWS services without automated backup
- **Manual Processes**: Time-consuming manual backup procedures prone to human error
- **Compliance Requirements**: Need for automated, scheduled backups to meet regulatory standards
- **Cost Optimization**: Inefficient backup strategies leading to unnecessary storage costs
- **Recovery Time**: Slow disaster recovery processes affecting business continuity

## Solution Overview

This automated AWS data backup pipeline provides:
- **Automated Scheduling**: Lambda-triggered backups on configurable schedules
- **Multi-Service Support**: Backs up EC2 instances, RDS databases, and S3 buckets
- **Cost-Effective Storage**: Intelligent tiering using S3 Glacier for long-term retention
- **Monitoring & Alerts**: CloudWatch integration with SNS notifications
- **Easy Recovery**: Streamlined restore processes with documented procedures

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CloudWatch    │───▶│   Lambda Trigger │───▶│  Backup Lambda  │
│   Events        │    │   (Scheduler)    │    │   Function      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│      SNS        │◀───│   CloudWatch     │◀───│  Target AWS     │
│  Notifications  │    │    Logs          │    │   Services      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
                                               ┌─────────────────┐
                                               │   S3 Backup     │
                                               │    Storage      │
                                               │  (with Glacier) │
                                               └─────────────────┘
```

## Features

- ✅ **Automated EC2 Snapshot Creation**
- ✅ **RDS Database Backups**
- ✅ **S3 Cross-Region Replication**
- ✅ **Lifecycle Management** (S3 → Glacier → Deep Archive)
- ✅ **Backup Verification & Validation**
- ✅ **Cost Optimization Reports**
- ✅ **Disaster Recovery Testing**
- ✅ **Compliance Reporting**

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

The pipeline includes comprehensive monitoring:

- **CloudWatch Dashboards**: Visual monitoring of backup operations
- **SNS Notifications**: Email/SMS alerts for backup failures
- **Cost Tracking**: Monthly backup cost reports
- **Compliance Reports**: Automated backup compliance documentation

## Security Considerations

- **IAM Roles**: Least privilege access for Lambda functions
- **Encryption**: All backups encrypted at rest and in transit
- **Access Logging**: CloudTrail integration for audit trails
- **Network Security**: VPC endpoints for secure communication

## Cost Optimization

- **Intelligent Tiering**: Automatic transition to cheaper storage classes
- **Lifecycle Policies**: Automated deletion of old backups
- **Cross-Region Optimization**: Strategic backup placement
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

- 📧 Email: [your-email@domain.com]
- 🐛 Issues: [GitHub Issues](https://github.com/LordSesay/aws-data-backup-pipeline/issues)
- 📖 Documentation: [Wiki](https://github.com/LordSesay/aws-data-backup-pipeline/wiki)

## Acknowledgments

- AWS Documentation and Best Practices
- Community contributions and feedback
- Open source libraries and tools used in this project