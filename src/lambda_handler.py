import json
import logging
from src.backup_manager import BackupManager

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda entry point for the backup pipeline.

    Routes on event["backup_type"]:
      ec2     — Tag-driven EC2/EBS snapshot (default)
      cleanup — Delete expired snapshots
      rds     — RDS snapshot (expansion)
      s3      — S3 bucket copy (expansion)
      full    — Run all modules sequentially
    """
    try:
        event = event or {}
        backup_type = event.get("backup_type", "ec2")
        logger.info(f"Backup request: {backup_type}")

        mgr = BackupManager()

        handlers = {
            "ec2": mgr.backup_ec2_instances,
            "cleanup": mgr.cleanup_old_backups,
            "rds": mgr.backup_rds_databases,
            "s3": mgr.backup_s3_buckets,
            "full": mgr.run_full_backup,
        }

        action = handlers.get(backup_type, mgr.backup_ec2_instances)
        results = action()

        return {
            "statusCode": 200,
            "body": json.dumps(results, default=str)
        }

    except Exception as e:
        logger.exception("Lambda execution failed")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
