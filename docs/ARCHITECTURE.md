# Architecture — AWS Smart Backup Pipeline

## Overview

A serverless, event-driven backup system focused on protecting tagged EC2 workloads through automated EBS snapshots, retention cleanup, alerting, and monitoring. Infrastructure is provisioned via Terraform.

## Primary Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                    AWS Smart Backup Pipeline                         │
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────────────────┐ │
│  │ EventBridge  │───▶│   Lambda    │───▶│  EC2 (backup=true)      │ │
│  │ cron(0 2 *)  │    │  Backup Fn  │    │  ├─ Discover instances  │ │
│  └─────────────┘    └──────┬──────┘    │  ├─ Create EBS snapshots│ │
│                            │           │  └─ Tag with metadata   │ │
│                            │           └──────────────────────────┘ │
│                            │                                        │
│                            ▼                                        │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────────────────┐ │
│  │ EventBridge  │───▶│   Lambda    │───▶│  Retention Cleanup      │ │
│  │ cron(0 4 *)  │    │ Cleanup Fn  │    │  └─ Delete expired      │ │
│  └─────────────┘    └──────┬──────┘    │     snapshots            │ │
│                            │           └──────────────────────────┘ │
│                            │                                        │
│                            ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                  Monitoring & Alerting                        │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────┐ │   │
│  │  │ CloudWatch   │  │    SNS      │  │  CloudWatch Logs     │ │   │
│  │  │ Metrics      │  │  Alerts     │  │  Execution traces    │ │   │
│  │  └─────────────┘  └─────────────┘  └──────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Scheduling — EventBridge

| Rule | Schedule | Payload |
|------|----------|---------|
| EC2 Backup | `cron(0 2 * * ? *)` | `{"backup_type": "ec2"}` |
| Cleanup | `cron(0 4 * * ? *)` | `{"backup_type": "cleanup"}` |
| RDS Backup (expansion) | `cron(0 3 * * ? *)` | `{"backup_type": "rds"}` |
| S3 Backup (expansion) | `cron(0 1 * * ? *)` | `{"backup_type": "s3"}` |

### 2. Execution — Lambda

- **Runtime**: Python 3.11
- **Memory**: 512 MB
- **Timeout**: 15 minutes
- **Handler**: `lambda_handler.lambda_handler`

The Lambda function routes on `backup_type`:

| Type | Action |
|------|--------|
| `ec2` (default) | Discover tagged instances → create EBS snapshots → tag → notify |
| `cleanup` | Find expired snapshots by retention policy → delete → notify |
| `rds` | Create manual RDS snapshots (expansion) |
| `s3` | Copy objects to backup bucket (expansion) |
| `full` | Run all of the above sequentially |

### 3. EC2 Backup Logic

```
EC2 Instances (backup=true tag)
       │
       ▼
  For each instance:
       │
       ├─ Get attached EBS volumes
       │
       ├─ Create snapshot per volume
       │     Tags:
       │       Name = backup-{instance_id}-{volume_id}
       │       InstanceId = i-xxx
       │       VolumeId = vol-xxx
       │       BackupDate = ISO timestamp
       │       AutomatedBackup = true
       │
       └─ Log result, continue on failure
       │
       ▼
  SNS notification (success count / failure count)
```

### 4. Retention Cleanup Logic

```
Describe all self-owned snapshots
       │
       ▼
  Filter: AutomatedBackup=true AND StartTime < (now - retention_days)
       │
       ▼
  Delete each expired snapshot
       │
       ▼
  Log deletion count
```

Default retention: 30 days (configurable via `BACKUP_RETENTION_DAYS`).

### 5. IAM Security Model

The Lambda execution role follows least-privilege:

| Permission | Scope |
|------------|-------|
| `ec2:DescribeInstances`, `ec2:CreateSnapshot`, `ec2:DeleteSnapshot`, `ec2:DescribeSnapshots`, `ec2:CreateTags` | EC2/EBS operations |
| `sns:Publish` | Backup notifications |
| `sts:GetCallerIdentity` | Account ID resolution |
| `logs:*` | CloudWatch logging |
| `rds:*Snapshot*`, `rds:Describe*` | RDS expansion |
| `s3:Get*`, `s3:Put*`, `s3:List*` | S3 expansion |

### 6. Monitoring

- **CloudWatch Logs**: Every Lambda invocation is logged with backup results
- **SNS Alerts**: Sent on backup completion and failure
- **CloudWatch Metrics**: Lambda invocation count, error count, duration

## Data Flow — Backup

```
1. EventBridge fires cron trigger
2. Lambda invoked with {"backup_type": "ec2"}
3. Lambda calls ec2:DescribeInstances with tag filter backup=true
4. For each instance, create EBS snapshot with metadata tags
5. Send SNS notification with success/failure summary
6. CloudWatch captures execution log
```

## Data Flow — Cleanup

```
1. EventBridge fires cleanup trigger
2. Lambda invoked with {"backup_type": "cleanup"}
3. Lambda calls ec2:DescribeSnapshots (owner=self, tag=AutomatedBackup)
4. Filter snapshots older than retention_days
5. Delete expired snapshots
6. Log cleanup results
```

## Data Flow — Restore

```
1. Operator identifies snapshot to restore
2. RestoreManager validates snapshot integrity
3. AMI registered from snapshot
4. New EC2 instance launched from AMI
5. Instance tagged with restore metadata
```

## Infrastructure (Terraform)

All infrastructure is defined in `infra/`:

| File | Purpose |
|------|---------|
| `main.tf` | Provider and version constraints |
| `lambda.tf` | Lambda function resource |
| `eventbridge.tf` | Scheduled triggers and permissions |
| `iam.tf` | Execution role and policies |
| `variables.tf` | Configurable inputs |
| `outputs.tf` | Deployment outputs |

## Expansion Modules

These are implemented but secondary to the core EC2/EBS backup flow:

### RDS Snapshot Automation
- Creates manual DB snapshots with metadata tags
- Cleanup deletes expired RDS snapshots
- Triggered on separate EventBridge schedule

### S3 Bucket Backup
- Copies objects from source buckets to centralized backup bucket
- Backup bucket configured with lifecycle policies:
  - Day 0–7: S3 Standard
  - Day 7+: Glacier
  - Day 30+: Deep Archive
- Versioning enabled on backup bucket

## Future Enhancements

- S3 Cross-Region Replication for disaster recovery
- CloudWatch dashboards for backup visibility
- Compliance reporting automation
- Cost optimization analytics
