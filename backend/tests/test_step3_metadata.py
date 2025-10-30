"""
Tests for Step 3: Metadata Extraction and Preview Generation
"""
import pytest
import json
from pathlib import Path
from app.metadata_extractor import MetadataExtractor
from app.preview_generator import PreviewGenerator
from app.config import config


class TestMetadataExtractor:
    """Test metadata extraction from various file formats."""
    
    def test_pdf_metadata_extraction(self):
        """Test extracting metadata from a PDF file."""
        # This test requires a sample PDF file
        # Create a dummy test or skip if no test files available
        pass  # Placeholder - requires test PDF file
    
    def test_epub_metadata_extraction(self):
        """Test extracting metadata from an EPUB file."""
        # This test requires a sample EPUB file
        pass  # Placeholder - requires test EPUB file
    
    def test_comic_metadata_extraction(self):
        """Test extracting metadata from CBZ/CBR files."""
        # This test requires a sample comic archive
        pass  # Placeholder - requires test CBZ/CBR file
    
    def test_validate_metadata_valid(self):
        """Test metadata validation with valid data."""
        metadata = {
            "title": "Test Book",
            "author": "Test Author",
            "language": "en",
            "year": "2024"
        }
        
        validation = MetadataExtractor.validate_metadata(metadata)
        
        # Check based on config.metadata.required_fields
        if config.metadata.required_fields:
            all_present = all(metadata.get(field) for field in config.metadata.required_fields)
            assert validation["is_valid"] == all_present
        else:
            assert validation["is_valid"] is True
    
    def test_validate_metadata_missing_required(self):
        """Test metadata validation with missing required fields."""
        metadata = {
            "title": "Test Book",
            # Missing "author" if it's required
        }
        
        validation = MetadataExtractor.validate_metadata(metadata)
        
        # If "author" is in required_fields, validation should fail
        if "author" in config.metadata.required_fields:
            assert validation["is_valid"] is False
            assert "author" in validation["missing_fields"]
    
    def test_validate_metadata_empty(self):
        """Test metadata validation with empty data."""
        metadata = {}
        
        validation = MetadataExtractor.validate_metadata(metadata)
        
        # Should fail if required fields are configured
        if config.metadata.required_fields:
            assert validation["is_valid"] is False
            assert len(validation["missing_fields"]) == len(config.metadata.required_fields)


class TestPreviewGenerator:
    """Test preview generation for PDF and EPUB files."""
    
    @pytest.mark.asyncio
    async def test_preview_generation_disabled(self):
        """Test preview generation when disabled in config."""
        if not config.preview.enabled:
            result = await PreviewGenerator.generate_preview(
                upload_uuid="test-uuid",
                file_path=Path("test.pdf"),
                file_extension="pdf"
            )
            
            assert result["status"] == "disabled"
    
    @pytest.mark.asyncio
    async def test_pdf_preview_generation(self):
        """Test PDF preview generation."""
        # This test requires a sample PDF file
        pass  # Placeholder - requires test PDF file
    
    @pytest.mark.asyncio
    async def test_epub_preview_generation(self):
        """Test EPUB preview generation."""
        # This test requires a sample EPUB file
        pass  # Placeholder - requires test EPUB file
    
    @pytest.mark.asyncio
    async def test_unsupported_format_preview(self):
        """Test preview generation for unsupported format."""
        result = await PreviewGenerator.generate_preview(
            upload_uuid="test-uuid",
            file_path=Path("test.txt"),
            file_extension="txt"
        )
        
        if config.preview.enabled:
            assert result["status"] == "unsupported"
    
    def test_preview_cache_path(self):
        """Test preview cache path generation."""
        cache_path = PreviewGenerator._get_cache_path("test-uuid", page_num=0)
        
        assert "test-uuid" in str(cache_path)
        assert "page_0.png" in str(cache_path)


class TestMetadataAPI:
    """Test metadata API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_metadata_endpoint(self, client):
        """Test GET /api/upload/{uuid}/metadata endpoint."""
        # This test requires a test client and uploaded file
        pass  # Placeholder - requires pytest fixtures
    
    @pytest.mark.asyncio
    async def test_update_metadata_endpoint(self, client):
        """Test PUT /api/upload/{uuid}/metadata endpoint."""
        # This test requires a test client and uploaded file
        pass  # Placeholder - requires pytest fixtures
    
    @pytest.mark.asyncio
    async def test_get_preview_endpoint(self, client):
        """Test GET /api/upload/{uuid}/preview endpoint."""
        # This test requires a test client and uploaded file
        pass  # Placeholder - requires pytest fixtures


class TestMetadataIntegration:
    """Integration tests for the complete metadata workflow."""
    
    @pytest.mark.asyncio
    async def test_full_metadata_workflow(self, client):
        """Test complete workflow: upload → scan → extract → edit → verify."""
        # 1. Upload a file
        # 2. Scan the file (mark as safe)
        # 3. Extract metadata
        # 4. Edit metadata
        # 5. Verify status changes
        pass  # Placeholder - requires full test infrastructure
    
    @pytest.mark.asyncio
    async def test_metadata_persistence(self, client, db_session):
        """Test that metadata changes persist in database."""
        pass  # Placeholder - requires pytest fixtures


# Manual test instructions
"""
MANUAL TESTING INSTRUCTIONS FOR STEP 3:

1. Upload a PDF file:
   curl -X POST http://localhost:5050/api/upload -F "file=@test.pdf"
   
2. Wait for scan to complete (or check status):
   curl http://localhost:5050/api/upload/{UUID}
   
3. Extract metadata:
   curl http://localhost:5050/api/upload/{UUID}/metadata
   
4. Get preview:
   curl http://localhost:5050/api/upload/{UUID}/preview
   
5. Update metadata:
   curl -X PUT http://localhost:5050/api/upload/{UUID}/metadata \
     -H "Content-Type: application/json" \
     -d '{"title": "Updated Title", "author": "Updated Author"}'
   
6. Verify status changed to metadata_verified:
   curl http://localhost:5050/api/upload/{UUID}

Expected Results:
- Metadata extraction returns title, author, and other fields
- Preview returns base64-encoded images (for PDF) or cover/text (for EPUB)
- Metadata update succeeds and changes status to "metadata_verified"
- Preview cache is created in previews/{UUID}/ directory
- Preview cache is cleaned up after 24 hours

Test Files Needed:
- Sample PDF with metadata (title, author, etc.)
- Sample EPUB with metadata
- Sample CBZ with ComicInfo.xml
"""


if __name__ == "__main__":
    print(__doc__)
    print("\nRun tests with: pytest backend/tests/test_step3_metadata.py -v")



