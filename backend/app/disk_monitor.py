"""
Disk space monitoring and protection service.
Prevents disk exhaustion from excessive uploads.
"""

import asyncio
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.database import Upload
from app.logger import app_logger


class DiskMonitor:
    """Monitor and manage disk space to prevent exhaustion."""
    
    @staticmethod
    def get_disk_usage(path: Path) -> Dict[str, int]:
        """Get disk usage statistics for a given path."""
        try:
            stat = shutil.disk_usage(path)
            return {
                "total": stat.total,
                "used": stat.used,
                "free": stat.free,
                "percent_used": (stat.used / stat.total * 100) if stat.total > 0 else 0
            }
        except Exception as e:
            app_logger.error(f"Failed to get disk usage for {path}: {e}")
            return {
                "total": 0,
                "used": 0,
                "free": 0,
                "percent_used": 0
            }
    
    @staticmethod
    def check_disk_space_available(
        path: Path,
        required_bytes: int,
        min_free_percent: float = None
    ) -> Tuple[bool, str]:
        """
        Check if enough disk space is available for an upload.
        
        Args:
            path: Path to check (quarantine directory)
            required_bytes: Bytes needed for the upload
            min_free_percent: Minimum free space percentage (from config if None)
        
        Returns:
            Tuple of (is_available, reason_if_not)
        """
        if min_free_percent is None:
            min_free_percent = config.disk_protection.min_free_space_percent
        
        usage = DiskMonitor.get_disk_usage(path)
        
        # Check 1: Absolute space requirement
        if usage["free"] < required_bytes:
            app_logger.warning(
                f"Insufficient disk space: {usage['free']:,} bytes free, "
                f"{required_bytes:,} bytes required",
                extra={"disk_free": usage["free"], "required": required_bytes}
            )
            return False, f"Insufficient disk space. Free: {usage['free']:,} bytes, Required: {required_bytes:,} bytes"
        
        # Check 2: Minimum free space percentage
        free_after_upload = usage["free"] - required_bytes
        percent_free_after = (free_after_upload / usage["total"] * 100) if usage["total"] > 0 else 0
        
        if percent_free_after < min_free_percent:
            app_logger.warning(
                f"Upload would leave insufficient free space: {percent_free_after:.1f}% < {min_free_percent}%",
                extra={"percent_free_after": percent_free_after, "min_required": min_free_percent}
            )
            return False, f"Upload would leave only {percent_free_after:.1f}% free space (minimum: {min_free_percent}%)"
        
        # Check 3: Reserve buffer
        reserve_bytes = config.disk_protection.reserve_space_bytes
        if usage["free"] - required_bytes < reserve_bytes:
            app_logger.warning(
                f"Upload would breach reserve buffer: {reserve_bytes:,} bytes",
                extra={"free_after": usage["free"] - required_bytes, "reserve": reserve_bytes}
            )
            return False, f"Upload would breach disk space reserve ({reserve_bytes:,} bytes)"
        
        return True, ""
    
    @staticmethod
    async def get_quarantine_size(db_session: AsyncSession) -> int:
        """Get total size of all files in quarantine."""
        result = await db_session.execute(
            select(func.sum(Upload.file_size)).where(
                Upload.status.in_(["quarantined", "scanning"])
            )
        )
        total_size = result.scalar()
        return total_size or 0
    
    @staticmethod
    async def check_quarantine_limit(
        db_session: AsyncSession,
        additional_bytes: int = 0
    ) -> Tuple[bool, str]:
        """
        Check if quarantine directory is within size limits.
        
        Args:
            db_session: Database session
            additional_bytes: Additional bytes to be added (for pre-upload check)
        
        Returns:
            Tuple of (is_within_limit, reason_if_not)
        """
        max_quarantine_size = config.disk_protection.max_quarantine_size_bytes
        
        if max_quarantine_size <= 0:
            return True, ""  # Unlimited
        
        current_size = await DiskMonitor.get_quarantine_size(db_session)
        projected_size = current_size + additional_bytes
        
        if projected_size > max_quarantine_size:
            app_logger.warning(
                f"Quarantine size limit exceeded: {projected_size:,} > {max_quarantine_size:,} bytes",
                extra={
                    "current_size": current_size,
                    "additional": additional_bytes,
                    "limit": max_quarantine_size
                }
            )
            return False, (
                f"Quarantine full. Current: {current_size:,} bytes, "
                f"Limit: {max_quarantine_size:,} bytes"
            )
        
        return True, ""
    
    @staticmethod
    async def cleanup_old_files(
        db_session: AsyncSession,
        max_age_hours: Optional[int] = None,
        target_bytes_to_free: Optional[int] = None
    ) -> int:
        """
        Clean up old files from quarantine to free space.
        
        Args:
            db_session: Database session
            max_age_hours: Maximum age in hours (from config if None)
            target_bytes_to_free: Stop after freeing this many bytes (optional)
        
        Returns:
            Total bytes freed
        """
        if max_age_hours is None:
            max_age_hours = config.disk_protection.auto_cleanup_age_hours
        
        if max_age_hours <= 0:
            return 0  # Auto-cleanup disabled
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        # Find old files in quarantine or failed states
        result = await db_session.execute(
            select(Upload)
            .where(
                Upload.uploaded_at < cutoff_time,
                Upload.status.in_([
                    "quarantined",
                    "scanning",
                    "scan_failed",
                    "infected"
                ])
            )
            .order_by(Upload.uploaded_at.asc())  # Oldest first
        )
        
        old_uploads = result.scalars().all()
        bytes_freed = 0
        files_deleted = 0
        
        for upload in old_uploads:
            try:
                # Delete physical file
                quarantine_path = Path(upload.quarantine_path)
                if quarantine_path.exists():
                    file_size = quarantine_path.stat().st_size
                    quarantine_path.unlink()
                    bytes_freed += file_size
                    files_deleted += 1
                    
                    app_logger.info(
                        f"Auto-cleanup: Deleted old file (age: {(datetime.utcnow() - upload.uploaded_at).days} days)",
                        extra={
                            "upload_uuid": upload.uuid,
                            "file_size": file_size,
                            "status": upload.status,
                            "age_hours": (datetime.utcnow() - upload.uploaded_at).total_seconds() / 3600
                        }
                    )
                
                # Update database status
                upload.status = "auto_deleted"
                upload.error_message = f"Auto-deleted after {max_age_hours} hours"
                
                # Check if we've freed enough space
                if target_bytes_to_free and bytes_freed >= target_bytes_to_free:
                    break
                    
            except Exception as e:
                app_logger.error(
                    f"Failed to delete old file during cleanup: {e}",
                    exc_info=True,
                    extra={"upload_uuid": upload.uuid}
                )
        
        await db_session.commit()
        
        if files_deleted > 0:
            app_logger.info(
                f"Auto-cleanup completed: {files_deleted} files, {bytes_freed:,} bytes freed",
                extra={"files_deleted": files_deleted, "bytes_freed": bytes_freed}
            )
        
        return bytes_freed
    
    @staticmethod
    async def emergency_cleanup(
        db_session: AsyncSession,
        target_free_bytes: int
    ) -> int:
        """
        Emergency cleanup to free space by deleting oldest quarantine files.
        Only used when disk is critically low.
        
        Args:
            db_session: Database session
            target_free_bytes: Target amount of space to free
        
        Returns:
            Bytes actually freed
        """
        app_logger.warning("EMERGENCY CLEANUP TRIGGERED - Disk critically low")
        
        # Get all quarantine files, oldest first
        result = await db_session.execute(
            select(Upload)
            .where(
                Upload.status.in_([
                    "quarantined",
                    "scanning",
                    "scan_failed"
                ])
            )
            .order_by(Upload.uploaded_at.asc())
        )
        
        uploads = result.scalars().all()
        bytes_freed = 0
        files_deleted = 0
        
        for upload in uploads:
            if bytes_freed >= target_free_bytes:
                break
            
            try:
                quarantine_path = Path(upload.quarantine_path)
                if quarantine_path.exists():
                    file_size = quarantine_path.stat().st_size
                    quarantine_path.unlink()
                    bytes_freed += file_size
                    files_deleted += 1
                    
                    app_logger.warning(
                        f"Emergency cleanup: Deleted file",
                        extra={
                            "upload_uuid": upload.uuid,
                            "file_size": file_size,
                            "original_status": upload.status
                        }
                    )
                
                upload.status = "emergency_deleted"
                upload.error_message = "Deleted during emergency disk cleanup"
                
            except Exception as e:
                app_logger.error(
                    f"Failed to delete file during emergency cleanup: {e}",
                    exc_info=True,
                    extra={"upload_uuid": upload.uuid}
                )
        
        await db_session.commit()
        
        app_logger.warning(
            f"Emergency cleanup completed: {files_deleted} files, {bytes_freed:,} bytes freed",
            extra={"files_deleted": files_deleted, "bytes_freed": bytes_freed}
        )
        
        return bytes_freed
    
    @staticmethod
    async def get_disk_status(db_session: AsyncSession) -> Dict:
        """Get comprehensive disk status information."""
        quarantine_path = Path(config.quarantine_dir)
        disk_usage = DiskMonitor.get_disk_usage(quarantine_path)
        quarantine_size = await DiskMonitor.get_quarantine_size(db_session)
        
        # Count files by status
        result = await db_session.execute(
            select(Upload.status, func.count(Upload.id))
            .group_by(Upload.status)
        )
        status_counts = {row[0]: row[1] for row in result.all()}
        
        return {
            "disk": disk_usage,
            "quarantine": {
                "total_size": quarantine_size,
                "max_size": config.disk_protection.max_quarantine_size_bytes,
                "percent_used": (
                    (quarantine_size / config.disk_protection.max_quarantine_size_bytes * 100)
                    if config.disk_protection.max_quarantine_size_bytes > 0
                    else 0
                ),
                "file_counts": status_counts
            },
            "protection": {
                "min_free_percent": config.disk_protection.min_free_space_percent,
                "reserve_bytes": config.disk_protection.reserve_space_bytes,
                "auto_cleanup_enabled": config.disk_protection.auto_cleanup_age_hours > 0,
                "auto_cleanup_age_hours": config.disk_protection.auto_cleanup_age_hours
            }
        }


# Background cleanup task
async def periodic_cleanup_task(db_session: AsyncSession):
    """Background task to periodically clean up old files."""
    while True:
        try:
            await asyncio.sleep(config.disk_protection.cleanup_interval_minutes * 60)
            
            app_logger.info("Running periodic quarantine cleanup")
            bytes_freed = await DiskMonitor.cleanup_old_files(db_session)
            
            if bytes_freed > 0:
                app_logger.info(f"Periodic cleanup freed {bytes_freed:,} bytes")
            
        except Exception as e:
            app_logger.error(f"Periodic cleanup failed: {e}", exc_info=True)



