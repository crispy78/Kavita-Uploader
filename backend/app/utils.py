"""Utility functions for file handling, validation, and security."""

import os
import re
import hashlib
import uuid
import magic
from pathlib import Path
from typing import Tuple, Optional
from datetime import datetime


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and other attacks.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem operations
    """
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove or replace dangerous characters
    # Keep only alphanumeric, dots, hyphens, underscores, and spaces
    filename = re.sub(r'[^\w\s\-\.]', '_', filename)
    
    # Replace multiple spaces/underscores with single ones
    filename = re.sub(r'[\s_]+', '_', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Limit length
    name, ext = os.path.splitext(filename)
    if len(name) > 200:
        name = name[:200]
    
    filename = name + ext
    
    # Ensure filename is not empty
    if not filename or filename == ext:
        filename = f"unnamed{ext}"
    
    return filename


def get_file_extension(filename: str) -> str:
    """Extract file extension without the dot.
    
    Args:
        filename: Filename to extract extension from
        
    Returns:
        File extension in lowercase without dot
    """
    ext = os.path.splitext(filename)[1].lstrip('.').lower()
    return ext


def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
    """Check if file extension is allowed.
    
    Args:
        filename: Filename to validate
        allowed_extensions: List of allowed extensions (without dots)
        
    Returns:
        True if extension is allowed, False otherwise
    """
    ext = get_file_extension(filename)
    return ext in [e.lower() for e in allowed_extensions]


def detect_mime_type(file_path: str) -> Optional[str]:
    """Detect MIME type using python-magic.
    
    Args:
        file_path: Path to file
        
    Returns:
        MIME type string or None if detection fails
    """
    try:
        mime = magic.Magic(mime=True)
        return mime.from_file(file_path)
    except Exception:
        return None


def validate_mime_type(mime_type: Optional[str], allowed_mime_types: list) -> bool:
    """Check if MIME type is allowed.
    
    Args:
        mime_type: MIME type to validate
        allowed_mime_types: List of allowed MIME types
        
    Returns:
        True if MIME type is allowed, False otherwise
    """
    if not mime_type:
        return False
    return mime_type in allowed_mime_types


async def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Hexadecimal SHA256 hash string
    """
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        # Read file in chunks for memory efficiency
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()


def generate_uuid_filename(original_filename: str) -> Tuple[str, str]:
    """Generate UUID-based filename while preserving extension.
    
    Args:
        original_filename: Original filename
        
    Returns:
        Tuple of (uuid_string, uuid_filename_with_extension)
    """
    file_uuid = str(uuid.uuid4())
    ext = get_file_extension(original_filename)
    uuid_filename = f"{file_uuid}.{ext}" if ext else file_uuid
    
    return file_uuid, uuid_filename


def set_secure_file_permissions(file_path: str, mode: int = 0o600):
    """Set restrictive file permissions.
    
    Args:
        file_path: Path to file
        mode: Permission mode (default: 0o600 = owner read/write only)
    """
    os.chmod(file_path, mode)


def get_file_size(file_path: str) -> int:
    """Get file size in bytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in bytes
    """
    return os.path.getsize(file_path)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "2.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def generate_timestamp_filename(original_filename: str) -> str:
    """Generate filename with timestamp for duplicate handling.
    
    Args:
        original_filename: Original filename
        
    Returns:
        Filename with timestamp inserted before extension
    """
    name, ext = os.path.splitext(original_filename)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{name}_{timestamp}{ext}"



