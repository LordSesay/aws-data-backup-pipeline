#!/usr/bin/env python3
"""
AWS Backup Pipeline Demo Script

This script demonstrates the complete functionality of the AWS backup pipeline
including local testing, AWS connectivity, and basic operations.
"""

import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_step(step_num, description):
    """Print formatted step"""
    print(f"\n[Step {step_num}] {description}")
    print("-" * 40)

def demo_local_functionality():
    """Demo local functionality without AWS"""
    print_header("LOCAL FUNCTIONALITY DEMO")
    
    print_step(1, "Testing imports and basic functionality")
    
    try:
        # Test imports
        import boto3
        print("✅ boto3 imported successfully")
        
        from backup_manager import BackupManager
        print("✅ BackupManager imported successfully")
        
        from restore_manager import RestoreManager
        print("✅ RestoreManager imported successfully")
        
        # Test initialization (will use AWS credentials if available)
        print("\n🔧 Testing component initialization...")
        
        # Set test environment
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['BACKUP_BUCKET'] = 'demo-backup-bucket'
        
        backup_manager = BackupManager()
        print("✅ BackupManager initialized")
        print(f"   Region: {backup_manager.region}")
        print(f"   Backup Bucket: {backup_manager.backup_bucket}")
        print(f"   Retention Days: {backup_manager.retention_days}")
        
        restore_manager = RestoreManager()
        print("✅ RestoreManager initialized")
        print(f"   Region: {restore_manager.region}")
        
        return True
        
    except Exception as e:
        print(f"❌ Local functionality test failed: {e}")
        return False

def demo_configuration():
    """Demo configuration management"""
    print_header("CONFIGURATION DEMO")
    
    print_step(1, "Environment Configuration")
    
    # Show current environment
    env_vars = [
        'AWS_REGION',
        'BACKUP_BUCKET', 
        'BACKUP_RETENTION_DAYS',
        'SNS_TOPIC_ARN'
    ]
    
    print("Current Environment Variables:")
    for var in env_vars:
        value = os.environ.get(var, 'Not set')
        print(f"  {var}: {value}")
    
    print_step(2, "Configuration Files")
    
    # Check for configuration files
    config_files = [
        'config/backup_schedule.json',
        '.env.example',
        'docs/iam_policies.json'
    ]
    
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ {config_file} - Found")
        else:
            print(f"❌ {config_file} - Missing")

def demo_aws_connectivity():
    """Demo AWS connectivity (if credentials available)"""
    print_header("AWS CONNECTIVITY DEMO")
    
    print_step(1, "Testing AWS credentials and connectivity")
    
    try:
        import boto3
        
        # Test STS (Security Token Service) - basic AWS connectivity
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print("✅ AWS connectivity successful!")
        print(f"   Account ID: {identity.get('Account', 'Unknown')}")
        print(f"   User ARN: {identity.get('Arn', 'Unknown')}")
        
        # Test basic service connectivity
        print("\n🔍 Testing service connectivity...")
        
        # EC2
        try:
            ec2 = boto3.client('ec2')
            regions = ec2.describe_regions()
            print(f"✅ EC2 service accessible - {len(regions['Regions'])} regions available")
        except Exception as e:
            print(f"⚠️ EC2 service issue: {e}")
        
        # S3
        try:
            s3 = boto3.client('s3')
            buckets = s3.list_buckets()
            print(f"✅ S3 service accessible - {len(buckets['Buckets'])} buckets found")
        except Exception as e:
            print(f"⚠️ S3 service issue: {e}")
        
        # RDS
        try:
            rds = boto3.client('rds')
            instances = rds.describe_db_instances()
            print(f"✅ RDS service accessible - {len(instances['DBInstances'])} instances found")
        except Exception as e:
            print(f"⚠️ RDS service issue: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ AWS connectivity failed: {e}")
        print("💡 This is normal if AWS credentials are not configured")
        print("   Run 'aws configure' to set up credentials for full demo")
        return False

def demo_backup_operations():
    """Demo backup operations (safe operations only)"""
    print_header("BACKUP OPERATIONS DEMO")
    
    print_step(1, "Backup Manager Operations")
    
    try:
        from backup_manager import BackupManager
        
        backup_manager = BackupManager()
        
        # Demo safe operations (no actual AWS resources created)
        print("🔍 Testing backup operations (dry run)...")
        
        # Test EC2 backup with empty list (safe)
        print("\n📦 EC2 Backup Test:")
        result = backup_manager.backup_ec2_instances([])
        print(f"   Success: {len(result['success'])}, Failed: {len(result['failed'])}")
        
        # Test RDS backup with empty list (safe)
        print("\n🗄️ RDS Backup Test:")
        result = backup_manager.backup_rds_databases([])
        print(f"   Success: {len(result['success'])}, Failed: {len(result['failed'])}")
        
        # Test S3 backup with empty list (safe)
        print("\n☁️ S3 Backup Test:")
        result = backup_manager.backup_s3_buckets([])
        print(f"   Success: {len(result['success'])}, Failed: {len(result['failed'])}")
        
        print("\n✅ All backup operations completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Backup operations demo failed: {e}")
        return False

def demo_restore_operations():
    """Demo restore operations (listing only)"""
    print_header("RESTORE OPERATIONS DEMO")
    
    print_step(1, "Restore Manager Operations")
    
    try:
        from restore_manager import RestoreManager
        
        restore_manager = RestoreManager()
        
        print("🔍 Testing restore operations (listing only)...")
        
        # List available backups (safe operation)
        print("\n📋 Listing Available Backups:")
        
        for backup_type in ['ec2', 'rds', 's3']:
            try:
                backups = restore_manager.list_available_backups(backup_type)
                if backups['success']:
                    count = len(backups.get('backups', {}).get(backup_type, []))
                    print(f"   {backup_type.upper()}: {count} backups found")
                else:
                    print(f"   {backup_type.upper()}: Error listing backups")
            except Exception as e:
                print(f"   {backup_type.upper()}: {e}")
        
        print("\n✅ Restore operations demo completed")
        return True
        
    except Exception as e:
        print(f"❌ Restore operations demo failed: {e}")
        return False

def demo_monitoring():
    """Demo monitoring capabilities"""
    print_header("MONITORING DEMO")
    
    print_step(1, "Status Checking")
    
    try:
        # Check if status script exists and is runnable
        status_script = 'scripts/check_backup_status.py'
        
        if os.path.exists(status_script):
            print(f"✅ Status checking script available: {status_script}")
            print("💡 Run 'python scripts/check_backup_status.py --full-report' for detailed status")
        else:
            print(f"❌ Status script not found: {status_script}")
        
        # Check deployment script
        deploy_script = 'scripts/deploy.sh'
        if os.path.exists(deploy_script):
            print(f"✅ Deployment script available: {deploy_script}")
        else:
            print(f"❌ Deployment script not found: {deploy_script}")
        
        return True
        
    except Exception as e:
        print(f"❌ Monitoring demo failed: {e}")
        return False

def generate_demo_report():
    """Generate demo execution report"""
    print_header("DEMO REPORT")
    
    report = {
        'demo_timestamp': datetime.now().isoformat(),
        'system_info': {
            'python_version': sys.version,
            'platform': sys.platform,
            'current_directory': os.getcwd()
        },
        'environment': {
            var: os.environ.get(var, 'Not set') 
            for var in ['AWS_REGION', 'BACKUP_BUCKET', 'AWS_PROFILE']
        },
        'files_checked': {
            'README.md': os.path.exists('README.md'),
            'requirements.txt': os.path.exists('requirements.txt'),
            'src/backup_manager.py': os.path.exists('src/backup_manager.py'),
            'src/restore_manager.py': os.path.exists('src/restore_manager.py'),
            'tests/test_local.py': os.path.exists('tests/test_local.py'),
            'docs/ARCHITECTURE.md': os.path.exists('docs/ARCHITECTURE.md'),
            'docs/STUDY_NOTES.md': os.path.exists('docs/STUDY_NOTES.md'),
            'docs/TESTING_GUIDE.md': os.path.exists('docs/TESTING_GUIDE.md')
        }
    }
    
    # Save report
    report_file = f"demo_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📄 Demo report saved: {report_file}")
    except Exception as e:
        print(f"⚠️ Could not save demo report: {e}")
    
    # Print summary
    print("\n📊 Demo Summary:")
    print(f"   Timestamp: {report['demo_timestamp']}")
    print(f"   Python Version: {sys.version.split()[0]}")
    print(f"   Platform: {sys.platform}")
    
    files_present = sum(1 for exists in report['files_checked'].values() if exists)
    total_files = len(report['files_checked'])
    print(f"   Files Present: {files_present}/{total_files}")
    
    if files_present == total_files:
        print("✅ All required files present - Repository is complete!")
    else:
        print("⚠️ Some files missing - Check repository structure")

def main():
    """Main demo execution"""
    print("AWS Data Backup Pipeline - Complete Demo")
    print(f"Demo Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Track demo results
    demo_results = {}
    
    # Run demo sections
    demo_results['local_functionality'] = demo_local_functionality()
    demo_results['configuration'] = demo_configuration()
    demo_results['aws_connectivity'] = demo_aws_connectivity()
    demo_results['backup_operations'] = demo_backup_operations()
    demo_results['restore_operations'] = demo_restore_operations()
    demo_results['monitoring'] = demo_monitoring()
    
    # Generate report
    generate_demo_report()
    
    # Final summary
    print_header("FINAL SUMMARY")
    
    passed_demos = sum(1 for result in demo_results.values() if result)
    total_demos = len(demo_results)
    
    print(f"Demo Results: {passed_demos}/{total_demos} sections passed")
    
    for demo_name, result in demo_results.items():
        status = "PASSED" if result else "FAILED"
        print(f"   {demo_name.replace('_', ' ').title()}: {status}")
    
    if passed_demos == total_demos:
        print("\nAll demo sections PASSED!")
        print("The AWS Backup Pipeline is ready for deployment!")
    else:
        print(f"\n{total_demos - passed_demos} demo sections had issues")
        print("Check the output above for details and troubleshooting")
    
    print("\nNext Steps:")
    print("   1. Review docs/SETUP_GUIDE.md for deployment instructions")
    print("   2. Configure AWS credentials: aws configure")
    print("   3. Run deployment: ./scripts/deploy.sh")
    print("   4. Test with real AWS resources")
    print("   5. Monitor with: python scripts/check_backup_status.py")
    
    return passed_demos == total_demos

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)