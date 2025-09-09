"""
Test suite for AWS Data Backup Pipeline

This module contains comprehensive tests for the backup and restore functionality
using moto for AWS service mocking.
"""

import pytest
import boto3
from moto import mock_ec2, mock_rds, mock_s3, mock_sns
from datetime import datetime, timedelta
import os
import sys

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from backup_manager import BackupManager
from restore_manager import RestoreManager


class TestBackupManager:
    """Test cases for BackupManager class."""
    
    @mock_ec2
    @mock_s3
    @mock_sns
    def setup_method(self):
        """Set up test environment before each test."""
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['BACKUP_BUCKET'] = 'test-backup-bucket'
        os.environ['BACKUP_RETENTION_DAYS'] = '7'
        
        self.backup_manager = BackupManager()
        
        # Create test EC2 instance
        self.ec2 = boto3.client('ec2', region_name='us-east-1')
        
        # Create VPC and subnet for testing
        vpc = self.ec2.create_vpc(CidrBlock='10.0.0.0/16')
        subnet = self.ec2.create_subnet(
            VpcId=vpc['Vpc']['VpcId'],
            CidrBlock='10.0.1.0/24'
        )
        
        # Create test instance
        response = self.ec2.run_instances(
            ImageId='ami-12345678',
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.micro',
            SubnetId=subnet['Subnet']['SubnetId']
        )
        self.test_instance_id = response['Instances'][0]['InstanceId']
    
    @mock_ec2
    @mock_s3
    @mock_sns
    def test_backup_ec2_instances_success(self):
        """Test successful EC2 instance backup."""
        # Run backup
        result = self.backup_manager.backup_ec2_instances([self.test_instance_id])
        
        # Verify results
        assert len(result['success']) > 0
        assert len(result['failed']) == 0
        assert result['success'][0]['instance_id'] == self.test_instance_id
        
        # Verify snapshot was created
        snapshots = self.ec2.describe_snapshots(OwnerIds=['self'])
        assert len(snapshots['Snapshots']) > 0
    
    @mock_rds
    @mock_s3
    @mock_sns
    def test_backup_rds_databases_success(self):
        """Test successful RDS database backup."""
        # Create test RDS instance
        rds = boto3.client('rds', region_name='us-east-1')
        
        rds.create_db_instance(
            DBInstanceIdentifier='test-db',
            DBInstanceClass='db.t3.micro',
            Engine='mysql',
            MasterUsername='admin',
            MasterUserPassword='password123',
            AllocatedStorage=20
        )
        
        # Run backup
        result = self.backup_manager.backup_rds_databases(['test-db'])
        
        # Verify results
        assert len(result['success']) > 0
        assert len(result['failed']) == 0
        assert result['success'][0]['db_identifier'] == 'test-db'
    
    @mock_s3
    @mock_sns
    def test_backup_s3_buckets_success(self):
        """Test successful S3 bucket backup."""
        # Create test S3 bucket and objects
        s3 = boto3.client('s3', region_name='us-east-1')
        
        test_bucket = 'test-source-bucket'
        s3.create_bucket(Bucket=test_bucket)
        s3.put_object(Bucket=test_bucket, Key='test-file.txt', Body=b'test content')
        
        # Run backup
        result = self.backup_manager.backup_s3_buckets([test_bucket])
        
        # Verify results
        assert len(result['success']) > 0
        assert len(result['failed']) == 0
        assert result['success'][0]['bucket_name'] == test_bucket
        assert result['success'][0]['objects_backed_up'] == 1
    
    @mock_ec2
    @mock_s3
    @mock_sns
    def test_cleanup_old_backups(self):
        """Test cleanup of old backups."""
        # Create old snapshot (simulate by creating and then modifying tags)
        volume_response = self.ec2.create_volume(
            Size=8,
            AvailabilityZone='us-east-1a'
        )
        volume_id = volume_response['VolumeId']
        
        snapshot_response = self.ec2.create_snapshot(
            VolumeId=volume_id,
            Description='Test old snapshot'
        )
        snapshot_id = snapshot_response['SnapshotId']
        
        # Tag as automated backup
        self.ec2.create_tags(
            Resources=[snapshot_id],
            Tags=[
                {'Key': 'AutomatedBackup', 'Value': 'true'},
                {'Key': 'BackupDate', 'Value': (datetime.now() - timedelta(days=10)).isoformat()}
            ]
        )
        
        # Run cleanup
        result = self.backup_manager.cleanup_old_backups()
        
        # Verify cleanup occurred
        assert isinstance(result['ec2_snapshots_deleted'], int)
    
    @mock_ec2
    @mock_rds
    @mock_s3
    @mock_sns
    def test_run_full_backup(self):
        """Test complete backup pipeline execution."""
        # Run full backup
        result = self.backup_manager.run_full_backup()
        
        # Verify structure
        assert 'timestamp' in result
        assert 'ec2_results' in result
        assert 'rds_results' in result
        assert 's3_results' in result
        assert 'cleanup_results' in result
        assert 'summary' in result
        
        # Verify summary
        assert 'total_successful_backups' in result['summary']
        assert 'total_failed_backups' in result['summary']
        assert 'backup_status' in result['summary']


class TestRestoreManager:
    """Test cases for RestoreManager class."""
    
    @mock_ec2
    @mock_rds
    @mock_s3
    def setup_method(self):
        """Set up test environment before each test."""
        os.environ['AWS_REGION'] = 'us-east-1'
        self.restore_manager = RestoreManager()
        
        # Set up EC2 client
        self.ec2 = boto3.client('ec2', region_name='us-east-1')
    
    @mock_ec2
    def test_list_available_backups_ec2(self):
        """Test listing available EC2 backups."""
        # Create test snapshot
        volume_response = self.ec2.create_volume(
            Size=8,
            AvailabilityZone='us-east-1a'
        )
        volume_id = volume_response['VolumeId']
        
        snapshot_response = self.ec2.create_snapshot(
            VolumeId=volume_id,
            Description='Test backup snapshot'
        )
        snapshot_id = snapshot_response['SnapshotId']
        
        # Tag as automated backup
        self.ec2.create_tags(
            Resources=[snapshot_id],
            Tags=[{'Key': 'AutomatedBackup', 'Value': 'true'}]
        )
        
        # List backups
        result = self.restore_manager.list_available_backups('ec2')
        
        # Verify results
        assert result['success'] is True
        assert 'ec2' in result['backups']
        assert len(result['backups']['ec2']) > 0
        assert result['backups']['ec2'][0]['snapshot_id'] == snapshot_id
    
    @mock_rds
    def test_list_available_backups_rds(self):
        """Test listing available RDS backups."""
        # Create test RDS snapshot
        rds = boto3.client('rds', region_name='us-east-1')
        
        # Create DB instance first
        rds.create_db_instance(
            DBInstanceIdentifier='test-db',
            DBInstanceClass='db.t3.micro',
            Engine='mysql',
            MasterUsername='admin',
            MasterUserPassword='password123',
            AllocatedStorage=20
        )
        
        # Create snapshot
        rds.create_db_snapshot(
            DBSnapshotIdentifier='test-snapshot',
            DBInstanceIdentifier='test-db',
            Tags=[{'Key': 'AutomatedBackup', 'Value': 'true'}]
        )
        
        # List backups
        result = self.restore_manager.list_available_backups('rds')
        
        # Verify results
        assert result['success'] is True
        assert 'rds' in result['backups']
        assert len(result['backups']['rds']) > 0
        assert result['backups']['rds'][0]['snapshot_id'] == 'test-snapshot'
    
    @mock_ec2
    def test_validate_backup_integrity_ec2(self):
        """Test EC2 backup integrity validation."""
        # Create test snapshot
        volume_response = self.ec2.create_volume(
            Size=8,
            AvailabilityZone='us-east-1a'
        )
        volume_id = volume_response['VolumeId']
        
        snapshot_response = self.ec2.create_snapshot(
            VolumeId=volume_id,
            Description='Test validation snapshot'
        )
        snapshot_id = snapshot_response['SnapshotId']
        
        # Validate backup
        result = self.restore_manager.validate_backup_integrity('ec2', snapshot_id)
        
        # Verify validation
        assert 'valid' in result
        assert 'state' in result
    
    @mock_rds
    def test_validate_backup_integrity_rds(self):
        """Test RDS backup integrity validation."""
        # Create test RDS snapshot
        rds = boto3.client('rds', region_name='us-east-1')
        
        # Create DB instance first
        rds.create_db_instance(
            DBInstanceIdentifier='test-db',
            DBInstanceClass='db.t3.micro',
            Engine='mysql',
            MasterUsername='admin',
            MasterUserPassword='password123',
            AllocatedStorage=20
        )
        
        # Create snapshot
        rds.create_db_snapshot(
            DBSnapshotIdentifier='test-validation-snapshot',
            DBInstanceIdentifier='test-db'
        )
        
        # Validate backup
        result = self.restore_manager.validate_backup_integrity('rds', 'test-validation-snapshot')
        
        # Verify validation
        assert 'valid' in result
        assert 'status' in result


class TestIntegration:
    """Integration tests for the complete backup and restore workflow."""
    
    @mock_ec2
    @mock_s3
    @mock_sns
    def test_backup_and_restore_workflow(self):
        """Test complete backup and restore workflow."""
        # Set up environment
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['BACKUP_BUCKET'] = 'test-backup-bucket'
        
        backup_manager = BackupManager()
        restore_manager = RestoreManager()
        
        # Create test EC2 instance
        ec2 = boto3.client('ec2', region_name='us-east-1')
        
        # Create VPC and subnet
        vpc = ec2.create_vpc(CidrBlock='10.0.0.0/16')
        subnet = ec2.create_subnet(
            VpcId=vpc['Vpc']['VpcId'],
            CidrBlock='10.0.1.0/24'
        )
        
        # Create test instance
        response = ec2.run_instances(
            ImageId='ami-12345678',
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.micro',
            SubnetId=subnet['Subnet']['SubnetId']
        )
        instance_id = response['Instances'][0]['InstanceId']
        
        # Perform backup
        backup_result = backup_manager.backup_ec2_instances([instance_id])
        assert len(backup_result['success']) > 0
        
        snapshot_id = backup_result['success'][0]['snapshot_id']
        
        # List available backups
        backups = restore_manager.list_available_backups('ec2')
        assert backups['success'] is True
        assert len(backups['backups']['ec2']) > 0
        
        # Validate backup integrity
        validation = restore_manager.validate_backup_integrity('ec2', snapshot_id)
        assert 'valid' in validation


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])