# Kavita Uploader - Installation Notes

## ✅ Clean Install Checklist

A clean installation should work without any manual fixes. This document ensures everything is correct.

### Prerequisites (Ubuntu 24.04 LTS)

- Sudo access
- Internet connection
- Git (if cloning repository)

### Installation Steps

```bash
# 1. Navigate to project directory
cd Kavita-Upload

# 2. Run installer
chmod +x install.sh
./install.sh
```

The installer will:
1. ✅ Install system dependencies (Python 3.12+ auto-detected, Node.js 20, libmagic, unzip, unrar)
2. ✅ Create Python virtual environment
3. ✅ Install Python dependencies (including PyMuPDF, ebooklib, Pillow)
4. ✅ Install Node.js dependencies
5. ✅ Create secure directories (quarantine, unsorted, logs)
6. ✅ Handle existing database (backup or migrate)
7. ✅ Generate config.yaml
8. ✅ **Build frontend with all Step 3 components**
9. ✅ Create systemd service

### Post-Installation Verification

The installer **automatically verifies** the installation at the end. It checks:
- ✅ Python dependencies installed (PyMuPDF, ebooklib, Pillow, etc.)
- ✅ Frontend build created successfully
- ✅ Required directories exist with correct permissions
- ✅ Configuration file generated

If verification fails, the installer will show clear error messages and stop.

### Expected Behavior After Clean Install

#### 1. Upload (Step 1)
- ✅ Drag & drop or browse for files
- ✅ Files quarantined with secure permissions
- ✅ SHA-256 hash calculated
- ✅ Upload status tracked

#### 2. Scanning (Step 2)
- ✅ Automatic VirusTotal scan triggered
- ✅ Scan status updates in real-time
- ✅ Results logged to files
- ✅ Hash-based duplicate detection

#### 3. Metadata & Preview (Step 3)
- ✅ "Preview & Edit Metadata" button appears after scan = safe
- ✅ Clicking button opens modal with:
  - PDF preview (first 3 pages as images)
  - Extracted metadata (title, author, etc.)
  - Editable fields with validation
  - Save & Continue button
- ✅ Saving updates database and changes status to `metadata_verified`

### Common Issues & Solutions

#### Issue: "Preview & Edit Metadata" button not appearing

**Symptoms:**
- Button doesn't show after file is scanned as safe
- Modal doesn't open

**Causes & Solutions:**

1. **Frontend not rebuilt after Step 3 added**
   ```bash
   cd frontend
   npm run build
   cd ..
   # Restart server
   ```

2. **Browser cache**
   - Hard refresh: Ctrl+F5 (Windows/Linux) or Cmd+Shift+R (Mac)
   - Clear browser cache

3. **API not returning scan_result**
   - Check: `curl http://localhost:5050/api/upload/{UUID}` should include `"scan_result": "safe"`
   - If missing: Restart server (database migration will add it)

#### Issue: Database schema errors

**Symptoms:**
```
sqlite3.OperationalError: table uploads has no column named metadata_extracted_at
```

**Solution:**
The database will **auto-migrate** on server start. If it doesn't:
1. Stop the server
2. Backup old database:
   ```bash
   cd backend
   mv uploader.db uploader.db.backup
   ```
3. Restart server (creates fresh database)

#### Issue: Preview images not showing

**Symptoms:**
- Modal opens but no preview images
- Logs show "Generated 3 PDF preview(s)" but UI is blank

**Causes:**
1. **Frontend not rebuilt** - See solution above
2. **API format mismatch** - Fixed in routes.py (extracts base64 from data URLs)

**Verify:**
```bash
curl -s http://localhost:5050/api/upload/{UUID}/preview | head -c 200
# Should show JSON with "previews": [...base64 strings...]
```

#### Issue: Missing Python dependencies

**Symptoms:**
- Import errors on server start
- Preview/metadata features don't work

**Solution:**
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

Required for Step 3:
- PyMuPDF (fitz) - PDF preview/metadata
- ebooklib - EPUB metadata
- Pillow - Image processing
- rarfile - CBR support

### Development vs Production

**Development (with hot reload):**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 5050
```

**Production (systemd):**
```bash
sudo systemctl start kavita-uploader
sudo systemctl enable kavita-uploader
```

### File Locations

```
Kavita-Upload/
├── backend/
│   ├── uploader.db          # SQLite database (auto-created/migrated)
│   ├── quarantine/              # Uploaded files (700 permissions)
│   ├── unsorted/                # Step 4 destination
│   ├── logs/                    # Application logs
│   │   ├── uploader.log    # Main log
│   │   ├── files/              # Per-upload logs
│   │   └── scans/              # Scan result JSON
│   └── previews/                # Temporary preview cache (auto-cleanup)
├── frontend/
│   └── dist/                    # Production build
└── config.yaml                  # Main configuration
```

### Testing Step 3

1. **Upload a PDF file**
2. **Wait for scan** (should be instant if hash is known)
3. **Expand upload details** (click on file)
4. **Click "Preview & Edit Metadata"**
5. **Verify modal shows:**
   - 3 preview images
   - Extracted title/author
   - Editable fields
6. **Edit metadata** (optional)
7. **Click "Save & Continue"**
8. **Verify:**
   - Status changes to `metadata_verified`
   - Checkmark appears next to "Metadata" in progress

### API Testing

```bash
UUID="your-file-uuid"

# 1. Check file status
curl http://localhost:5050/api/upload/$UUID

# 2. Extract metadata
curl http://localhost:5050/api/upload/$UUID/metadata

# 3. Get preview
curl http://localhost:5050/api/upload/$UUID/preview

# 4. Update metadata
curl -X PUT http://localhost:5050/api/upload/$UUID/metadata \
  -H "Content-Type: application/json" \
  -d '{"title": "My Book", "author": "John Doe"}'
```

### Support

If you encounter issues not covered here:

1. **Check logs:**
   ```bash
   # Application logs
   tail -f backend/logs/uploader.log
   
   # Per-file logs
   ls -lt backend/logs/files/
   tail backend/logs/files/YYYYMMDD_HHMMSS_uuid.log
   
   # Systemd logs (if using service)
   journalctl -u kavita-uploader -f
   ```

2. **Check configuration:**
   ```bash
   cat config.yaml
   ```

3. **Verify frontend build:**
   ```bash
   ls -la frontend/dist/
   grep -r "metadata" frontend/dist/assets/
   ```

### Next Steps (Step 4)

After Step 3 is working:
- Files with `metadata_verified` status are ready for Step 4
- Step 4 will implement moving files to Kavita library
- Duplicate detection against existing library
- Automatic file organization

---

**Installation Date:** Run `date` when installing  
**Version:** 0.1.0 (Steps 1-3 complete)

