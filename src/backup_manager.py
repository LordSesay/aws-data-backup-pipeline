"""
AWS Data Backup Pipeline - Main Backup Manager

This module provides automated backup functionality for AWS resources including
EC2 instances, RDS databases, and S3 buckets with intelligent lifecycle management.
"""

import boto3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BackupManager:
    """
    Manages automated backups for AWS resources with cost optimization
    and compliance features.
    """
    
    def __init__(self, region: str = None):
        """
        Initialize the backup manager with AWS clients.
        
        Args:
            region: AWS region (defaults to environment variable or us-east-1)
        """
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize AWS clients
        self.ec2 = boto3.client('ec2', region_name=self.region)
        self.rds = boto3.client('rds', region_name=self.region)
        self.s3 = boto3.client('s3', region_name=self.region)
        self.sns = boto3.client('sns', region_name=self.region)
        
        # Configuration
        self.backup_bucket = os.getenv('BACKUP_BUCKET', f'aws-backup-pipeline-{self._get_account_id()}')
        self.sns_topic_arn = os.getenv('SNS_TOPIC_ARN')
        self.retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
        
        logger.info(f"BackupManager initialized for region: {self.region}")
    
    def _get_account_id(self) -> str:
        """Get AWS account ID."""
        sts = boto3.client('sts')
        return sts.get_caller_identity()['Account']
    
    def backup_ec2_instances(self, instance_ids: List[str] = None) -> Dict:
        """
        Create snapshots for EC2 instances.
        
        Args:
            instance_ids: List of instance IDs to backup (None for all)
            
        Returns:
            Dict with backup results and snapshot IDs
        """
        results = {'success': [], 'failed': []}
        
        try:
            # Get instances to backup
            if instance_ids:
                instances = self.ec2.describe_instances(InstanceIds=instance_ids)
            else:
                instances = self.ec2.describe_instances(
                    Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
                )
            
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    
                    try:
                        # Create snapshots for each EBS volume
                        for block_device in instance.get('BlockDeviceMappings', []):
                            volume_id = block_device['Ebs']['VolumeId']
                            
                            snapshot = self.ec2.create_snapshot(
                                VolumeId=volume_id,
                                Description=f'Automated backup of {instance_id} - {datetime.now().isoformat()}',
                                TagSpecifications=[{
                                    'ResourceType': 'snapshot',
                                    'Tags': [
                                        {'Key': 'Name', 'Value': f'backup-{instance_id}-{volume_id}'},
                                        {'Key': 'InstanceId', 'Value': instance_id},
                                        {'Key': 'BackupDate', 'Value': datetime.now().isoformat()},
                                        {'Key': 'AutomatedBackup', 'Value': 'true'}
                                    ]
                                }]
                            )
                            
                            results['success'].append({
                                'instance_id': instance_id,
                                'volume_id': volume_id,
                                'snapshot_id': snapshot['SnapshotId']
                            })
                            
                            logger.info(f"Created snapshot {snapshot['SnapshotId']} for instance {instance_id}")
                    
                    except Exception as e:
                        logger.error(f"Failed to backup instance {instance_id}: {str(e)}")
                        results['failed'].append({'instance_id': instance_id, 'error': str(e)})
            
            # Send notification
            self._send_notification(
                f"EC2 Backup Complete: {len(results['success'])} successful, {len(results['failed'])} failed"
            )
            
        except Exception as e:
            logger.error(f"EC2 backup operation failed: {str(e)}")
            results['failed'].append({'error': str(e)})
        
        return results
    
    def backup_rds_databases(self, db_identifiers: List[str] = None) -> Dict:
        """
        Create manual snapshots for RDS databases.
        
        Args:
            db_identifiers: List of DB identifiers to backup (None for all)
            
        Returns:
            Dict with backup results and snapshot identifiers
        """
        results = {'success': [], 'failed': []}
        
        try:
            # Get databases to backup
            if db_identifiers:
                databases = []
                for db_id in db_identifiers:
                    try:
                        db = self.rds.describe_db_instances(DBInstanceIdentifier=db_id)
                        databases.extend(db['DBInstances'])
                    except Exception as e:
                        results['failed'].append({'db_identifier': db_id, 'error': str(e)})
            else:
                response = self.rds.describe_db_instances()
                databases = response['DBInstances']
            
            for db in databases:
                db_identifier = db['DBInstanceIdentifier']
                
                try:
                    # Create manual snapshot
                    snapshot_id = f"{db_identifier}-backup-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    
                    snapshot = self.rds.create_db_snapshot(
                        DBSnapshotIdentifier=snapshot_id,
                        DBInstanceIdentifier=db_identifier,
                        Tags=[
                            {'Key': 'BackupDate', 'Value': datetime.now().isoformat()},
                            {'Key': 'AutomatedBackup', 'Value': 'true'},
                            {'Key': 'SourceDB', 'Value': db_identifier}
                        ]
                    )
                    
                    results['success'].append({
                        'db_identifier': db_identifier,
                        'snapshot_id': snapshot_id
                    })
                    
                    logger.info(f"Created RDS snapshot {snapshot_id} for database {db_identifier}")
                
                except Exception as e:
                    logger.error(f"Failed to backup database {db_identifier}: {str(e)}")
                    results['failed'].append({'db_identifier': db_identifier, 'error': str(e)})
            
            # Send notification
            self._send_notification(
                f"RDS Backup Complete: {len(results['success'])} successful, {len(results['failed'])} failed"
            )
            
        except Exception as e:
            logger.error(f"RDS backup operation failed: {str(e)}")
            results['failed'].append({'error': str(e)})
        
        return results
    
    def backup_s3_buckets(self, bucket_names: List[str] = None) -> Dict:
        """
        Sync S3 buckets to backup bucket with versioning.
        
        Args:
            bucket_names: List of bucket names to backup (None for all)
            
        Returns:
            Dict with backup results
        """
        results = {'success': [], 'failed': []}
        
        try:
            # Ensure backup bucket exists
            self._ensure_backup_bucket()
            
            # Get buckets to backup
            if bucket_names:
                buckets = [{'Name': name} for name in bucket_names]
            else:
                response = self.s3.list_buckets()
                buckets = [b for b in response['Buckets'] if b['Name'] != self.backup_bucket]
            
            for bucket in buckets:
                bucket_name = bucket['Name']
                
                try:
                    # Create backup prefix
                    backup_prefix = f"s3-backups/{bucket_name}/{datetime.now().strftime('%Y/%m/%d')}/"
                    
                    # List and copy objects
                    paginator = self.s3.get_paginator('list_objects_v2')
                    pages = paginator.paginate(Bucket=bucket_name)
                    
                    object_count = 0
                    for page in pages:
                        for obj in page.get('Contents', []):
                            copy_source = {'Bucket': bucket_name, 'Key': obj['Key']}
                            copy_key = f"{backup_prefix}{obj['Key']}"
                            
                            self.s3.copy_object(
                                CopySource=copy_source,
                                Bucket=self.backup_bucket,
                                Key=copy_key,
                                TaggingDirective='REPLACE',
                                Tagging='BackupDate=' + datetime.now().isoformat() + '&SourceBucket=' + bucket_name
                            )
                            object_count += 1
                    
                    results['success'].append({
                        'bucket_name': bucket_name,
                        'objects_backed_up': object_count,
                        'backup_location': f"s3://{self.backup_bucket}/{backup_prefix}"
                    })
                    
                    logger.info(f"Backed up {object_count} objects from bucket {bucket_name}")
                
                except Exception as e:
                    logger.error(f"Failed to backup bucket {bucket_name}: {str(e)}")
                    results['failed'].append({'bucket_name': bucket_name, 'error': str(e)})
            
            # Send notification
            self._send_notification(
                f"S3 Backup Complete: {len(results['success'])} buckets successful, {len(results['failed'])} failed"
            )
            
        except Exception as e:
            logger.error(f"S3 backup operation failed: {str(e)}")
            results['failed'].append({'error': str(e)})
        
        return results
    
    def cleanup_old_backups(self) -> Dict:
        """
        Remove backups older than retention period.
        
        Returns:
            Dict with cleanup results
        """
        results = {'ec2_snapshots_deleted': 0, 'rds_snapshots_deleted': 0, 's3_objects_deleted': 0}
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        try:
            # Cleanup EC2 snapshots
            snapshots = self.ec2.describe_snapshots(OwnerIds=['self'])
            for snapshot in snapshots['Snapshots']:
                if (snapshot.get('StartTime').replace(tzinfo=None) < cutoff_date and 
                    any(tag.get('Key') == 'AutomatedBackup' and tag.get('Value') == 'true' 
                        for tag in snapshot.get('Tags', []))):
                    
                    self.ec2.delete_snapshot(SnapshotId=snapshot['SnapshotId'])
                    results['ec2_snapshots_deleted'] += 1
                    logger.info(f"Deleted old EC2 snapshot: {snapshot['SnapshotId']}")
            
            # Cleanup RDS snapshots
            rds_snapshots = self.rds.describe_db_snapshots(SnapshotType='manual')
            for snapshot in rds_snapshots['DBSnapshots']:
                if (snapshot.get('SnapshotCreateTime').replace(tzinfo=None) < cutoff_date and
                    any(tag.get('Key') == 'AutomatedBackup' and tag.get('Value') == 'true'
                        for tag in snapshot.get('TagList', []))):
                    
                    self.rds.delete_db_snapshot(DBSnapshotIdentifier=snapshot['DBSnapshotIdentifier'])
                    results['rds_snapshots_deleted'] += 1
                    logger.info(f"Deleted old RDS snapshot: {snapshot['DBSnapshotIdentifier']}")
            
            logger.info(f"Cleanup complete: {results}")
            
        except Exception as e:
            logger.error(f"Cleanup operation failed: {str(e)}")
        
        return results
    
    def _ensure_backup_bucket(self):
        """Ensure the backup S3 bucket exists with proper configuration."""
        try:
            self.s3.head_bucket(Bucket=self.backup_bucket)
        except:
            # Create bucket
            if self.region == 'us-east-1':
                self.s3.create_bucket(Bucket=self.backup_bucket)
            else:
                self.s3.create_bucket(
                    Bucket=self.backup_bucket,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
            
            # Enable versioning
            self.s3.put_bucket_versioning(
                Bucket=self.backup_bucket,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # Set lifecycle policy for cost optimization
            lifecycle_config = {
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
            
            self.s3.put_bucket_lifecycle_configuration(
                Bucket=self.backup_bucket,
                LifecycleConfiguration=lifecycle_config
            )
            
            logger.info(f"Created and configured backup bucket: {self.backup_bucket}")
    
    def _send_notification(self, message: str):
        """Send SNS notification about backup status."""
        if self.sns_topic_arn:
            try:
                self.sns.publish(
                    TopicArn=self.sns_topic_arn,
                    Message=message,
                    Subject='AWS Backup Pipeline Notification'
                )
                logger.info(f"Notification sent: {message}")
            except Exception as e:
                logger.error(f"Failed to send notification: {str(e)}")
    
    def run_full_backup(self) -> Dict:
        """
        Execute complete backup pipeline for all supported services.
        
        Returns:
            Dict with comprehensive backup results
        """
        logger.info("Starting full backup pipeline...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'ec2_results': self.backup_ec2_instances(),
            'rds_results': self.backup_rds_databases(),
            's3_results': self.backup_s3_buckets(),
            'cleanup_results': self.cleanup_old_backups()
        }
        
        # Calculate summary
        total_success = (len(results['ec2_results']['success']) + 
                        len(results['rds_results']['success']) + 
                        len(results['s3_results']['success']))
        
        total_failed = (len(results['ec2_results']['failed']) + 
                       len(results['rds_results']['failed']) + 
                       len(results['s3_results']['failed']))
        
        results['summary'] = {
            'total_successful_backups': total_success,
            'total_failed_backups': total_failed,
            'backup_status': 'SUCCESS' if total_failed == 0 else 'PARTIAL_FAILURE'
        }
        
        logger.info(f"Full backup pipeline completed: {results['summary']}")
        
        # Send comprehensive notification
        self._send_notification(
            f"Full Backup Pipeline Complete\n"
            f"Successful: {total_success}\n"
            f"Failed: {total_failed}\n"
            f"Status: {results['summary']['backup_status']}"
        )
        
        return results


def lambda_handler(event, context):
    """
    AWS Lambda entry point for scheduled backups.
    
    Args:
        event: Lambda event data
        context: Lambda context object
        
    Returns:
        Dict with execution results
    """
    try:
        backup_manager = BackupManager()
        
        # Determine backup type from event
        backup_type = event.get('backup_type', 'full')
        
        if backup_type == 'ec2':
            results = backup_manager.backup_ec2_instances()
        elif backup_type == 'rds':
            results = backup_manager.backup_rds_databases()
        elif backup_type == 's3':
            results = backup_manager.backup_s3_buckets()
        elif backup_type == 'cleanup':
            results = backup_manager.cleanup_old_backups()
        else:
            results = backup_manager.run_full_backup()
        
        return {
            'statusCode': 200,
            'body': json.dumps(results, default=str)
        }
        
    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


if __name__ == "__main__":
    # For local testing
    backup_manager = BackupManager()
    results = backup_manager.run_full_backup()
    print(json.dumps(results, indent=2, default=str))