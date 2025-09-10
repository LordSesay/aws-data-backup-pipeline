#!/usr/bin/env python3
"""
Backup validation test script for AWS environment
"""

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from restore_manager import RestoreManager


def test_backup_validation():
    """Test backup validation functionality"""
    print("🔍 Starting backup validation tests...")
    
    try:
        restore_manager = RestoreManager()
        print("✅ RestoreManager initialized successfully")
        
        # Test 1: List available backups
        print("\n📋 Test 1: Listing available backups...")
        
        # Check EC2 backups
        ec2_backups = restore_manager.list_available_backups('ec2')
        if ec2_backups['success']:
            ec2_count = len(ec2_backups.get('backups', {}).get('ec2', []))
            print(f"✅ Found {ec2_count} EC2 backups")
            
            if ec2_count > 0:
                # Test backup validation
                snapshot_id = ec2_backups['backups']['ec2'][0]['snapshot_id']
                print(f"🔍 Validating EC2 backup: {snapshot_id}")
                
                validation = restore_manager.validate_backup_integrity('ec2', snapshot_id)
                if validation.get('valid'):
                    print(f"✅ EC2 backup validation PASSED - State: {validation.get('state')}")
                else:
                    print(f"❌ EC2 backup validation FAILED - {validation.get('error', 'Unknown error')}")
        else:
            print("⚠️ No EC2 backups found or error occurred")
        
        # Check RDS backups
        print("\n📋 Test 2: Checking RDS backups...")
        rds_backups = restore_manager.list_available_backups('rds')
        if rds_backups['success']:
            rds_count = len(rds_backups.get('backups', {}).get('rds', []))
            print(f"✅ Found {rds_count} RDS backups")
            
            if rds_count > 0:
                # Test RDS backup validation
                snapshot_id = rds_backups['backups']['rds'][0]['snapshot_id']
                print(f"🔍 Validating RDS backup: {snapshot_id}")
                
                validation = restore_manager.validate_backup_integrity('rds', snapshot_id)
                if validation.get('valid'):
                    print(f"✅ RDS backup validation PASSED - Status: {validation.get('status')}")
                else:
                    print(f"❌ RDS backup validation FAILED - {validation.get('error', 'Unknown error')}")
        else:
            print("⚠️ No RDS backups found or error occurred")
        
        # Test 3: Check S3 backups
        print("\n📋 Test 3: Checking S3 backups...")
        s3_backups = restore_manager.list_available_backups('s3')
        if s3_backups['success']:
            s3_count = len(s3_backups.get('backups', {}).get('s3', []))
            print(f"✅ Found {s3_count} S3 backup locations")
        else:
            print("⚠️ No S3 backups found or error occurred")
        
        # Test 4: Comprehensive backup listing
        print("\n📋 Test 4: Comprehensive backup listing...")
        all_backups = restore_manager.list_available_backups('all')
        if all_backups['success']:
            total_backups = 0
            for backup_type, backups_list in all_backups.get('backups', {}).items():
                count = len(backups_list) if isinstance(backups_list, list) else 0
                total_backups += count
                print(f"  {backup_type.upper()}: {count} backups")
            
            print(f"✅ Total backups found: {total_backups}")
            
            # Generate summary report
            generate_validation_report(all_backups)
            
        else:
            print("❌ Failed to list all backups")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation test failed: {str(e)}")
        return False


def generate_validation_report(backup_data):
    """Generate a validation report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'validation_results': backup_data,
        'summary': {
            'total_backups': 0,
            'backup_types': [],
            'oldest_backup': None,
            'newest_backup': None
        }
    }
    
    # Calculate summary statistics
    for backup_type, backups_list in backup_data.get('backups', {}).items():
        if isinstance(backups_list, list) and len(backups_list) > 0:
            report['summary']['total_backups'] += len(backups_list)
            report['summary']['backup_types'].append(backup_type)
    
    # Save report
    report_file = f"backup_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        print(f"📄 Validation report saved: {report_file}")
    except Exception as e:
        print(f"⚠️ Could not save report: {e}")


def test_restore_functionality():
    """Test restore functionality (non-destructive)"""
    print("\n🔄 Testing restore functionality (validation only)...")
    
    try:
        restore_manager = RestoreManager()
        
        # Get available backups
        backups = restore_manager.list_available_backups('ec2')
        
        if backups['success'] and backups.get('backups', {}).get('ec2'):
            snapshot_id = backups['backups']['ec2'][0]['snapshot_id']
            
            # Validate backup before restore (non-destructive test)
            print(f"🔍 Testing restore readiness for snapshot: {snapshot_id}")
            
            validation = restore_manager.validate_backup_integrity('ec2', snapshot_id)
            
            if validation.get('valid'):
                print("✅ Backup is ready for restore operations")
                print(f"   State: {validation.get('state')}")
                print(f"   Encrypted: {validation.get('encrypted', 'Unknown')}")
                return True
            else:
                print("❌ Backup is not ready for restore")
                return False
        else:
            print("⚠️ No EC2 backups available for restore testing")
            return True  # Not a failure, just no data
            
    except Exception as e:
        print(f"❌ Restore functionality test failed: {str(e)}")
        return False


def main():
    """Main test execution"""
    print("🧪 AWS Backup Pipeline Validation Tests")
    print("=" * 50)
    
    # Check environment
    required_env = ['AWS_REGION']
    missing_env = [var for var in required_env if not os.environ.get(var)]
    
    if missing_env:
        print(f"❌ Missing environment variables: {missing_env}")
        print("Please ensure AWS credentials are configured")
        return False
    
    print(f"🌍 Region: {os.environ.get('AWS_REGION', 'Not set')}")
    print(f"📅 Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run tests
    tests_passed = 0
    total_tests = 2
    
    # Test 1: Backup validation
    if test_backup_validation():
        tests_passed += 1
        print("✅ Backup validation test PASSED")
    else:
        print("❌ Backup validation test FAILED")
    
    # Test 2: Restore functionality
    if test_restore_functionality():
        tests_passed += 1
        print("✅ Restore functionality test PASSED")
    else:
        print("❌ Restore functionality test FAILED")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Summary: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All validation tests PASSED!")
        return True
    else:
        print("⚠️ Some validation tests FAILED!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)