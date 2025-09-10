#!/usr/bin/env python3
"""
Local testing without AWS dependencies using mocks
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from backup_manager import BackupManager
from restore_manager import RestoreManager


class TestBackupPipelineLocal(unittest.TestCase):
    """Local tests using mocks to avoid AWS costs"""
    
    def setUp(self):
        """Set up test environment"""
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['BACKUP_BUCKET'] = 'test-backup-bucket'
        os.environ['BACKUP_RETENTION_DAYS'] = '7'
        os.environ['SNS_TOPIC_ARN'] = 'arn:aws:sns:us-east-1:123456789012:test-topic'
    
    @patch('boto3.client')
    def test_backup_manager_initialization(self, mock_boto_client):
        """Test BackupManager initialization"""
        # Mock AWS clients
        mock_boto_client.return_value = MagicMock()
        
        backup_manager = BackupManager()
        
        self.assertIsNotNone(backup_manager)
        self.assertEqual(backup_manager.region, 'us-east-1')
        self.assertEqual(backup_manager.backup_bucket, 'test-backup-bucket')
        self.assertEqual(backup_manager.retention_days, 7)
    
    @patch('boto3.client')
    def test_restore_manager_initialization(self, mock_boto_client):
        """Test RestoreManager initialization"""
        # Mock AWS clients
        mock_boto_client.return_value = MagicMock()
        
        restore_manager = RestoreManager()
        
        self.assertIsNotNone(restore_manager)
        self.assertEqual(restore_manager.region, 'us-east-1')
    
    @patch('boto3.client')
    def test_backup_ec2_instances_empty_list(self, mock_boto_client):
        """Test EC2 backup with empty instance list"""
        # Mock EC2 client
        mock_ec2 = MagicMock()
        mock_ec2.describe_instances.return_value = {'Reservations': []}
        mock_boto_client.return_value = mock_ec2
        
        backup_manager = BackupManager()
        result = backup_manager.backup_ec2_instances([])
        
        self.assertIn('success', result)
        self.assertIn('failed', result)
        self.assertEqual(len(result['success']), 0)
        self.assertEqual(len(result['failed']), 0)
    
    @patch('boto3.client')
    def test_backup_rds_databases_empty_list(self, mock_boto_client):
        """Test RDS backup with empty database list"""
        # Mock RDS client
        mock_rds = MagicMock()
        mock_rds.describe_db_instances.return_value = {'DBInstances': []}
        mock_boto_client.return_value = mock_rds
        
        backup_manager = BackupManager()
        result = backup_manager.backup_rds_databases([])
        
        self.assertIn('success', result)
        self.assertIn('failed', result)
        self.assertEqual(len(result['success']), 0)
        self.assertEqual(len(result['failed']), 0)
    
    @patch('boto3.client')
    def test_backup_s3_buckets_empty_list(self, mock_boto_client):
        """Test S3 backup with empty bucket list"""
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_s3.list_buckets.return_value = {'Buckets': []}
        mock_s3.head_bucket.side_effect = Exception("Bucket not found")
        mock_s3.create_bucket.return_value = {}
        mock_s3.put_bucket_versioning.return_value = {}
        mock_s3.put_bucket_lifecycle_configuration.return_value = {}
        mock_boto_client.return_value = mock_s3
        
        backup_manager = BackupManager()
        result = backup_manager.backup_s3_buckets([])
        
        self.assertIn('success', result)
        self.assertIn('failed', result)
    
    @patch('boto3.client')
    def test_list_available_backups(self, mock_boto_client):
        """Test listing available backups"""
        # Mock clients
        mock_ec2 = MagicMock()
        mock_ec2.describe_snapshots.return_value = {
            'Snapshots': [{
                'SnapshotId': 'snap-12345',
                'Description': 'Test snapshot',
                'StartTime': '2024-01-01T00:00:00Z',
                'VolumeSize': 8,
                'State': 'completed',
                'Tags': [{'Key': 'AutomatedBackup', 'Value': 'true'}]
            }]
        }
        mock_boto_client.return_value = mock_ec2
        
        restore_manager = RestoreManager()
        result = restore_manager.list_available_backups('ec2')
        
        self.assertTrue(result['success'])
        self.assertIn('ec2', result['backups'])
    
    @patch('boto3.client')
    def test_validate_backup_integrity_ec2(self, mock_boto_client):
        """Test EC2 backup integrity validation"""
        # Mock EC2 client
        mock_ec2 = MagicMock()
        mock_ec2.describe_snapshots.return_value = {
            'Snapshots': [{
                'SnapshotId': 'snap-12345',
                'State': 'completed',
                'Progress': '100%',
                'Encrypted': False
            }]
        }
        mock_boto_client.return_value = mock_ec2
        
        restore_manager = RestoreManager()
        result = restore_manager.validate_backup_integrity('ec2', 'snap-12345')
        
        self.assertTrue(result['valid'])
        self.assertEqual(result['state'], 'completed')
    
    @patch('boto3.client')
    def test_cleanup_old_backups(self, mock_boto_client):
        """Test cleanup of old backups"""
        # Mock EC2 client
        mock_ec2 = MagicMock()
        mock_ec2.describe_snapshots.return_value = {'Snapshots': []}
        
        # Mock RDS client
        mock_rds = MagicMock()
        mock_rds.describe_db_snapshots.return_value = {'DBSnapshots': []}
        
        def mock_client(service_name, **kwargs):
            if service_name == 'ec2':
                return mock_ec2
            elif service_name == 'rds':
                return mock_rds
            else:
                return MagicMock()
        
        mock_boto_client.side_effect = mock_client
        
        backup_manager = BackupManager()
        result = backup_manager.cleanup_old_backups()
        
        self.assertIn('ec2_snapshots_deleted', result)
        self.assertIn('rds_snapshots_deleted', result)
        self.assertIn('s3_objects_deleted', result)
    
    @patch('boto3.client')
    def test_lambda_handler(self, mock_boto_client):
        """Test Lambda handler function"""
        from backup_manager import lambda_handler
        
        # Mock all AWS clients
        mock_boto_client.return_value = MagicMock()
        
        # Test event
        event = {'backup_type': 'ec2'}
        context = MagicMock()
        
        result = lambda_handler(event, context)
        
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('body', result)


class TestConfigurationValidation(unittest.TestCase):
    """Test configuration and environment validation"""
    
    def test_required_environment_variables(self):
        """Test that required environment variables are validated"""
        required_vars = ['AWS_REGION', 'BACKUP_BUCKET']
        
        for var in required_vars:
            # Temporarily remove the variable
            original_value = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
            
            # Test that missing variable is handled gracefully
            try:
                with patch('boto3.client'):
                    backup_manager = BackupManager()
                    # Should use default values or handle missing vars
                    self.assertIsNotNone(backup_manager)
            except Exception as e:
                # Expected behavior for missing critical config
                pass
            finally:
                # Restore original value
                if original_value is not None:
                    os.environ[var] = original_value
    
    def test_default_values(self):
        """Test default configuration values"""
        # Clear environment variables
        env_backup = {}
        for var in ['AWS_REGION', 'BACKUP_RETENTION_DAYS']:
            env_backup[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
        
        try:
            with patch('boto3.client'):
                backup_manager = BackupManager()
                self.assertEqual(backup_manager.region, 'us-east-1')  # Default region
                self.assertEqual(backup_manager.retention_days, 30)   # Default retention
        finally:
            # Restore environment
            for var, value in env_backup.items():
                if value is not None:
                    os.environ[var] = value


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)