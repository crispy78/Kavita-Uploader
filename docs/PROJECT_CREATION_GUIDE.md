# Project Creation Guide: Kavita Uploader

**How This Project Was Built - A Guide for Vibe-Coding Projects**

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack Decisions](#technology-stack-decisions)
3. [Step-by-Step Development](#step-by-step-development)
4. [Key Implementation Decisions](#key-implementation-decisions)
5. [Lessons Learned](#lessons-learned)
6. [Replication Guide](#replication-guide)

---

## 🎯 Project Overview

**Goal:** Create a secure, self-hosted web application for uploading e-books to Kavita with virus scanning, metadata validation, and duplicate detection.

**Target Platform:** Ubuntu 24.04 LTS

**Development Approach:** Incremental, step-by-step implementation with full testing at each stage

**Total Development Time:** ~4 development phases

---

## 🏗️ Technology Stack Decisions

### Backend: Python + FastAPI

**Why FastAPI?**
- Async/await support for concurrent operations
- Automatic API documentation (Swagger)
- Built-in data validation (Pydantic)
- Excellent performance
- Type hints for better IDE support

**Key Libraries:**
```python
fastapi==0.120.4          # Web framework (requires Python 3.12+)
uvicorn==0.32.1           # ASGI server
sqlalchemy==2.0.36        # ORM with async support
aiosqlite==0.20.0         # Async SQLite driver
python-magic==0.4.27      # MIME type detection
slowapi==0.1.9            # Rate limiting
PyMuPDF==1.24.14          # PDF processing
ebooklib==0.18            # EPUB processing
Pillow==11.0.0            # Image processing
```

### Frontend: React + Vite

**Why React + Vite?**
- Fast development with hot reload
- Modern build tooling
- Optimal bundle sizes
- Large ecosystem

**Key Libraries:**
```json
"react": "^19.2.0"
"vite": "^5.4.11"
"axios": "^1.7.8"
"tailwindcss": "^3.4.17"
```

### Database: SQLite

**Why SQLite?**
- Zero configuration
- Single file database
- Perfect for single-server deployments
- ACID compliant
- No separate database server needed

---

## 📈 Step-by-Step Development

### Phase 1: Upload & Quarantine (Foundation)

**Duration:** 1 day

**Implementation Order:**

1. **Project Structure**
   ```
   backend/
     app/
       main.py          # FastAPI app
       database.py      # SQLAlchemy models
       routes.py        # API endpoints
       config.py        # Configuration
   frontend/
     src/
       App.jsx          # Main component
       components/      # UI components
   ```

2. **Core Features Implemented:**
   - File upload with drag-and-drop
   - MIME type validation
   - File size limits
   - UUID-based storage
   - Secure file permissions (0600)
   - SQLite database with async support
   - Rate limiting

3. **Database Schema (Initial):**
   ```sql
   CREATE TABLE uploads (
       id INTEGER PRIMARY KEY,
       uuid TEXT UNIQUE NOT NULL,
       original_filename TEXT NOT NULL,
       sanitized_filename TEXT NOT NULL,
       file_size INTEGER NOT NULL,
       mime_type TEXT,
       file_extension TEXT NOT NULL,
       status TEXT DEFAULT 'quarantined',
       quarantine_path TEXT NOT NULL,
       file_hash_sha256 TEXT,
       uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

4. **Key Code Patterns:**
   ```python
   # Async database session management
   async def get_db_session():
       async with db.async_session_maker() as session:
           yield session
   
   # File upload with validation
   @router.post("/upload")
   async def upload_file(
       file: UploadFile,
       db_session: AsyncSession = Depends(get_db_session)
   ):
       # Validate file type
       # Compute hash
       # Save with UUID
       # Create database record
   ```

5. **Frontend Components:**
   - `UploadZone.jsx` - Drag-and-drop interface
   - `UploadStatus.jsx` - Upload history
   - `Header.jsx` - Application header

**Testing:**
- Manual file uploads
- MIME type validation
- File size limits
- Database persistence

---

### Phase 2: VirusTotal Integration & Duplicate Detection

**Duration:** 2 days

**Implementation Order:**

1. **VirusTotal API Client** (`virustotal.py`)
   ```python
   class VirusTotalScanner:
       def __init__(self, api_key: str):
           self.api_key = api_key
           self.base_url = "https://www.virustotal.com/api/v3"
       
       async def check_file_hash(self, file_hash: str):
           # Check if hash exists in VT database
       
       async def upload_file(self, file_path: Path):
           # Upload file for scanning
       
       async def poll_analysis(self, analysis_id: str):
           # Poll for scan results
   ```

2. **Scanning Service** (`services.py`)
   - Async background task execution
   - Hash-based duplicate detection
   - Scan result reuse (saves API quota)
   - Automatic status updates
   - Comprehensive logging

3. **Database Updates:**
   ```sql
   ALTER TABLE uploads ADD COLUMN scanned_at TIMESTAMP;
   ALTER TABLE uploads ADD COLUMN scan_result TEXT;
   ALTER TABLE uploads ADD COLUMN scan_details TEXT;
   ```

4. **Structured Logging** (`logger.py`)
   ```python
   class JSONFormatter(logging.Formatter):
       def format(self, record):
           log_data = {
               "timestamp": datetime.utcnow().isoformat(),
               "level": record.levelname,
               "message": record.getMessage(),
               "upload_uuid": getattr(record, "upload_uuid", None),
               "scan_phase": getattr(record, "scan_phase", None),
               # ... custom fields
           }
           return json.dumps(log_data)
   ```

5. **Frontend Updates:**
   - Real-time scan progress
   - Status indicators
   - VirusTotal link display

**Key Learnings:**
- Use async/await for long-running operations
- Background tasks need their own database session
- Hash-based caching saves API quota dramatically
- Structured logging is essential for debugging async operations

**Testing:**
- Malicious file detection (EICAR test file)
- Clean file scanning
- Duplicate file handling
- Scan result reuse
- API rate limiting

---

### Phase 3: Metadata Extraction & Preview

**Duration:** 2 days

**Implementation Order:**

1. **Metadata Extractor** (`metadata_extractor.py`)
   ```python
   class MetadataExtractor:
       @staticmethod
       def extract_pdf(file_path: Path) -> dict:
           import fitz  # PyMuPDF
           doc = fitz.open(file_path)
           return {
               "title": doc.metadata.get("title"),
               "author": doc.metadata.get("author"),
               # ... more fields
           }
       
       @staticmethod
       def extract_epub(file_path: Path) -> dict:
           import ebooklib
           # Extract EPUB metadata
       
       @staticmethod
       def extract_comic(file_path: Path) -> dict:
           import rarfile, zipfile
           # Extract ComicInfo.xml
   ```

2. **Preview Generator** (`preview_generator.py`)
   ```python
   class PreviewGenerator:
       async def generate_pdf_preview(self, file_path: Path):
           # Generate first 3 pages as images
           # Base64 encode for secure transmission
           # Cache with auto-cleanup
       
       async def generate_epub_preview(self, file_path: Path):
           # Extract cover image
           # Extract text excerpt
   ```

3. **Database Updates:**
   ```sql
   ALTER TABLE uploads ADD COLUMN metadata_json TEXT;
   ALTER TABLE uploads ADD COLUMN metadata_edited BOOLEAN DEFAULT 0;
   ALTER TABLE uploads ADD COLUMN metadata_extracted_at TIMESTAMP;
   ALTER TABLE uploads ADD COLUMN metadata_verified_at TIMESTAMP;
   ALTER TABLE uploads ADD COLUMN preview_generated BOOLEAN DEFAULT 0;
   ALTER TABLE uploads ADD COLUMN preview_path TEXT;
   ```

4. **Automatic Schema Migration:**
   ```python
   async def _migrate_schema(self, conn):
       # Check existing columns
       result = await conn.execute(text("PRAGMA table_info(uploads)"))
       existing_columns = {row[1] for row in result.fetchall()}
       
       # Add missing columns
       required_columns = {
           'metadata_json': 'TEXT',
           'metadata_edited': 'BOOLEAN DEFAULT 0',
           # ...
       }
       
       for column_name, column_type in required_columns.items():
           if column_name not in existing_columns:
               await conn.execute(text(
                   f"ALTER TABLE uploads ADD COLUMN {column_name} {column_type}"
               ))
   ```

5. **Frontend Components:**
   - `MetadataModal.jsx` - Full-screen metadata editor
   - Preview image display
   - Editable form fields
   - Validation

**Security Considerations:**
- Base64-encoded previews (no direct file serving)
- XSS protection (sanitize user inputs)
- Preview cache auto-cleanup (24 hours)
- Secure file permissions

**Testing:**
- PDF metadata extraction
- EPUB metadata extraction
- Comic book metadata extraction
- Preview generation
- User metadata editing
- Validation rules

---

### Phase 4: Duplicate Detection & File Moving

**Duration:** 2 days

**Implementation Order:**

1. **Mover Service** (`mover_service.py`)
   ```python
   class MoverService:
       @staticmethod
       async def move_file(upload_uuid: str, db_session: AsyncSession):
           # 3-phase duplicate detection:
           
           # Phase 1: Database hash check
           is_db_dup = await check_duplicates_by_hash(...)
           
           # Phase 2: Filesystem hash check
           is_fs_dup = await check_duplicates_in_filesystem(...)
           
           # Phase 3: Name conflict check
           has_conflict = await check_name_conflict(...)
           
           # Move file (atomic or copy+verify)
           if atomic_operations:
               os.replace(source, dest)
           else:
               shutil.copy2(source, dest)
               verify_integrity(dest, expected_hash)
               source.unlink()
           
           # Update database
           # Write to manifest
   ```

2. **Duplicate Detection Strategies:**
   - **Exact Hash Match:** SHA-256 comparison
   - **Filesystem Scan:** Recursive directory walking
   - **Name Conflict:** Metadata comparison (title + author)

3. **Integrity Verification:**
   ```python
   async def verify_integrity(file_path: Path, expected_hash: str):
       actual_hash = await compute_file_hash(file_path)
       if actual_hash != expected_hash:
           # Corruption detected - rollback
           file_path.unlink()
           raise IntegrityError("Hash mismatch")
   ```

4. **Checksum Manifest** (CSV Audit Trail)
   ```csv
   timestamp,uuid,original_filename,destination_path,file_hash,file_size,action,reason
   2025-10-30T12:00:00Z,abc123,book.pdf,/unsorted/book.pdf,def456,1048576,moved,
   2025-10-30T12:01:00Z,abc456,dup.pdf,N/A,def456,1048576,discarded,exact_hash_match
   ```

5. **Database Updates:**
   ```sql
   ALTER TABLE uploads ADD COLUMN moved_at TIMESTAMP;
   ALTER TABLE uploads ADD COLUMN final_path TEXT;
   ALTER TABLE uploads ADD COLUMN is_duplicate BOOLEAN DEFAULT 0;
   ALTER TABLE uploads ADD COLUMN duplicate_of TEXT;
   ALTER TABLE uploads ADD COLUMN duplicate_reason TEXT;
   ```

6. **Configuration:**
   ```yaml
   moving:
     enabled: true
     unsorted_dir: "./unsorted"
     kavita_library_dirs:
       - "./library"
     rename_on_name_conflict: true
     rename_pattern: "{title} - {author} (duplicate_{timestamp}){ext}"
     discard_on_exact_duplicate: true
     verify_integrity_post_move: true
     dry_run: false
     checksum_manifest: true
     atomic_operations: true
     cleanup_quarantine_on_success: true
   ```

**Testing:**
- Unique file moves
- Exact duplicate detection (database)
- Exact duplicate detection (filesystem)
- Name conflict with rename
- Name conflict without rename (discard)
- Integrity verification
- Dry-run mode
- Manifest logging

---

## 🔑 Key Implementation Decisions

### 1. Async/Await Throughout

**Why:** Non-blocking I/O for better performance

**Pattern:**
```python
# Bad: Blocking I/O
def upload_file(file):
    hash = compute_hash(file)  # Blocks
    db.save(hash)               # Blocks
    return result

# Good: Async I/O
async def upload_file(file):
    hash = await compute_hash(file)  # Non-blocking
    await db.save(hash)               # Non-blocking
    return result
```

### 2. Background Tasks for Long Operations

**Why:** Don't make users wait for VirusTotal scans

**Pattern:**
```python
@router.post("/upload")
async def upload_file(file: UploadFile):
    # Save file immediately
    upload = await save_file(file)
    
    # Return response to user
    response = {"uuid": upload.uuid}
    
    # Start background scan (don't await)
    asyncio.create_task(scan_file(upload.uuid))
    
    return response
```

**Critical:** Background tasks need their own DB session:
```python
async def scan_file(upload_uuid: str):
    # Create new session for background task
    async with db.async_session_maker() as session:
        # Do scan
        pass
```

### 3. Configuration Management

**Why:** Environment variables override YAML for 12-factor principles

**Pattern:**
```python
class Config(BaseSettings):
    server_port: int = Field(default=5050)
    
    class Config:
        env_prefix = "SERVER_"  # Allows SERVER_PORT env var

# Load from YAML first, then override with env vars
config = Config(**yaml_config)
```

### 4. Structured Logging

**Why:** Machine-parseable logs for analysis

**Pattern:**
```python
# Bad: String concatenation
logger.info(f"File uploaded: {filename}")

# Good: Structured with extra fields
logger.info(
    "File uploaded",
    extra={
        "upload_uuid": uuid,
        "uploaded_file": filename,
        "file_size": size
    }
)
```

**Output:**
```json
{
  "timestamp": "2025-10-30T12:00:00Z",
  "level": "INFO",
  "message": "File uploaded",
  "upload_uuid": "abc123",
  "uploaded_file": "book.pdf",
  "file_size": 1048576
}
```

### 5. Database Schema Migrations

**Why:** Automatic schema updates across versions

**Pattern:**
```python
async def _migrate_schema(self):
    existing_cols = await get_existing_columns()
    
    for col_name, col_type in REQUIRED_COLUMNS.items():
        if col_name not in existing_cols:
            await add_column(col_name, col_type)
```

**Benefit:** Users can upgrade without manual SQL

### 6. Security-First Design

**Principles:**
- Never trust user input (validate everything)
- Minimal file permissions (0600 for files, 0700 for dirs)
- UUID-based filenames (prevent path traversal)
- Rate limiting (prevent abuse)
- XSS protection (sanitize metadata)
- Base64 previews (no direct file serving)

### 7. Comprehensive Testing

**Test Structure:**
```python
# Unit tests
def test_metadata_extraction():
    metadata = extract_pdf("test.pdf")
    assert "title" in metadata

# Integration tests
async def test_upload_workflow():
    upload = await upload_file(test_file)
    scan = await scan_file(upload.uuid)
    metadata = await extract_metadata(upload.uuid)
    move = await move_file(upload.uuid)
    assert move.status == "moved"
```

---

## 💡 Lessons Learned

### 1. Start Simple, Iterate

**What worked:** Building in clear phases (Upload → Scan → Metadata → Move)

**Why:** Each phase had a working product, making debugging easier

### 2. Logging is Critical

**What worked:** Structured JSON logs with contextual fields

**Why:** Debugging async operations requires detailed logs

### 3. Configuration Over Code

**What worked:** YAML config with env var overrides

**Why:** Easy to adjust without code changes

### 4. Database Schema Evolution

**What worked:** Automatic migrations

**Why:** Users can upgrade seamlessly

**Mistake:** Initially didn't have migrations, required manual database deletion

### 5. Frontend Build Caching

**Problem:** Vite aggressive caching caused blank pages

**Solution:** 
- Version bumps for cache busting
- Clear dist/ and node_modules/.vite on rebuild
- Use hard refresh (Ctrl+Shift+R) during development

### 6. Background Tasks Need Their Own Sessions

**Problem:** FastAPI closes DB sessions after response

**Solution:** Create new session in background tasks:
```python
asyncio.create_task(scan_with_new_session(uuid))
```

### 7. Null Safety in React

**Problem:** Accessing `.length` on undefined caused blank pages

**Solution:** Always check for null/undefined:
```javascript
if (!uploadInfo) return null
if (!previews || previews.length === 0) return <div>No previews</div>
```

---

## 🔄 Replication Guide

### For Your Own Vibe-Coding Project

**Step 1: Define Clear Phases**

Break your project into 3-5 distinct phases where each phase adds one major feature:

```
Phase 1: Core functionality (MVP)
Phase 2: Integration with external service
Phase 3: Advanced features
Phase 4: Polishing and optimization
```

**Step 2: Technology Selection**

Choose technologies based on:
- ✅ Async support (if needed)
- ✅ Good documentation
- ✅ Active community
- ✅ Compatibility with Ubuntu 24.04 LTS

**Step 3: Project Structure**

Create a clean structure from day 1:

```
project/
  backend/
    app/
      __init__.py
      main.py          # FastAPI entry point
      config.py        # Configuration
      database.py      # Models
      routes.py        # API endpoints
      services.py      # Business logic
    tests/
      test_*.py        # Tests
    requirements.txt
  frontend/
    src/
      App.jsx
      components/
      services/
    package.json
  install.sh           # Installer
  config.example.yaml  # Config template
  README.md
```

**Step 4: Implement Phase by Phase**

For each phase:

1. **Plan** - Write down exactly what this phase does
2. **Implement** - Code the feature
3. **Test** - Manual + automated tests
4. **Document** - Update README with new features
5. **Commit** - Git commit with clear message

**Step 5: Installer from Day 1**

Create `install.sh` that:
- Installs system dependencies
- Sets up Python venv
- Installs backend packages
- Sets up frontend (npm install + build)
- Creates config file
- Creates systemd service

**Step 6: Configuration Management**

Use YAML + environment variables:

```python
# config.py
class Config(BaseSettings):
    api_key: str = Field(default="")
    
    class Config:
        env_prefix = "MYAPP_"

# Load
with open("config.yaml") as f:
    yaml_config = yaml.safe_load(f)

config = Config(**yaml_config)
```

**Step 7: Comprehensive Logging**

Set up structured logging early:

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            **{k: v for k, v in record.__dict__.items() 
               if k not in logging.LogRecord.__dict__}
        })

logger = logging.getLogger("myapp")
handler = logging.FileHandler("app.log")
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

**Step 8: Database with Migrations**

Use SQLAlchemy with automatic schema updates:

```python
async def migrate_schema():
    existing = await get_columns()
    for col, type in REQUIRED_COLS.items():
        if col not in existing:
            await add_column(col, type)
```

**Step 9: Testing Strategy**

Create tests for each phase:

```python
# tests/test_phase1.py
def test_upload():
    assert upload_file("test.pdf").success

# tests/test_phase2.py  
def test_scan():
    assert scan_file("uuid").result == "safe"
```

**Step 10: Documentation**

Maintain:
- `README.md` - User-facing documentation
- `INSTALL_NOTES.md` - Installation guide
- `DEVELOPMENT.md` - Developer guide
- `PROJECT_CREATION_GUIDE.md` - How it was built (this file!)

---

## 📊 Project Statistics

**Final Stats:**

- **Backend Code:** ~3,500 lines of Python
- **Frontend Code:** ~1,200 lines of JavaScript/JSX
- **Tests:** 24 test cases across 4 test files
- **Documentation:** ~5,000 lines across 9 documents
- **Dependencies:** 30 Python packages, 15 npm packages
- **Development Time:** ~1 week (4 phases)
- **Git Commits:** ~50+ commits

**File Breakdown:**

| Component | Files | Lines |
|-----------|-------|-------|
| Backend API | 10 | 2,000 |
| Frontend UI | 8 | 1,200 |
| Configuration | 3 | 200 |
| Tests | 4 | 600 |
| Documentation | 9 | 5,000 |
| Scripts | 2 | 500 |

---

## 🎓 Key Takeaways for Vibe-Coding

1. **Plan in Phases** - Each phase should be independently usable
2. **Async from Day 1** - Don't retrofit async later
3. **Log Everything** - Structured JSON logs are your friend
4. **Test as You Go** - Don't leave testing for the end
5. **Document Early** - Write docs while the code is fresh
6. **Automate Installation** - Users should never need manual setup
7. **Configuration is Key** - YAML + env vars for flexibility
8. **Security First** - Validate inputs, limit permissions, sanitize outputs
9. **Iterate Quickly** - Get feedback early and often
10. **Clean Up** - Remove dead code, consolidate docs (like we're doing now!)

---

## 🚀 Next Steps for Similar Projects

**Want to build something similar?**

1. **Fork this project** - Use it as a template
2. **Replace the domain logic** - Keep the structure, change the features
3. **Maintain the phase approach** - It works!
4. **Use the installer pattern** - One-command installs are awesome
5. **Follow the documentation pattern** - Users will thank you

**Example Adaptations:**

- **Image Uploader** - Replace e-book logic with image processing
- **Document Manager** - Add OCR and full-text search
- **Media Library** - Add video transcoding
- **Data Pipeline** - Add data transformation steps

The patterns and structure are reusable!

---

## 📚 Additional Resources

**Learning Resources:**

- FastAPI Documentation: https://fastapi.tiangolo.com/
- React Documentation: https://react.dev/
- SQLAlchemy Async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Vite Documentation: https://vitejs.dev/
- Tailwind CSS: https://tailwindcss.com/

**Similar Projects for Inspiration:**

- Paperless-ngx (document management)
- Calibre-Web (e-book server)
- Nextcloud (file sharing)

---

## 🙏 Acknowledgments

This project was built using:
- Cursor IDE with Claude Sonnet 4.5
- Ubuntu 24.04 LTS
- Modern Python and JavaScript ecosystems
- Open-source libraries and frameworks

**Built with vibe-coding principles:**
- Iterative development
- Comprehensive testing
- Clear documentation
- User-focused design

---

**End of Guide**

*For questions or improvements, see the main README.md*

