"""File moving service with duplicate detection and integrity verification (Step 4)."""

import hashlib
import os
import csv
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.database import Upload
from app.logger import app_logger


class MoverService:
    """Service for moving files from quarantine to unsorted library with duplicate detection."""
    
    @staticmethod
    async def compute_file_hash(file_path: Path) -> str:
        """Compute SHA-256 hash of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Hexadecimal hash string
        """
        sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        
        return sha256.hexdigest()
    
    @staticmethod
    async def check_duplicates_by_hash(
        file_hash: str,
        db_session: AsyncSession,
        exclude_uuid: Optional[str] = None
    ) -> Tuple[bool, Optional[Upload]]:
        """Check if a file with this hash already exists in the database.
        
        Args:
            file_hash: SHA-256 hash to check
            db_session: Database session
            exclude_uuid: UUID to exclude from search (current file)
            
        Returns:
            Tuple of (is_duplicate, original_upload)
        """
        query = select(Upload).where(
            Upload.file_hash_sha256 == file_hash,
            Upload.status.in_(["moved", "safe", "metadata_verified"])
        )
        
        if exclude_uuid:
            query = query.where(Upload.uuid != exclude_uuid)
        
        result = await db_session.execute(query)
        duplicate = result.scalar_one_or_none()
        
        return (duplicate is not None, duplicate)
    
    @staticmethod
    async def check_duplicates_in_filesystem(
        file_hash: str,
        search_dirs: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """Check if a file with this hash exists in filesystem directories.
        
        Args:
            file_hash: SHA-256 hash to check
            search_dirs: List of directories to search
            
        Returns:
            Tuple of (is_duplicate, file_path)
        """
        for search_dir in search_dirs:
            if not os.path.exists(search_dir):
                app_logger.warning(f"Search directory does not exist: {search_dir}")
                continue
            
            for root, _, files in os.walk(search_dir):
                for file in files:
                    file_path = Path(root) / file
                    
                    # Skip hidden files and non-ebook files
                    if file.startswith('.'):
                        continue
                    
                    try:
                        existing_hash = await MoverService.compute_file_hash(file_path)
                        if existing_hash == file_hash:
                            return (True, str(file_path))
                    except Exception as e:
                        app_logger.debug(f"Failed to hash {file_path}: {e}")
                        continue
        
        return (False, None)
    
    @staticmethod
    async def check_name_conflict(
        metadata: Dict,
        db_session: AsyncSession,
        exclude_uuid: Optional[str] = None
    ) -> Tuple[bool, Optional[Upload]]:
        """Check if a file with same title/author exists (different hash).
        
        Args:
            metadata: File metadata dict with title and author
            db_session: Database session
            exclude_uuid: UUID to exclude from search
            
        Returns:
            Tuple of (has_conflict, conflicting_upload)
        """
        title = metadata.get("title", "").strip()
        author = metadata.get("author", "").strip()
        
        if not title or not author:
            return (False, None)
        
        # Search for files with same metadata
        query = select(Upload).where(
            Upload.status.in_(["moved", "safe", "metadata_verified"]),
            Upload.metadata_json.isnot(None)
        )
        
        if exclude_uuid:
            query = query.where(Upload.uuid != exclude_uuid)
        
        result = await db_session.execute(query)
        uploads = result.scalars().all()
        
        for upload in uploads:
            try:
                upload_metadata = json.loads(upload.metadata_json)
                if (upload_metadata.get("title", "").strip().lower() == title.lower() and
                    upload_metadata.get("author", "").strip().lower() == author.lower()):
                    return (True, upload)
            except json.JSONDecodeError:
                continue
        
        return (False, None)
    
    @staticmethod
    def generate_renamed_filename(
        metadata: Dict,
        file_extension: str,
        timestamp: Optional[datetime] = None
    ) -> str:
        """Generate a renamed filename for duplicate files.
        
        Args:
            metadata: File metadata
            file_extension: Original file extension
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            New filename
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        title = metadata.get("title", "unknown").strip()
        author = metadata.get("author", "unknown").strip()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        
        # Sanitize title and author for filename
        def sanitize(s: str) -> str:
            # Remove invalid filename characters
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                s = s.replace(char, '')
            return s.strip()[:100]  # Limit length
        
        title = sanitize(title)
        author = sanitize(author)
        
        # Use pattern from config
        pattern = config.moving.rename_pattern
        filename = pattern.format(
            title=title,
            author=author,
            timestamp=timestamp_str,
            ext=file_extension
        )
        
        return filename
    
    @staticmethod
    async def verify_integrity(
        file_path: Path,
        expected_hash: str
    ) -> Tuple[bool, str]:
        """Verify file integrity by re-computing hash.
        
        Args:
            file_path: Path to file
            expected_hash: Expected SHA-256 hash
            
        Returns:
            Tuple of (is_valid, actual_hash)
        """
        actual_hash = await MoverService.compute_file_hash(file_path)
        is_valid = actual_hash == expected_hash
        
        return (is_valid, actual_hash)
    
    @staticmethod
    async def write_to_manifest(
        upload: Upload,
        destination_path: str,
        action: str,
        reason: Optional[str] = None
    ):
        """Write an entry to the checksum manifest CSV.
        
        Args:
            upload: Upload record
            destination_path: Final file path
            action: Action taken (moved, discarded, renamed)
            reason: Optional reason for action
        """
        if not config.moving.checksum_manifest:
            return
        
        manifest_path = Path(config.moving.manifest_path)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists to determine if we need headers
        file_exists = manifest_path.exists()
        
        with open(manifest_path, 'a', newline='') as csvfile:
            fieldnames = [
                'timestamp', 'uuid', 'original_filename', 'destination_path',
                'file_hash', 'file_size', 'action', 'reason'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                'timestamp': datetime.utcnow().isoformat(),
                'uuid': upload.uuid,
                'original_filename': upload.original_filename,
                'destination_path': destination_path or 'N/A',
                'file_hash': upload.file_hash_sha256,
                'file_size': upload.file_size,
                'action': action,
                'reason': reason or ''
            })
    
    @staticmethod
    async def move_file(
        upload_uuid: str,
        db_session: AsyncSession
    ) -> Dict:
        """Move a file from quarantine to unsorted library with duplicate detection.
        
        Args:
            upload_uuid: UUID of upload to move
            db_session: Database session
            
        Returns:
            Dict with success status, message, and details
        """
        app_logger.info(
            "Starting file move operation",
            extra={"upload_uuid": upload_uuid}
        )
        
        # Check if moving is enabled
        if not config.moving.enabled:
            return {
                "success": False,
                "message": "Moving is disabled in configuration",
                "status": "disabled"
            }
        
        # Get upload record
        result = await db_session.execute(
            select(Upload).where(Upload.uuid == upload_uuid)
        )
        upload = result.scalar_one_or_none()
        
        if not upload:
            return {
                "success": False,
                "message": "Upload not found",
                "status": "not_found"
            }
        
        # Verify upload is in correct state
        if upload.status not in ["metadata_verified", "safe", "clean"]:
            return {
                "success": False,
                "message": f"File must be verified before moving (current status: {upload.status})",
                "status": "invalid_state"
            }
        
        # Verify source file exists
        source_path = Path(upload.quarantine_path)
        if not source_path.exists():
            return {
                "success": False,
                "message": "Source file not found in quarantine",
                "status": "source_missing"
            }
        
        # Compute hash if not already done
        if not upload.file_hash_sha256:
            upload.file_hash_sha256 = await MoverService.compute_file_hash(source_path)
            await db_session.commit()
        
        file_hash = upload.file_hash_sha256
        
        # STEP 1: Check for exact hash duplicates in database
        is_db_duplicate, db_duplicate = await MoverService.check_duplicates_by_hash(
            file_hash,
            db_session,
            exclude_uuid=upload_uuid
        )
        
        if is_db_duplicate and config.moving.discard_on_exact_duplicate:
            app_logger.warning(
                "Exact duplicate found in database - discarding",
                extra={
                    "upload_uuid": upload_uuid,
                    "duplicate_of": db_duplicate.uuid,
                    "file_hash": file_hash
                }
            )
            
            upload.status = "duplicate_discarded"
            upload.is_duplicate = True
            upload.duplicate_of = db_duplicate.uuid
            upload.duplicate_reason = "exact_hash_match_database"
            await db_session.commit()
            
            await MoverService.write_to_manifest(
                upload,
                None,
                "discarded",
                "exact_hash_match_database"
            )
            
            return {
                "success": False,
                "message": "Duplicate file (exact hash match in database)",
                "status": "duplicate_discarded",
                "duplicate_of": db_duplicate.uuid,
                "duplicate_reason": "exact_hash_match_database"
            }
        
        # STEP 2: Check for exact hash duplicates in filesystem
        # Get library directories from Kavita API if enabled, otherwise use config
        search_dirs = [config.moving.unsorted_dir]
        
        if config.kavita.enabled:
            try:
                from app.kavita_api import kavita_api
                library_paths = await kavita_api.get_library_paths()
                if library_paths:
                    app_logger.info(
                        f"Using {len(library_paths)} libraries from Kavita API",
                        extra={"library_paths": library_paths}
                    )
                    search_dirs.extend(library_paths)
                else:
                    app_logger.warning(
                        "No libraries found from Kavita API, falling back to config",
                        extra={"config_libraries": config.moving.kavita_library_dirs}
                    )
                    search_dirs.extend(config.moving.kavita_library_dirs)
            except Exception as e:
                app_logger.warning(
                    f"Failed to fetch libraries from Kavita API, using config fallback",
                    extra={"error": str(e), "config_libraries": config.moving.kavita_library_dirs}
                )
                search_dirs.extend(config.moving.kavita_library_dirs)
        else:
            # Kavita not enabled, use config libraries
            search_dirs.extend(config.moving.kavita_library_dirs)
        is_fs_duplicate, fs_duplicate_path = await MoverService.check_duplicates_in_filesystem(
            file_hash,
            search_dirs
        )
        
        if is_fs_duplicate and config.moving.discard_on_exact_duplicate:
            app_logger.warning(
                "Exact duplicate found in filesystem - discarding",
                extra={
                    "upload_uuid": upload_uuid,
                    "duplicate_path": fs_duplicate_path,
                    "file_hash": file_hash
                }
            )
            
            upload.status = "duplicate_discarded"
            upload.is_duplicate = True
            upload.duplicate_reason = f"exact_hash_match_filesystem:{fs_duplicate_path}"
            await db_session.commit()
            
            await MoverService.write_to_manifest(
                upload,
                None,
                "discarded",
                f"exact_hash_match_filesystem"
            )
            
            return {
                "success": False,
                "message": "Duplicate file (exact hash match in filesystem)",
                "status": "duplicate_discarded",
                "duplicate_path": fs_duplicate_path,
                "duplicate_reason": "exact_hash_match_filesystem"
            }
        
        # STEP 3: Check for name conflicts (same title/author, different hash)
        metadata = {}
        if upload.metadata_json:
            try:
                metadata = json.loads(upload.metadata_json)
            except json.JSONDecodeError:
                pass
        
        has_name_conflict, conflicting_upload = await MoverService.check_name_conflict(
            metadata,
            db_session,
            exclude_uuid=upload_uuid
        )
        
        # Determine final filename
        filename = upload.original_filename
        renamed = False
        
        if has_name_conflict and config.moving.rename_on_name_conflict:
            filename = MoverService.generate_renamed_filename(
                metadata,
                upload.file_extension
            )
            renamed = True
            
            app_logger.info(
                "Name conflict detected - renaming file",
                extra={
                    "upload_uuid": upload_uuid,
                    "original": upload.original_filename,
                    "new_name": filename
                }
            )
        elif has_name_conflict and not config.moving.rename_on_name_conflict:
            # Name conflict but renaming disabled - discard
            upload.status = "duplicate_discarded"
            upload.is_duplicate = True
            upload.duplicate_of = conflicting_upload.uuid if conflicting_upload else None
            upload.duplicate_reason = "name_conflict_rename_disabled"
            await db_session.commit()
            
            return {
                "success": False,
                "message": "Name conflict detected but renaming is disabled",
                "status": "duplicate_discarded",
                "duplicate_reason": "name_conflict_rename_disabled"
            }
        
        # STEP 4: Prepare destination directory
        # Kavita requires files in a subfolder (e.g., unsorted/processed/)
        # Ensure we're using the processed subfolder
        base_dir = Path(config.moving.unsorted_dir)
        dest_dir = base_dir / "processed"
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure secure permissions
        try:
            os.chmod(dest_dir, config.security.directory_permissions_mode)
        except Exception as e:
            app_logger.warning(f"Failed to set directory permissions: {e}")
        
        destination_path = dest_dir / filename
        
        # Ensure destination doesn't exist
        counter = 1
        base_name = destination_path.stem
        while destination_path.exists():
            destination_path = dest_dir / f"{base_name}_{counter}{destination_path.suffix}"
            counter += 1
        
        # DRY RUN MODE
        if config.moving.dry_run:
            app_logger.info(
                "DRY RUN: Would move file",
                extra={
                    "upload_uuid": upload_uuid,
                    "source": str(source_path),
                    "destination": str(destination_path),
                    "renamed": renamed
                }
            )
            
            return {
                "success": True,
                "message": "DRY RUN: File would be moved (no actual changes made)",
                "status": "dry_run",
                "source": str(source_path),
                "destination": str(destination_path),
                "renamed": renamed
            }
        
        # STEP 5: Move the file
        try:
            if config.moving.atomic_operations and source_path.parent == destination_path.parent:
                # Atomic move (same filesystem)
                os.replace(source_path, destination_path)
                app_logger.info("File moved atomically (os.replace)")
            else:
                # Copy + verify + delete (different filesystem or atomic disabled)
                shutil.copy2(source_path, destination_path)
                app_logger.info("File copied to destination")
                
                # Verify integrity if configured
                if config.moving.verify_integrity_post_move:
                    is_valid, actual_hash = await MoverService.verify_integrity(
                        destination_path,
                        file_hash
                    )
                    
                    if not is_valid:
                        # Integrity check failed - rollback
                        app_logger.error(
                            "Integrity check failed after move - rolling back",
                            extra={
                                "upload_uuid": upload_uuid,
                                "expected_hash": file_hash,
                                "actual_hash": actual_hash
                            }
                        )
                        
                        # Delete the corrupt copy
                        destination_path.unlink()
                        
                        upload.status = "move_failed"
                        upload.error_message = "Integrity check failed after move"
                        await db_session.commit()
                        
                        return {
                            "success": False,
                            "message": "Integrity check failed - file may be corrupted",
                            "status": "integrity_failed",
                            "expected_hash": file_hash,
                            "actual_hash": actual_hash
                        }
                    
                    app_logger.info("Integrity verified successfully")
                
                # Delete quarantine file only after successful verification
                if config.moving.cleanup_quarantine_on_success:
                    source_path.unlink()
                    app_logger.info("Quarantine file deleted")
            
            # Set secure file permissions
            try:
                os.chmod(destination_path, config.security.file_permissions_mode)
            except Exception as e:
                app_logger.warning(f"Failed to set file permissions: {e}")
            
        except Exception as e:
            app_logger.error(
                f"Failed to move file: {str(e)}",
                exc_info=True,
                extra={"upload_uuid": upload_uuid}
            )
            
            upload.status = "move_failed"
            upload.error_message = str(e)
            await db_session.commit()
            
            return {
                "success": False,
                "message": f"Failed to move file: {str(e)}",
                "status": "move_failed"
            }
        
        # STEP 6: Update database
        upload.status = "moved"
        upload.final_path = str(destination_path)
        upload.moved_at = datetime.utcnow()
        
        if renamed:
            upload.is_duplicate = False  # Different content, just renamed for clarity
            upload.duplicate_reason = "name_conflict_renamed"
        
        await db_session.commit()
        
        # STEP 7: Write to manifest
        await MoverService.write_to_manifest(
            upload,
            str(destination_path),
            "renamed" if renamed else "moved",
            upload.duplicate_reason
        )
        
        app_logger.info(
            "File moved successfully",
            extra={
                "upload_uuid": upload_uuid,
                "destination": str(destination_path),
                "renamed": renamed
            }
        )
        
        return {
            "success": True,
            "message": "File moved successfully" + (" (renamed due to name conflict)" if renamed else ""),
            "status": "moved",
            "destination": str(destination_path),
            "renamed": renamed,
            "original_name": upload.original_filename if renamed else None
        }



