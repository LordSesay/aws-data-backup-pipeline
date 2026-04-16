"""
AWS Smart Backup Pipeline — Backup Manager

Primary: Tag-driven EC2/EBS snapshot automation with retention cleanup.
Secondary: RDS snapshot and S3 bucket backup (expansion modules).
"""

import boto3
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupManager:
    """Automated backup manager for AWS resources. EC2/EBS is the primary workflow."""

    def __init__(self, region: str = None):
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        self.ec2 = boto3.client('ec2', region_name=self.region)
        self.rds = boto3.client('rds', region_name=self.region)
        self.s3 = boto3.client('s3', region_name=self.region)
        self.sns = boto3.client('sns', region_name=self.region)

        self.backup_bucket = os.getenv('BACKUP_BUCKET', f'aws-backup-pipeline-{self._get_account_id()}')
        self.sns_topic_arn = os.getenv('SNS_TOPIC_ARN')
        self.retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))

        logger.info(f"BackupManager initialized for region: {self.region}")

    def _get_account_id(self) -> str:
        return boto3.client('sts').get_caller_identity()['Account']

    # ── Primary: EC2/EBS Backup ──────────────────────────────────────

    def backup_ec2_instances(self, instance_ids: List[str] = None) -> Dict:
        """
        Create EBS snapshots for EC2 instances.

        If no instance_ids provided, discovers instances tagged backup=true.
        Each snapshot is tagged with instance ID, volume ID, backup date,
        and an AutomatedBackup flag for retention cleanup.
        """
        results = {'success': [], 'failed': []}

        try:
            if instance_ids:
                instances = self.ec2.describe_instances(InstanceIds=instance_ids)
            else:
                # Tag-driven discovery: find instances tagged for backup
                instances = self.ec2.describe_instances(Filters=[
                    {'Name': 'tag:backup', 'Values': ['true']},
                    {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
                ])

            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    try:
                        for block_device in instance.get('BlockDeviceMappings', []):
                            volume_id = block_device['Ebs']['VolumeId']
                            now = datetime.now()

                            snapshot = self.ec2.create_snapshot(
                                VolumeId=volume_id,
                                Description=f'Automated backup — {instance_id} — {now.isoformat()}',
                                TagSpecifications=[{
                                    'ResourceType': 'snapshot',
                                    'Tags': [
                                        {'Key': 'Name', 'Value': f'backup-{instance_id}-{volume_id}'},
                                        {'Key': 'InstanceId', 'Value': instance_id},
                                        {'Key': 'VolumeId', 'Value': volume_id},
                                        {'Key': 'BackupDate', 'Value': now.isoformat()},
                                        {'Key': 'AutomatedBackup', 'Value': 'true'},
                                    ]
                                }]
                            )

                            results['success'].append({
                                'instance_id': instance_id,
                                'volume_id': volume_id,
                                'snapshot_id': snapshot['SnapshotId']
                            })
                            logger.info(f"Snapshot {snapshot['SnapshotId']} created for {instance_id}/{volume_id}")

                    except Exception as e:
                        logger.error(f"Failed to backup {instance_id}: {e}")
                        results['failed'].append({'instance_id': instance_id, 'error': str(e)})

            self._send_notification(
                f"EC2 Backup: {len(results['success'])} snapshots created, {len(results['failed'])} failed"
            )

        except Exception as e:
            logger.error(f"EC2 backup operation failed: {e}")
            results['failed'].append({'error': str(e)})

        return results

    # ── Retention Cleanup ────────────────────────────────────────────

    def cleanup_old_backups(self) -> Dict:
        """Delete automated snapshots older than the retention period."""
        results = {'ec2_snapshots_deleted': 0, 'rds_snapshots_deleted': 0, 's3_objects_deleted': 0}
        cutoff = datetime.now() - timedelta(days=self.retention_days)

        try:
            # EC2 snapshot cleanup
            snapshots = self.ec2.describe_snapshots(OwnerIds=['self'])
            for snap in snapshots['Snapshots']:
                tags = {t['Key']: t['Value'] for t in snap.get('Tags', [])}
                if (tags.get('AutomatedBackup') == 'true' and
                        snap['StartTime'].replace(tzinfo=None) < cutoff):
                    self.ec2.delete_snapshot(SnapshotId=snap['SnapshotId'])
                    results['ec2_snapshots_deleted'] += 1
                    logger.info(f"Deleted expired snapshot: {snap['SnapshotId']}")

            # RDS snapshot cleanup (expansion)
            rds_snapshots = self.rds.describe_db_snapshots(SnapshotType='manual')
            for snap in rds_snapshots['DBSnapshots']:
                tags = {t['Key']: t['Value'] for t in snap.get('TagList', [])}
                if (tags.get('AutomatedBackup') == 'true' and
                        snap.get('SnapshotCreateTime', datetime.min).replace(tzinfo=None) < cutoff):
                    self.rds.delete_db_snapshot(DBSnapshotIdentifier=snap['DBSnapshotIdentifier'])
                    results['rds_snapshots_deleted'] += 1
                    logger.info(f"Deleted expired RDS snapshot: {snap['DBSnapshotIdentifier']}")

            logger.info(f"Cleanup complete: {results}")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

        return results

    # ── Expansion: RDS Backup ────────────────────────────────────────

    def backup_rds_databases(self, db_identifiers: List[str] = None) -> Dict:
        """Create manual snapshots for RDS databases (expansion module)."""
        results = {'success': [], 'failed': []}

        try:
            if db_identifiers:
                databases = []
                for db_id in db_identifiers:
                    try:
                        db = self.rds.describe_db_instances(DBInstanceIdentifier=db_id)
                        databases.extend(db['DBInstances'])
                    except Exception as e:
                        results['failed'].append({'db_identifier': db_id, 'error': str(e)})
            else:
                databases = self.rds.describe_db_instances()['DBInstances']

            for db in databases:
                db_id = db['DBInstanceIdentifier']
                try:
                    snapshot_id = f"{db_id}-backup-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    self.rds.create_db_snapshot(
                        DBSnapshotIdentifier=snapshot_id,
                        DBInstanceIdentifier=db_id,
                        Tags=[
                            {'Key': 'BackupDate', 'Value': datetime.now().isoformat()},
                            {'Key': 'AutomatedBackup', 'Value': 'true'},
                            {'Key': 'SourceDB', 'Value': db_id}
                        ]
                    )
                    results['success'].append({'db_identifier': db_id, 'snapshot_id': snapshot_id})
                    logger.info(f"RDS snapshot {snapshot_id} created for {db_id}")
                except Exception as e:
                    logger.error(f"Failed to backup RDS {db_id}: {e}")
                    results['failed'].append({'db_identifier': db_id, 'error': str(e)})

            self._send_notification(
                f"RDS Backup: {len(results['success'])} successful, {len(results['failed'])} failed"
            )

        except Exception as e:
            logger.error(f"RDS backup operation failed: {e}")
            results['failed'].append({'error': str(e)})

        return results

    # ── Expansion: S3 Backup ─────────────────────────────────────────

    def backup_s3_buckets(self, bucket_names: List[str] = None) -> Dict:
        """Copy S3 objects to centralized backup bucket (expansion module)."""
        results = {'success': [], 'failed': []}

        try:
            self._ensure_backup_bucket()

            if bucket_names:
                buckets = [{'Name': n} for n in bucket_names]
            else:
                buckets = [b for b in self.s3.list_buckets()['Buckets']
                           if b['Name'] != self.backup_bucket]

            for bucket in buckets:
                name = bucket['Name']
                try:
                    prefix = f"s3-backups/{name}/{datetime.now().strftime('%Y/%m/%d')}/"
                    count = 0
                    for page in self.s3.get_paginator('list_objects_v2').paginate(Bucket=name):
                        for obj in page.get('Contents', []):
                            self.s3.copy_object(
                                CopySource={'Bucket': name, 'Key': obj['Key']},
                                Bucket=self.backup_bucket,
                                Key=f"{prefix}{obj['Key']}",
                                TaggingDirective='REPLACE',
                                Tagging=f"BackupDate={datetime.now().isoformat()}&SourceBucket={name}"
                            )
                            count += 1

                    results['success'].append({
                        'bucket_name': name,
                        'objects_backed_up': count,
                        'backup_location': f"s3://{self.backup_bucket}/{prefix}"
                    })
                    logger.info(f"Backed up {count} objects from {name}")
                except Exception as e:
                    logger.error(f"Failed to backup bucket {name}: {e}")
                    results['failed'].append({'bucket_name': name, 'error': str(e)})

            self._send_notification(
                f"S3 Backup: {len(results['success'])} buckets successful, {len(results['failed'])} failed"
            )

        except Exception as e:
            logger.error(f"S3 backup operation failed: {e}")
            results['failed'].append({'error': str(e)})

        return results

    # ── Full Backup (all modules) ────────────────────────────────────

    def run_full_backup(self) -> Dict:
        """Execute backup across all modules and cleanup."""
        logger.info("Starting full backup pipeline...")

        results = {
            'timestamp': datetime.now().isoformat(),
            'ec2_results': self.backup_ec2_instances(),
            'rds_results': self.backup_rds_databases(),
            's3_results': self.backup_s3_buckets(),
            'cleanup_results': self.cleanup_old_backups()
        }

        total_ok = (len(results['ec2_results']['success']) +
                    len(results['rds_results']['success']) +
                    len(results['s3_results']['success']))
        total_fail = (len(results['ec2_results']['failed']) +
                      len(results['rds_results']['failed']) +
                      len(results['s3_results']['failed']))

        results['summary'] = {
            'total_successful_backups': total_ok,
            'total_failed_backups': total_fail,
            'backup_status': 'SUCCESS' if total_fail == 0 else 'PARTIAL_FAILURE'
        }

        logger.info(f"Full backup complete: {results['summary']}")
        self._send_notification(
            f"Full Backup — Success: {total_ok}, Failed: {total_fail}, "
            f"Status: {results['summary']['backup_status']}"
        )

        return results

    # ── Internal Helpers ─────────────────────────────────────────────

    def _ensure_backup_bucket(self):
        try:
            self.s3.head_bucket(Bucket=self.backup_bucket)
        except Exception:
            create_args = {'Bucket': self.backup_bucket}
            if self.region != 'us-east-1':
                create_args['CreateBucketConfiguration'] = {'LocationConstraint': self.region}
            self.s3.create_bucket(**create_args)

            self.s3.put_bucket_versioning(
                Bucket=self.backup_bucket,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            self.s3.put_bucket_lifecycle_configuration(
                Bucket=self.backup_bucket,
                LifecycleConfiguration={
                    'Rules': [{
                        'ID': 'BackupLifecycle',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': ''},
                        'Transitions': [
                            {'Days': 7, 'StorageClass': 'GLACIER'},
                            {'Days': 30, 'StorageClass': 'DEEP_ARCHIVE'}
                        ],
                        'Expiration': {'Days': self.retention_days}
                    }]
                }
            )
            logger.info(f"Created backup bucket: {self.backup_bucket}")

    def _send_notification(self, message: str):
        if self.sns_topic_arn:
            try:
                self.sns.publish(
                    TopicArn=self.sns_topic_arn,
                    Message=message,
                    Subject='AWS Backup Pipeline Notification'
                )
                logger.info(f"Notification sent: {message}")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
