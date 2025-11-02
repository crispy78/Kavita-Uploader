"""Tests for Step 4: File Moving and Duplicate Detection."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import json
import csv

from app.mover_service import MoverService
from app.database import Upload
from app.config import config


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for testing."""
    quarantine = tmp_path / "quarantine"
    unsorted = tmp_path / "unsorted"
    library = tmp_path / "library"
    logs = tmp_path / "logs"
    
    quarantine.mkdir()
    unsorted.mkdir()
    library.mkdir()
    logs.mkdir()
    
    # Override config for testing
    original_unsorted = config.moving.unsorted_dir
    original_library_dirs = config.moving.kavita_library_dirs
    original_manifest = config.moving.manifest_path
    
    config.moving.unsorted_dir = str(unsorted)
    config.moving.kavita_library_dirs = [str(library)]
    config.moving.manifest_path = str(logs / "manifest.csv")
    
    yield {
        "quarantine": quarantine,
        "unsorted": unsorted,
        "library": library,
        "logs": logs
    }
    
    # Restore config
    config.moving.unsorted_dir = original_unsorted
    config.moving.kavita_library_dirs = original_library_dirs
    config.moving.manifest_path = original_manifest


@pytest.fixture
def test_file(temp_dirs):
    """Create a test file in quarantine."""
    file_path = temp_dirs["quarantine"] / "test_file.pdf"
    file_content = b"This is a test PDF file for duplicate detection."
    file_path.write_bytes(file_content)
    return file_path


@pytest.fixture
async def upload_record(test_file, db_session):
    """Create a test upload record."""
    upload = Upload(
        uuid="test-uuid-123",
        original_filename="test_book.pdf",
        sanitized_filename="test_book.pdf",
        file_size=len(test_file.read_bytes()),
        mime_type="application/pdf",
        file_extension=".pdf",
        status="metadata_verified",
        quarantine_path=str(test_file),
        file_hash_sha256=await MoverService.compute_file_hash(test_file),
        metadata_json=json.dumps({
            "title": "Test Book",
            "author": "Test Author",
            "year": 2024
        })
    )
    
    db_session.add(upload)
    await db_session.commit()
    await db_session.refresh(upload)
    
    return upload


@pytest.mark.asyncio
async def test_compute_file_hash(test_file):
    """Test file hash computation."""
    hash1 = await MoverService.compute_file_hash(test_file)
    hash2 = await MoverService.compute_file_hash(test_file)
    
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 produces 64 hex characters
    assert hash1.isalnum()


@pytest.mark.asyncio
async def test_move_unique_file(upload_record, temp_dirs, db_session):
    """Test moving a unique file (no duplicates)."""
    result = await MoverService.move_file(upload_record.uuid, db_session)
    
    assert result["success"] is True
    assert result["status"] == "moved"
    assert "destination" in result
    
    # Verify file was moved
    dest_path = Path(result["destination"])
    assert dest_path.exists()
    assert dest_path.parent == temp_dirs["unsorted"]
    
    # Verify database was updated
    await db_session.refresh(upload_record)
    assert upload_record.status == "moved"
    assert upload_record.final_path == str(dest_path)
    assert upload_record.moved_at is not None


@pytest.mark.asyncio
async def test_duplicate_hash_in_database(upload_record, test_file, temp_dirs, db_session):
    """Test duplicate detection when hash exists in database."""
    # Create an existing upload with same hash
    existing_upload = Upload(
        uuid="existing-uuid",
        original_filename="existing_book.pdf",
        sanitized_filename="existing_book.pdf",
        file_size=upload_record.file_size,
        mime_type="application/pdf",
        file_extension=".pdf",
        status="moved",
        quarantine_path="/old/path",
        file_hash_sha256=upload_record.file_hash_sha256,
        final_path=str(temp_dirs["unsorted"] / "existing_book.pdf")
    )
    
    db_session.add(existing_upload)
    await db_session.commit()
    
    # Try to move the duplicate
    result = await MoverService.move_file(upload_record.uuid, db_session)
    
    assert result["success"] is False
    assert result["status"] == "duplicate_discarded"
    assert result["duplicate_reason"] == "exact_hash_match_database"
    assert result["duplicate_of"] == existing_upload.uuid
    
    # Verify database was updated
    await db_session.refresh(upload_record)
    assert upload_record.status == "duplicate_discarded"
    assert upload_record.is_duplicate is True
    assert upload_record.duplicate_of == existing_upload.uuid


@pytest.mark.asyncio
async def test_duplicate_hash_in_filesystem(upload_record, test_file, temp_dirs, db_session):
    """Test duplicate detection when hash exists in filesystem."""
    # Copy file to library with same content
    library_file = temp_dirs["library"] / "existing_book.pdf"
    shutil.copy2(test_file, library_file)
    
    # Try to move the file
    result = await MoverService.move_file(upload_record.uuid, db_session)
    
    assert result["success"] is False
    assert result["status"] == "duplicate_discarded"
    assert result["duplicate_reason"] == "exact_hash_match_filesystem"
    assert str(library_file) in result["duplicate_path"]
    
    # Verify database was updated
    await db_session.refresh(upload_record)
    assert upload_record.status == "duplicate_discarded"
    assert upload_record.is_duplicate is True


@pytest.mark.asyncio
async def test_name_conflict_with_rename(upload_record, temp_dirs, db_session):
    """Test name conflict with automatic renaming."""
    # Create an existing upload with same title/author but different hash
    different_metadata = json.dumps({
        "title": "Test Book",  # Same title
        "author": "Test Author",  # Same author
        "year": 2023  # Different year (different content)
    })
    
    existing_upload = Upload(
        uuid="existing-uuid",
        original_filename="test_book.pdf",
        sanitized_filename="test_book.pdf",
        file_size=1000,
        mime_type="application/pdf",
        file_extension=".pdf",
        status="moved",
        quarantine_path="/old/path",
        file_hash_sha256="different_hash_123456789",
        metadata_json=different_metadata,
        final_path=str(temp_dirs["unsorted"] / "test_book.pdf")
    )
    
    db_session.add(existing_upload)
    await db_session.commit()
    
    # Enable renaming
    original_rename = config.moving.rename_on_name_conflict
    config.moving.rename_on_name_conflict = True
    
    try:
        result = await MoverService.move_file(upload_record.uuid, db_session)
        
        assert result["success"] is True
        assert result["status"] == "moved"
        assert result["renamed"] is True
        
        # Verify filename was changed
        dest_path = Path(result["destination"])
        assert dest_path.exists()
        assert "duplicate_" in dest_path.name
        assert "Test Book" in dest_path.name
        assert "Test Author" in dest_path.name
    finally:
        config.moving.rename_on_name_conflict = original_rename


@pytest.mark.asyncio
async def test_name_conflict_without_rename(upload_record, temp_dirs, db_session):
    """Test name conflict with renaming disabled (should discard)."""
    # Create an existing upload with same title/author
    different_metadata = json.dumps({
        "title": "Test Book",
        "author": "Test Author",
        "year": 2023
    })
    
    existing_upload = Upload(
        uuid="existing-uuid",
        original_filename="test_book.pdf",
        sanitized_filename="test_book.pdf",
        file_size=1000,
        mime_type="application/pdf",
        file_extension=".pdf",
        status="moved",
        quarantine_path="/old/path",
        file_hash_sha256="different_hash_123456789",
        metadata_json=different_metadata
    )
    
    db_session.add(existing_upload)
    await db_session.commit()
    
    # Disable renaming
    original_rename = config.moving.rename_on_name_conflict
    config.moving.rename_on_name_conflict = False
    
    try:
        result = await MoverService.move_file(upload_record.uuid, db_session)
        
        assert result["success"] is False
        assert result["status"] == "duplicate_discarded"
        assert result["duplicate_reason"] == "name_conflict_rename_disabled"
    finally:
        config.moving.rename_on_name_conflict = original_rename


@pytest.mark.asyncio
async def test_integrity_verification(upload_record, test_file, temp_dirs, db_session):
    """Test integrity verification after move."""
    # Enable integrity verification
    original_verify = config.moving.verify_integrity_post_move
    config.moving.verify_integrity_post_move = True
    
    try:
        result = await MoverService.move_file(upload_record.uuid, db_session)
        
        assert result["success"] is True
        assert result["status"] == "moved"
        
        # Verify file integrity
        dest_path = Path(result["destination"])
        is_valid, actual_hash = await MoverService.verify_integrity(
            dest_path,
            upload_record.file_hash_sha256
        )
        
        assert is_valid is True
        assert actual_hash == upload_record.file_hash_sha256
    finally:
        config.moving.verify_integrity_post_move = original_verify


@pytest.mark.asyncio
async def test_dry_run_mode(upload_record, test_file, temp_dirs, db_session):
    """Test dry run mode (no actual move)."""
    # Enable dry run
    original_dry_run = config.moving.dry_run
    config.moving.dry_run = True
    
    try:
        result = await MoverService.move_file(upload_record.uuid, db_session)
        
        assert result["success"] is True
        assert result["status"] == "dry_run"
        assert "destination" in result
        
        # Verify file was NOT moved
        dest_path = Path(result["destination"])
        assert not dest_path.exists()
        
        # Verify source still exists
        assert test_file.exists()
        
        # Verify database was NOT updated
        await db_session.refresh(upload_record)
        assert upload_record.status == "metadata_verified"
        assert upload_record.moved_at is None
    finally:
        config.moving.dry_run = original_dry_run


@pytest.mark.asyncio
async def test_checksum_manifest(upload_record, temp_dirs, db_session):
    """Test that move is logged to checksum manifest."""
    # Enable manifest
    original_manifest = config.moving.checksum_manifest
    config.moving.checksum_manifest = True
    
    try:
        result = await MoverService.move_file(upload_record.uuid, db_session)
        
        assert result["success"] is True
        
        # Verify manifest was created
        manifest_path = Path(config.moving.manifest_path)
        assert manifest_path.exists()
        
        # Read manifest
        with open(manifest_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Verify entry exists
        assert len(rows) > 0
        last_row = rows[-1]
        assert last_row["uuid"] == upload_record.uuid
        assert last_row["original_filename"] == upload_record.original_filename
        assert last_row["file_hash"] == upload_record.file_hash_sha256
        assert last_row["action"] in ["moved", "renamed"]
    finally:
        config.moving.checksum_manifest = original_manifest


@pytest.mark.asyncio
async def test_move_invalid_status(upload_record, db_session):
    """Test that move fails if file is not in correct status."""
    upload_record.status = "quarantined"
    await db_session.commit()
    
    result = await MoverService.move_file(upload_record.uuid, db_session)
    
    assert result["success"] is False
    assert result["status"] == "invalid_state"


@pytest.mark.asyncio
async def test_move_missing_file(upload_record, db_session):
    """Test that move fails if source file is missing."""
    # Delete the source file
    Path(upload_record.quarantine_path).unlink()
    
    result = await MoverService.move_file(upload_record.uuid, db_session)
    
    assert result["success"] is False
    assert result["status"] == "source_missing"


@pytest.mark.asyncio
async def test_move_disabled(upload_record, db_session):
    """Test that move fails if moving is disabled in config."""
    original_enabled = config.moving.enabled
    config.moving.enabled = False
    
    try:
        result = await MoverService.move_file(upload_record.uuid, db_session)
        
        assert result["success"] is False
        assert result["status"] == "disabled"
    finally:
        config.moving.enabled = original_enabled


def test_generate_renamed_filename():
    """Test filename generation for duplicates."""
    metadata = {
        "title": "Test Book: A Story",
        "author": "Test Author",
        "year": 2024
    }
    
    timestamp = datetime(2024, 1, 15, 10, 30, 45)
    filename = MoverService.generate_renamed_filename(metadata, ".pdf", timestamp)
    
    assert "Test Book" in filename
    assert "Test Author" in filename
    assert "20240115_103045" in filename
    assert filename.endswith(".pdf")
    
    # Test that invalid characters are removed
    metadata_with_invalid = {
        "title": "Test<>:Book/\\|?*",
        "author": "Author\"Name",
        "year": 2024
    }
    
    filename = MoverService.generate_renamed_filename(metadata_with_invalid, ".epub", timestamp)
    
    # Should not contain invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        assert char not in filename



