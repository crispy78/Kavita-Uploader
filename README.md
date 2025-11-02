# Kavita Uploader

**Version:** 0.1.0  
**License:** MIT  
**Platform:** Ubuntu 24.04 LTS

A secure, self-hosted web application for safely uploading e-books to Kavita with virus scanning, metadata validation, and duplicate detection.

![Upload Interface](docs/screenshot-placeholder.png)

## 🎯 Overview

Kavita Uploader provides a WeTransfer-style interface for securely uploading e-books with a comprehensive security pipeline:

1. **Upload & Quarantine** (✅ Implemented - Step 1)
2. **Virus/Malware Scanning** (✅ Implemented - Step 2)
3. **Metadata Extraction & Editing** (✅ Implemented - Step 3)
4. **Duplicate Detection & Move** (✅ Implemented - Step 4)

## 🏗️ Tech Stack

### Backend
- **FastAPI** (Python 3.12+) - Modern async web framework (auto-detects 3.13, 3.12, or system default)
- **SQLAlchemy** - ORM with async support
- **SQLite** - Lightweight database
- **python-magic** - MIME type detection
- **slowapi** - Rate limiting
- **aiofiles** - Async file operations
- **PyMuPDF** (fitz) - PDF metadata and preview generation (Step 3)
- **ebooklib** - EPUB metadata extraction (Step 3)
- **Pillow** - Image processing for previews (Step 3)
- **rarfile** - CBR comic archive support (Step 3)

### Frontend
- **React 19** - UI library
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **Axios** - HTTP client

### Rationale
- **FastAPI**: Excellent async performance, automatic API docs, built-in validation
- **React + Vite**: Fast development, modern tooling, optimal bundle size
- **Tailwind**: Rapid UI development, consistent design system
- **SQLite**: Zero-configuration, perfect for single-server deployments
- **Python 3.12+**: Auto-detects latest available (3.13 preferred, 3.12 fallback), improved performance, modern type hints

## ✨ Features

### Disk Space Protection 🛡️ (NEW!)
- ✅ **Multi-layer disk protection** - Prevent DoS via disk exhaustion
- ✅ **Pre-upload validation** - Reject uploads if insufficient space
- ✅ **Quarantine size limits** - Cap total quarantine directory size
- ✅ **Automatic cleanup** - Delete old quarantine files (configurable age)
- ✅ **Emergency cleanup** - Aggressive cleanup when disk critically low
- ✅ **Monitoring API** - Real-time disk status and warnings
- ✅ **Configurable thresholds** - Adjust all limits per your needs

See [docs/DISK_PROTECTION.md](../DISK_PROTECTION.md) for the complete guide (and more docs in the `docs/` folder).

### Current (Steps 1-4) ✅
- ✅ Drag-and-drop file upload
- ✅ WeTransfer-style modern UI
- ✅ 25 MB file size limit (configurable)
- ✅ File type validation (EPUB, PDF, CBZ, CBR, MOBI, AZW3)
- ✅ MIME type verification
- ✅ Secure filename sanitization
- ✅ UUID-based file storage
- ✅ Restrictive file permissions (0600)
- ✅ Rate limiting
- ✅ Structured JSON logging
- ✅ Upload status tracking
- ✅ SHA256 hash calculation
- ✅ **VirusTotal API v3 integration** (Step 2)
- ✅ **Automatic malware scanning** (Step 2)
- ✅ **Hash-based duplicate detection** (Step 2)
- ✅ **Scan result reuse** (Step 2)
- ✅ **Real-time scan progress** (Step 2)
- ✅ **Automatic scan triggering** (Step 2)
- ✅ **Per-file logging** for debugging

### Current (Step 3) ✅
- ✅ **Automatic metadata extraction** from PDF, EPUB, CBZ, CBR
- ✅ **Live file preview** (first 3 pages for PDF, cover + text for EPUB)
- ✅ **User-editable metadata modal** with validation
- ✅ **Base64-encoded preview images** (secure, no direct file access)
- ✅ **Auto-cleanup** of preview cache after 24 hours
- ✅ **Required field validation** (configurable)
- ✅ **Metadata persistence** in database

### Current (Step 4) ✅
- ✅ **Comprehensive duplicate detection** (hash-based in database + filesystem)
- ✅ **Automatic file moving** from quarantine to unsorted library
- ✅ **Name conflict resolution** with automatic renaming
- ✅ **Integrity verification** (post-move hash check)
- ✅ **Checksum manifest** (CSV audit trail)
- ✅ **Dry-run mode** for testing
- ✅ **Atomic file operations** (prevents corruption)
- ✅ **Configurable duplicate handling** (discard or rename)
- ✅ **Move status tracking** and user feedback

## 📦 Installation

### Prerequisites
- Ubuntu 24.04 LTS
- Sudo access
- Internet connection

### Quick Install

```bash
# Clone or extract the repository
cd Kavita-Upload

# Make installer executable
chmod +x install.sh

# Run installer
./install.sh
```

The installer will:
1. Install system dependencies (Python 3.12+ auto-detected, Node.js 20, libmagic, unzip, unrar)
2. Setup Python virtual environment
3. Install backend dependencies (including PyMuPDF, ebooklib, Pillow for Step 3)
4. Install frontend dependencies
5. Create necessary directories with secure permissions
6. Handle existing database (auto-migrate or backup)
7. Generate configuration file
8. Build frontend for production (includes all Step 3 components)
9. Create systemd service
10. **Verify installation automatically**

✅ **Clean installs work without manual fixes!**

### Troubleshooting Installation

If the installer reports that the **frontend build failed**:

```bash
# Check the npm build output for errors
cd Kavita-Upload/frontend
npm run build
```

Common issues:
- **Missing node_modules**: Run `npm install` first
- **Permission errors**: Ensure you have write access to the directory
- **Old Node.js version**: The installer installs Node.js 20, but verify with `node --version`
- **Disk space**: Building requires ~200MB free space

The installer now includes:
- ✅ Automatic cleanup of old builds
- ✅ Verification that `dist/index.html` was created
- ✅ File count confirmation
- ✅ Clear error messages with exit on failure

If the build succeeds but the app shows a blank page:
1. Check browser console (F12) for JavaScript errors
2. Verify `backend/frontend/dist/index.html` exists
3. Restart the FastAPI server

### Manual Installation

<details>
<summary>Click to expand manual installation steps</summary>

```bash
# 1. Install system dependencies
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3-pip libmagic1 nodejs npm

# 2. Setup backend
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..

# 3. Setup frontend
cd frontend
npm install
npm run build
cd ..

# 4. Create directories
mkdir -p quarantine unsorted library logs
chmod 700 quarantine unsorted
chmod 755 library logs

# 5. Configure
cp config.example.yaml config.yaml
# Edit config.yaml with your settings

# 6. Generate secret key
openssl rand -hex 32
# Add to config.yaml under server.secret_key
```

</details>

## ⚙️ Configuration

Configuration is managed through `config.yaml` with environment variable overrides.

### Key Configuration Options

```yaml
server:
  port: 5050                    # Application port (Kavita uses 5000)
  secret_key: "your-secret-key" # Generate with: openssl rand -hex 32

folders:
  quarantine: "./quarantine"    # Temporary secure storage
  unsorted: "./unsorted"        # Final destination for safe files
  library: "./library"          # Kavita library path (for duplicate checking)

upload:
  max_file_size_mb: 25          # Maximum upload size
  allowed_extensions:           # Allowed file types
    - "epub"
    - "pdf"
    - "cbz"
    - "cbr"
    - "mobi"
    - "azw3"

security:
  enable_rate_limiting: true
  rate_limit_uploads_per_minute: 10
  file_permissions_mode: 0o600  # Owner read/write only

# Step 2: VirusTotal Integration
scanning:
  enabled: false               # Set to true after configuring API key
  provider: virustotal
  virustotal_api_key: ""      # Get free key at https://www.virustotal.com/gui/join-us
  polling_interval_sec: 30     # How often to check scan status
  max_retries: 20             # Maximum polling attempts
  auto_skip_known_hashes: true # Reuse previous scan results

# Step 2: Duplicate Detection
duplicate_detection:
  enabled: true               # Hash-based duplicate checking
  hash_algorithm: sha256
  check_by_hash: true
  discard_exact_hash: true   # Reject exact duplicates

# Step 4: File Moving and Duplicate Detection
moving:
  enabled: true                      # Enable file moving to library
  unsorted_dir: "./unsorted"         # Destination for clean files
  kavita_library_dirs:               # Additional paths to check for duplicates
    - "./library"
  rename_on_name_conflict: true      # Rename files with same title/author
  rename_pattern: "{title} - {author} (duplicate_{timestamp}){ext}"
  discard_on_exact_duplicate: true   # Discard files with exact hash match
  verify_integrity_post_move: true   # Re-hash file after move
  dry_run: false                     # Test mode (no actual moves)
  checksum_manifest: true            # Maintain CSV audit trail
  atomic_operations: true            # Use atomic file operations
  cleanup_quarantine_on_success: true # Delete quarantine file after move
```

### Environment Variables

Override any config setting using environment variables:

```bash
# Server settings
export SERVER_PORT=5050
export SERVER_HOST=0.0.0.0

# Folder paths
export FOLDERS_QUARANTINE=/path/to/quarantine
export FOLDERS_UNSORTED=/path/to/unsorted
export FOLDERS_LIBRARY=/path/to/kavita/library

# Upload settings
export UPLOAD_MAX_FILE_SIZE_MB=50

# Security
export SECURITY_ENABLE_RATE_LIMITING=true

# Scanning (Step 2)
export SCANNING_ENABLED=true
export SCANNING_VIRUSTOTAL_API_KEY=your_api_key

# Logging
export LOGGING_LEVEL=DEBUG
```

## 🚀 Usage

### Development Mode

**Backend:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 5050
```

Access:
- Application (UI served by backend): http://localhost:5050
- API docs are disabled by default for security. Enable only in development by setting `server.debug: true` and `api_protection.disable_docs: false`.

### Production Mode

**Using systemd:**
```bash
# Start service
sudo systemctl start kavita-safeuploader

# Enable auto-start on boot
sudo systemctl enable kavita-safeuploader

# Check status
sudo systemctl status kavita-safeuploader

# View logs
journalctl -u kavita-safeuploader -f

# Stop service
sudo systemctl stop kavita-safeuploader

# Restart service
sudo systemctl restart kavita-safeuploader
```

**Direct execution:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 5050
```

Access: http://localhost:5050

## 📖 Step 3: Using Metadata Extraction & Preview

### Workflow

Once a file passes the VirusTotal scan (Step 2) and is marked as `safe`:

1. **Automatic Metadata Extraction**
   - Click on an uploaded file in the Upload History
   - Click "Preview & Edit Metadata" button
   - Metadata is automatically extracted from the file

2. **Review and Edit**
   - View file preview (first 3 pages for PDF, cover + excerpt for EPUB)
   - Edit extracted metadata fields:
     - Title (required)
     - Author (required)
     - Series (optional)
     - Volume (optional)
     - Publisher (optional)
     - Year (optional)
     - Language (optional)

3. **Save and Continue**
   - Click "Save & Continue" to verify metadata
   - File status changes to `metadata_verified`
   - Ready for Step 4 (Move to library)

### API Endpoints (Step 3)

#### Extract Metadata
```bash
GET /api/upload/{uuid}/metadata

# Example response:
{
  "success": true,
  "message": "Metadata extracted successfully",
  "metadata": {
    "title": "Example Book",
    "author": "John Doe",
    "language": "en",
    "year": "2024"
  },
  "validation": {
    "is_valid": true,
    "missing_fields": [],
    "required_fields": ["title", "author"]
  },
  "extracted_at": "2025-10-28T21:34:49Z",
  "edited": false
}
```

#### Update Metadata
```bash
PUT /api/upload/{uuid}/metadata
Content-Type: application/json

{
  "title": "Updated Title",
  "author": "Updated Author",
  "series": "My Series",
  "volume": "1",
  "publisher": "Publisher Name",
  "year": "2024",
  "language": "en"
}

# Example response:
{
  "success": true,
  "message": "Metadata updated successfully",
  "metadata": { ... },
  "validation": {
    "is_valid": true,
    "missing_fields": []
  },
  "status": "metadata_verified"
}
```

#### Get Preview
```bash
GET /api/upload/{uuid}/preview?page=0&max_pages=3

# Example response:
{
  "success": true,
  "message": "Preview generated successfully",
  "previews": [
    "iVBORw0KGgoAAAANSUhEUgAAA...",  # Base64-encoded PNG
    "iVBORw0KGgoAAAANSUhEUgAAA...",
    "iVBORw0KGgoAAAANSUhEUgAAA..."
  ],
  "file_extension": "pdf",
  "status": "generated"
}
```

### Configuration (Step 3)

Edit `config.yaml` to customize metadata extraction:

```yaml
metadata:
  enabled: true
  extract_on_upload: false  # Auto-extract after scan
  allow_user_editing: true
  required_fields:
    - "title"
    - "author"
  auto_save_on_no_changes: true
  preview_settings:
    max_pages: 3
    width: 1024
    height: 768

preview:
  enabled: true
  max_pages: 3
  width: 1024
  height: 768
  supported_types:
    - pdf
    - epub
  cache_previews: true
  preview_format: base64
  auto_cleanup_hours: 24
```

### Dependencies (Step 3)

Metadata extraction requires:
- **PyMuPDF** (fitz) - PDF metadata and preview
- **ebooklib** - EPUB metadata
- **Pillow** - Image processing
- **rarfile** - CBR support

System dependencies:
- `unzip` - EPUB extraction
- `unrar` - CBR extraction

All dependencies are automatically installed by `install.sh`.

### Security Notes (Step 3)

1. **Preview Security**
   - Previews are base64-encoded, never served as direct files
   - Preview cache stored in `previews/{uuid}/` with secure permissions (0600)
   - Auto-cleanup after 24 hours (configurable)
   - No direct file streaming to prevent unauthorized access

2. **Metadata Sanitization**
   - All user inputs are sanitized against XSS
   - HTML tags stripped from metadata fields
   - Only quarantined files can be accessed for preview

3. **Privacy**
   - Embedded metadata (annotations, comments) are stripped from previews
   - Preview generation reads from quarantine only

## 📦 Step 4: File Moving & Duplicate Detection

### Overview

Step 4 is the final stage of the upload pipeline, moving verified files from quarantine to the unsorted library while ensuring no duplicates are introduced.

### Workflow

Once a file has been scanned (Step 2) and metadata verified (Step 3):

1. **Click "Move to Library"** button
   - Button appears after metadata verification
   - Initiates comprehensive duplicate detection

2. **Duplicate Detection** (3-phase check)
   - **Phase 1**: Hash check in database
     - Searches for exact SHA-256 hash matches in uploads table
     - If found: File is discarded as duplicate
   - **Phase 2**: Hash check in filesystem
     - Scans `unsorted_dir` and `kavita_library_dirs` for matching hashes
     - If found: File is discarded as duplicate
   - **Phase 3**: Name conflict check
     - Checks for same title + author (different hash)
     - If found and `rename_on_name_conflict=true`: File is renamed
     - If found and `rename_on_name_conflict=false`: File is discarded

3. **File Move**
   - File moved from quarantine to `unsorted_dir`
   - Uses atomic operations (same filesystem) or copy+verify+delete
   - Integrity verification: Re-hash file after move
   - Secure permissions applied (0600)

4. **Post-Move**
   - Database updated: `status=moved`, `moved_at`, `final_path`
   - Entry logged to checksum manifest CSV
   - Quarantine file deleted (if `cleanup_quarantine_on_success=true`)

5. **Result Display**
   - Success: Green notification with destination path
   - Duplicate: Yellow warning with reason
   - Renamed: Green notification + original filename shown

### Move Behavior Table

| Scenario | Hash Match | Name Match | Action | Database Status | Result |
|----------|------------|------------|--------|-----------------|--------|
| Unique file | ❌ No | ❌ No | **Move** | `moved` | ✅ Success |
| Exact duplicate (DB) | ✅ Yes | ✅ Yes | **Discard** | `duplicate_discarded` | ⚠️ Duplicate |
| Exact duplicate (FS) | ✅ Yes | ✅ Yes | **Discard** | `duplicate_discarded` | ⚠️ Duplicate |
| Name conflict (rename ON) | ❌ No | ✅ Yes | **Rename + Move** | `moved` | ✅ Renamed |
| Name conflict (rename OFF) | ❌ No | ✅ Yes | **Discard** | `duplicate_discarded` | ⚠️ Conflict |

### API Endpoints (Step 4)

#### Move File to Library
```bash
POST /api/upload/{uuid}/move

# Example response (success):
{
  "success": true,
  "message": "File moved successfully",
  "status": "moved",
  "destination": "/path/to/unsorted/book.pdf",
  "renamed": false
}

# Example response (duplicate):
{
  "success": false,
  "message": "Duplicate file (exact hash match in database)",
  "status": "duplicate_discarded",
  "duplicate_of": "original-uuid-123",
  "duplicate_reason": "exact_hash_match_database"
}

# Example response (name conflict with rename):
{
  "success": true,
  "message": "File moved successfully (renamed due to name conflict)",
  "status": "moved",
  "destination": "/path/to/unsorted/Book - Author (duplicate_20240129_153045).pdf",
  "renamed": true,
  "original_name": "book.pdf"
}
```

#### Get Move Status
```bash
GET /api/upload/{uuid}/move/status

# Example response:
{
  "success": true,
  "uuid": "upload-uuid-123",
  "status": "moved",
  "can_move": false,
  "is_duplicate": false,
  "moved_at": "2024-01-29T15:30:45",
  "final_path": "/path/to/unsorted/book.pdf",
  "moving_enabled": true,
  "dry_run_mode": false
}
```

### Configuration (Step 4)

Edit `config.yaml` to customize file moving behavior:

```yaml
moving:
  enabled: true                      # Enable/disable file moving
  unsorted_dir: "./unsorted"         # Destination for clean files
  kavita_library_dirs:               # Additional paths to check for duplicates
    - "./library"
    - "/external/kavita/library"
  
  # Duplicate handling
  discard_on_exact_duplicate: true   # Discard files with exact hash match
  rename_on_name_conflict: true      # Rename files with same title/author
  rename_pattern: "{title} - {author} (duplicate_{timestamp}){ext}"
  
  # Integrity and safety
  verify_integrity_post_move: true   # Re-hash file after move to detect corruption
  atomic_operations: true            # Use os.replace() for same-filesystem moves
  cleanup_quarantine_on_success: true # Delete quarantine file after successful move
  
  # Audit and testing
  checksum_manifest: true            # Maintain CSV audit trail
  manifest_path: "logs/manifest.csv"
  log_moves: true                    # Log all move operations
  dry_run: false                     # Test mode (no actual moves, just simulation)
  
  # Optional notifications (not yet implemented)
  notification:
    email_enabled: false
    webhook_enabled: false
```

### Checksum Manifest (Audit Trail)

When `checksum_manifest: true`, all file operations are logged to a CSV file:

```csv
timestamp,uuid,original_filename,destination_path,file_hash,file_size,action,reason
2024-01-29T15:30:45Z,uuid-123,book.pdf,/unsorted/book.pdf,abc123...,1048576,moved,
2024-01-29T15:31:22Z,uuid-456,duplicate.pdf,N/A,abc123...,1048576,discarded,exact_hash_match_database
2024-01-29T15:32:10Z,uuid-789,book.epub,/unsorted/Book - Author (duplicate_20240129_153210).epub,def456...,2097152,renamed,name_conflict_renamed
```

**Fields:**
- `timestamp`: UTC ISO 8601 timestamp
- `uuid`: Upload UUID
- `original_filename`: User-uploaded filename
- `destination_path`: Final path (or N/A if discarded)
- `file_hash`: SHA-256 hash
- `file_size`: Size in bytes
- `action`: `moved`, `renamed`, or `discarded`
- `reason`: Empty for success, or duplicate reason

**Use cases:**
- Audit compliance: Track all file movements
- Duplicate analysis: Identify frequent duplicates
- Recovery: Locate files by hash after disaster
- Forensics: Timeline of file operations

### Integrity Verification Workflow

When `verify_integrity_post_move: true`:

```
1. Compute hash of file in quarantine
   → Example: abc123...

2. Move file to unsorted directory
   → Copy to destination
   → Set permissions (0600)

3. Re-compute hash of file in destination
   → Example: abc123...

4. Compare hashes
   ✅ Match: Success, delete quarantine file
   ❌ Mismatch: Corruption detected
      → Delete destination file (rollback)
      → Keep quarantine file
      → Mark upload as move_failed
      → Return error to user
```

**Why this matters:**
- Detects filesystem corruption during copy
- Prevents data loss from incomplete writes
- Ensures bit-perfect file transfer
- Critical for large files (>100MB)

### Dry Run Mode

Enable `dry_run: true` to test moving logic without actually moving files:

```yaml
moving:
  dry_run: true
```

**Behavior:**
- All duplicate detection runs normally
- Database queries execute
- Filesystem scans complete
- **BUT**: No files are moved or deleted
- Log output shows what *would* happen
- Status returned as `dry_run` instead of `moved`

**Example response:**
```json
{
  "success": true,
  "message": "DRY RUN: File would be moved (no actual changes made)",
  "status": "dry_run",
  "source": "/quarantine/uuid-123",
  "destination": "/unsorted/book.pdf",
  "renamed": false
}
```

**Use cases:**
- Test configuration changes
- Validate duplicate detection logic
- Preview file organization
- Training and demonstrations

### Security Notes (Step 4)

1. **Atomic Operations**
   - Same filesystem: `os.replace()` (atomic, instant)
   - Different filesystem: Copy → Verify → Delete (safer, but slower)
   - Prevents partial moves and corruption

2. **Duplicate Detection Security**
   - Hash-based checking prevents bypass attacks
   - Filesystem walks respect permissions
   - Database queries use parameterized SQL (SQLAlchemy ORM)

3. **File Permissions**
   - Moved files: `0600` (owner read/write only)
   - Directories: `0700` (owner full access only)
   - No group or world access

4. **Quarantine Cleanup**
   - Only deleted after successful move + integrity check
   - Preserved on error for recovery
   - Logged before deletion

5. **Path Traversal Protection**
   - Destination paths sanitized
   - Cannot move outside configured directories
   - UUID-based quarantine prevents collisions

### Docker (Optional)

```bash
# Build and run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 🧪 Testing

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_upload.py

# Run specific test
pytest tests/test_upload.py::TestUploadFile::test_upload_valid_file
```

### Test Coverage

Current test coverage includes:
- ✅ Configuration loading
- ✅ Valid file upload
- ✅ File size validation
- ✅ Extension validation
- ✅ Empty file rejection
- ✅ Filename sanitization
- ✅ Upload status retrieval
- ✅ Secure file permissions
- ✅ VirusTotal scanning (Step 2)
- ✅ Metadata extraction (Step 3)
- ✅ Preview generation (Step 3)

## 🔒 Security Design

### Defense in Depth

1. **Upload Validation**
   - File size limits (configurable, default 25 MB)
   - Extension whitelist validation
   - MIME type verification using libmagic
   - Empty file rejection

2. **Filename Security**
   - Path traversal prevention (`../` removed)
   - Special character sanitization
   - Length limits
   - UUID-based storage names

3. **File Storage**
   - Quarantine isolation (separate directory)
   - Restrictive permissions (0600 - owner only)
   - No direct web access to quarantined files
   - SHA256 hashing for integrity

4. **Rate Limiting**
   - Configurable upload rate limits
   - IP-based tracking
   - DDoS protection

5. **Structured Logging**
   - JSON format for parsing
   - Upload tracking by UUID
   - IP address logging
   - Error tracking

6. **Future Enhancements (Steps 2-4)**
   - VirusTotal integration
   - Automatic infected file handling
   - Metadata validation
   - Duplicate detection

### Security Checklist

- [x] Filename sanitization
- [x] File size validation
- [x] Extension validation
- [x] MIME type validation
- [x] Restrictive file permissions
- [x] Rate limiting
- [x] Structured logging
- [x] No direct file access via web
- [x] UUID-based file storage
- [x] SHA256 hashing
- [ ] CSRF protection (configured, needs frontend tokens)
- [ ] Virus scanning (Step 2)
- [ ] Metadata validation (Step 3)
- [ ] Duplicate detection (Step 4)

## 📁 Project Structure

```
Kavita-Upload/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI application
│   │   ├── config.py         # Configuration management
│   │   ├── database.py       # Database models
│   │   ├── routes.py         # API endpoints
│   │   ├── services.py       # Business logic (Steps 1-4)
│   │   ├── utils.py          # Utility functions
│   │   └── logger.py         # Logging configuration
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_upload.py    # Test suite
│   ├── requirements.txt      # Python dependencies
│   └── pytest.ini           # Test configuration
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Header.jsx
│   │   │   ├── UploadZone.jsx
│   │   │   └── UploadStatus.jsx
│   │   ├── services/
│   │   │   └── api.js        # API client
│   │   ├── App.jsx           # Main component
│   │   ├── main.jsx          # Entry point
│   │   └── index.css         # Styles
│   ├── package.json          # Node dependencies
│   ├── vite.config.js        # Vite configuration
│   └── tailwind.config.js    # Tailwind configuration
├── config.example.yaml       # Example configuration
├── install.sh               # Installation script
├── Dockerfile               # Docker image
├── docker-compose.yml       # Docker compose
├── .gitignore
└── README.md
```

## 🗺️ Roadmap

### Step 1: Upload & Quarantine ✅ (Completed)
- [x] WeTransfer-style UI
- [x] File upload with validation
- [x] Secure quarantine storage
- [x] Upload tracking
- [x] API documentation

### Step 2: VirusTotal Scanning ✅ (Completed)
- [x] VirusTotal API v3 integration
- [x] Automatic file scanning
- [x] Hash-based duplicate detection
- [x] Scan result reuse for known hashes
- [x] Scan result storage (logs/scans/)
- [x] Infected file handling
- [x] Real-time scan status updates
- [x] Frontend progress display
- [x] Enhanced logging with scan phase tracking
- [x] Human-readable console output + JSON file logs

### Step 3: Metadata & Preview ✅ (Completed)
- [x] PDF metadata extraction (PyMuPDF)
- [x] EPUB metadata extraction (ebooklib)
- [x] CBZ/CBR metadata extraction (ComicInfo.xml)
- [x] PDF preview generation (PyMuPDF, base64-encoded)
- [x] EPUB preview generation (cover + text snippets)
- [x] User-editable metadata modal UI
- [x] Required field validation
- [x] Metadata persistence in database
- [x] Preview cache with auto-cleanup (24h)
- [x] Secure preview access (no direct file streaming)

### Step 4: Duplicate Detection & Move (Planned)
- [ ] Library folder scanning
- [ ] Cross-library duplicate detection
- [ ] Duplicate handling (rename/skip)
- [ ] Atomic file moving
- [ ] Final destination organization
- [ ] Cleanup of quarantine

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Check what's using port 5050
sudo lsof -i :5050

# Change port in config.yaml or use environment variable
export SERVER_PORT=5051
```

### Permission Denied
```bash
# Ensure correct ownership
sudo chown -R $USER:$USER .

# Fix directory permissions
chmod 700 quarantine unsorted
chmod 755 library logs
```

### Frontend Build Fails
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Database Locked
```bash
# Stop any running instances
sudo systemctl stop kavita-safeuploader
pkill -f uvicorn

# Remove database lock (development only)
rm backend/safeuploader.db-shm backend/safeuploader.db-wal
```

## 📝 API Documentation

Interactive API documentation is available at:
- **Swagger UI:** http://localhost:5050/docs
- **ReDoc:** http://localhost:5050/redoc

### Key Endpoints

#### `GET /api/config`
Get public configuration for frontend.

#### `POST /api/upload`
Upload file to quarantine (Step 1).

**Request:** `multipart/form-data` with file field

**Response:**
```json
{
  "success": true,
  "message": "File uploaded and quarantined successfully",
  "upload": {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "book.epub",
    "file_size": 1048576,
    "file_size_formatted": "1.00 MB",
    "mime_type": "application/epub+zip",
    "status": "quarantined",
    "uploaded_at": "2024-01-01T12:00:00"
  }
}
```

#### `GET /api/upload/{uuid}`
Get upload status by UUID.

#### `POST /api/upload/{uuid}/scan`
Trigger virus scan (Step 2 - Stub).

#### `GET /api/upload/{uuid}/metadata`
Get extracted metadata (Step 3 - Stub).

#### `POST /api/upload/{uuid}/check-duplicate`
Check for duplicates (Step 4 - Stub).

#### `POST /api/upload/{uuid}/move`
Move to unsorted folder (Step 4 - Stub).

## 📚 Documentation

All documentation is centralized under `docs/`:

- Start here: [docs/INDEX.md](docs/INDEX.md)
- For builders: [docs/PROJECT_CREATION_GUIDE.md](../PROJECT_CREATION_GUIDE.md)
- Install: [docs/INSTALL.md](../INSTALL_NOTES.md)
- Security: [docs/SECURITY.md](../SECURITY.md)
- Disk Protection: [docs/DISK_PROTECTION.md](../DISK_PROTECTION.md)
- Logging: [docs/LOGGING_GUIDE.md](../LOGGING_GUIDE.md)
- Testing: [docs/TESTING.md](../TESTING.md)
- VirusTotal Setup: [docs/VIRUSTOTAL_SETUP.md](../VIRUSTOTAL_SETUP.md)
- Development: [docs/DEVELOPMENT.md](../DEVELOPMENT.md)

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
cd backend
source venv/bin/activate
pip install pytest pytest-asyncio pytest-cov

# Run tests before committing
pytest

# Check code style (optional)
pip install black flake8
black app/
flake8 app/
```

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Inspired by WeTransfer's user interface
- Built for the Kavita e-book server community
- Uses VirusTotal API for malware scanning (Step 2)
- Vibe-coded with Cursor — download at https://www.cursor.com

## 📞 Support

- **Issues:** GitHub Issues
- **Documentation:** This README and `/docs` endpoint
- **Logs:** `logs/safeuploader.log` or `journalctl -u kavita-safeuploader`

## 🔄 Changelog

### v0.2.1 (Current)
- ✅ **Enhanced logging system**
- ✅ Dual-format logging (JSON files + human-readable console)
- ✅ Dedicated scan phase tracking with detailed progress
- ✅ **Per-file logging** - individual log file for each upload
- ✅ **Automatic scan triggering** - scans start immediately after upload
- ✅ Structured fields for easy log parsing
- ✅ Configurable log levels per output
- ✅ Performance metrics (duration tracking)
- ✅ Comprehensive logging guide
- ✅ Updated to ESLint 9 (removed deprecated packages)

### v0.2.0
- ✅ **Step 2: VirusTotal Scanning fully implemented**
- ✅ Complete VirusTotal API v3 integration
- ✅ Hash-based duplicate detection
- ✅ Scan result reuse for efficiency
- ✅ Real-time frontend progress display
- ✅ Secure scan log storage
- ✅ Rate limit optimizations
- ✅ Enhanced test suite
- ⏳ Steps 3-4: Preview stubs ready

### v0.1.0
- ✅ Step 1: Upload and Quarantine
- ✅ WeTransfer-style UI
- ✅ Security hardening
- ✅ Production-ready installer

---

**Note:** All 4 steps are now complete and fully functional! See `PROJECT_CREATION_GUIDE.md` for a comprehensive guide on how this project was built.

