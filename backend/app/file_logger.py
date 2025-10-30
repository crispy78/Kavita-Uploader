"""Per-file logging system for detailed debugging."""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler

from app.config import config


class FileLogger:
    """Creates individual log files for each uploaded file."""
    
    def __init__(self, upload_uuid: str, original_filename: str):
        """Initialize file logger for a specific upload.
        
        Args:
            upload_uuid: UUID of the upload
            original_filename: Original filename
        """
        self.upload_uuid = upload_uuid
        self.original_filename = original_filename
        self.log_dir = Path("logs/files")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file path
        safe_uuid = upload_uuid[:8]  # Use first 8 chars for readability
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"{timestamp}_{safe_uuid}.log"
        
        # Initialize logger
        self.logger = self._setup_logger()
        
        # Write header
        self.log_event("upload_started", {
            "uuid": upload_uuid,
            "filename": original_filename,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated logger for this file.
        
        Returns:
            Configured logger
        """
        logger_name = f"file.{self.upload_uuid}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.handlers = []  # Clear existing handlers
        
        # File handler
        handler = RotatingFileHandler(
            self.log_file,
            maxBytes=5242880,  # 5MB
            backupCount=1,
        )
        handler.setLevel(logging.DEBUG)
        
        # Simple text formatter for readability
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
        logger.propagate = False  # Don't propagate to root logger
        
        return logger
    
    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Log an event with structured data.
        
        Args:
            event_type: Type of event (e.g., "upload_started", "scan_complete")
            data: Event data
        """
        message = f"[{event_type.upper()}] {json.dumps(data, indent=2)}"
        self.logger.info(message)
    
    def log_phase(self, phase: str, status: str, details: Optional[Dict[str, Any]] = None):
        """Log a processing phase.
        
        Args:
            phase: Phase name (e.g., "upload", "scan", "metadata")
            status: Phase status (e.g., "started", "completed", "failed")
            details: Additional details
        """
        data = {
            "phase": phase,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        if details:
            data.update(details)
        
        self.log_event(f"{phase}_{status}", data)
    
    def log_error(self, error: str, exception: Optional[Exception] = None):
        """Log an error.
        
        Args:
            error: Error message
            exception: Exception object if available
        """
        data = {
            "error": error,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if exception:
            data["exception"] = str(exception)
            data["exception_type"] = type(exception).__name__
        
        self.log_event("error", data)
        
        if exception:
            self.logger.exception(f"Exception details: {exception}")
    
    def log_scan_progress(
        self,
        phase: str,
        status: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log scan progress with specific formatting.
        
        Args:
            phase: Scan phase (e.g., "check_hash", "upload", "poll", "complete")
            status: Status message
            details: Additional details
        """
        data = {
            "scan_phase": phase,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if details:
            data.update(details)
        
        self.logger.info(f"[SCAN:{phase.upper()}] {json.dumps(data, indent=2)}")
    
    def finalize(self, final_status: str, details: Optional[Dict[str, Any]] = None):
        """Write final status and close log.
        
        Args:
            final_status: Final status of the upload
            details: Final details
        """
        data = {
            "final_status": final_status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if details:
            data.update(details)
        
        self.log_event("upload_finalized", data)
        self.logger.info("=" * 80)
        self.logger.info(f"FINAL STATUS: {final_status}")
        self.logger.info("=" * 80)
        
        # Close handlers
        for handler in self.logger.handlers:
            handler.close()
            self.logger.removeHandler(handler)
    
    @staticmethod
    def get_log_file_for_upload(upload_uuid: str) -> Optional[Path]:
        """Find the log file for a given upload UUID.
        
        Args:
            upload_uuid: UUID to search for
            
        Returns:
            Path to log file if found, None otherwise
        """
        log_dir = Path("logs/files")
        if not log_dir.exists():
            return None
        
        safe_uuid = upload_uuid[:8]
        
        # Search for files containing this UUID
        for log_file in log_dir.glob(f"*_{safe_uuid}.log"):
            return log_file
        
        return None


def get_file_logger(upload_uuid: str, original_filename: str) -> FileLogger:
    """Factory function to get a file logger.
    
    Args:
        upload_uuid: UUID of upload
        original_filename: Original filename
        
    Returns:
        FileLogger instance
    """
    return FileLogger(upload_uuid, original_filename)



