"""
AWS Data Backup Pipeline - Restore Manager

This module provides disaster recovery functionality to restore AWS resources
from backups created by the backup pipeline.
"""

import boto3
import logging
from datetime import datetime
from typing import Dict, List, Optional
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RestoreManager:
    """
    Manages disaster recovery operations for AWS resources.
    """
    
    def __init__(self, region: str = None):
        """
        Initialize the restore manager with AWS clients.
        
        Args:
            region: AWS region (defaults to environment variable or us-east-1)
        """
        self.region = region or os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize AWS clients
        self.ec2 = boto3.client('ec2', region_name=self.region)
        self.rds = boto3.client('rds', region_name=self.region)
        self.s3 = boto3.client('s3', region_name=self.region)
        
        logger.info(f"RestoreManager initialized for region: {self.region}")
    
    def restore_ec2_from_snapshot(self, snapshot_id: str, instance_type: str = 't3.micro', 
                                 subnet_id: str = None, security_group_ids: List[str] = None) -> Dict:
        """
        Restore EC2 instance from EBS snapshot.
        
        Args:
            snapshot_id: EBS snapshot ID to restore from
            instance_type: EC2 instance type for new instance
            subnet_id: Subnet ID for instance placement
            security_group_ids: List of security group IDs
            
        Returns:
            Dict with restore operation results
        """
        try:
            # Get snapshot details
            snapshots = self.ec2.describe_snapshots(SnapshotIds=[snapshot_id])
            snapshot = snapshots['Snapshots'][0]
            
            # Create AMI from snapshot
            ami_name = f"restore-ami-{snapshot_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            ami_response = self.ec2.register_image(
                Name=ami_name,
                Description=f"AMI created from snapshot {snapshot_id} for restore",
                Architecture='x86_64',
                RootDeviceName='/dev/sda1',
                BlockDeviceMappings=[{
                    'DeviceName': '/dev/sda1',
                    'Ebs': {
                        'SnapshotId': snapshot_id,
                        'VolumeType': 'gp3',
                        'DeleteOnTermination': True
                    }
                }],
                VirtualizationType='hvm'
            )
            
            ami_id = ami_response['ImageId']
            logger.info(f"Created AMI {ami_id} from snapshot {snapshot_id}")
            
            # Wait for AMI to be available
            waiter = self.ec2.get_waiter('image_available')
            waiter.wait(ImageIds=[ami_id])
            
            # Launch instance from AMI
            run_params = {
                'ImageId': ami_id,
                'MinCount': 1,
                'MaxCount': 1,
                'InstanceType': instance_type,
                'TagSpecifications': [{
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'restored-from-{snapshot_id}'},
                        {'Key': 'RestoredFrom', 'Value': snapshot_id},
                        {'Key': 'RestoreDate', 'Value': datetime.now().isoformat()}
                    ]
                }]
            }
            
            if subnet_id:
                run_params['SubnetId'] = subnet_id
            
            if security_group_ids:
                run_params['SecurityGroupIds'] = security_group_ids
            
            instance_response = self.ec2.run_instances(**run_params)
            instance_id = instance_response['Instances'][0]['InstanceId']
            
            logger.info(f"Launched restored instance {instance_id}")
            
            return {
                'success': True,
                'instance_id': instance_id,
                'ami_id': ami_id,
                'snapshot_id': snapshot_id,
                'restore_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to restore EC2 from snapshot {snapshot_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'snapshot_id': snapshot_id
            }
    
    def restore_rds_from_snapshot(self, snapshot_id: str, new_db_identifier: str,
                                 db_instance_class: str = 'db.t3.micro') -> Dict:
        """
        Restore RDS database from snapshot.
        
        Args:
            snapshot_id: RDS snapshot identifier
            new_db_identifier: Identifier for the restored database
            db_instance_class: Instance class for restored database
            
        Returns:
            Dict with restore operation results
        """
        try:
            # Get snapshot details
            snapshots = self.rds.describe_db_snapshots(DBSnapshotIdentifier=snapshot_id)
            snapshot = snapshots['DBSnapshots'][0]
            
            # Restore database from snapshot
            restore_response = self.rds.restore_db_instance_from_db_snapshot(
                DBInstanceIdentifier=new_db_identifier,
                DBSnapshotIdentifier=snapshot_id,
                DBInstanceClass=db_instance_class,
                MultiAZ=False,  # Single AZ for cost optimization
                PubliclyAccessible=False,
                Tags=[
                    {'Key': 'RestoredFrom', 'Value': snapshot_id},
                    {'Key': 'RestoreDate', 'Value': datetime.now().isoformat()},
                    {'Key': 'OriginalDB', 'Value': snapshot.get('DBInstanceIdentifier', 'unknown')}
                ]
            )
            
            logger.info(f"Started RDS restore: {new_db_identifier} from {snapshot_id}")
            
            return {
                'success': True,
                'db_identifier': new_db_identifier,
                'snapshot_id': snapshot_id,
                'status': 'restoring',
                'restore_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to restore RDS from snapshot {snapshot_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'snapshot_id': snapshot_id
            }
    
    def restore_s3_objects(self, backup_bucket: str, backup_prefix: str, 
                          target_bucket: str, target_prefix: str = '') -> Dict:
        """
        Restore S3 objects from backup location.
        
        Args:
            backup_bucket: Source backup bucket
            backup_prefix: Prefix in backup bucket
            target_bucket: Destination bucket for restore
            target_prefix: Prefix for restored objects
            
        Returns:
            Dict with restore operation results
        """
        try:
            restored_objects = 0
            failed_objects = 0
            
            # List objects in backup location
            paginator = self.s3.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=backup_bucket, Prefix=backup_prefix)
            
            for page in pages:
                for obj in page.get('Contents', []):
                    try:
                        # Calculate target key
                        relative_key = obj['Key'][len(backup_prefix):]
                        target_key = f"{target_prefix}{relative_key}" if target_prefix else relative_key
                        
                        # Copy object to target location
                        copy_source = {'Bucket': backup_bucket, 'Key': obj['Key']}
                        
                        self.s3.copy_object(
                            CopySource=copy_source,
                            Bucket=target_bucket,
                            Key=target_key,
                            TaggingDirective='REPLACE',
                            Tagging=f'RestoredFrom={backup_bucket}&RestoreDate={datetime.now().isoformat()}'
                        )
                        
                        restored_objects += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to restore object {obj['Key']}: {str(e)}")
                        failed_objects += 1
            
            logger.info(f"S3 restore complete: {restored_objects} objects restored, {failed_objects} failed")
            
            return {
                'success': True,
                'restored_objects': restored_objects,
                'failed_objects': failed_objects,
                'target_bucket': target_bucket,
                'restore_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to restore S3 objects: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def list_available_backups(self, resource_type: str = 'all') -> Dict:
        """
        List available backups for restore operations.
        
        Args:
            resource_type: Type of resource ('ec2', 'rds', 's3', or 'all')
            
        Returns:
            Dict with available backups organized by type
        """
        backups = {}
        
        try:
            if resource_type in ['ec2', 'all']:
                # List EC2 snapshots
                snapshots = self.ec2.describe_snapshots(OwnerIds=['self'])
                ec2_backups = []
                
                for snapshot in snapshots['Snapshots']:
                    if any(tag.get('Key') == 'AutomatedBackup' and tag.get('Value') == 'true' 
                           for tag in snapshot.get('Tags', [])):
                        
                        ec2_backups.append({
                            'snapshot_id': snapshot['SnapshotId'],
                            'description': snapshot.get('Description', ''),
                            'start_time': snapshot['StartTime'].isoformat(),
                            'volume_size': snapshot['VolumeSize'],
                            'state': snapshot['State']
                        })
                
                backups['ec2'] = sorted(ec2_backups, key=lambda x: x['start_time'], reverse=True)
            
            if resource_type in ['rds', 'all']:
                # List RDS snapshots
                rds_snapshots = self.rds.describe_db_snapshots(SnapshotType='manual')
                rds_backups = []
                
                for snapshot in rds_snapshots['DBSnapshots']:
                    if any(tag.get('Key') == 'AutomatedBackup' and tag.get('Value') == 'true'
                           for tag in snapshot.get('TagList', [])):
                        
                        rds_backups.append({
                            'snapshot_id': snapshot['DBSnapshotIdentifier'],
                            'db_instance_id': snapshot.get('DBInstanceIdentifier', ''),
                            'snapshot_create_time': snapshot['SnapshotCreateTime'].isoformat(),
                            'engine': snapshot.get('Engine', ''),
                            'status': snapshot['Status']
                        })
                
                backups['rds'] = sorted(rds_backups, key=lambda x: x['snapshot_create_time'], reverse=True)
            
            if resource_type in ['s3', 'all']:
                # List S3 backup prefixes (simplified)
                backup_bucket = os.getenv('BACKUP_BUCKET')
                if backup_bucket:
                    try:
                        response = self.s3.list_objects_v2(
                            Bucket=backup_bucket,
                            Prefix='s3-backups/',
                            Delimiter='/'
                        )
                        
                        s3_backups = []
                        for prefix in response.get('CommonPrefixes', []):
                            s3_backups.append({
                                'backup_prefix': prefix['Prefix'],
                                'bucket': backup_bucket
                            })
                        
                        backups['s3'] = s3_backups
                    except Exception as e:
                        logger.warning(f"Could not list S3 backups: {str(e)}")
                        backups['s3'] = []
            
            return {
                'success': True,
                'backups': backups,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to list backups: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_backup_integrity(self, backup_type: str, backup_id: str) -> Dict:
        """
        Validate the integrity of a backup before restore.
        
        Args:
            backup_type: Type of backup ('ec2', 'rds', 's3')
            backup_id: Backup identifier
            
        Returns:
            Dict with validation results
        """
        try:
            if backup_type == 'ec2':
                # Validate EC2 snapshot
                snapshots = self.ec2.describe_snapshots(SnapshotIds=[backup_id])
                snapshot = snapshots['Snapshots'][0]
                
                return {
                    'valid': snapshot['State'] == 'completed',
                    'state': snapshot['State'],
                    'progress': snapshot.get('Progress', ''),
                    'encrypted': snapshot.get('Encrypted', False)
                }
                
            elif backup_type == 'rds':
                # Validate RDS snapshot
                snapshots = self.rds.describe_db_snapshots(DBSnapshotIdentifier=backup_id)
                snapshot = snapshots['DBSnapshots'][0]
                
                return {
                    'valid': snapshot['Status'] == 'available',
                    'status': snapshot['Status'],
                    'percent_progress': snapshot.get('PercentProgress', 0),
                    'encrypted': snapshot.get('Encrypted', False)
                }
                
            else:
                return {'valid': False, 'error': 'Unsupported backup type'}
                
        except Exception as e:
            logger.error(f"Failed to validate backup {backup_id}: {str(e)}")
            return {
                'valid': False,
                'error': str(e)
            }


if __name__ == "__main__":
    # For local testing
    restore_manager = RestoreManager()
    backups = restore_manager.list_available_backups()
    print("Available backups:")
    print(backups)