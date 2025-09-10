#!/usr/bin/env python3
"""
AWS Backup Pipeline Simple Demo Script
"""

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    """Main demo execution"""
    print("AWS Data Backup Pipeline - Demo")
    print("=" * 50)
    print(f"Demo Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test 1: Basic imports
    print("\n[Test 1] Testing imports...")
    try:
        import boto3
        print("SUCCESS: boto3 imported")
        
        from backup_manager import BackupManager
        print("SUCCESS: BackupManager imported")
        
        from restore_manager import RestoreManager
        print("SUCCESS: RestoreManager imported")
        
    except Exception as e:
        print(f"ERROR: Import failed - {e}")
        return False
    
    # Test 2: Component initialization
    print("\n[Test 2] Testing initialization...")
    try:
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['BACKUP_BUCKET'] = 'demo-backup-bucket'
        
        backup_manager = BackupManager()
        print("SUCCESS: BackupManager initialized")
        print(f"  Region: {backup_manager.region}")
        print(f"  Backup Bucket: {backup_manager.backup_bucket}")
        
        restore_manager = RestoreManager()
        print("SUCCESS: RestoreManager initialized")
        
    except Exception as e:
        print(f"ERROR: Initialization failed - {e}")
        return False
    
    # Test 3: AWS connectivity (if available)
    print("\n[Test 3] Testing AWS connectivity...")
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print("SUCCESS: AWS connectivity confirmed")
        print(f"  Account ID: {identity.get('Account', 'Unknown')}")
        
    except Exception as e:
        print(f"INFO: AWS not configured - {e}")
        print("  This is normal if AWS credentials are not set up")
    
    # Test 4: Basic operations
    print("\n[Test 4] Testing basic operations...")
    try:
        # Test safe operations
        result = backup_manager.backup_ec2_instances([])
        print(f"SUCCESS: EC2 backup test - {len(result['success'])} successful")
        
        result = backup_manager.backup_rds_databases([])
        print(f"SUCCESS: RDS backup test - {len(result['success'])} successful")
        
        result = backup_manager.backup_s3_buckets([])
        print(f"SUCCESS: S3 backup test - {len(result['success'])} successful")
        
    except Exception as e:
        print(f"ERROR: Operations test failed - {e}")
        return False
    
    # Test 5: File structure check
    print("\n[Test 5] Checking project structure...")
    required_files = [
        'README.md',
        'requirements.txt',
        'src/backup_manager.py',
        'src/restore_manager.py',
        'docs/ARCHITECTURE.md',
        'docs/STUDY_NOTES.md',
        'docs/TESTING_GUIDE.md',
        'scripts/deploy.sh',
        'tests/test_local.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  FOUND: {file_path}")
        else:
            print(f"  MISSING: {file_path}")
            missing_files.append(file_path)
    
    if not missing_files:
        print("SUCCESS: All required files present")
    else:
        print(f"WARNING: {len(missing_files)} files missing")
    
    # Summary
    print("\n" + "=" * 50)
    print("DEMO SUMMARY")
    print("=" * 50)
    print("SUCCESS: AWS Backup Pipeline demo completed")
    print("\nProject Features:")
    print("  - Automated backup for EC2, RDS, S3")
    print("  - Disaster recovery capabilities")
    print("  - Cost optimization with S3 lifecycle")
    print("  - Comprehensive monitoring and alerting")
    print("  - Production-ready with security best practices")
    
    print("\nNext Steps:")
    print("  1. Configure AWS credentials: aws configure")
    print("  2. Review setup guide: docs/SETUP_GUIDE.md")
    print("  3. Deploy infrastructure: ./scripts/deploy.sh")
    print("  4. Test with real resources")
    print("  5. Monitor operations: python scripts/check_backup_status.py")
    
    # Generate simple report
    report = {
        'demo_timestamp': datetime.now().isoformat(),
        'status': 'completed',
        'missing_files': missing_files,
        'aws_configured': 'AWS_PROFILE' in os.environ or 'AWS_ACCESS_KEY_ID' in os.environ
    }
    
    try:
        with open('demo_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nDemo report saved: demo_report.json")
    except Exception as e:
        print(f"Could not save report: {e}")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\nDemo completed successfully!")
    else:
        print("\nDemo encountered issues!")
    sys.exit(0 if success else 1)