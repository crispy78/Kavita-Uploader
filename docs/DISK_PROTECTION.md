# Disk Space Protection Guide

**Prevent DoS attacks and disk exhaustion from excessive uploads**

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Protection Layers](#protection-layers)
3. [Configuration](#configuration)
4. [How It Works](#how-it-works)
5. [API Endpoints](#api-endpoints)
6. [Monitoring](#monitoring)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The disk protection system prevents your server from being overwhelmed by file uploads that could lead to disk space exhaustion and system instability. It implements multiple layers of protection:

- **Pre-upload checks** - Reject uploads if insufficient space
- **Quarantine size limits** - Limit total quarantine directory size
- **Automatic cleanup** - Delete old files based on age
- **Emergency cleanup** - Aggressive cleanup when critically low
- **Rate limiting** - Prevent upload spam (existing feature)
- **Monitoring & alerts** - Track disk usage and warn administrators

---

## 🛡️ Protection Layers

### Layer 1: Pre-Upload Validation

**Before accepting any upload:**

1. ✅ Check if enough disk space exists for the upload
2. ✅ Verify free space won't drop below minimum threshold
3. ✅ Ensure reserve buffer won't be breached
4. ❌ **Reject upload if any check fails** (HTTP 507)

**Example:**
```
Upload: 100 MB file
Current Free Space: 2 GB (10% of 20 GB disk)
Min Free Threshold: 10%
Reserve Buffer: 1 GB

Check: 2 GB - 100 MB = 1.9 GB
       1.9 GB / 20 GB = 9.5% < 10% → REJECT
```

### Layer 2: Quarantine Size Limits

**Limit the total size of quarantine directory:**

- Set maximum total size (e.g., 10 GB)
- Count all files in "quarantined" or "scanning" status
- Trigger auto-cleanup if limit exceeded
- Reject if cleanup insufficient

**Example:**
```
Max Quarantine Size: 10 GB
Current Quarantine: 9.8 GB
New Upload: 500 MB

Check: 9.8 GB + 500 MB = 10.3 GB > 10 GB
Action: Trigger auto-cleanup
Result: If cleanup frees ≥500 MB → Accept, else → Reject
```

### Layer 3: Auto-Cleanup

**Automatically delete old quarantine files:**

- Runs periodically (default: every hour)
- Deletes files older than threshold (default: 72 hours)
- Only removes files in safe states:
  - `quarantined` - Never scanned
  - `scanning` - Scan in progress
  - `scan_failed` - Scan error
  - `infected` - Malware detected

**Protected statuses** (never auto-deleted):
- `safe` / `clean` - Passed scan
- `metadata_verified` - User reviewed
- `moved` - Already processed

### Layer 4: Emergency Cleanup

**Triggered when disk critically low:**

- Activates at emergency threshold (default: 5% free)
- Aggressively deletes oldest quarantine files
- Deletes until target space freed
- Logs all deletions for audit

### Layer 5: Single Upload Limits

**Additional per-file size restriction:**

- Separate from general `max_file_size_mb`
- Provides extra protection layer
- Can be more restrictive than general limit

**Example:**
```yaml
upload:
  max_file_size_mb: 25  # General limit for file validation

disk_protection:
  max_single_upload_size_mb: 100  # Additional disk protection limit
```

---

## ⚙️ Configuration

### config.yaml

```yaml
disk_protection:
  # Enable/disable entire disk protection system
  enabled: true
  
  # Minimum % of free disk space required (reject uploads if would drop below)
  min_free_space_percent: 10.0
  
  # Reserve space in bytes that must always remain free (default: 1 GB)
  reserve_space_bytes: 1073741824
  
  # Maximum total size of quarantine directory (0 = unlimited)
  max_quarantine_size_bytes: 10737418240  # 10 GB
  
  # Maximum size for single upload (additional to max_file_size_mb)
  max_single_upload_size_mb: 100
  
  # Automatically delete old quarantine files
  auto_cleanup_enabled: true
  
  # Delete files older than this many hours
  auto_cleanup_age_hours: 72  # 3 days
  
  # How often to run automatic cleanup
  cleanup_interval_minutes: 60  # Hourly
  
  # Trigger emergency cleanup when free space drops below this %
  emergency_cleanup_threshold_percent: 5.0
  
  # Alert threshold for disk space warnings
  alert_threshold_percent: 15.0
```

### Environment Variables

Override any setting using environment variables:

```bash
# Enable disk protection
export DISK_PROTECTION_ENABLED=true

# Set minimum free space to 15%
export DISK_PROTECTION_MIN_FREE_SPACE_PERCENT=15.0

# Set max quarantine size to 5 GB
export DISK_PROTECTION_MAX_QUARANTINE_SIZE_BYTES=5368709120

# Auto-cleanup every 30 minutes
export DISK_PROTECTION_CLEANUP_INTERVAL_MINUTES=30
```

---

## 🔄 How It Works

### Upload Flow with Disk Protection

```
1. User uploads file (e.g., 500 MB PDF)
   ↓
2. Validate file extension & MIME type
   ↓
3. Check file size vs max_file_size_mb
   ↓
4. ⭐ DISK PROTECTION CHECKS ⭐
   ├─ Check disk space available
   ├─ Check quarantine size limit
   ├─ Check single upload limit
   ├─ If fails → Try auto-cleanup
   └─ If still fails → Reject (HTTP 507)
   ↓
5. Save to quarantine
   ↓
6. Trigger virus scan
   ↓
7. (Optional) Extract metadata
   ↓
8. User verifies metadata
   ↓
9. Move to library
   ↓
10. Delete quarantine file (or auto-cleanup after N hours)
```

### Auto-Cleanup Process

```
Periodic Task (Every hour):
  1. Query database for old files:
     - Status IN (quarantined, scanning, scan_failed, infected)
     - Age > auto_cleanup_age_hours
  
  2. Sort by oldest first
  
  3. For each file:
     - Delete physical file
     - Update DB status to "auto_deleted"
     - Log deletion
  
  4. Report total bytes freed
```

### Emergency Cleanup Process

```
Triggered when disk < emergency_threshold:
  1. Log CRITICAL alert
  
  2. Query ALL quarantine files
     (including recent ones)
  
  3. Sort by oldest first
  
  4. Delete files until target_bytes freed
  
  5. Update DB status to "emergency_deleted"
  
  6. Send notifications (if configured)
```

---

## 📡 API Endpoints

### GET /api/system/disk-status

**Get comprehensive disk status information.**

**Response:**
```json
{
  "success": true,
  "disk_protection_enabled": true,
  "status": {
    "disk": {
      "total": 107374182400,
      "used": 85899345920,
      "free": 21474836480,
      "percent_used": 80
    },
    "quarantine": {
      "total_size": 5368709120,
      "max_size": 10737418240,
      "percent_used": 50,
      "file_counts": {
        "quarantined": 25,
        "scanning": 3,
        "safe": 10,
        "metadata_verified": 5
      }
    },
    "protection": {
      "min_free_percent": 10.0,
      "reserve_bytes": 1073741824,
      "auto_cleanup_enabled": true,
      "auto_cleanup_age_hours": 72
    }
  },
  "warnings": [
    "Disk usage above alert threshold (15% free)"
  ],
  "timestamp": "2025-10-30T12:00:00Z"
}
```

**Usage:**
```bash
# Check disk status
curl http://localhost:5050/api/system/disk-status

# Monitor in real-time
watch -n 10 'curl -s http://localhost:5050/api/system/disk-status | jq ".status.disk"'
```

### POST /api/system/cleanup

**Manually trigger cleanup of old quarantine files.**

**Response:**
```json
{
  "success": true,
  "bytes_freed": 2147483648,
  "bytes_freed_formatted": "2.00 GB",
  "message": "Cleanup completed successfully"
}
```

**Usage:**
```bash
# Trigger manual cleanup
curl -X POST http://localhost:5050/api/system/cleanup

# Script to cleanup when disk usage high
#!/bin/bash
USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $USAGE -gt 85 ]; then
  curl -X POST http://localhost:5050/api/system/cleanup
fi
```

---

## 📊 Monitoring

### Logging

All disk protection events are logged:

```json
{
  "timestamp": "2025-10-30T12:00:00Z",
  "level": "WARNING",
  "message": "Upload rejected - insufficient disk space",
  "uploaded_file": "large_book.pdf",
  "file_size": 524288000,
  "reason": "Upload would leave only 8.5% free space (minimum: 10%)",
  "ip_address": "192.168.1.100"
}
```

```json
{
  "timestamp": "2025-10-30T12:15:00Z",
  "level": "INFO",
  "message": "Auto-cleanup: Deleted old file (age: 5 days)",
  "upload_uuid": "abc123...",
  "file_size": 104857600,
  "status": "quarantined",
  "age_hours": 120
}
```

### Monitoring Script

Create a monitoring script:

```bash
#!/bin/bash
# monitor_disk.sh

API_URL="http://localhost:5050/api/system/disk-status"

while true; do
  STATUS=$(curl -s $API_URL)
  
  DISK_PCT=$(echo $STATUS | jq -r '.status.disk.percent_used')
  WARNINGS=$(echo $STATUS | jq -r '.warnings | length')
  
  if [ $WARNINGS -gt 0 ]; then
    echo "⚠️  WARNINGS DETECTED:"
    echo $STATUS | jq -r '.warnings[]'
    
    # Send alert (example: email)
    echo $STATUS | mail -s "Disk Space Alert" admin@example.com
  fi
  
  echo "Disk Usage: ${DISK_PCT}%"
  sleep 300  # Check every 5 minutes
done
```

### System Metrics

Monitor with system tools:

```bash
# Disk usage
df -h /path/to/kavita-upload

# Quarantine size
du -sh /path/to/kavita-upload/quarantine

# File count by age
find /path/to/kavita-upload/quarantine -type f -mtime +3 | wc -l

# Oldest file
find /path/to/kavita-upload/quarantine -type f -printf '%T+ %p\n' | sort | head -1
```

---

## ✅ Best Practices

### 1. Set Reasonable Limits

```yaml
# For a 100 GB disk:
disk_protection:
  min_free_space_percent: 15.0  # Leave 15 GB free
  reserve_space_bytes: 5368709120  # 5 GB reserve
  max_quarantine_size_bytes: 21474836480  # 20 GB max quarantine
```

**Rule of Thumb:**
- Minimum free space: 10-20% of total disk
- Reserve bytes: 5-10% of total disk
- Max quarantine: 15-25% of total disk

### 2. Adjust Cleanup Frequency

**High Traffic Sites:**
```yaml
auto_cleanup_age_hours: 24  # 1 day
cleanup_interval_minutes: 30  # Every 30 minutes
```

**Low Traffic Sites:**
```yaml
auto_cleanup_age_hours: 168  # 7 days
cleanup_interval_minutes: 360  # Every 6 hours
```

### 3. Monitor Regularly

- Check disk status daily
- Review cleanup logs weekly
- Adjust limits based on usage patterns
- Set up automated alerts

### 4. Test Emergency Scenarios

```bash
# Simulate low disk space
dd if=/dev/zero of=/tmp/Kavita-upload/fillfile bs=1M count=10000

# Try upload (should trigger protection)
curl -F "file=@test.pdf" http://localhost:5050/api/upload

# Cleanup test file
rm /tmp/Kavita-upload/fillfile
```

### 5. Document Your Limits

Create a `DISK_LIMITS.txt` in your installation:

```
Disk Protection Configuration
=============================
Server: production-01
Total Disk: 500 GB
Kavita Upload Installation: /srv/kavita-upload

Limits:
- Min Free Space: 10% (50 GB)
- Reserve: 10 GB
- Max Quarantine: 50 GB
- Auto-cleanup Age: 72 hours
- Single Upload Max: 100 MB

Last Updated: 2025-10-30
```

---

## 🔧 Troubleshooting

### Problem: Uploads Always Rejected (HTTP 507)

**Symptoms:**
```
Error: Insufficient disk space
Message: Upload would leave only 8% free space (minimum: 10%)
```

**Solutions:**

1. **Check actual disk space:**
   ```bash
   df -h /path/to/kavita-upload
   ```

2. **Adjust minimum free space:**
   ```yaml
   disk_protection:
     min_free_space_percent: 5.0  # Lower threshold
   ```

3. **Trigger manual cleanup:**
   ```bash
   curl -X POST http://localhost:5050/api/system/cleanup
   ```

4. **Increase disk size** or **move to larger partition**

### Problem: Quarantine Full Despite Low Disk Usage

**Symptoms:**
```
Error: Quarantine full
Message: Current: 10.5 GB, Limit: 10 GB
```

**Solutions:**

1. **Increase quarantine limit:**
   ```yaml
   disk_protection:
     max_quarantine_size_bytes: 21474836480  # 20 GB
   ```

2. **Enable auto-cleanup:**
   ```yaml
   disk_protection:
     auto_cleanup_enabled: true
     auto_cleanup_age_hours: 48  # 2 days
   ```

3. **Manually cleanup:**
   ```bash
   curl -X POST http://localhost:5050/api/system/cleanup
   ```

### Problem: Files Deleted Too Quickly

**Symptoms:**
```
Log: Auto-cleanup: Deleted old file (age: 1 days)
```

**Solutions:**

1. **Increase cleanup age:**
   ```yaml
   disk_protection:
     auto_cleanup_age_hours: 168  # 7 days
   ```

2. **Disable auto-cleanup:**
   ```yaml
   disk_protection:
     auto_cleanup_enabled: false
   ```

### Problem: Emergency Cleanup Triggered Unexpectedly

**Symptoms:**
```
Log: EMERGENCY CLEANUP TRIGGERED - Disk critically low
```

**Investigation:**

1. **Check disk usage:**
   ```bash
   df -h
   du -sh /path/to/kavita-upload/*
   ```

2. **Review logs for patterns:**
   ```bash
   grep "emergency_cleanup" logs/uploader.log
   ```

3. **Identify space hogs:**
   ```bash
   du -h /path/to/kavita-upload | sort -h | tail -20
   ```

**Prevention:**

1. **Increase emergency threshold:**
   ```yaml
   disk_protection:
     emergency_cleanup_threshold_percent: 8.0  # Higher threshold
   ```

2. **More aggressive auto-cleanup:**
   ```yaml
   disk_protection:
     auto_cleanup_age_hours: 24  # Delete after 1 day
     cleanup_interval_minutes: 15  # Every 15 minutes
   ```

### Problem: Disk Protection Not Working

**Symptoms:**
- No rejections despite low disk space
- No auto-cleanup running

**Check:**

1. **Verify enabled:**
   ```bash
   curl http://localhost:5050/api/config | jq '.disk_protection'
   ```

2. **Check logs for errors:**
   ```bash
   grep "disk_protection\|DiskMonitor" logs/uploader.log
   ```

3. **Restart service:**
   ```bash
   sudo systemctl restart kavita-uploader
   ```

---

## 📈 Capacity Planning

### Example Scenarios

**Scenario 1: Home Server (1 TB disk)**
```yaml
disk_protection:
  min_free_space_percent: 10.0  # 100 GB free
  reserve_space_bytes: 53687091200  # 50 GB
  max_quarantine_size_bytes: 107374182400  # 100 GB
  auto_cleanup_age_hours: 168  # 7 days
```

**Scenario 2: Small Office (500 GB disk, high traffic)**
```yaml
disk_protection:
  min_free_space_percent: 15.0  # 75 GB free
  reserve_space_bytes: 26843545600  # 25 GB
  max_quarantine_size_bytes: 53687091200  # 50 GB
  auto_cleanup_age_hours: 48  # 2 days
  cleanup_interval_minutes: 30  # Every 30 min
```

**Scenario 3: Enterprise (2 TB disk, very high traffic)**
```yaml
disk_protection:
  min_free_space_percent: 20.0  # 400 GB free
  reserve_space_bytes: 107374182400  # 100 GB
  max_quarantine_size_bytes: 214748364800  # 200 GB
  auto_cleanup_age_hours: 24  # 1 day
  cleanup_interval_minutes: 15  # Every 15 min
```

---

## 🎓 Summary

The disk protection system provides comprehensive defense against disk exhaustion:

✅ **Pre-upload validation** - Reject uploads proactively  
✅ **Quarantine limits** - Cap total quarantine size  
✅ **Automatic cleanup** - Delete old files regularly  
✅ **Emergency cleanup** - Aggressive cleanup when critical  
✅ **Monitoring & alerts** - Track usage and warn  
✅ **Configurable** - Adjust all thresholds  
✅ **Auditable** - Complete logging of all actions  

**Key Takeaway:** Enable disk protection, set reasonable limits for your disk size, and monitor regularly. Your system will be protected from DoS attacks via excessive uploads!

---

**For more information:**
- [Installation Guide](INSTALL.md)
- [Security Guide](SECURITY.md)

