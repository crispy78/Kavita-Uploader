"""Business logic services for upload processing pipeline."""

import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import Upload
from app.config import config
from app.utils import (
    sanitize_filename,
    generate_uuid_filename,
    set_secure_file_permissions,
    get_file_size,
    calculate_file_hash,
    detect_mime_type,
    get_file_extension,
)
from app.logger import app_logger


class UploadService:
    """Service for handling file uploads and quarantine (Step 1)."""

    @staticmethod
    async def save_to_quarantine(
        file_content: bytes,
        original_filename: str,
        db_session: AsyncSession,
    ) -> Upload:
        """Save uploaded file to quarantine with UUID name.
        
        This implements Step 1: Upload + Quarantine functionality.
        
        Args:
            file_content: File content bytes
            original_filename: Original filename from upload
            db_session: Database session
            
        Returns:
            Upload database record
            
        Raises:
            Exception: If file cannot be saved
        """
        # Sanitize filename
        sanitized_name = sanitize_filename(original_filename)
        file_ext = get_file_extension(sanitized_name)
        
        # Generate UUID filename
        file_uuid, uuid_filename = generate_uuid_filename(sanitized_name)
        
        # Prepare quarantine path
        quarantine_dir = Path(config.folders.quarantine)
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        quarantine_path = quarantine_dir / uuid_filename
        
        # Write file with secure permissions
        try:
            with open(quarantine_path, "wb") as f:
                f.write(file_content)
            
            # Set restrictive permissions (owner read/write only)
            set_secure_file_permissions(
                str(quarantine_path),
                config.security.file_permissions_mode
            )
            
            # Get file info
            file_size = get_file_size(str(quarantine_path))
            mime_type = detect_mime_type(str(quarantine_path))
            file_hash = await calculate_file_hash(str(quarantine_path))
            
            # Create database record
            upload = Upload(
                uuid=file_uuid,
                original_filename=original_filename,
                sanitized_filename=sanitized_name,
                file_size=file_size,
                mime_type=mime_type,
                file_extension=file_ext,
                status="quarantined",
                quarantine_path=str(quarantine_path),
                file_hash_sha256=file_hash,
                uploaded_at=datetime.utcnow(),
            )
            
            db_session.add(upload)
            await db_session.commit()
            await db_session.refresh(upload)
            
            app_logger.info(
                f"File quarantined successfully",
                extra={
                    "upload_uuid": file_uuid,
                    "uploaded_file": original_filename,
                    "file_size": file_size,
                    "status": "quarantined",
                }
            )
            
            return upload
            
        except Exception as e:
            app_logger.error(
                f"Failed to quarantine file: {str(e)}",
                extra={
                    "uploaded_file": original_filename,
                }
            )
            # Clean up file if database operation failed
            if quarantine_path.exists():
                quarantine_path.unlink()
            raise

    @staticmethod
    async def get_upload_status(
        upload_uuid: str,
        db_session: AsyncSession,
    ) -> Optional[Dict[str, Any]]:
        """Get upload status by UUID.
        
        Args:
            upload_uuid: Upload UUID
            db_session: Database session
            
        Returns:
            Upload status dictionary or None if not found
        """
        result = await db_session.execute(
            select(Upload).where(Upload.uuid == upload_uuid)
        )
        upload = result.scalar_one_or_none()
        
        if not upload:
            return None
        
        return {
            "uuid": upload.uuid,
            "original_filename": upload.original_filename,
            "file_size": upload.file_size,
            "mime_type": upload.mime_type,
            "status": upload.status,
            "scan_result": upload.scan_result,
            "uploaded_at": upload.uploaded_at.isoformat(),
            "is_duplicate": upload.is_duplicate,
            "error_message": upload.error_message,
        }


class ScanningService:
    """Service for virus/malware scanning (Step 2 - IMPLEMENTED)."""

    @staticmethod
    async def scan_file_with_logging(
        upload_uuid: str,
        db_session: AsyncSession,
        file_logger: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Scan file with integrated file logging.
        
        Args:
            upload_uuid: Upload UUID to scan
            db_session: Database session
            file_logger: Optional FileLogger instance
            
        Returns:
            Scan result dictionary
        """
        try:
            if file_logger:
                file_logger.log_phase("scan", "started")
            
            # Call the regular scan with file logger integration
            result = await ScanningService._scan_file_internal(
                upload_uuid,
                db_session,
                file_logger
            )
            
            if file_logger:
                file_logger.log_phase("scan", "completed", {
                    "scan_result": result.get("scan_result", "unknown"),
                    "scan_details": result.get("scan_details", {})
                })
                
                # Finalize log
                file_logger.finalize(
                    result.get("scan_result", "unknown"),
                    {"scan_status": result.get("status")}
                )
            
            return result
            
        except Exception as e:
            if file_logger:
                file_logger.log_error("Scan failed", e)
                file_logger.finalize("scan_error")
            raise

    @staticmethod
    async def scan_file(upload_uuid: str, db_session: AsyncSession) -> Dict[str, Any]:
        """Public scan method without logging (for manual API calls).
        
        Args:
            upload_uuid: Upload UUID to scan
            db_session: Database session
            
        Returns:
            Scan result dictionary
        """
        return await ScanningService._scan_file_internal(upload_uuid, db_session, None)

    @staticmethod
    async def _scan_file_internal(
        upload_uuid: str,
        db_session: AsyncSession,
        file_logger: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Internal scan implementation with optional file logging.
        
        Complete implementation of Step 2:
        - Check for duplicate hash (reuse previous scan)
        - Upload file to VirusTotal API if needed
        - Poll for scan results
        - Update upload record with scan status
        - Save scan report to logs/scans/
        - Handle infected files according to config
        
        Args:
            upload_uuid: Upload UUID to scan
            db_session: Database session
            
        Returns:
            Scan result dictionary
        """
        from app.virustotal import VirusTotalScanner
        from app.duplicate_detection import DuplicateDetector
        import json
        from pathlib import Path
        
        # Check if scanning is enabled
        if not config.scanning.enabled:
            app_logger.warning("Scanning disabled in configuration")
            return {
                "status": "disabled",
                "message": "Virus scanning is not enabled",
            }
        
        # Get upload record
        result = await db_session.execute(
            select(Upload).where(Upload.uuid == upload_uuid)
        )
        upload = result.scalar_one_or_none()
        
        if not upload:
            return {
                "status": "error",
                "message": "Upload not found"
            }
        
        # Check if already scanned
        if upload.scan_result in ["safe", "clean"]:
            app_logger.info(
                f"File already marked as clean",
                extra={"upload_uuid": upload_uuid, "scan_result": upload.scan_result}
            )
            return {
                "status": "already_scanned",
                "scan_result": upload.scan_result,
                "scanned_at": upload.scanned_at.isoformat() if upload.scanned_at else None
            }
        
        # Check for previous scan of same hash
        previous_scan = await DuplicateDetector.get_scan_history(
            upload.file_hash_sha256,
            db_session
        )
        
        if previous_scan:
            app_logger.info(
                f"Reusing previous scan results for hash",
                extra={
                    "upload_uuid": upload_uuid,
                    "file_hash": upload.file_hash_sha256,
                    "previous_result": previous_scan["scan_result"]
                }
            )
            
            # Update current upload with previous scan results
            upload.scan_result = previous_scan["scan_result"]
            upload.scan_details = previous_scan["scan_details"]
            upload.scanned_at = datetime.utcnow()
            upload.status = "scanned" if previous_scan["scan_result"] in ["safe", "clean"] else "infected"
            
            await db_session.commit()
            
            return {
                "status": "reused",
                "scan_result": previous_scan["scan_result"],
                "message": "Reused scan results from previous upload with same hash",
                "original_uuid": previous_scan["original_uuid"]
            }
        
        # Update status to scanning
        upload.status = "scanning"
        await db_session.commit()
        
        # Initialize VirusTotal scanner
        scanner = VirusTotalScanner()
        
        # Perform scan with file logger
        scan_results = await scanner.scan_file(
            upload.quarantine_path,
            upload.file_hash_sha256,
            file_logger=file_logger
        )
        
        # Save scan results to file
        scan_log_dir = Path("logs/scans")
        scan_log_dir.mkdir(parents=True, exist_ok=True)
        
        scan_log_file = scan_log_dir / f"{upload_uuid}.json"
        with open(scan_log_file, "w") as f:
            json.dump(scan_results, f, indent=2)
        
        # Set restrictive permissions on scan log
        import os
        os.chmod(scan_log_file, 0o600)
        
        # Determine final status
        scan_status = scan_results.get("status", "error")
        
        if scan_status == "malicious":
            upload.scan_result = "infected"
            upload.status = "infected"
            
            # Auto-delete if configured
            if config.scanning.auto_delete_infected:
                app_logger.warning(
                    f"Auto-deleting infected file",
                    extra={"upload_uuid": upload_uuid}
                )
                try:
                    os.remove(upload.quarantine_path)
                    upload.status = "deleted"
                except Exception as e:
                    app_logger.error(
                        f"Failed to delete infected file: {str(e)}",
                        extra={"upload_uuid": upload_uuid}
                    )
        elif scan_status in ["clean", "undetected"]:
            upload.scan_result = "safe"
            upload.status = "scanned"
        elif scan_status == "suspicious":
            upload.scan_result = "suspicious"
            upload.status = "suspicious"
        elif scan_status == "pending":
            upload.scan_result = "pending"
            upload.status = "scanning"
        else:
            upload.scan_result = "error"
            upload.status = "scan_error"
        
        # Update database
        upload.scan_details = json.dumps(scan_results)
        upload.scanned_at = datetime.utcnow()
        
        await db_session.commit()
        await db_session.refresh(upload)
        
        app_logger.info(
            f"Scan completed",
            extra={
                "upload_uuid": upload_uuid,
                "scan_result": upload.scan_result,
                "scan_status": scan_status
            }
        )
        
        return {
            "status": "completed",
            "scan_result": upload.scan_result,
            "scan_details": scan_results,
            "scanned_at": upload.scanned_at.isoformat()
        }


class MetadataService:
    """Service for metadata extraction and editing (Step 3 - STUB)."""

    @staticmethod
    async def extract_metadata(
        upload_uuid: str,
        db_session: AsyncSession,
    ) -> Dict[str, Any]:
        """Extract metadata from e-book file.
        
        TODO: Step 3 - Implement metadata extraction
        - Use ebooklib for EPUB files
        - Use PyPDF2 for PDF files
        - Extract title, author, publisher, ISBN, etc.
        - Store metadata in upload record
        - Return metadata for user editing
        
        Args:
            upload_uuid: Upload UUID
            db_session: Database session
            
        Returns:
            Extracted metadata dictionary
        """
        app_logger.warning(
            "Metadata extraction not yet implemented (Step 3)",
            extra={"upload_uuid": upload_uuid}
        )
        
        # STUB: Return empty metadata
        return {
            "status": "not_implemented",
            "message": "Metadata extraction will be implemented in Step 3",
            "metadata": {},
        }

    @staticmethod
    async def update_metadata(
        upload_uuid: str,
        metadata: Dict[str, Any],
        db_session: AsyncSession,
    ) -> bool:
        """Update metadata for upload.
        
        TODO: Step 3 - Implement metadata update
        - Validate metadata fields
        - Update upload record
        - Mark as user-edited
        
        Args:
            upload_uuid: Upload UUID
            metadata: Updated metadata dictionary
            db_session: Database session
            
        Returns:
            True if successful
        """
        app_logger.warning(
            "Metadata update not yet implemented (Step 3)",
            extra={"upload_uuid": upload_uuid}
        )
        
        # STUB
        return False


class DuplicateService:
    """Service for duplicate detection (Step 4 - STUB)."""

    @staticmethod
    async def check_duplicate(
        upload_uuid: str,
        db_session: AsyncSession,
    ) -> Dict[str, Any]:
        """Check if file is a duplicate.
        
        TODO: Step 4 - Implement duplicate detection
        - Check against existing uploads by hash
        - Check against library files by hash and size
        - Check against unsorted folder
        - Handle same-name files (rename according to config)
        - Update upload record with duplicate status
        
        Args:
            upload_uuid: Upload UUID
            db_session: Database session
            
        Returns:
            Duplicate check result dictionary
        """
        app_logger.warning(
            "Duplicate detection not yet implemented (Step 4)",
            extra={"upload_uuid": upload_uuid}
        )
        
        # STUB: Return not duplicate
        return {
            "status": "not_implemented",
            "message": "Duplicate detection will be implemented in Step 4",
            "is_duplicate": False,
        }


class MoveService:
    """Service for moving files to final destination (Step 4 - STUB)."""

    @staticmethod
    async def move_to_unsorted(
        upload_uuid: str,
        db_session: AsyncSession,
    ) -> Dict[str, Any]:
        """Move file from quarantine to unsorted folder.
        
        TODO: Step 4 - Implement file moving
        - Check all previous steps completed
        - Move file from quarantine to unsorted
        - Rename if duplicate name exists
        - Update upload record with final path
        - Set proper permissions on final file
        - Clean up quarantine file
        
        Args:
            upload_uuid: Upload UUID
            db_session: Database session
            
        Returns:
            Move result dictionary
        """
        app_logger.warning(
            "File moving not yet implemented (Step 4)",
            extra={"upload_uuid": upload_uuid}
        )
        
        # STUB
        return {
            "status": "not_implemented",
            "message": "File moving will be implemented in Step 4",
        }

