# Testing Guide - Kavita SafeUploader

Quick guide to test the application after installation.

## 📋 Prerequisites

- Server running at `http://localhost:5050` (or your configured address)
- VirusTotal API key configured (for scan testing)

## ✅ Test Checklist

### 1. Basic Upload Test

```bash
# Upload a small test file
curl -X POST http://localhost:5050/api/upload \
  -F "file=@/path/to/test.pdf" \
  -v
```

**Expected Response:**
```json
{
  "success": true,
  "message": "File uploaded and quarantined successfully",
  "upload": {
    "uuid": "abc123...",
    "filename": "test.pdf",
    "file_size": 12345,
    "status": "quarantined",
    "log_file": "logs/files/abc123.log"
  },
  "next_steps": [
    "File is quarantined",
    "Virus scanning in progress (VirusTotal)"
  ]
}
```

### 2. Check Per-File Log

```bash
# Get UUID from upload response
UUID="abc123..."

# View the individual file log
cat "logs/files/*_${UUID:0:8}.log"
```

**Expected Content:**
```
2024-01-01 12:00:00 [INFO] [UPLOAD_STARTED] {
  "uuid": "abc123...",
  "filename": "test.pdf",
  "timestamp": "2024-01-01T12:00:00Z"
}
2024-01-01 12:00:01 [INFO] [UPLOAD_COMPLETED] {
  "phase": "upload",
  "status": "completed",
  "file_size": 12345,
  ...
}
2024-01-01 12:00:02 [INFO] [SCAN_QUEUED] {
  "phase": "scan",
  "status": "queued",
  ...
}
...
```

### 3. Monitor Scan Progress

**In Console (real-time):**
```bash
# Watch the main log
tail -f logs/safeuploader.log | jq -C '.'
```

You should see scan phases:
```
[INFO] Checking hash in VirusTotal database (Phase:check_hash)
[INFO] Hash not found - will upload for scanning
[INFO] Uploading file to VirusTotal (508149 bytes) (Phase:upload)
[INFO] ✓ File uploaded successfully - analysis started
[INFO] Polling for analysis results (Phase:poll)
[INFO] ⏳ Analysis in progress... (attempt 1/20)
[INFO] ✓ Analysis completed after 2 attempt(s)
[INFO] ✓ Scan results: CLEAN - 0/70 engines detected threats
```

### 4. Check Upload Status

```bash
# Check status via API
curl http://localhost:5050/api/upload/$UUID
```

**Expected (after scan completes):**
```json
{
  "success": true,
  "upload": {
    "uuid": "abc123...",
    "status": "scanned",
    "scan_result": "safe",
    "scanned_at": "2024-01-01T12:05:00Z"
  }
}
```

### 5. Test File Rejection

**Test oversized file:**
```bash
# Create a 30MB file (exceeds 25MB limit)
dd if=/dev/zero of=/tmp/large.pdf bs=1M count=30

curl -X POST http://localhost:5050/api/upload \
  -F "file=@/tmp/large.pdf"
```

**Expected:**
```json
{
  "detail": {
    "error": "File too large",
    "message": "Maximum file size is 25 MB"
  }
}
```

**Test invalid extension:**
```bash
curl -X POST http://localhost:5050/api/upload \
  -F "file=@test.exe"
```

**Expected:**
```json
{
  "detail": {
    "error": "Invalid file type",
    "message": "Only .epub, .pdf, .cbz, .cbr, .mobi, .azw3 files are allowed"
  }
}
```

## 🔍 Debugging Steps

### Issue: No Scan Activity

**Check 1: Is scanning enabled?**
```bash
grep "scanning:" config.yaml
# Should show:
#   enabled: true
#   virustotal_api_key: "your-key"
```

**Check 2: View configuration:**
```bash
curl http://localhost:5050/api/config
```

Should show:
```json
{
  "features": {
    "scanning_enabled": true
  }
}
```

**Check 3: View VirusTotal API key (first 8 chars):**
```bash
grep "virustotal_api_key" config.yaml | head -c 50
```

### Issue: Scan Stuck in "Scanning"

**Check poll attempts:**
```bash
# Search logs for polling
jq 'select(.scan_phase == "poll")' logs/safeuploader.log
```

**Manual scan status check:**
```bash
curl http://localhost:5050/api/upload/$UUID/scan/status
```

### Issue: Can't Find Per-File Log

**List all file logs:**
```bash
ls -lh logs/files/
```

**Search by date:**
```bash
ls -lt logs/files/ | head
```

**Search by UUID:**
```bash
UUID="abc123..."
find logs/files -name "*${UUID:0:8}*"
```

## 📊 Log Analysis Examples

### Count Today's Uploads

```bash
TODAY=$(date +%Y%m%d)
ls logs/files/${TODAY}_*.log | wc -l
```

### Find Failed Scans

```bash
grep -l "scan_error\|SCAN_ERROR" logs/files/*.log
```

### View All Scan Results

```bash
for log in logs/files/*.log; do
  echo "=== $log ==="
  grep "FINAL STATUS" "$log"
done
```

### Check Average Scan Duration

```bash
jq 'select(.scan_phase == "poll" and .attempt == 1) | .timestamp' logs/safeuploader.log
```

## 🧪 Automated Test Suite

Run the Python test suite:

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

**Key tests:**
- `test_upload.py` - Upload validation and quarantine
- `test_scanning.py` - VirusTotal integration
- `test_file_size_limit.py` - Size validation
- `test_file_type_validation.py` - Extension validation

## 🚨 Common Issues & Fixes

### 1. "VirusTotal API key not configured"

**Fix:**
```bash
# Edit config.yaml
nano config.yaml

# Set:
scanning:
  enabled: true
  virustotal_api_key: "your-actual-key-here"

# Restart
sudo systemctl restart kavita-safeuploader
```

### 2. Permissions Error on Logs

**Fix:**
```bash
# Ensure log directories exist with correct permissions
mkdir -p logs/files logs/scans
chmod 755 logs logs/files logs/scans
```

### 3. Database Lock Error

**Fix:**
```bash
# Stop service
sudo systemctl stop kavita-safeuploader

# Remove lock
rm -f data/uploads.db-wal data/uploads.db-shm

# Restart
sudo systemctl start kavita-safeuploader
```

## 📝 Test Data

### Sample Test Files

Use EICAR test file (safe malware test):
```bash
# Create EICAR test file
echo 'X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*' > eicar.txt

# Upload (should be detected as malicious)
curl -X POST http://localhost:5050/api/upload \
  -F "file=@eicar.txt"
```

### Clean Test PDFs

```bash
# Use any legitimate PDF
curl -X POST http://localhost:5050/api/upload \
  -F "file=@/usr/share/doc/*/README.pdf"
```

## ✅ Success Criteria

After installation, verify:

- [ ] Files upload successfully
- [ ] Per-file logs created in `logs/files/`
- [ ] Console shows colored scan progress
- [ ] JSON logs in `logs/safeuploader.log`
- [ ] Scans complete within 2-3 minutes
- [ ] Clean files marked as "safe"
- [ ] Status API returns correct information
- [ ] File size/type validation works
- [ ] Rate limiting prevents abuse

## 📚 More Information

- [Logging Guide](LOGGING_GUIDE.md) - Detailed logging documentation
- [README.md](README.md) - Full feature documentation
- [SECURITY.md](SECURITY.md) - Security considerations

---

**Need Help?** Check logs first:
```bash
# Application logs
tail -100 logs/safeuploader.log | jq '.'

# System logs
journalctl -u kavita-safeuploader -n 100

# Per-file logs
ls -lt logs/files/ | head -5
```



