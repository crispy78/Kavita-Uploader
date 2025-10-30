"""Structured JSON logging configuration with enhanced scan tracking."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record
            
        Returns:
            JSON formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }

        # Core file tracking fields
        if hasattr(record, "upload_uuid"):
            log_data["upload_uuid"] = record.upload_uuid
        if hasattr(record, "uploaded_file"):
            log_data["uploaded_file"] = record.uploaded_file
        if hasattr(record, "file_size"):
            log_data["file_size"] = record.file_size
        if hasattr(record, "file_hash"):
            log_data["file_hash"] = record.file_hash
        if hasattr(record, "status"):
            log_data["status"] = record.status
        if hasattr(record, "ip_address"):
            log_data["ip_address"] = record.ip_address
        
        # Scanning specific fields
        if hasattr(record, "scan_phase"):
            log_data["scan_phase"] = record.scan_phase  # "check_hash", "upload", "poll", "complete"
        if hasattr(record, "scan_result"):
            log_data["scan_result"] = record.scan_result
        if hasattr(record, "analysis_id"):
            log_data["analysis_id"] = record.analysis_id
        if hasattr(record, "malicious_count"):
            log_data["malicious_count"] = record.malicious_count
        if hasattr(record, "total_engines"):
            log_data["total_engines"] = record.total_engines
        if hasattr(record, "virustotal_link"):
            log_data["virustotal_link"] = record.virustotal_link
        
        # Performance tracking
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "attempt"):
            log_data["attempt"] = record.attempt
        if hasattr(record, "max_attempts"):
            log_data["max_attempts"] = record.max_attempts

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter for console output."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as readable text.
        
        Args:
            record: Log record
            
        Returns:
            Formatted text string
        """
        # Color codes for different log levels
        colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        reset = '\033[0m'
        
        color = colors.get(record.levelname, '')
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        # Build base message
        msg = f"{color}[{record.levelname}]{reset} {timestamp} - {record.getMessage()}"
        
        # Add context if available
        context_parts = []
        if hasattr(record, "upload_uuid"):
            context_parts.append(f"UUID:{record.upload_uuid[:8]}")
        if hasattr(record, "scan_phase"):
            context_parts.append(f"Phase:{record.scan_phase}")
        if hasattr(record, "scan_result"):
            context_parts.append(f"Result:{record.scan_result}")
        
        if context_parts:
            msg += f" ({', '.join(context_parts)})"
        
        return msg


def setup_logger(
    name: str,
    log_level: str = "INFO",
    log_file: str = "logs/safeuploader.log",
    max_bytes: int = 10485760,
    backup_count: int = 5,
    log_format: str = "json",
    console_format: str = "text",
    console_level: str = None,
) -> logging.Logger:
    """Setup logger with file and console handlers.
    
    Args:
        name: Logger name
        log_level: Logging level for file
        log_file: Path to log file
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
        log_format: Log format for file ("json" or "text")
        console_format: Log format for console ("json" or "text")
        console_level: Logging level for console (defaults to log_level)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Set to DEBUG, handlers will filter

    # Remove existing handlers
    logger.handlers = []

    # Create log directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # File handler with rotation - always JSON for parsing
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(JSONFormatter())

    # Console handler - human-readable by default
    console_handler = logging.StreamHandler(sys.stdout)
    console_level = console_level or log_level
    console_handler.setLevel(getattr(logging, console_level.upper()))
    
    if console_format.lower() == "json":
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(TextFormatter())

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_scan_logger() -> logging.Logger:
    """Get specialized logger for scan operations.
    
    Returns:
        Logger configured for scan tracking
    """
    return logging.getLogger("safeuploader.scan")


# Create default loggers
app_logger = setup_logger("safeuploader")
scan_logger = get_scan_logger()

