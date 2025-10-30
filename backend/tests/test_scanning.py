"""Tests for Step 2: Scanning and duplicate detection."""

import pytest
import asyncio
from pathlib import Path
from httpx import AsyncClient
from unittest.mock import Mock, patch, AsyncMock

from app.main import app
from app.database import Upload
from app.virustotal import VirusTotalScanner
from app.duplicate_detection import DuplicateDetector


class TestVirusTotalScanner:
    """Tests for VirusTotal scanner."""
    
    @pytest.mark.asyncio
    async def test_scanner_initialization(self):
        """Test VirusTotal scanner initialization."""
        scanner = VirusTotalScanner(api_key="test_key_123")
        assert scanner.api_key == "test_key_123"
        assert scanner.headers["x-apikey"] == "test_key_123"
    
    @pytest.mark.asyncio
    async def test_check_hash_not_found(self):
        """Test hash check when file not in VirusTotal."""
        scanner = VirusTotalScanner(api_key="test_key")
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            exists, data = await scanner.check_hash("test_hash_123")
            
            assert exists is False
            assert data is None
    
    @pytest.mark.asyncio
    async def test_check_hash_found(self):
        """Test hash check when file exists in VirusTotal."""
        scanner = VirusTotalScanner(api_key="test_key")
        
        mock_data = {
            "data": {
                "attributes": {
                    "stats": {
                        "malicious": 0,
                        "suspicious": 0,
                        "undetected": 70,
                        "harmless": 0
                    }
                }
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_data
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            exists, data = await scanner.check_hash("known_hash")
            
            assert exists is True
            assert data == mock_data
    
    def test_parse_analysis_results_clean(self):
        """Test parsing clean scan results."""
        scanner = VirusTotalScanner()
        
        data = {
            "data": {
                "attributes": {
                    "stats": {
                        "malicious": 0,
                        "suspicious": 0,
                        "undetected": 0,
                        "harmless": 70
                    },
                    "date": 1234567890
                }
            },
            "meta": {
                "file_info": {
                    "sha256": "abc123"
                }
            }
        }
        
        result = scanner.parse_analysis_results(data)
        
        assert result["status"] == "clean"
        assert result["malicious_count"] == 0
        assert result["total_engines"] == 70
        assert result["file_hash"] == "abc123"
    
    def test_parse_analysis_results_malicious(self):
        """Test parsing malicious scan results."""
        scanner = VirusTotalScanner()
        
        data = {
            "data": {
                "attributes": {
                    "stats": {
                        "malicious": 15,
                        "suspicious": 2,
                        "undetected": 50,
                        "harmless": 3
                    },
                    "date": 1234567890
                }
            },
            "meta": {
                "file_info": {
                    "sha256": "infected123"
                }
            }
        }
        
        result = scanner.parse_analysis_results(data)
        
        assert result["status"] == "malicious"
        assert result["malicious_count"] == 15
        assert result["total_engines"] == 70


class TestDuplicateDetection:
    """Tests for duplicate detection."""
    
    @pytest.mark.asyncio
    async def test_check_duplicate_not_found(self, async_client, test_db):
        """Test duplicate check when file is unique."""
        # This would need proper database setup
        # Placeholder for now
        pass
    
    @pytest.mark.asyncio
    async def test_check_duplicate_found(self, async_client, test_db):
        """Test duplicate check when file already exists."""
        # This would need proper database setup
        # Placeholder for now
        pass


class TestScanningEndpoints:
    """Tests for scanning API endpoints."""
    
    @pytest.mark.asyncio
    async def test_scan_endpoint_disabled(self, async_client, sample_epub_file):
        """Test scan endpoint when scanning is disabled."""
        # Upload file first
        filename, content, mime_type = sample_epub_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await async_client.post("/api/upload", files=files)
        uuid = upload_response.json()["upload"]["uuid"]
        
        # Try to scan
        with patch('app.config.config.scanning.enabled', False):
            response = await async_client.post(f"/api/upload/{uuid}/scan")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True  # Request succeeds
            assert "disabled" in data["result"]["status"]
    
    @pytest.mark.asyncio
    async def test_get_scan_status(self, async_client, sample_epub_file):
        """Test getting scan status."""
        # Upload file first
        filename, content, mime_type = sample_epub_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await async_client.post("/api/upload", files=files)
        uuid = upload_response.json()["upload"]["uuid"]
        
        # Get scan status
        response = await async_client.get(f"/api/upload/{uuid}/scan/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "scan_status" in data
    
    @pytest.mark.asyncio
    async def test_check_duplicate_endpoint(self, async_client, sample_epub_file):
        """Test duplicate check endpoint."""
        # Upload file first
        filename, content, mime_type = sample_epub_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await async_client.post("/api/upload", files=files)
        uuid = upload_response.json()["upload"]["uuid"]
        
        # Check for duplicates
        response = await async_client.post(f"/api/upload/{uuid}/check-duplicate")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "result" in data
    
    @pytest.mark.asyncio
    async def test_preview_endpoint(self, async_client, sample_epub_file):
        """Test preview endpoint (stub)."""
        # Upload file first
        filename, content, mime_type = sample_epub_file
        files = {"file": (filename, content, mime_type)}
        upload_response = await async_client.post("/api/upload", files=files)
        uuid = upload_response.json()["upload"]["uuid"]
        
        # Get preview
        response = await async_client.get(f"/api/upload/{uuid}/preview")
        
        assert response.status_code == 200
        data = response.json()
        assert "preview" in data


class TestHashBasedWorkflow:
    """Test complete hash-based workflow."""
    
    @pytest.mark.asyncio
    async def test_duplicate_hash_skips_scan(self):
        """Test that uploading same file twice reuses scan results."""
        # This would test:
        # 1. Upload file A
        # 2. Scan file A
        # 3. Upload file B (same hash as A)
        # 4. Scan file B - should reuse A's results
        # Placeholder for integration test
        pass



