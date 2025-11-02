"""Metadata extraction service for various e-book formats (Step 3)."""

import json
import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.config import config
from app.logger import app_logger

# Conditional imports with fallbacks
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    app_logger.warning("PyMuPDF not installed - PDF metadata extraction limited")

try:
    import ebooklib
    from ebooklib import epub
    HAS_EBOOKLIB = True
except ImportError:
    HAS_EBOOKLIB = False
    app_logger.warning("ebooklib not installed - EPUB metadata extraction unavailable")

try:
    import rarfile
    HAS_RARFILE = True
except ImportError:
    HAS_RARFILE = False
    app_logger.warning("rarfile not installed - CBR extraction unavailable")


class MetadataExtractor:
    """Extract metadata from various e-book formats."""
    
    SUPPORTED_FORMATS = {
        'pdf': ['pdf'],
        'epub': ['epub'],
        'comic': ['cbz', 'cbr'],
        'mobi': ['mobi', 'azw', 'azw3']
    }
    
    @staticmethod
    def extract(file_path: Path, file_extension: str) -> Dict[str, Any]:
        """Extract metadata from file based on extension.
        
        Args:
            file_path: Path to the file
            file_extension: File extension (without dot)
            
        Returns:
            Dictionary with extracted metadata
        """
        extension = file_extension.lower().lstrip('.')
        
        app_logger.info(
            f"Extracting metadata from {extension.upper()} file",
            extra={"file_path": str(file_path), "extension": extension}
        )
        
        try:
            if extension == 'pdf':
                return MetadataExtractor._extract_pdf(file_path)
            elif extension == 'epub':
                return MetadataExtractor._extract_epub(file_path)
            elif extension in ['cbz', 'cbr']:
                return MetadataExtractor._extract_comic(file_path, extension)
            elif extension in ['mobi', 'azw', 'azw3']:
                return MetadataExtractor._extract_mobi(file_path)
            else:
                app_logger.warning(f"Unsupported format for metadata extraction: {extension}")
                return MetadataExtractor._default_metadata()
                
        except Exception as e:
            app_logger.error(
                f"Metadata extraction failed: {str(e)}",
                exc_info=True,
                extra={"file_path": str(file_path)}
            )
            return MetadataExtractor._default_metadata(error=str(e))
    
    @staticmethod
    def _extract_pdf(file_path: Path) -> Dict[str, Any]:
        """Extract metadata from PDF using PyMuPDF."""
        if not HAS_PYMUPDF:
            return MetadataExtractor._default_metadata(error="PyMuPDF not available")
        
        try:
            doc = fitz.open(file_path)
            metadata = doc.metadata or {}
            
            # Extract standard PDF metadata
            result = {
                "title": metadata.get("title", "") or file_path.stem,
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "keywords": metadata.get("keywords", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "created_date": metadata.get("creationDate", ""),
                "modified_date": metadata.get("modDate", ""),
                "language": "",
                "publisher": "",
                "series": "",
                "volume": "",
                "year": "",
                "pages": doc.page_count,
                "format": "PDF",
                "extraction_method": "PyMuPDF"
            }
            
            # Try to extract year from date
            if result["created_date"]:
                try:
                    # PDF dates are in format: D:YYYYMMDDHHmmSS
                    date_str = result["created_date"].replace("D:", "")[:4]
                    if date_str.isdigit():
                        result["year"] = date_str
                except:
                    pass
            
            doc.close()
            
            app_logger.info(
                f"PDF metadata extracted: {result['title']} by {result['author']}",
                extra={"pages": result["pages"]}
            )
            
            return result
            
        except Exception as e:
            app_logger.error(f"PDF metadata extraction error: {str(e)}", exc_info=True)
            return MetadataExtractor._default_metadata(error=str(e))
    
    @staticmethod
    def _extract_epub(file_path: Path) -> Dict[str, Any]:
        """Extract metadata from EPUB."""
        if not HAS_EBOOKLIB:
            return MetadataExtractor._default_metadata(error="ebooklib not available")
        
        try:
            book = epub.read_epub(file_path)
            
            # Extract Dublin Core metadata
            title = book.get_metadata('DC', 'title')
            author = book.get_metadata('DC', 'creator')
            language = book.get_metadata('DC', 'language')
            publisher = book.get_metadata('DC', 'publisher')
            date = book.get_metadata('DC', 'date')
            subject = book.get_metadata('DC', 'subject')
            
            result = {
                "title": title[0][0] if title else file_path.stem,
                "author": author[0][0] if author else "",
                "language": language[0][0] if language else "",
                "publisher": publisher[0][0] if publisher else "",
                "subject": subject[0][0] if subject else "",
                "year": date[0][0][:4] if date and len(date[0][0]) >= 4 else "",
                "series": "",
                "volume": "",
                "pages": len(list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))),
                "format": "EPUB",
                "extraction_method": "ebooklib"
            }
            
            app_logger.info(
                f"EPUB metadata extracted: {result['title']} by {result['author']}",
                extra={"pages": result["pages"]}
            )
            
            return result
            
        except Exception as e:
            app_logger.error(f"EPUB metadata extraction error: {str(e)}", exc_info=True)
            return MetadataExtractor._default_metadata(error=str(e))
    
    @staticmethod
    def _extract_comic(file_path: Path, extension: str) -> Dict[str, Any]:
        """Extract metadata from CBZ/CBR using ComicInfo.xml if present."""
        try:
            comic_info = None
            
            if extension == 'cbz':
                # CBZ is a ZIP file
                with zipfile.ZipFile(file_path, 'r') as z:
                    if 'ComicInfo.xml' in z.namelist():
                        with z.open('ComicInfo.xml') as f:
                            comic_info = f.read()
                    image_count = len([n for n in z.namelist() if n.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
            
            elif extension == 'cbr' and HAS_RARFILE:
                # CBR is a RAR file
                with rarfile.RarFile(file_path, 'r') as r:
                    if 'ComicInfo.xml' in r.namelist():
                        comic_info = r.read('ComicInfo.xml')
                    image_count = len([n for n in r.namelist() if n.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))])
            else:
                image_count = 0
            
            result = {
                "title": file_path.stem,
                "author": "",
                "series": "",
                "volume": "",
                "publisher": "",
                "year": "",
                "language": "",
                "pages": image_count,
                "format": extension.upper(),
                "extraction_method": "archive"
            }
            
            # Parse ComicInfo.xml if found
            if comic_info:
                try:
                    root = ET.fromstring(comic_info)
                    result["title"] = root.findtext('Title', result["title"])
                    result["series"] = root.findtext('Series', '')
                    result["volume"] = root.findtext('Volume', '')
                    result["author"] = root.findtext('Writer', '')
                    result["publisher"] = root.findtext('Publisher', '')
                    result["year"] = root.findtext('Year', '')
                    result["pages"] = int(root.findtext('PageCount', image_count))
                    result["extraction_method"] = "ComicInfo.xml"
                except Exception as e:
                    app_logger.warning(f"Failed to parse ComicInfo.xml: {e}")
            
            app_logger.info(
                f"Comic metadata extracted: {result['title']}",
                extra={"format": extension.upper(), "pages": result["pages"]}
            )
            
            return result
            
        except Exception as e:
            app_logger.error(f"Comic metadata extraction error: {str(e)}", exc_info=True)
            return MetadataExtractor._default_metadata(error=str(e))
    
    @staticmethod
    def _extract_mobi(file_path: Path) -> Dict[str, Any]:
        """Extract metadata from MOBI/AZW files (limited support)."""
        # MOBI/AZW metadata extraction is complex and requires specialized libraries
        # For now, return basic metadata with filename
        app_logger.warning("MOBI/AZW metadata extraction not fully implemented")
        
        return {
            "title": file_path.stem,
            "author": "",
            "language": "",
            "publisher": "",
            "series": "",
            "volume": "",
            "year": "",
            "pages": 0,
            "format": "MOBI/AZW",
            "extraction_method": "filename",
            "note": "MOBI metadata extraction requires additional libraries"
        }
    
    @staticmethod
    def _default_metadata(error: Optional[str] = None) -> Dict[str, Any]:
        """Return default/empty metadata structure."""
        metadata = {
            "title": "",
            "author": "",
            "language": "",
            "publisher": "",
            "series": "",
            "volume": "",
            "year": "",
            "pages": 0,
            "format": "Unknown",
            "extraction_method": "none",
            "extracted_at": datetime.utcnow().isoformat() + "Z"
        }
        
        if error:
            metadata["extraction_error"] = error
        
        return metadata
    
    @staticmethod
    def validate_metadata(metadata: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate metadata against required fields from config.
        
        Returns:
            Dictionary with 'errors' and 'warnings' lists
        """
        errors = []
        warnings = []
        
        required_fields = config.metadata.required_fields
        
        for field in required_fields:
            if not metadata.get(field):
                errors.append(f"Required field '{field}' is missing or empty")
        
        # Validate year format if present
        if metadata.get('year'):
            try:
                year = int(metadata['year'])
                if year < 1000 or year > datetime.now().year + 1:
                    warnings.append(f"Year {year} seems invalid")
            except ValueError:
                warnings.append(f"Year '{metadata['year']}' is not a valid number")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "is_valid": len(errors) == 0
        }





