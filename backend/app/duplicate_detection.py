"""Hash-based duplicate detection service."""

from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path

from app.database import Upload
from app.config import config
from app.logger import app_logger


class DuplicateDetector:
    """Duplicate file detection based on SHA256 hash."""
    
    @staticmethod
    async def check_duplicate(
        file_hash: str,
        file_size: int,
        db_session: AsyncSession
    ) -> Dict[str, Any]:
        """Check if file is a duplicate based on hash.
        
        Args:
            file_hash: SHA256 hash of file
            file_size: File size in bytes
            db_session: Database session
            
        Returns:
            Dictionary with duplicate status and details
        """
        if not config.duplicate_detection.enabled:
            return {
                "is_duplicate": False,
                "reason": "duplicate_detection_disabled"
            }
        
        # Primary check: hash-based
        if config.duplicate_detection.check_by_hash:
            result = await db_session.execute(
                select(Upload).where(Upload.file_hash_sha256 == file_hash)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                app_logger.info(
                    f"Duplicate file detected by hash",
                    extra={
                        "file_hash": file_hash,
                        "original_upload_uuid": existing.uuid,
                        "original_filename": existing.original_filename
                    }
                )
                
                return {
                    "is_duplicate": True,
                    "method": "hash",
                    "original_uuid": existing.uuid,
                    "original_filename": existing.original_filename,
                    "original_status": existing.status,
                    "uploaded_at": existing.uploaded_at.isoformat(),
                    "action": "discard" if config.duplicate_detection.discard_exact_hash else "allow"
                }
        
        # Secondary check: size-based (for performance)
        if config.duplicate_detection.check_by_size:
            result = await db_session.execute(
                select(Upload).where(Upload.file_size == file_size)
            )
            possible_duplicates = result.scalars().all()
            
            if possible_duplicates:
                app_logger.info(
                    f"Found {len(possible_duplicates)} files with same size",
                    extra={
                        "file_size": file_size,
                        "file_hash": file_hash
                    }
                )
                # Note: These might not be duplicates, just same size
                # Would need content comparison to confirm
        
        return {
            "is_duplicate": False,
            "reason": "unique_file"
        }
    
    @staticmethod
    async def check_library_duplicates(
        file_hash: str,
        library_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check if file exists in Kavita library by hash.
        
        Uses Kavita API to get library paths if available, otherwise uses config.
        
        Args:
            file_hash: SHA256 hash of file
            library_path: Path to Kavita library (defaults to API or config)
            
        Returns:
            Dictionary with library duplicate status
        """
        # Try to get libraries from Kavita API if enabled
        search_paths = []
        
        if config.kavita.enabled:
            try:
                from app.kavita_api import kavita_api
                library_paths = await kavita_api.get_library_paths()
                if library_paths:
                    search_paths = library_paths
            except Exception as e:
                app_logger.debug(
                    f"Failed to fetch libraries from API, using config",
                    extra={"error": str(e)}
                )
        
        # Fallback to config if API not available
        if not search_paths:
            if library_path:
                search_paths = [library_path]
            else:
                # Use config libraries
                search_paths = config.moving.kavita_library_dirs if hasattr(config.moving, 'kavita_library_dirs') else []
                if config.folders.library:
                    search_paths.append(config.folders.library)
        
        if not search_paths:
            return {
                "in_library": False,
                "reason": "no_libraries_configured"
            }
        
        # Check each library path for duplicates
        from app.mover_service import MoverService
        is_duplicate, duplicate_path = await MoverService.check_duplicates_in_filesystem(
            file_hash,
            search_paths
        )
        
        return {
            "in_library": is_duplicate,
            "reason": "hash_match" if is_duplicate else "not_found",
            "duplicate_path": duplicate_path if is_duplicate else None
        }
    
    @staticmethod
    async def get_scan_history(
        file_hash: str,
        db_session: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Get previous scan results for a file hash.
        
        If auto_skip_known_hashes is enabled and we've scanned this hash before,
        we can reuse the scan results.
        
        Args:
            file_hash: SHA256 hash of file
            db_session: Database session
            
        Returns:
            Previous scan results if available
        """
        if not config.scanning.auto_skip_known_hashes:
            return None
        
        # Find any upload with this hash that has been scanned
        result = await db_session.execute(
            select(Upload).where(
                Upload.file_hash_sha256 == file_hash,
                Upload.scan_result.isnot(None)
            ).order_by(Upload.scanned_at.desc()).limit(1)
        )
        previous = result.scalar_one_or_none()
        
        if previous:
            app_logger.info(
                f"Found previous scan results for hash",
                extra={
                    "file_hash": file_hash,
                    "scan_result": previous.scan_result,
                    "scanned_at": previous.scanned_at.isoformat() if previous.scanned_at else None
                }
            )
            
            return {
                "scan_result": previous.scan_result,
                "scan_details": previous.scan_details,
                "scanned_at": previous.scanned_at.isoformat() if previous.scanned_at else None,
                "original_uuid": previous.uuid
            }
        
        return None

