"""Preview generation service for PDF and EPUB files (Step 3)."""

import base64
import io
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

from app.config import config
from app.logger import app_logger

# Conditional imports
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    app_logger.warning("PyMuPDF not installed - PDF preview generation unavailable")

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    app_logger.warning("Pillow not installed - Image processing unavailable")

try:
    import ebooklib
    from ebooklib import epub
    HAS_EBOOKLIB = True
except ImportError:
    HAS_EBOOKLIB = False


class PreviewGenerator:
    """Generate preview images for various file formats."""
    
    # Preview image dimensions from config
    DEFAULT_WIDTH = 1024
    DEFAULT_HEIGHT = 768
    THUMBNAIL_WIDTH = 300
    THUMBNAIL_HEIGHT = 400
    
    @staticmethod
    def generate_previews(
        file_path: Path,
        file_extension: str,
        upload_uuid: str,
        max_pages: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate preview images for a file.
        
        Args:
            file_path: Path to the file
            file_extension: File extension
            upload_uuid: UUID of the upload
            max_pages: Maximum pages to generate (from config if None)
            
        Returns:
            Dictionary with preview data
        """
        if not config.preview.enabled:
            return {
                "status": "disabled",
                "message": "Preview generation is disabled"
            }
        
        max_pages = max_pages or config.preview.max_pages
        extension = file_extension.lower().lstrip('.')
        
        app_logger.info(
            f"Generating previews for {extension.upper()} file",
            extra={
                "file_path": str(file_path),
                "max_pages": max_pages,
                "upload_uuid": upload_uuid
            }
        )
        
        try:
            if extension == 'pdf':
                return PreviewGenerator._generate_pdf_previews(
                    file_path, upload_uuid, max_pages
                )
            elif extension == 'epub':
                return PreviewGenerator._generate_epub_previews(
                    file_path, upload_uuid, max_pages
                )
            elif extension in ['cbz', 'cbr']:
                return PreviewGenerator._generate_comic_previews(
                    file_path, upload_uuid, max_pages
                )
            else:
                return {
                    "status": "unsupported",
                    "message": f"Preview not supported for {extension} files",
                    "pages": []
                }
        
        except Exception as e:
            app_logger.error(
                f"Preview generation failed: {str(e)}",
                exc_info=True,
                extra={"file_path": str(file_path)}
            )
            return {
                "status": "error",
                "message": str(e),
                "pages": []
            }
    
    @staticmethod
    def _generate_pdf_previews(
        file_path: Path,
        upload_uuid: str,
        max_pages: int
    ) -> Dict[str, Any]:
        """Generate previews from PDF pages."""
        if not HAS_PYMUPDF or not HAS_PIL:
            return {
                "status": "error",
                "message": "PyMuPDF or Pillow not available",
                "pages": []
            }
        
        try:
            doc = fitz.open(file_path)
            total_pages = len(doc)
            pages_to_render = min(max_pages, total_pages)
            
            previews = []
            preview_dir = Path("previews") / upload_uuid
            preview_dir.mkdir(parents=True, exist_ok=True)
            
            for page_num in range(pages_to_render):
                page = doc[page_num]
                
                # Render page to image
                mat = fitz.Matrix(2, 2)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Resize to standard preview size
                img.thumbnail(
                    (PreviewGenerator.DEFAULT_WIDTH, PreviewGenerator.DEFAULT_HEIGHT),
                    Image.Resampling.LANCZOS
                )
                
                # Save as PNG
                preview_path = preview_dir / f"page_{page_num + 1}.png"
                img.save(preview_path, "PNG", optimize=True)
                
                # Convert to base64 if configured
                if config.preview.preview_format == "base64":
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG")
                    buffer.seek(0)
                    base64_data = base64.b64encode(buffer.read()).decode('utf-8')
                    preview_data = f"data:image/png;base64,{base64_data}"
                else:
                    preview_data = str(preview_path)
                
                previews.append({
                    "page": page_num + 1,
                    "path": str(preview_path),
                    "data": preview_data if config.preview.preview_format == "base64" else None,
                    "width": img.width,
                    "height": img.height
                })
            
            doc.close()
            
            # Set restrictive permissions
            os.chmod(preview_dir, 0o700)
            for preview in previews:
                os.chmod(preview["path"], 0o600)
            
            app_logger.info(
                f"Generated {len(previews)} PDF preview(s)",
                extra={"upload_uuid": upload_uuid, "total_pages": total_pages}
            )
            
            return {
                "status": "success",
                "message": f"Generated {len(previews)} preview(s)",
                "total_pages": total_pages,
                "previewed_pages": len(previews),
                "pages": previews,
                "preview_dir": str(preview_dir)
            }
        
        except Exception as e:
            app_logger.error(f"PDF preview generation error: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "pages": []
            }
    
    @staticmethod
    def _generate_epub_previews(
        file_path: Path,
        upload_uuid: str,
        max_pages: int
    ) -> Dict[str, Any]:
        """Generate previews from EPUB (cover + first pages)."""
        if not HAS_EBOOKLIB or not HAS_PIL:
            return {
                "status": "error",
                "message": "ebooklib or Pillow not available",
                "pages": []
            }
        
        try:
            book = epub.read_epub(file_path)
            previews = []
            preview_dir = Path("previews") / upload_uuid
            preview_dir.mkdir(parents=True, exist_ok=True)
            
            # Try to extract cover image
            cover_image = None
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_COVER:
                    cover_image = item.get_content()
                    break
            
            if cover_image:
                try:
                    img = Image.open(io.BytesIO(cover_image))
                    img.thumbnail(
                        (PreviewGenerator.THUMBNAIL_WIDTH, PreviewGenerator.THUMBNAIL_HEIGHT),
                        Image.Resampling.LANCZOS
                    )
                    
                    preview_path = preview_dir / "cover.png"
                    img.save(preview_path, "PNG", optimize=True)
                    
                    if config.preview.preview_format == "base64":
                        buffer = io.BytesIO()
                        img.save(buffer, format="PNG")
                        buffer.seek(0)
                        base64_data = base64.b64encode(buffer.read()).decode('utf-8')
                        preview_data = f"data:image/png;base64,{base64_data}"
                    else:
                        preview_data = str(preview_path)
                    
                    previews.append({
                        "page": 0,
                        "type": "cover",
                        "path": str(preview_path),
                        "data": preview_data if config.preview.preview_format == "base64" else None,
                        "width": img.width,
                        "height": img.height
                    })
                except Exception as e:
                    app_logger.warning(f"Failed to process EPUB cover: {e}")
            
            # Extract text snippets from first chapters
            documents = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
            text_previews = []
            
            for idx, item in enumerate(documents[:max_pages]):
                try:
                    content = item.get_content().decode('utf-8', errors='ignore')
                    # Strip HTML tags (basic)
                    import re
                    text = re.sub('<[^<]+?>', '', content)
                    text = text.strip()[:500]  # First 500 chars
                    
                    if text:
                        text_previews.append({
                            "page": idx + 1,
                            "type": "text",
                            "content": text
                        })
                except:
                    pass
            
            # Set permissions
            os.chmod(preview_dir, 0o700)
            for preview in previews:
                if preview.get("path"):
                    os.chmod(preview["path"], 0o600)
            
            app_logger.info(
                f"Generated EPUB preview with cover and {len(text_previews)} text snippet(s)",
                extra={"upload_uuid": upload_uuid}
            )
            
            return {
                "status": "success",
                "message": f"Generated EPUB preview",
                "total_pages": len(documents),
                "previewed_pages": len(previews) + len(text_previews),
                "pages": previews,
                "text_previews": text_previews,
                "preview_dir": str(preview_dir)
            }
        
        except Exception as e:
            app_logger.error(f"EPUB preview generation error: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "pages": []
            }
    
    @staticmethod
    def _generate_comic_previews(
        file_path: Path,
        upload_uuid: str,
        max_pages: int
    ) -> Dict[str, Any]:
        """Generate previews from comic archives (CBZ/CBR)."""
        # Comic preview would extract first N images from the archive
        # For now, return a stub
        return {
            "status": "success",
            "message": "Comic preview generation (stub)",
            "pages": [],
            "note": "Comic preview generation will be implemented in future update"
        }
    
    @staticmethod
    def cleanup_previews(upload_uuid: str) -> bool:
        """Delete preview files for an upload.
        
        Args:
            upload_uuid: UUID of the upload
            
        Returns:
            True if successful
        """
        try:
            preview_dir = Path("previews") / upload_uuid
            
            if preview_dir.exists():
                import shutil
                shutil.rmtree(preview_dir)
                
                app_logger.info(
                    f"Cleaned up preview directory",
                    extra={"upload_uuid": upload_uuid}
                )
                return True
            
            return False
        
        except Exception as e:
            app_logger.error(
                f"Preview cleanup failed: {str(e)}",
                exc_info=True,
                extra={"upload_uuid": upload_uuid}
            )
            return False
    
    @staticmethod
    def cleanup_old_previews(hours: int = 24) -> int:
        """Clean up preview directories older than specified hours.
        
        Args:
            hours: Age threshold in hours
            
        Returns:
            Number of directories cleaned
        """
        try:
            preview_base = Path("previews")
            if not preview_base.exists():
                return 0
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cleaned_count = 0
            
            for preview_dir in preview_base.iterdir():
                if preview_dir.is_dir():
                    # Check directory modification time
                    mtime = datetime.fromtimestamp(preview_dir.stat().st_mtime)
                    
                    if mtime < cutoff_time:
                        import shutil
                        shutil.rmtree(preview_dir)
                        cleaned_count += 1
                        
                        app_logger.info(
                            f"Cleaned up old preview directory",
                            extra={
                                "directory": preview_dir.name,
                                "age_hours": (datetime.now() - mtime).total_seconds() / 3600
                            }
                        )
            
            return cleaned_count
        
        except Exception as e:
            app_logger.error(f"Preview cleanup failed: {str(e)}", exc_info=True)
            return 0



