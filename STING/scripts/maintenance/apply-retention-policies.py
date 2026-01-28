#!/usr/bin/env python3
"""
Honey Reserve Retention Policy Manager
Applies data lifecycle policies to user files based on configured retention rules
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import boto3
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/sting/maintenance/retention-policy.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class RetentionPolicyManager:
    """Manages file retention policies for Honey Reserve"""
    
    def __init__(self, config_path: str = '/etc/sting/honey-reserve.conf'):
        self.config = self._load_config(config_path)
        self.db_conn = self._get_db_connection()
        self.storage_path = self.config.get('storage_path', '/var/sting/honey-reserve')
        self.archive_path = self.config.get('archive_path', '/var/sting/archives')
        self.s3_client = self._init_s3_client() if self.config.get('s3_enabled') else None
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            # Return default config
            return {
                'retention_policies': {
                    'temporary': {'days': 2, 'action': 'delete'},
                    'reports': {'days': 30, 'action': 'delete'},
                    'honey_jar': {'days': 365, 'action': 'archive'},
                    'audit_logs': {'days': 1095, 'action': 'archive'}  # 3 years
                },
                'database': {
                    'host': 'localhost',
                    'port': 5432,
                    'name': 'sting_app',
                    'user': 'sting',
                    'password': os.environ.get('DB_PASSWORD', 'password')
                }
            }
    
    def _get_db_connection(self):
        """Create database connection"""
        db_config = self.config['database']
        return psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['name'],
            user=db_config['user'],
            password=db_config['password'],
            cursor_factory=RealDictCursor
        )
    
    def _init_s3_client(self):
        """Initialize S3 client for archive storage"""
        return boto3.client(
            's3',
            aws_access_key_id=self.config.get('aws_access_key'),
            aws_secret_access_key=self.config.get('aws_secret_key'),
            region_name=self.config.get('aws_region', 'us-east-1')
        )
    
    def apply_retention_policies(self, dry_run: bool = False):
        """Apply all configured retention policies"""
        logger.info(f"Starting retention policy application (dry_run={dry_run})")
        
        policies = self.config.get('retention_policies', {})
        total_processed = 0
        total_size_freed = 0
        
        for file_type, policy in policies.items():
            processed, size_freed = self._apply_policy(
                file_type, policy, dry_run
            )
            total_processed += processed
            total_size_freed += size_freed
        
        logger.info(
            f"Retention policies applied. Files processed: {total_processed}, "
            f"Space freed: {self._format_bytes(total_size_freed)}"
        )
        
        # Generate summary report
        self._generate_summary_report(total_processed, total_size_freed, dry_run)
    
    def _apply_policy(self, file_type: str, policy: Dict, dry_run: bool) -> tuple:
        """Apply retention policy for specific file type"""
        retention_days = policy.get('days', 365)
        action = policy.get('action', 'delete')
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        logger.info(
            f"Processing {file_type} files older than {cutoff_date.date()} "
            f"(action: {action})"
        )
        
        # Query files matching retention criteria
        query = """
        SELECT id, user_id, filename, size, created_at, file_path, checksum
        FROM user_files
        WHERE file_type = %s 
        AND created_at < %s
        AND status NOT IN ('archived', 'deleted')
        ORDER BY created_at ASC
        LIMIT 1000
        """
        
        cursor = self.db_conn.cursor()
        cursor.execute(query, (file_type, cutoff_date))
        files = cursor.fetchall()
        
        processed_count = 0
        total_size = 0
        
        for file_data in files:
            try:
                if action == 'delete':
                    size = self._delete_file(file_data, dry_run)
                elif action == 'archive':
                    size = self._archive_file(file_data, dry_run)
                else:
                    logger.warning(f"Unknown action: {action}")
                    continue
                
                processed_count += 1
                total_size += size
                
                # Log progress every 100 files
                if processed_count % 100 == 0:
                    logger.info(f"Processed {processed_count} {file_type} files...")
                    
            except Exception as e:
                logger.error(f"Failed to process file {file_data['id']}: {e}")
                continue
        
        cursor.close()
        return processed_count, total_size
    
    def _delete_file(self, file_data: Dict, dry_run: bool) -> int:
        """Delete file and update database"""
        file_path = file_data['file_path']
        file_size = file_data['size']
        
        if dry_run:
            logger.info(f"[DRY RUN] Would delete: {file_path}")
            return file_size
        
        # Delete physical file
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"Deleted file: {file_path}")
        
        # Update database
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            UPDATE user_files 
            SET status = 'deleted', deleted_at = NOW() 
            WHERE id = %s
            """,
            (file_data['id'],)
        )
        self.db_conn.commit()
        cursor.close()
        
        # Log deletion for audit
        self._log_file_action(file_data, 'deleted')
        
        return file_size
    
    def _archive_file(self, file_data: Dict, dry_run: bool) -> int:
        """Archive file to cold storage"""
        file_path = file_data['file_path']
        file_size = file_data['size']
        
        if dry_run:
            logger.info(f"[DRY RUN] Would archive: {file_path}")
            return 0  # No space freed in dry run
        
        # Generate archive path
        archive_key = self._generate_archive_key(file_data)
        
        try:
            if self.s3_client:
                # Archive to S3
                self._archive_to_s3(file_path, archive_key, file_data)
            else:
                # Archive to local storage
                self._archive_to_local(file_path, archive_key, file_data)
            
            # Delete original file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Update database
            cursor = self.db_conn.cursor()
            cursor.execute(
                """
                UPDATE user_files 
                SET status = 'archived', 
                    archived_at = NOW(),
                    archive_location = %s
                WHERE id = %s
                """,
                (archive_key, file_data['id'])
            )
            self.db_conn.commit()
            cursor.close()
            
            # Log archival for audit
            self._log_file_action(file_data, 'archived', {'location': archive_key})
            
            return file_size
            
        except Exception as e:
            logger.error(f"Failed to archive file {file_path}: {e}")
            raise
    
    def _archive_to_s3(self, file_path: str, archive_key: str, file_data: Dict):
        """Archive file to S3"""
        bucket = self.config.get('s3_archive_bucket', 'sting-archives')
        
        # Add metadata
        metadata = {
            'user_id': str(file_data['user_id']),
            'original_filename': file_data['filename'],
            'created_at': file_data['created_at'].isoformat(),
            'checksum': file_data['checksum']
        }
        
        # Upload with encryption
        self.s3_client.upload_file(
            file_path,
            bucket,
            archive_key,
            ExtraArgs={
                'ServerSideEncryption': 'AES256',
                'Metadata': metadata,
                'StorageClass': 'GLACIER'
            }
        )
        
        logger.debug(f"Archived to S3: s3://{bucket}/{archive_key}")
    
    def _archive_to_local(self, file_path: str, archive_key: str, file_data: Dict):
        """Archive file to local storage"""
        archive_full_path = os.path.join(self.archive_path, archive_key)
        
        # Create directory structure
        os.makedirs(os.path.dirname(archive_full_path), exist_ok=True)
        
        # Copy and compress file
        import gzip
        import shutil
        
        with open(file_path, 'rb') as f_in:
            with gzip.open(f"{archive_full_path}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Save metadata
        metadata_path = f"{archive_full_path}.meta.json"
        with open(metadata_path, 'w') as f:
            json.dump({
                'user_id': file_data['user_id'],
                'original_filename': file_data['filename'],
                'created_at': file_data['created_at'].isoformat(),
                'checksum': file_data['checksum'],
                'archived_at': datetime.now().isoformat()
            }, f)
        
        logger.debug(f"Archived locally: {archive_full_path}.gz")
    
    def _generate_archive_key(self, file_data: Dict) -> str:
        """Generate archive storage key"""
        created_date = file_data['created_at']
        return (
            f"{created_date.year}/{created_date.month:02d}/"
            f"{file_data['user_id']}/{file_data['id']}"
        )
    
    def _log_file_action(self, file_data: Dict, action: str, extra_data: Dict = None):
        """Log file action for audit trail"""
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            INSERT INTO file_audit_log 
            (file_id, user_id, action, metadata, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (
                file_data['id'],
                file_data['user_id'],
                action,
                json.dumps(extra_data or {})
            )
        )
        self.db_conn.commit()
        cursor.close()
    
    def _generate_summary_report(self, total_processed: int, 
                               total_size_freed: int, dry_run: bool):
        """Generate summary report of retention policy application"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'dry_run': dry_run,
            'total_files_processed': total_processed,
            'total_space_freed': total_size_freed,
            'total_space_freed_formatted': self._format_bytes(total_size_freed),
            'policies_applied': self.config.get('retention_policies', {})
        }
        
        # Save report
        report_path = (
            f"/var/log/sting/maintenance/retention-report-"
            f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Summary report saved to: {report_path}")
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"
    
    def restore_archived_file(self, file_id: str, target_path: str = None):
        """Restore an archived file"""
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            SELECT * FROM user_files 
            WHERE id = %s AND status = 'archived'
            """,
            (file_id,)
        )
        file_data = cursor.fetchone()
        cursor.close()
        
        if not file_data:
            raise ValueError(f"Archived file not found: {file_id}")
        
        archive_location = file_data['archive_location']
        original_path = file_data['file_path']
        target_path = target_path or original_path
        
        logger.info(f"Restoring file {file_id} from {archive_location}")
        
        try:
            if self.s3_client:
                # Restore from S3
                self._restore_from_s3(archive_location, target_path)
            else:
                # Restore from local archive
                self._restore_from_local(archive_location, target_path)
            
            # Update database
            cursor = self.db_conn.cursor()
            cursor.execute(
                """
                UPDATE user_files 
                SET status = 'active', 
                    archived_at = NULL,
                    archive_location = NULL
                WHERE id = %s
                """,
                (file_id,)
            )
            self.db_conn.commit()
            cursor.close()
            
            logger.info(f"Successfully restored file {file_id} to {target_path}")
            
        except Exception as e:
            logger.error(f"Failed to restore file {file_id}: {e}")
            raise
    
    def _restore_from_s3(self, archive_key: str, target_path: str):
        """Restore file from S3 archive"""
        bucket = self.config.get('s3_archive_bucket', 'sting-archives')
        
        # Initiate restore if needed (for Glacier)
        try:
            response = self.s3_client.head_object(Bucket=bucket, Key=archive_key)
            if 'Restore' not in response or 'ongoing-request="false"' not in response['Restore']:
                # Need to initiate restore
                self.s3_client.restore_object(
                    Bucket=bucket,
                    Key=archive_key,
                    RestoreRequest={'Days': 1, 'Tier': 'Expedited'}
                )
                raise Exception("Restore initiated. File will be available in 1-5 minutes.")
        except:
            pass
        
        # Download file
        self.s3_client.download_file(bucket, archive_key, target_path)
    
    def _restore_from_local(self, archive_key: str, target_path: str):
        """Restore file from local archive"""
        import gzip
        
        archive_path = os.path.join(self.archive_path, f"{archive_key}.gz")
        
        # Decompress and restore
        with gzip.open(archive_path, 'rb') as f_in:
            with open(target_path, 'wb') as f_out:
                f_out.write(f_in.read())


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Apply retention policies to Honey Reserve files'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--config',
        default='/etc/sting/honey-reserve.conf',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--restore',
        metavar='FILE_ID',
        help='Restore an archived file by ID'
    )
    parser.add_argument(
        '--target',
        help='Target path for restored file'
    )
    
    args = parser.parse_args()
    
    try:
        manager = RetentionPolicyManager(args.config)
        
        if args.restore:
            # Restore mode
            manager.restore_archived_file(args.restore, args.target)
        else:
            # Apply retention policies
            manager.apply_retention_policies(dry_run=args.dry_run)
            
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()