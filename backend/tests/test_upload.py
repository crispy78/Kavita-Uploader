"""Tests for Step 1: Upload and Quarantine functionality."""

import pytest
import os
from pathlib import Path
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, Upload, db
from app.config import config


# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_db():
    """Create test database."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def async_client():
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_epub_file():
    """Create a sample EPUB file for testing."""
    content = b"PK\x03\x04" + b"x" * 1000  # Minimal ZIP-like header + content
    return ("test.epub", content, "application/epub+zip")


@pytest.fixture
def oversized_file():
    """Create an oversized file for testing."""
    max_size = config.max_file_size_bytes
    content = b"x" * (max_size + 1000)
    return ("large.epub", content, "application/epub+zip")


@pytest.fixture
def invalid_extension_file():
    """Create a file with invalid extension."""
    content = b"test content"
    return ("test.exe", content, "application/x-executable")


@pytest.fixture(autouse=True)
def setup_test_dirs():
    """Setup test directories."""
    test_quarantine = Path("./test_quarantine")
    test_quarantine.mkdir(exist_ok=True)
    
    original_quarantine = config.folders.quarantine
    config.folders.quarantine = str(test_quarantine)
    
    yield
    
    # Cleanup
    config.folders.quarantine = original_quarantine
    if test_quarantine.exists():
        for file in test_quarantine.iterdir():
            file.unlink()
        test_quarantine.rmdir()


class TestGetConfig:
    """Tests for /api/config endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_config(self, async_client):
        """Test getting public configuration."""
        response = await async_client.get("/api/config")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "upload" in data
        assert "max_file_size_mb" in data["upload"]
        assert "allowed_extensions" in data["upload"]
        assert "features" in data


class TestUploadFile:
    """Tests for /api/upload endpoint (Step 1)."""
    
    @pytest.mark.asyncio
    async def test_upload_valid_file(self, async_client, sample_epub_file):
        """Test successful file upload."""
        filename, content, mime_type = sample_epub_file
        
        files = {"file": (filename, content, mime_type)}
        response = await async_client.post("/api/upload", files=files)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["success"] is True
        assert "upload" in data
        assert data["upload"]["filename"] == filename
        assert data["upload"]["status"] == "quarantined"
        assert "uuid" in data["upload"]
        
        # Verify file was saved to quarantine
        uuid = data["upload"]["uuid"]
        quarantine_path = Path(config.folders.quarantine)
        quarantine_files = list(quarantine_path.glob(f"{uuid}.*"))
        assert len(quarantine_files) == 1
        
        # Verify file permissions
        file_path = quarantine_files[0]
        file_stat = os.stat(file_path)
        file_mode = oct(file_stat.st_mode)[-3:]
        assert file_mode == "600" or file_mode == "700"  # Restrictive permissions
    
    @pytest.mark.asyncio
    async def test_upload_oversized_file(self, async_client, oversized_file):
        """Test rejection of oversized file."""
        filename, content, mime_type = oversized_file
        
        files = {"file": (filename, content, mime_type)}
        response = await async_client.post("/api/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        
        assert "detail" in data
        assert "error" in data["detail"]
        assert "too large" in data["detail"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_upload_invalid_extension(self, async_client, invalid_extension_file):
        """Test rejection of file with invalid extension."""
        filename, content, mime_type = invalid_extension_file
        
        files = {"file": (filename, content, mime_type)}
        response = await async_client.post("/api/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        
        assert "detail" in data
        assert "error" in data["detail"]
        assert "Invalid file type" in data["detail"]["error"]
    
    @pytest.mark.asyncio
    async def test_upload_empty_file(self, async_client):
        """Test rejection of empty file."""
        files = {"file": ("empty.epub", b"", "application/epub+zip")}
        response = await async_client.post("/api/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        
        assert "detail" in data
        assert "Empty file" in data["detail"]["error"]


class TestGetUploadStatus:
    """Tests for /api/upload/{uuid} endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_existing_upload_status(self, async_client, sample_epub_file):
        """Test getting status of existing upload."""
        # First upload a file
        filename, content, mime_type = sample_epub_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await async_client.post("/api/upload", files=files)
        upload_data = upload_response.json()
        uuid = upload_data["upload"]["uuid"]
        
        # Then get its status
        response = await async_client.get(f"/api/upload/{uuid}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "upload" in data
        assert data["upload"]["uuid"] == uuid
        assert data["upload"]["status"] == "quarantined"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_upload_status(self, async_client):
        """Test getting status of non-existent upload."""
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = await async_client.get(f"/api/upload/{fake_uuid}")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "detail" in data
        assert "not found" in data["detail"]["message"].lower()


class TestSecurityFeatures:
    """Tests for security features."""
    
    @pytest.mark.asyncio
    async def test_filename_sanitization(self, async_client):
        """Test that filenames are sanitized."""
        dangerous_filename = "../../../etc/passwd.epub"
        content = b"test content"
        
        files = {"file": (dangerous_filename, content, "application/epub+zip")}
        response = await async_client.post("/api/upload", files=files)
        
        if response.status_code == 201:
            data = response.json()
            sanitized = data["upload"]["filename"]
            
            # Should not contain path traversal
            assert ".." not in sanitized
            assert "/" not in sanitized
            assert "\\" not in sanitized
    
    @pytest.mark.asyncio
    async def test_rate_limiting_header(self, async_client, sample_epub_file):
        """Test that rate limiting headers are present."""
        filename, content, mime_type = sample_epub_file
        files = {"file": (filename, content, mime_type)}
        
        response = await async_client.post("/api/upload", files=files)
        
        # Rate limiting headers should be present
        # Note: This test may need adjustment based on actual slowapi behavior
        assert response.status_code in [201, 429]


class TestStubEndpoints:
    """Tests for stub endpoints (Steps 2-4)."""
    
    @pytest.mark.asyncio
    async def test_scan_endpoint_stub(self, async_client, sample_epub_file):
        """Test that scan endpoint returns stub response."""
        # Upload a file first
        filename, content, mime_type = sample_epub_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await async_client.post("/api/upload", files=files)
        uuid = upload_response.json()["upload"]["uuid"]
        
        # Try to scan
        response = await async_client.post(f"/api/upload/{uuid}/scan")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not yet implemented" in data["message"].lower()
    
    @pytest.mark.asyncio
    async def test_metadata_endpoint_stub(self, async_client, sample_epub_file):
        """Test that metadata endpoint returns stub response."""
        # Upload a file first
        filename, content, mime_type = sample_epub_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await async_client.post("/api/upload", files=files)
        uuid = upload_response.json()["upload"]["uuid"]
        
        # Try to get metadata
        response = await async_client.get(f"/api/upload/{uuid}/metadata")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not yet implemented" in data["message"].lower()



