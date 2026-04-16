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

---

## Architecture Diagram

![AWS Backup Architecture](./docs/aws_backup_architecture_diagram.png)

This diagram represents the current and evolving architecture of the backup pipeline.

### Flow Overview

- EventBridge triggers scheduled backup jobs
- AWS Lambda executes backup logic across EC2, RDS, and S3
- Backups are stored in a centralized S3 bucket
- Lifecycle policies optimize storage cost (Glacier / Deep Archive)
- SNS provides alerting for backup success/failure
- CloudWatch captures logs and metrics for monitoring

> Current implementation includes core backup logic and lifecycle management.  
> Monitoring, compliance reporting, and infrastructure automation are being actively implemented.

> Cross-region replication and Terraform-based provisioning are part of the next implementation phase.

---

## Current Architecture (Implemented)

- Python Backup Manager (boto3)
- EC2 Snapshot Automation
- RDS Snapshot Automation
- S3 Backup Copy Process
- Backup S3 Bucket with Lifecycle Policies
- SNS Notifications

---

## Target Architecture (In Progress)

- EventBridge → Scheduled backup triggers
- AWS Lambda → Serverless execution layer
- S3 Cross-Region Replication (CRR) → Disaster recovery
- CloudWatch → Logging and alerting
- Terraform → Infrastructure provisioning
- IAM Roles → Least privilege security model

---

## Features

- ✅ **Automated EC2 Snapshot Creation**
- ✅ **RDS Database Backups**
- ✅ **S3 Backup Copy into Centralized Backup Bucket**
- ✅ **Lifecycle Management (S3 → Glacier → Deep Archive)**
- ✅ **Backup Verification & Validation**
- ✅ **Disaster Recovery Restore Workflows**
- ✅ **SNS Backup Notifications**

### Planned Enhancements

- Native S3 Cross-Region Replication (CRR)
- Infrastructure provisioning with Terraform
- Enhanced monitoring and reporting

---

## Example Output

Backup Execution Result:

```json
{
  "ec2_snapshots_created": 2,
  "rds_snapshots_created": 1,
  "s3_objects_copied": 145,
  "status": "SUCCESS"
}
