"""API routes for upload and processing."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException,
    Depends,
    Request,
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import config
from app.database import db, Upload
from app.services import (
    UploadService,
    ScanningService,
    MetadataService,
    DuplicateService,
    MoveService,
)
from app.utils import (
    validate_file_extension,
    validate_mime_type,
    detect_mime_type,
    format_file_size,
)
from app.logger import app_logger
from slowapi import Limiter
from slowapi.util import get_remote_address

async def verify_ui_header(request: Request):
    """Reject API calls unless they carry the trusted UI header when protection is enabled."""
    if not config.api_protection.enabled or not config.api_protection.require_header:
        return
    expected = config.api_protection.header_value
    header_name = config.api_protection.header_name
    actual = request.headers.get(header_name)
    if actual != expected:
        raise HTTPException(status_code=403, detail={
            "error": "Forbidden",
            "message": "API access is restricted"
        })


router = APIRouter(dependencies=[Depends(verify_ui_header)])
limiter = Limiter(key_func=get_remote_address)


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """Dependency to get current authenticated user.
    
    Returns user data if authenticated, None otherwise.
    Does not raise exception - allows optional auth.
    """
    from app.kavita_auth import kavita_auth
    
    if not config.kavita.enabled:
        return None
    
    # Debug logging
    app_logger.debug(
        f"get_current_user called",
        extra={
            "kavita_enabled": config.kavita.enabled,
            "cookie_name": config.auth.cookie_name,
            "cookies_received": list(request.cookies.keys()),
            "has_auth_cookie": config.auth.cookie_name in request.cookies,
        }
    )
    
    user = kavita_auth.get_current_user(request)
    
    app_logger.debug(
        f"get_current_user result",
        extra={
            "user_found": user is not None,
            "username": user.get("username") if user else None,
        }
    )
    
    return user


async def require_auth(request: Request) -> Dict[str, Any]:
    """Dependency that requires authentication.
    
    Raises HTTPException if user is not authenticated.
    """
    from app.kavita_auth import kavita_auth
    
    if not config.kavita.enabled or not config.auth.require_auth:
        return {"username": "anonymous"}
    
    user = kavita_auth.get_current_user(request)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Authentication required",
                "message": "Please log in to upload files"
            }
        )
    
    return user


async def get_db_session():
    """Dependency for database session."""
    async for session in db.get_session():
        yield session


@router.get("/config")
async def get_config():
    """Get public configuration for frontend.
    
    Returns configuration that frontend needs to know about.
    Does NOT expose sensitive values like API keys.
    """
    return {
        "upload": {
            "max_file_size_mb": config.upload.max_file_size_mb,
            "max_file_size_bytes": config.max_file_size_bytes,
            "allowed_extensions": config.upload.allowed_extensions,
        },
        "disk_protection": {
            "enabled": config.disk_protection.enabled,
            "max_single_upload_size_mb": config.disk_protection.max_single_upload_size_mb,
            "auto_cleanup_enabled": config.disk_protection.auto_cleanup_enabled,
            "auto_cleanup_age_hours": config.disk_protection.auto_cleanup_age_hours,
        },
        "features": {
            "scanning_enabled": config.scanning.enabled,
            "metadata_extraction_enabled": config.metadata.extract_on_upload,
            "duplicate_detection_enabled": config.duplicate_detection.enabled,
        },
        "auth": {
            "kavita_enabled": config.kavita.enabled,
            "require_auth": config.auth.require_auth,
        }
    }


# Authentication endpoints
@router.post("/auth/login")
async def login(
    request: Request,
):
    """Login with Kavita credentials.
    
    Expects JSON body with:
    - username: Kavita username
    - password: Kavita password
    
    Returns:
        Session token and user information
    """
    from app.kavita_auth import kavita_auth
    
    if not config.kavita.enabled:
        raise HTTPException(
            status_code=400,
            detail="Kavita authentication is not enabled"
        )
    
    try:
        # Get JSON body
        body = await request.json()
        username = body.get("username")
        password = body.get("password")
        
        if not username or not password:
            raise HTTPException(
                status_code=400,
                detail="Username and password are required"
            )
        
        # Username/password authentication
        user_data = await kavita_auth.authenticate_with_kavita(username, password)
        
        # Create session token
        token = kavita_auth.create_session_token(user_data["username"], user_data)
        
        app_logger.info(
            f"User logged in successfully",
            extra={"username": user_data["username"]}
        )
        
        # Create response with cookie
        response = JSONResponse({
            "success": True,
            "message": "Login successful",
            "user": {
                "username": user_data["username"],
                "email": user_data.get("email"),
                "roles": user_data.get("roles", [])
            }
        })
        
        # Set secure cookie
        # Only use secure=True if we're actually using HTTPS (not just in production)
        # Check if request is HTTPS by looking for X-Forwarded-Proto header (for reverse proxies)
        # or checking the request URL scheme
        is_https = (
            request.url.scheme == "https" or
            request.headers.get("X-Forwarded-Proto") == "https"
        )
        
        max_age = config.auth.token_expiry_hours * 3600
        response.set_cookie(
            key=config.auth.cookie_name,
            value=token,
            max_age=max_age,
            httponly=True,
            secure=is_https,  # Only use secure cookies over HTTPS
            samesite="lax"
        )
        
        app_logger.debug(
            f"Cookie set",
            extra={
                "cookie_name": config.auth.cookie_name,
                "secure": is_https,
                "scheme": request.url.scheme,
                "x_forwarded_proto": request.headers.get("X-Forwarded-Proto"),
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(
            f"Login failed: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/auth/logout")
async def logout():
    """Logout and clear session.
    
    Returns:
        Success message
    """
    response = JSONResponse({
        "success": True,
        "message": "Logged out successfully"
    })
    
    # Clear cookie
    response.delete_cookie(
        key=config.auth.cookie_name,
        httponly=True,
        samesite="lax"
    )
    
    return response


@router.get("/auth/me")
async def get_current_session(
    user: Optional[Dict[str, Any]] = Depends(get_current_user)
):
    """Get current authenticated user session.
    
    Returns:
        Current user information or None if not authenticated
    """
    if not user:
        return {
            "authenticated": False,
            "message": "Not authenticated"
        }
    
    return {
        "authenticated": True,
        "user": {
            "username": user.get("username"),
            "email": user.get("email"),
            "roles": user.get("roles", [])
        }
    }


@router.post("/upload")
@limiter.limit(f"{config.security.rate_limit_uploads_per_minute}/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    db_session: AsyncSession = Depends(get_db_session),
    user: Optional[Dict[str, Any]] = Depends(get_current_user),
):
    """Upload file to quarantine (Step 1).
    
    Debug logging for authentication:
    
    This endpoint implements the complete Step 1 functionality:
    - Validates file size and extension
    - Sanitizes filename
    - Saves to quarantine with UUID name
    - Sets restrictive permissions
    - Records metadata in database
    
    Args:
        request: FastAPI request (for rate limiting)
        file: Uploaded file
        db_session: Database session
        
    Returns:
        Upload status and UUID
    """
    try:
        # Validate file extension
        if not validate_file_extension(file.filename, config.upload.allowed_extensions):
            app_logger.warning(
                f"Rejected file with invalid extension",
                extra={
                    "uploaded_file": file.filename,
                    "ip_address": request.client.host if request.client else "unknown"
                }
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid file type",
                    "message": f"Only {', '.join(config.upload.allowed_extensions)} files are allowed",
                    "allowed_extensions": config.upload.allowed_extensions,
                }
            )
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Validate file size
        if file_size > config.max_file_size_bytes:
            app_logger.warning(
                f"Rejected file exceeding size limit",
                extra={
                    "uploaded_file": file.filename,
                    "file_size": file_size,
                    "max_size": config.max_file_size_bytes,
                    "ip_address": request.client.host if request.client else "unknown"
                }
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "File too large",
                    "message": f"Maximum file size is {config.upload.max_file_size_mb} MB",
                    "file_size": format_file_size(file_size),
                    "max_size": f"{config.upload.max_file_size_mb} MB",
                }
            )
        
        # Validate file is not empty
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Empty file",
                    "message": "Cannot upload empty files",
                }
            )
        
        # Disk protection checks (if enabled)
        if config.disk_protection.enabled:
            from app.disk_monitor import DiskMonitor
            from pathlib import Path
            
            # Check 1: Disk space availability
            quarantine_path = Path(config.quarantine_dir)
            space_ok, space_reason = DiskMonitor.check_disk_space_available(
                quarantine_path,
                file_size
            )
            
            if not space_ok:
                app_logger.error(
                    f"Upload rejected - insufficient disk space",
                    extra={
                        "uploaded_file": file.filename,
                        "file_size": file_size,
                        "reason": space_reason,
                        "ip_address": request.client.host if request.client else "unknown"
                    }
                )
                raise HTTPException(
                    status_code=507,  # Insufficient Storage
                    detail={
                        "error": "Insufficient disk space",
                        "message": space_reason,
                    }
                )
            
            # Check 2: Quarantine size limit
            quarantine_ok, quarantine_reason = await DiskMonitor.check_quarantine_limit(
                db_session,
                file_size
            )
            
            if not quarantine_ok:
                app_logger.warning(
                    f"Upload rejected - quarantine full",
                    extra={
                        "uploaded_file": file.filename,
                        "file_size": file_size,
                        "reason": quarantine_reason,
                        "ip_address": request.client.host if request.client else "unknown"
                    }
                )
                
                # Try auto-cleanup to make space
                if config.disk_protection.auto_cleanup_enabled:
                    app_logger.info("Attempting auto-cleanup to free quarantine space")
                    bytes_freed = await DiskMonitor.cleanup_old_files(
                        db_session,
                        target_bytes_to_free=file_size
                    )
                    
                    if bytes_freed >= file_size:
                        app_logger.info(f"Auto-cleanup freed {bytes_freed:,} bytes, upload can proceed")
                    else:
                        raise HTTPException(
                            status_code=507,
                            detail={
                                "error": "Quarantine full",
                                "message": quarantine_reason,
                            }
                        )
                else:
                    raise HTTPException(
                        status_code=507,
                        detail={
                            "error": "Quarantine full",
                            "message": quarantine_reason,
                        }
                    )
            
            # Check 3: Single upload size limit (additional check)
            max_single_upload = config.disk_protection.max_single_upload_size_mb * 1024 * 1024
            if file_size > max_single_upload:
                app_logger.warning(
                    f"Upload rejected - exceeds single upload limit",
                    extra={
                        "uploaded_file": file.filename,
                        "file_size": file_size,
                        "limit": max_single_upload,
                        "ip_address": request.client.host if request.client else "unknown"
                    }
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "File exceeds disk protection limit",
                        "message": f"Maximum single upload size is {config.disk_protection.max_single_upload_size_mb} MB",
                        "file_size": format_file_size(file_size),
                        "max_size": f"{config.disk_protection.max_single_upload_size_mb} MB",
                    }
                )
        
        # Get username for tracking (if authenticated)
        username = None
        if user:
            username = user.get("username")
        
        # Debug logging for authentication issues
        app_logger.debug(
            f"Upload authentication check",
            extra={
                "kavita_enabled": config.kavita.enabled,
                "require_auth": config.auth.require_auth,
                "user": username,
                "has_user_object": user is not None,
                "cookies": list(request.cookies.keys()),
                "cookie_name": config.auth.cookie_name,
            }
        )
        
        # Check if authentication is required
        if config.kavita.enabled and config.auth.require_auth and not username:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Authentication required",
                    "message": "Please log in to upload files"
                }
            )
        
        # Save to quarantine
        upload = await UploadService.save_to_quarantine(
            file_content=file_content,
            original_filename=file.filename,
            db_session=db_session,
            uploaded_by=username,
        )
        
        app_logger.info(
            f"File uploaded successfully",
            extra={
                "upload_uuid": upload.uuid,
                "uploaded_file": file.filename,
                "file_size": file_size,
                "uploaded_by": username or "anonymous",
                "ip_address": request.client.host if request.client else "unknown"
            }
        )
        
        # Create per-file log
        from app.file_logger import get_file_logger
        file_logger = get_file_logger(upload.uuid, file.filename)
        file_logger.log_phase("upload", "completed", {
            "file_size": file_size,
            "mime_type": upload.mime_type,
            "file_hash": upload.file_hash_sha256
        })
        
        # Auto-trigger scan if enabled (Step 2)
        next_steps = ["File is quarantined"]
        
        if config.scanning.enabled:
            file_logger.log_phase("scan", "queued", {"message": "Automatic scan triggered"})
            
            # Import here to avoid circular imports
            import asyncio
            from app.database import db as database
            
            # Trigger scan asynchronously with its own DB session (don't block upload response)
            async def trigger_scan():
                """Background task with its own DB session."""
                try:
                    async for scan_session in database.get_session():
                        await ScanningService.scan_file_with_logging(
                            upload.uuid,
                            scan_session,
                            file_logger
                        )
                        break  # Only need one session
                except Exception as e:
                    app_logger.error(
                        f"Background scan failed: {str(e)}",
                        exc_info=True,
                        extra={"upload_uuid": upload.uuid}
                    )
                    if file_logger:
                        file_logger.log_error(f"Background scan task failed: {str(e)}", e)
            
            asyncio.create_task(trigger_scan())
            next_steps.append("Virus scanning in progress (VirusTotal)")
        else:
            next_steps.append("Scanning disabled - configure VirusTotal API key")
        
        if config.metadata.extract_on_upload:
            next_steps.append("Metadata extraction")
        
        next_steps.append("Duplicate check and move")
        
        return JSONResponse(
            status_code=201,
            content={
                "success": True,
                "message": "File uploaded and quarantined successfully",
                "upload": {
                    "uuid": upload.uuid,
                    "filename": upload.original_filename,
                    "file_size": upload.file_size,
                    "file_size_formatted": format_file_size(upload.file_size),
                    "mime_type": upload.mime_type,
                    "status": upload.status,
                    "uploaded_at": upload.uploaded_at.isoformat(),
                    "log_file": f"logs/files/{upload.uuid[:8]}.log"
                },
                "next_steps": next_steps,
                "features": {
                    "scanning_enabled": config.scanning.enabled,
                    "metadata_enabled": config.metadata.extract_on_upload,
                    "duplicate_detection_enabled": config.duplicate_detection.enabled,
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(
            f"Upload failed: {str(e)}",
            exc_info=True,
            extra={
                "uploaded_file": file.filename if file else "unknown",
            }
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Upload failed",
                "message": "An error occurred while processing your upload",
            }
        )


@router.get("/upload/{upload_uuid}")
async def get_upload_status(
    upload_uuid: str,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Get upload status by UUID.
    
    Args:
        upload_uuid: Upload UUID
        db_session: Database session
        
    Returns:
        Upload status information
    """
    status = await UploadService.get_upload_status(upload_uuid, db_session)
    
    if not status:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Upload not found",
                "message": f"No upload found with UUID {upload_uuid}",
            }
        )
    
    return {
        "success": True,
        "upload": status,
    }


# Step 2: Scanning endpoints (IMPLEMENTED)
@router.post("/upload/{upload_uuid}/scan")
async def scan_upload(
    upload_uuid: str,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Scan uploaded file for viruses/malware (Step 2 - IMPLEMENTED).
    
    Performs VirusTotal scan with:
    - Hash-based duplicate detection
    - Reuse of previous scan results
    - Complete VirusTotal API v3 integration
    - Automatic status updates
    
    Args:
        upload_uuid: UUID of upload to scan
        db_session: Database session
        
    Returns:
        Scan results
    """
    try:
        result = await ScanningService.scan_file(upload_uuid, db_session)
        
        # Determine success based on result status
        success = result.get("status") not in ["error"]
        
        return {
            "success": success,
            "message": result.get("message", "Scan completed"),
            "result": result,
        }
    except Exception as e:
        app_logger.error(
            f"Scan failed: {str(e)}",
            exc_info=True,
            extra={"upload_uuid": upload_uuid}
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Scan failed",
                "message": str(e)
            }
        )


@router.get("/upload/{upload_uuid}/scan/status")
async def get_scan_status(
    upload_uuid: str,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Get current scan status (Step 2).
    
    Returns detailed scan information including:
    - Scan result (safe/infected/pending)
    - VirusTotal statistics
    - Link to full VirusTotal report
    
    Args:
        upload_uuid: UUID of upload
        db_session: Database session
        
    Returns:
        Scan status and details
    """
    import json
    
    result = await db_session.execute(
        select(Upload).where(Upload.uuid == upload_uuid)
    )
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(
            status_code=404,
            detail={"error": "Upload not found"}
        )
    
    scan_details = None
    if upload.scan_details:
        try:
            scan_details = json.loads(upload.scan_details)
        except:
            pass
    
    return {
        "success": True,
        "scan_status": upload.scan_result,
        "status": upload.status,
        "scanned_at": upload.scanned_at.isoformat() if upload.scanned_at else None,
        "scan_details": scan_details,
    }


# Step 3: Metadata endpoints (STUBS)
@router.get("/upload/{upload_uuid}/metadata")
async def get_metadata(
    upload_uuid: str,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Extract and return metadata from uploaded file (Step 3 - IMPLEMENTED).
    
    Extracts metadata automatically if not already extracted.
    Returns cached metadata if already extracted.
    """
    from app.metadata_extractor import MetadataExtractor
    from app.database import Upload
    from sqlalchemy import select
    import json
    from pathlib import Path
    
    try:
        # Get upload record
        result = await db_session.execute(
            select(Upload).where(Upload.uuid == upload_uuid)
        )
        upload = result.scalar_one_or_none()
        
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        # Check if file is safe to process
        if upload.scan_result not in ["safe", None]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot extract metadata: file status is {upload.status}"
            )
        
        # Return cached metadata if already extracted
        if upload.metadata_json:
            metadata = json.loads(upload.metadata_json)
            validation = MetadataExtractor.validate_metadata(metadata)
            
            return {
                "success": True,
                "message": "Metadata retrieved from cache",
                "metadata": metadata,
                "validation": validation,
                "extracted_at": upload.metadata_extracted_at.isoformat() if upload.metadata_extracted_at else None,
                "edited": upload.metadata_edited
            }
        
        # Extract metadata
        file_path = Path(upload.quarantine_path)
        metadata = MetadataExtractor.extract(file_path, upload.file_extension)
        
        # Add original filename if title is empty
        if not metadata.get("title"):
            metadata["title"] = upload.original_filename
        
        # Save to database
        upload.metadata_json = json.dumps(metadata)
        upload.metadata_extracted_at = datetime.utcnow()
        await db_session.commit()
        
        # Validate metadata
        validation = MetadataExtractor.validate_metadata(metadata)
        
        app_logger.info(
            f"Metadata extracted",
            extra={
                "upload_uuid": upload_uuid,
                "title": metadata.get("title"),
                "author": metadata.get("author")
            }
        )
        
        return {
            "success": True,
            "message": "Metadata extracted successfully",
            "metadata": metadata,
            "validation": validation,
            "extracted_at": upload.metadata_extracted_at.isoformat(),
            "edited": False
        }
    
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(
            f"Metadata extraction failed: {str(e)}",
            exc_info=True,
            extra={"upload_uuid": upload_uuid}
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Metadata extraction failed",
                "message": str(e)
            }
        )


@router.put("/upload/{upload_uuid}/metadata")
async def update_metadata(
    upload_uuid: str,
    metadata: dict,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Update file metadata (Step 3 - IMPLEMENTED).
    
    Allows user to edit extracted metadata before verification.
    """
    from app.metadata_extractor import MetadataExtractor
    from app.database import Upload
    from sqlalchemy import select
    import json
    
    try:
        # Get upload record
        result = await db_session.execute(
            select(Upload).where(Upload.uuid == upload_uuid)
        )
        upload = result.scalar_one_or_none()
        
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")
        
        # Validate incoming metadata
        validation = MetadataExtractor.validate_metadata(metadata)
        
        if not validation["is_valid"] and config.metadata.required_fields:
            return {
                "success": False,
                "message": "Validation failed",
                "validation": validation
            }
        
        # Sanitize metadata (basic XSS protection)
        for key in metadata:
            if isinstance(metadata[key], str):
                # Strip HTML tags and dangerous characters
                import re
                metadata[key] = re.sub(r'<[^>]*>', '', metadata[key])
                metadata[key] = metadata[key].strip()
        
        # Update metadata
        upload.metadata_json = json.dumps(metadata)
        upload.metadata_edited = True
        upload.metadata_verified_at = datetime.utcnow()
        upload.status = "metadata_verified"
        
        await db_session.commit()
        
        app_logger.info(
            f"Metadata updated by user",
            extra={
                "upload_uuid": upload_uuid,
                "title": metadata.get("title"),
                "author": metadata.get("author")
            }
        )
        
        return {
            "success": True,
            "message": "Metadata updated successfully",
            "metadata": metadata,
            "validation": validation,
            "status": upload.status
        }
    
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(
            f"Metadata update failed: {str(e)}",
            exc_info=True,
            extra={"upload_uuid": upload_uuid}
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Metadata update failed",
                "message": str(e)
            }
        )


# Step 2: Duplicate check endpoint (IMPLEMENTED)
@router.post("/upload/{upload_uuid}/check-duplicate")
async def check_duplicate(
    upload_uuid: str,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Check for duplicates by hash (Step 2 - IMPLEMENTED).
    
    Checks if file with same SHA256 hash already exists in:
    - Upload database
    - Library folder (future)
    
    Args:
        upload_uuid: UUID of upload to check
        db_session: Database session
        
    Returns:
        Duplicate status
    """
    from app.duplicate_detection import DuplicateDetector
    
    result = await db_session.execute(
        select(Upload).where(Upload.uuid == upload_uuid)
    )
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(
            status_code=404,
            detail={"error": "Upload not found"}
        )
    
    duplicate_check = await DuplicateDetector.check_duplicate(
        upload.file_hash_sha256,
        upload.file_size,
        db_session
    )
    
    return {
        "success": True,
        "result": duplicate_check,
    }


# Step 2: Preview endpoint (STUB for Step 3)
@router.get("/upload/{upload_uuid}/preview")
async def get_preview(
    upload_uuid: str,
    db_session: AsyncSession = Depends(get_db_session),
    page: int = 0,
    max_pages: int = None,
    width: int = None,
    height: int = None,
):
    """Get file preview (Step 3 full implementation).
    
    Generates preview images from specified pages of PDF/EPUB files.
    
    Args:
        upload_uuid: UUID of upload
        db_session: Database session
        page: Page number to start from (default: 0)
        max_pages: Maximum number of pages (default: from config)
        width: Preview image width (default: from config)
        height: Preview image height (default: from config)
        
    Returns:
        Preview data with base64-encoded images
    """
    from app.preview_generator import PreviewGenerator
    from pathlib import Path
    
    try:
        result = await db_session.execute(
            select(Upload).where(Upload.uuid == upload_uuid)
        )
        upload = result.scalar_one_or_none()
        
        if not upload:
            raise HTTPException(
                status_code=404,
                detail={"error": "Upload not found"}
            )
        
        # Only allow preview for safe files
        if upload.scan_result not in ["safe", "clean", None]:
            raise HTTPException(
                status_code=400,
                detail=f"Preview only available for safe files (current status: {upload.scan_result})"
            )
        
        preview_data = PreviewGenerator.generate_previews(
            Path(upload.quarantine_path),
            upload.file_extension,
            upload_uuid,
            max_pages=max_pages or config.preview.max_pages
        )
        
        if preview_data["status"] == "unsupported":
            raise HTTPException(
                status_code=400,
                detail={"error": preview_data["message"]}
            )
        
        # Update preview_generated status in DB
        if preview_data["status"] == "success" and not upload.preview_generated:
            upload.preview_generated = True
            await db_session.commit()
        
        # Extract base64 data from data URLs for frontend compatibility
        pages = preview_data.get("pages", [])
        base64_previews = []
        for page in pages:
            if isinstance(page, dict) and "data" in page:
                # Extract base64 from data URL: "data:image/png;base64,XXX" -> "XXX"
                data_url = page["data"]
                if "base64," in data_url:
                    base64_previews.append(data_url.split("base64,")[1])
                else:
                    base64_previews.append(data_url)
            elif isinstance(page, str):
                base64_previews.append(page)
        
        return {
            "success": preview_data["status"] == "success",
            "message": preview_data.get("message", "Preview generated"),
            "previews": base64_previews,
            "file_extension": upload.file_extension,
            "status": preview_data["status"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(
            f"Preview generation failed: {str(e)}",
            exc_info=True,
            extra={"upload_uuid": upload_uuid}
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Preview generation failed",
                "message": str(e)
            }
        )


# Step 4: Move endpoints (IMPLEMENTED)
@router.post("/upload/{upload_uuid}/move")
async def move_to_unsorted(
    upload_uuid: str,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Move file from quarantine to unsorted library (Step 4 - IMPLEMENTED).
    
    Performs comprehensive duplicate detection:
    - Checks database for exact hash matches
    - Checks filesystem for exact hash matches
    - Checks for name conflicts (same title/author)
    - Renames or discards based on configuration
    - Verifies integrity after move
    - Logs to manifest CSV
    
    Args:
        upload_uuid: UUID of upload to move
        db_session: Database session
        
    Returns:
        Move result with status and details
    """
    from app.mover_service import MoverService
    
    try:
        result = await MoverService.move_file(upload_uuid, db_session)
        
        app_logger.info(
            f"Move operation completed",
            extra={
                "upload_uuid": upload_uuid,
                "success": result.get("success"),
                "status": result.get("status")
            }
        )
        
        return result
    
    except Exception as e:
        app_logger.error(
            f"Move operation failed: {str(e)}",
            exc_info=True,
            extra={"upload_uuid": upload_uuid}
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Move failed",
                "message": str(e)
            }
        )


@router.get("/upload/{upload_uuid}/move/status")
async def get_move_status(
    upload_uuid: str,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Get current move status for an upload (Step 4 - IMPLEMENTED).
    
    Returns detailed information about whether file has been moved,
    is a duplicate, or is pending move.
    
    Args:
        upload_uuid: UUID of upload
        db_session: Database session
        
    Returns:
        Move status and details
    """
    result = await db_session.execute(
        select(Upload).where(Upload.uuid == upload_uuid)
    )
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(
            status_code=404,
            detail={"error": "Upload not found"}
        )
    
    # Determine if file can be moved
    can_move = upload.status in ["metadata_verified", "safe", "clean"]
    
    response = {
        "success": True,
        "uuid": upload.uuid,
        "status": upload.status,
        "can_move": can_move,
        "is_duplicate": upload.is_duplicate,
        "duplicate_reason": upload.duplicate_reason,
        "moved_at": upload.moved_at.isoformat() if upload.moved_at else None,
        "final_path": upload.final_path,
        "moving_enabled": config.moving.enabled,
        "dry_run_mode": config.moving.dry_run
    }
    
    # Add duplicate information if applicable
    if upload.is_duplicate and upload.duplicate_of:
        result = await db_session.execute(
            select(Upload).where(Upload.uuid == upload.duplicate_of)
        )
        duplicate_upload = result.scalar_one_or_none()
        if duplicate_upload:
            response["duplicate_of"] = {
                "uuid": duplicate_upload.uuid,
                "filename": duplicate_upload.original_filename,
                "moved_at": duplicate_upload.moved_at.isoformat() if duplicate_upload.moved_at else None
            }
    
    return response


# Disk monitoring endpoint
@router.get("/system/disk-status")
async def get_disk_status(
    db_session: AsyncSession = Depends(get_db_session),
):
    """Get disk space and quarantine status for monitoring.
    
    Returns comprehensive disk usage information including:
    - Total disk space and free space
    - Quarantine directory size and limits
    - File counts by status
    - Protection settings
    
    Args:
        db_session: Database session
        
    Returns:
        Disk status information
    """
    if not config.disk_protection.enabled:
        return {
            "success": True,
            "disk_protection_enabled": False,
            "message": "Disk protection is disabled"
        }
    
    try:
        from app.disk_monitor import DiskMonitor
        
        status = await DiskMonitor.get_disk_status(db_session)
        
        # Add warnings if thresholds exceeded
        warnings = []
        
        if status["disk"]["percent_used"] > (100 - config.disk_protection.alert_threshold_percent):
            warnings.append(f"Disk usage above alert threshold ({config.disk_protection.alert_threshold_percent}% free)")
        
        if status["disk"]["percent_used"] > (100 - config.disk_protection.emergency_cleanup_threshold_percent):
            warnings.append(f"CRITICAL: Disk usage above emergency threshold")
        
        if (status["quarantine"]["max_size"] > 0 and 
            status["quarantine"]["percent_used"] > 90):
            warnings.append("Quarantine near capacity limit")
        
        return {
            "success": True,
            "disk_protection_enabled": True,
            "status": status,
            "warnings": warnings,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    except Exception as e:
        app_logger.error(
            f"Failed to get disk status: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve disk status",
                "message": str(e)
            }
        )


@router.post("/system/cleanup")
async def trigger_manual_cleanup(
    db_session: AsyncSession = Depends(get_db_session),
):
    """Manually trigger cleanup of old quarantine files.
    
    Removes files older than the configured age limit.
    Useful for freeing space before it becomes critical.
    
    Args:
        db_session: Database session
        
    Returns:
        Cleanup results
    """
    if not config.disk_protection.enabled:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Disk protection disabled",
                "message": "Disk protection must be enabled to perform cleanup"
            }
        )
    
    try:
        from app.disk_monitor import DiskMonitor
        
        app_logger.info("Manual cleanup triggered")
        
        bytes_freed = await DiskMonitor.cleanup_old_files(db_session)
        
        app_logger.info(
            f"Manual cleanup completed: {bytes_freed:,} bytes freed",
            extra={"bytes_freed": bytes_freed}
        )
        
        return {
            "success": True,
            "bytes_freed": bytes_freed,
            "bytes_freed_formatted": format_file_size(bytes_freed),
            "message": f"Cleanup completed successfully"
        }
    
    except Exception as e:
        app_logger.error(
            f"Manual cleanup failed: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Cleanup failed",
                "message": str(e)
            }
        )

