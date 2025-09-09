#!/usr/bin/env python3
"""
Backup Status Checker

This script provides a comprehensive status check of the backup pipeline,
including recent backup operations, storage utilization, and system health.
"""

import boto3
import json
import sys
import os
from datetime import datetime, timedelta
from tabulate import tabulate

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from backup_manager import BackupManager
from restore_manager import RestoreManager


class BackupStatusChecker:
    """Check and report on backup pipeline status."""
    
    def __init__(self):
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.backup_bucket = os.getenv('BACKUP_BUCKET')
        
        # Initialize AWS clients
        self.ec2 = boto3.client('ec2', region_name=self.region)
        self.rds = boto3.client('rds', region_name=self.region)
        self.s3 = boto3.client('s3', region_name=self.region)
        self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
        self.logs = boto3.client('logs', region_name=self.region)
    
    def check_recent_backups(self, days=7):
        """Check backup operations from the last N days."""
        print(f"\n📊 Recent Backup Operations (Last {days} days)")
        print("=" * 60)
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Check EC2 snapshots
        ec2_snapshots = []
        try:
            snapshots = self.ec2.describe_snapshots(OwnerIds=['self'])
            for snapshot in snapshots['Snapshots']:
                if (snapshot.get('StartTime').replace(tzinfo=None) > cutoff_date and
                    any(tag.get('Key') == 'AutomatedBackup' and tag.get('Value') == 'true'
                        for tag in snapshot.get('Tags', []))):
                    
                    ec2_snapshots.append([
                        snapshot['SnapshotId'][:20] + '...',
                        snapshot.get('Description', '')[:30] + '...',
                        snapshot['StartTime'].strftime('%Y-%m-%d %H:%M'),
                        snapshot['State'],
                        f"{snapshot['VolumeSize']} GB"
                    ])
        except Exception as e:
            print(f"❌ Error checking EC2 snapshots: {e}")
        
        if ec2_snapshots:
            print("\n🖥️  EC2 Snapshots:")
            print(tabulate(ec2_snapshots, 
                         headers=['Snapshot ID', 'Description', 'Created', 'State', 'Size'],
                         tablefmt='grid'))
        else:
            print("\n🖥️  No recent EC2 snapshots found")
        
        # Check RDS snapshots
        rds_snapshots = []
        try:
            snapshots = self.rds.describe_db_snapshots(SnapshotType='manual')
            for snapshot in snapshots['DBSnapshots']:
                if (snapshot.get('SnapshotCreateTime').replace(tzinfo=None) > cutoff_date and
                    any(tag.get('Key') == 'AutomatedBackup' and tag.get('Value') == 'true'
                        for tag in snapshot.get('TagList', []))):
                    
                    rds_snapshots.append([
                        snapshot['DBSnapshotIdentifier'][:25] + '...',
                        snapshot.get('DBInstanceIdentifier', '')[:20],
                        snapshot['SnapshotCreateTime'].strftime('%Y-%m-%d %H:%M'),
                        snapshot['Status'],
                        snapshot.get('Engine', 'Unknown')
                    ])
        except Exception as e:
            print(f"❌ Error checking RDS snapshots: {e}")
        
        if rds_snapshots:
            print("\n🗄️  RDS Snapshots:")
            print(tabulate(rds_snapshots,
                         headers=['Snapshot ID', 'DB Instance', 'Created', 'Status', 'Engine'],
                         tablefmt='grid'))
        else:
            print("\n🗄️  No recent RDS snapshots found")
    
    def check_storage_utilization(self):
        """Check backup storage utilization and costs."""
        print("\n💾 Storage Utilization")
        print("=" * 40)
        
        if not self.backup_bucket:
            print("❌ BACKUP_BUCKET not configured")
            return
        
        try:
            # Get bucket size metrics
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/S3',
                MetricName='BucketSizeBytes',
                Dimensions=[
                    {'Name': 'BucketName', 'Value': self.backup_bucket},
                    {'Name': 'StorageType', 'Value': 'StandardStorage'}
                ],
                StartTime=datetime.now() - timedelta(days=2),
                EndTime=datetime.now(),
                Period=86400,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                size_bytes = response['Datapoints'][-1]['Average']
                size_gb = size_bytes / (1024**3)
                
                print(f"📦 Backup Bucket: {self.backup_bucket}")
                print(f"📊 Total Size: {size_gb:.2f} GB")
                print(f"💰 Estimated Monthly Cost: ${size_gb * 0.023:.2f}")
            else:
                print("📦 No storage metrics available")
                
        except Exception as e:
            print(f"❌ Error checking storage: {e}")
    
    def check_lambda_health(self):
        """Check Lambda function health and recent executions."""
        print("\n⚡ Lambda Function Health")
        print("=" * 35)
        
        function_name = 'aws-backup-pipeline'
        
        try:
            # Get function configuration
            lambda_client = boto3.client('lambda', region_name=self.region)
            function = lambda_client.get_function(FunctionName=function_name)
            
            print(f"📋 Function: {function_name}")
            print(f"🔧 Runtime: {function['Configuration']['Runtime']}")
            print(f"💾 Memory: {function['Configuration']['MemorySize']} MB")
            print(f"⏱️  Timeout: {function['Configuration']['Timeout']} seconds")
            print(f"📅 Last Modified: {function['Configuration']['LastModified']}")
            
            # Get recent invocations
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            
            invocations = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Sum']
            )
            
            errors = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Errors',
                Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Sum']
            )
            
            total_invocations = sum(point['Sum'] for point in invocations['Datapoints'])
            total_errors = sum(point['Sum'] for point in errors['Datapoints'])
            
            success_rate = ((total_invocations - total_errors) / total_invocations * 100) if total_invocations > 0 else 0
            
            print(f"📊 Invocations (7 days): {int(total_invocations)}")
            print(f"❌ Errors (7 days): {int(total_errors)}")
            print(f"✅ Success Rate: {success_rate:.1f}%")
            
        except Exception as e:
            print(f"❌ Error checking Lambda function: {e}")
    
    def check_recent_logs(self, hours=24):
        """Check recent Lambda execution logs."""
        print(f"\n📋 Recent Logs (Last {hours} hours)")
        print("=" * 40)
        
        log_group = '/aws/lambda/aws-backup-pipeline'
        
        try:
            # Get recent log events
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)
            
            response = self.logs.filter_log_events(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                limit=10
            )
            
            if response['events']:
                print("\n🔍 Recent Log Events:")
                for event in response['events'][-5:]:  # Show last 5 events
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    message = event['message'].strip()[:100]
                    print(f"  {timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {message}")
            else:
                print("📋 No recent log events found")
                
        except Exception as e:
            print(f"❌ Error checking logs: {e}")
    
    def check_backup_schedule(self):
        """Check CloudWatch Events rules for backup scheduling."""
        print("\n⏰ Backup Schedule Status")
        print("=" * 35)
        
        try:
            events_client = boto3.client('events', region_name=self.region)
            
            # Check backup schedule rule
            rule_name = 'backup-pipeline-schedule'
            
            try:
                rule = events_client.describe_rule(Name=rule_name)
                
                print(f"📅 Schedule Rule: {rule_name}")
                print(f"🔧 Schedule: {rule.get('ScheduleExpression', 'Not set')}")
                print(f"📊 State: {rule.get('State', 'Unknown')}")
                print(f"📝 Description: {rule.get('Description', 'No description')}")
                
                # Check targets
                targets = events_client.list_targets_by_rule(Rule=rule_name)
                print(f"🎯 Targets: {len(targets['Targets'])}")
                
            except events_client.exceptions.ResourceNotFoundException:
                print(f"❌ Schedule rule '{rule_name}' not found")
                
        except Exception as e:
            print(f"❌ Error checking schedule: {e}")
    
    def generate_health_report(self):
        """Generate comprehensive health report."""
        print("🏥 AWS Backup Pipeline Health Report")
        print("=" * 50)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Region: {self.region}")
        
        # Run all checks
        self.check_lambda_health()
        self.check_backup_schedule()
        self.check_recent_backups()
        self.check_storage_utilization()
        self.check_recent_logs()
        
        print("\n" + "=" * 50)
        print("✅ Health check completed")


def main():
    """Main function to run backup status checks."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Check AWS Backup Pipeline Status')
    parser.add_argument('--days', type=int, default=7, 
                       help='Number of days to check for recent backups (default: 7)')
    parser.add_argument('--logs-hours', type=int, default=24,
                       help='Number of hours to check for recent logs (default: 24)')
    parser.add_argument('--full-report', action='store_true',
                       help='Generate full health report')
    
    args = parser.parse_args()
    
    checker = BackupStatusChecker()
    
    if args.full_report:
        checker.generate_health_report()
    else:
        checker.check_recent_backups(args.days)
        checker.check_storage_utilization()


if __name__ == "__main__":
    main()