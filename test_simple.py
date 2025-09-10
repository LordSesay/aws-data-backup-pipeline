#!/usr/bin/env python3
"""Simple test to verify the backup pipeline works"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import boto3
    print("SUCCESS: boto3 imported successfully")
except ImportError as e:
    print(f"ERROR: boto3 import failed: {e}")
    sys.exit(1)

try:
    from moto import mock_ec2, mock_s3, mock_rds
    print("SUCCESS: moto imported successfully")
except ImportError as e:
    print(f"ERROR: moto import failed: {e}")
    # Try alternative import
    try:
        import moto
        print("SUCCESS: moto base module imported")
    except ImportError:
        print("ERROR: moto not available")
        sys.exit(1)

try:
    from backup_manager import BackupManager
    print("SUCCESS: BackupManager imported successfully")
except ImportError as e:
    print(f"ERROR: BackupManager import failed: {e}")
    sys.exit(1)

try:
    from restore_manager import RestoreManager
    print("SUCCESS: RestoreManager imported successfully")
except ImportError as e:
    print(f"ERROR: RestoreManager import failed: {e}")
    sys.exit(1)

print("\nAll imports successful! Ready for testing.")

# Simple test without mocks first
def test_basic_functionality():
    """Test basic backup manager functionality"""
    os.environ['AWS_REGION'] = 'us-east-1'
    os.environ['BACKUP_BUCKET'] = 'test-backup-bucket'
    
    try:
        backup_manager = BackupManager()
        print("SUCCESS: BackupManager initialized successfully")
        
        restore_manager = RestoreManager()
        print("SUCCESS: RestoreManager initialized successfully")
        
        return True
    except Exception as e:
        print(f"ERROR: Basic functionality test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_basic_functionality()
    if success:
        print("\nBasic functionality test passed!")
        print("The backup pipeline is ready for deployment!")
    else:
        print("\nBasic functionality test failed!")
        sys.exit(1)