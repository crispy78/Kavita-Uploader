# Logging Guide - Kavita SafeUploader

Complete guide to logging, monitoring, and troubleshooting.

## 📋 Table of Contents

1. [Log Configuration](#log-configuration)
2. [Log Formats](#log-formats)
3. [Viewing Logs](#viewing-logs)
4. [Filtering & Searching](#filtering--searching)
5. [Scan Tracking](#scan-tracking)
6. [Troubleshooting](#troubleshooting)

## Log Configuration

### Configuration File

Edit `config.yaml`:

```yaml
logging:
  level: "INFO"              # File log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
  console_level: "INFO"      # Console log level (can be different from file)
  format: "json"             # File format (always JSON for parsing)
  console_format: "text"     # Console format: "text" (human-readable) or "json"
  file: "logs/safeuploader.log"
  max_bytes: 10485760        # 10MB per file
  backup_count: 5            # Keep 5 rotated logs
```

### Environment Variables

Override via environment:

```bash
export LOGGING_LEVEL=DEBUG
export LOGGING_CONSOLE_LEVEL=WARNING
export LOGGING_CONSOLE_FORMAT=json
```

## Log Formats

### JSON Format (File Logs)

All file logs are in JSON for easy parsing:

```json
{
  "timestamp": "2024-01-01T12:00:00.123456Z",
  "level": "INFO",
  "logger": "safeuploader.scan",
  "module": "virustotal",
  "function": "scan_file",
  "message": "✓ Scan results: CLEAN - 0/70 engines detected threats",
  "upload_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "file_hash": "abc123...",
  "scan_phase": "complete",
  "scan_result": "clean",
  "malicious_count": 0,
  "total_engines": 70,
  "virustotal_link": "https://www.virustotal.com/gui/file/abc123..."
}
```

### Text Format (Console)

Human-readable console output:

```
[INFO] 2024-01-01 12:00:00 - ✓ Scan results: CLEAN - 0/70 engines detected threats (UUID:550e8400, Phase:complete, Result:clean)
```

## Viewing Logs

### Real-Time Log Viewing

**Follow all logs:**
```bash
tail -f logs/safeuploader.log
```

**Pretty-print JSON logs:**
```bash
tail -f logs/safeuploader.log | jq '.'
```

**Colorized output:**
```bash
tail -f logs/safeuploader.log | jq -C '.'
```

### Systemd Service Logs

```bash
# Follow logs
journalctl -u kavita-safeuploader -f

# View last 100 lines
journalctl -u kavita-safeuploader -n 100

# Show logs from last hour
journalctl -u kavita-safeuploader --since "1 hour ago"

# Show only errors
journalctl -u kavita-safeuploader -p err
```

## Filtering & Searching

### By Log Level

```bash
# Show only errors
jq 'select(.level == "ERROR")' logs/safeuploader.log

# Show warnings and errors
jq 'select(.level == "WARNING" or .level == "ERROR")' logs/safeuploader.log
```

### By Upload UUID

Track a specific file through the entire pipeline:

```bash
UUID="550e8400-e29b-41d4-a716-446655440000"
jq "select(.upload_uuid == \"$UUID\")" logs/safeuploader.log
```

### By Module/Function

```bash
# All scan-related logs
jq 'select(.module == "virustotal")' logs/safeuploader.log

# All upload operations
jq 'select(.function == "save_to_quarantine")' logs/safeuploader.log
```

### By Scan Phase

```bash
# Show hash checking
jq 'select(.scan_phase == "check_hash")' logs/safeuploader.log

# Show upload phase
jq 'select(.scan_phase == "upload")' logs/safeuploader.log

# Show polling
jq 'select(.scan_phase == "poll")' logs/safeuploader.log

# Show completed scans
jq 'select(.scan_phase == "complete")' logs/safeuploader.log
```

### By Scan Result

```bash
# Show infected files
jq 'select(.scan_result == "malicious")' logs/safeuploader.log

# Show clean files
jq 'select(.scan_result == "clean")' logs/safeuploader.log

# Show suspicious files
jq 'select(.scan_result == "suspicious")' logs/safeuploader.log
```

## Scan Tracking

### Complete Scan Workflow

Follow a file from upload to scan completion:

```bash
UUID="your-upload-uuid"

# Step 1: Upload
jq "select(.upload_uuid == \"$UUID\" and .message | contains(\"uploaded\"))" logs/safeuploader.log

# Step 2: Hash Check
jq "select(.upload_uuid == \"$UUID\" and .scan_phase == \"check_hash\")" logs/safeuploader.log

# Step 3: Upload to VirusTotal
jq "select(.upload_uuid == \"$UUID\" and .scan_phase == \"upload\")" logs/safeuploader.log

# Step 4: Polling
jq "select(.upload_uuid == \"$UUID\" and .scan_phase == \"poll\")" logs/safeuploader.log

# Step 5: Results
jq "select(.upload_uuid == \"$UUID\" and .scan_phase == \"complete\")" logs/safeuploader.log
```

### Scan Statistics

**Daily scan summary:**
```bash
# Count scans by result
jq -s 'group_by(.scan_result) | map({result: .[0].scan_result, count: length})' logs/safeuploader.log
```

**Average scan duration:**
```bash
# Show scan durations
jq 'select(.duration_ms != null) | {phase: .scan_phase, duration_ms}' logs/safeuploader.log
```

**Today's scans:**
```bash
TODAY=$(date +%Y-%m-%d)
jq "select(.timestamp | startswith(\"$TODAY\") and .scan_phase == \"complete\")" logs/safeuploader.log
```

## Troubleshooting

### Debug Mode

Enable verbose logging:

1. **Temporary (current session):**
```bash
# Stop service
sudo systemctl stop kavita-safeuploader

# Run with debug logging
cd /tmp/Kavita-upload/backend
source venv/bin/activate
LOGGING_LEVEL=DEBUG uvicorn app.main:app --host 0.0.0.0 --port 5050
```

2. **Permanent:**

Edit `config.yaml`:
```yaml
logging:
  level: "DEBUG"
  console_level: "DEBUG"
```

Restart:
```bash
sudo systemctl restart kavita-safeuploader
```

### Common Issues

#### 1. Scan Not Starting

```bash
# Check if file uploaded
jq 'select(.message | contains("quarantined"))' logs/safeuploader.log | tail -1

# Check for scan trigger
jq 'select(.scan_phase == "check_hash")' logs/safeuploader.log | tail -5

# Check for errors
jq 'select(.level == "ERROR")' logs/safeuploader.log | tail -10
```

#### 2. VirusTotal API Issues

```bash
# Check API key errors
jq 'select(.message | contains("API key"))' logs/safeuploader.log

# Check rate limits
jq 'select(.status_code == 429)' logs/safeuploader.log

# Check timeouts
jq 'select(.message | contains("timeout"))' logs/safeuploader.log
```

#### 3. Slow Scans

```bash
# Find slow polls
jq 'select(.scan_phase == "poll" and .attempt > 10)' logs/safeuploader.log

# Check durations
jq 'select(.duration_ms > 5000)' logs/safeuploader.log
```

### Log Rotation

Logs automatically rotate when reaching 10MB. View rotated logs:

```bash
ls -lh logs/safeuploader.log*
# safeuploader.log       (current)
# safeuploader.log.1     (previous)
# safeuploader.log.2
# ... (up to .5)
```

View old logs:
```bash
cat logs/safeuploader.log.1 | jq '.'
```

### Exporting Logs

**Export today's scans:**
```bash
TODAY=$(date +%Y-%m-%d)
jq "select(.timestamp | startswith(\"$TODAY\"))" logs/safeuploader.log > scans-$TODAY.json
```

**Export infected files:**
```bash
jq 'select(.scan_result == "malicious")' logs/safeuploader.log > infected-files.json
```

**Generate CSV report:**
```bash
jq -r '
  select(.scan_phase == "complete") |
  [.timestamp, .upload_uuid, .uploaded_file, .scan_result, .malicious_count, .total_engines] |
  @csv
' logs/safeuploader.log > scan-report.csv
```

## Log Fields Reference

### Core Fields (All Logs)

| Field | Description | Example |
|-------|-------------|---------|
| `timestamp` | UTC timestamp | `2024-01-01T12:00:00Z` |
| `level` | Log level | `INFO`, `ERROR` |
| `logger` | Logger name | `safeuploader.scan` |
| `module` | Python module | `virustotal` |
| `function` | Function name | `scan_file` |
| `message` | Log message | `File uploaded` |

### Upload Fields

| Field | Description |
|-------|-------------|
| `upload_uuid` | Unique file identifier |
| `uploaded_file` | Original filename |
| `file_size` | Size in bytes |
| `file_hash` | SHA256 hash |
| `status` | Current status |
| `ip_address` | Client IP |

### Scan Fields

| Field | Description |
|-------|-------------|
| `scan_phase` | Current phase: `check_hash`, `upload`, `poll`, `complete` |
| `scan_result` | Result: `clean`, `malicious`, `suspicious`, `pending` |
| `analysis_id` | VirusTotal analysis ID |
| `malicious_count` | Engines detecting threats |
| `suspicious_count` | Engines flagging as suspicious |
| `total_engines` | Total engines that scanned |
| `virustotal_link` | Link to full report |
| `attempt` | Current polling attempt |
| `max_attempts` | Maximum polling attempts |
| `duration_ms` | Operation duration in milliseconds |

## Performance Monitoring

### Track API Usage

```bash
# Count VirusTotal API calls today
TODAY=$(date +%Y-%m-%d)
jq "select(.timestamp | startswith(\"$TODAY\") and .scan_phase == \"upload\")" logs/safeuploader.log | wc -l

# Count hash checks (free lookups)
jq "select(.timestamp | startswith(\"$TODAY\") and .scan_phase == \"check_hash\")" logs/safeuploader.log | wc -l
```

### Monitor Upload Volume

```bash
# Files uploaded today
TODAY=$(date +%Y-%m-%d)
jq "select(.timestamp | startswith(\"$TODAY\") and .message | contains(\"quarantined\"))" logs/safeuploader.log | wc -l

# Average file size
jq -s 'map(select(.file_size != null) | .file_size) | add / length' logs/safeuploader.log
```

## Alert Setup

### Email on Infected Files

Create `/usr/local/bin/check-infected.sh`:

```bash
#!/bin/bash
INFECTED=$(jq -r 'select(.scan_result == "malicious") | select(.timestamp | startswith("'$(date +%Y-%m-%d)'"))' /path/to/logs/safeuploader.log)

if [ -n "$INFECTED" ]; then
    echo "$INFECTED" | mail -s "Infected Files Detected" admin@example.com
fi
```

Add to crontab:
```bash
0 */6 * * * /usr/local/bin/check-infected.sh
```

### Slack Notifications

Use webhook to send scan results:

```bash
#!/bin/bash
WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

tail -n 1 logs/safeuploader.log | jq 'select(.scan_phase == "complete")' | while read -r line; do
    RESULT=$(echo "$line" | jq -r '.scan_result')
    FILE=$(echo "$line" | jq -r '.uploaded_file')
    
    curl -X POST "$WEBHOOK_URL" -H 'Content-Type: application/json' -d "{
        \"text\": \"Scan complete: $FILE - $RESULT\"
    }"
done
```

## Best Practices

1. **Keep DEBUG logs enabled during initial setup**
2. **Switch to INFO for production**
3. **Monitor logs daily for first week**
4. **Set up alerts for infected files**
5. **Review ERROR logs regularly**
6. **Export monthly reports**
7. **Archive old logs**

---

**Pro Tip:** Use `jq` cheat sheet: https://stedolan.github.io/jq/manual/



