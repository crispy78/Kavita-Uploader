# VirusTotal Setup Guide

Complete guide to configuring VirusTotal scanning for Kavita Uploader.

## 📋 Prerequisites

- Ubuntu 24.04 LTS
- Kavita Uploader installed
- Internet connection

## 🔑 Getting a VirusTotal API Key

### Free Tier (Recommended for Personal Use)

1. **Visit VirusTotal**
   - Go to: https://www.virustotal.com/gui/join-us

2. **Create Account**
   - Sign up with email or Google/GitHub account
   - Verify your email address

3. **Get API Key**
   - After logging in, go to your profile
   - Navigate to "API Key" section
   - Copy your API key (64-character hexadecimal string)

### Free Tier Limits

- ✅ 4 requests per minute
- ✅ 500 requests per day
- ✅ 178 GB per month upload quota
- ✅ Access to 70+ antivirus engines

**Perfect for personal Kavita libraries!**

### Premium Tier (Optional)

For heavy usage:
- 1,000 requests per minute
- No daily limits
- Priority support
- Advanced features

Visit: https://www.virustotal.com/gui/premium

## ⚙️ Configuration

### Method 1: During Installation

When running `./install.sh`, you'll see:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  VirusTotal Integration (Step 2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VirusTotal scans files for malware using 70+ antivirus engines.
Get a free API key at: https://www.virustotal.com/gui/join-us

Features:
  • Automatic malware scanning
  • Hash-based duplicate detection
  • Reuse of previous scan results
  • Free tier: 4 requests/minute, 500/day

Enable VirusTotal scanning? (y/n) [n]: y
Enter your VirusTotal API Key: ****
Confirm API Key: ****
```

The installer will:
- Validate your key
- Store it securely in `config.yaml`
- Enable scanning automatically

### Method 2: Manual Configuration

Edit `config.yaml`:

```yaml
scanning:
  enabled: true
  provider: virustotal
  virustotal_api_key: "YOUR_64_CHARACTER_API_KEY_HERE"
  virustotal_timeout: 60
  polling_interval_sec: 30
  max_retries: 20
  auto_delete_infected: false
  auto_skip_known_hashes: true
```

**Important:** Replace `YOUR_64_CHARACTER_API_KEY_HERE` with your actual key.

### Method 3: Environment Variable

For production deployments:

```bash
export SCANNING_ENABLED=true
export SCANNING_VIRUSTOTAL_API_KEY="your_key_here"
```

Add to systemd service:

```bash
sudo nano /etc/systemd/system/kavita-uploader.service
```

Add under `[Service]`:
```ini
Environment="SCANNING_ENABLED=true"
Environment="SCANNING_VIRUSTOTAL_API_KEY=your_key_here"
```

Reload and restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart kavita-uploader
```

## 🧪 Testing Your Setup

### 1. Check Configuration

```bash
# View current config
cat config.yaml | grep -A 8 "scanning:"

# Test API key (from backend directory)
cd backend
source venv/bin/activate
python -c "
from app.virustotal import VirusTotalScanner
import asyncio
scanner = VirusTotalScanner()
result = asyncio.run(scanner.check_hash('44d88612fea8a8f36de82e1278abb02f'))
print('API Key Valid!' if result[0] else 'API Key Invalid or Network Error')
"
```

### 2. Upload Test File

1. Access web UI: http://your-server:5050
2. Upload a small, safe PDF or EPUB
3. Watch scan progress automatically start
4. Verify results appear in UI

### 3. Check Logs

```bash
# View scan logs
tail -f logs/uploader.log | jq 'select(.message | contains("Scan"))'

# View specific scan result
cat logs/scans/<upload-uuid>.json | jq .
```

## 📊 Understanding Scan Results

### Status Values

| Status | Meaning | Color | Action |
|--------|---------|-------|--------|
| `clean` | No threats detected | 🟢 Green | Continue to metadata |
| `safe` | Alias for clean | 🟢 Green | Continue |
| `undetected` | File not recognized | 🟡 Yellow | Usually safe |
| `suspicious` | 3+ engines flagged | 🟡 Yellow | Manual review |
| `malicious` | Threats detected | 🔴 Red | Quarantine/delete |
| `infected` | Alias for malicious | 🔴 Red | Block |
| `pending` | Scan in progress | ⏳ Blue | Wait |
| `error` | Scan failed | ⚠️ Orange | Retry |

### Reading Scan Details

```json
{
  "status": "clean",
  "malicious_count": 0,
  "suspicious_count": 0,
  "harmless_count": 70,
  "total_engines": 70,
  "scan_date": "2024-01-01T12:00:00",
  "file_hash": "abc123...",
  "virustotal_link": "https://www.virustotal.com/gui/file/abc123..."
}
```

- **malicious_count**: Number of engines detecting threats
- **total_engines**: Total engines that scanned the file
- **virustotal_link**: View full report on VirusTotal website

## ⚡ Optimization Tips

### 1. Hash-Based Duplicate Detection

**Enabled by default** - saves API credits:

```yaml
scanning:
  auto_skip_known_hashes: true  # Reuse previous scans

duplicate_detection:
  enabled: true
  check_by_hash: true
```

**How it works:**
1. First upload of `book.epub` → Full VirusTotal scan
2. Second upload of same file → Instant result (no API call!)
3. Even with different filename → Recognized by hash

**Savings:** Up to 99% of API calls for duplicate files

### 2. Polling Configuration

Adjust based on file size:

```yaml
scanning:
  polling_interval_sec: 30  # Check every 30 seconds
  max_retries: 20           # Try for 10 minutes max
```

**Small files (<1 MB):** 15-30 seconds  
**Medium files (1-10 MB):** 30-60 seconds  
**Large files (>10 MB):** 60-90 seconds

### 3. Rate Limit Management

Free tier: 4 req/min = ~240 files/hour

**Strategies:**
- Enable `auto_skip_known_hashes` ✅
- Upload during off-peak hours
- Batch similar files together
- Consider premium tier for large libraries

## 🚨 Troubleshooting

### API Key Not Working

**Error:** "VirusTotal API key not configured"

**Solutions:**
```bash
# 1. Check config
grep virustotal_api_key config.yaml

# 2. Verify key format (should be 64 hex characters)
echo -n "YOUR_KEY" | wc -c  # Should output: 64

# 3. Test directly
curl https://www.virustotal.com/api/v3/files/44d88612fea8a8f36de82e1278abb02f \
  -H "x-apikey: YOUR_KEY"

# Should return JSON, not 401 Unauthorized
```

### Rate Limit Exceeded

**Error:** HTTP 429 or "Too many requests"

**Solutions:**
- Wait 1 minute
- Check daily quota: https://www.virustotal.com/gui/user/YOUR_USERNAME/api-usage
- Enable hash checking to reduce requests
- Consider premium tier

### Scan Timeout

**Error:** "Analysis timeout after 20 attempts"

**Solutions:**
```yaml
scanning:
  polling_interval_sec: 60  # Increase interval
  max_retries: 30           # Increase max attempts
```

### Hash Already Exists

**Not an error!** This is optimization working:

```
Hash found in VirusTotal
Reusing previous scan results
```

File was already scanned (by you or someone else). Result is instant and free!

## 🔐 Security Best Practices

### 1. Protect API Key

```bash
# Config file permissions
chmod 600 config.yaml

# Environment variable (better for production)
export SCANNING_VIRUSTOTAL_API_KEY="key"
# Add to ~/.bashrc for persistence

# Never commit to Git
echo "config.yaml" >> .gitignore
```

### 2. Log File Security

Scan logs are automatically created with `0600` permissions:

```bash
ls -la logs/scans/
# -rw------- 1 user user ... <uuid>.json
```

API key is **never** written to logs.

### 3. Network Security

VirusTotal connections use HTTPS:
- Certificate verification enabled
- TLS 1.2+ required
- No sensitive data in URLs

## 📈 Monitoring Usage

### Check API Usage

1. **VirusTotal Dashboard:**
   - Login to: https://www.virustotal.com
   - Go to: Profile → API Key → Usage

2. **Local Logs:**
```bash
# Count scans today
grep "File uploaded to VirusTotal" logs/uploader.log | \
  grep "$(date +%Y-%m-%d)" | wc -l

# Count hash reuses (saved requests)
grep "Using existing VirusTotal report" logs/uploader.log | wc -l
```

### Estimate Monthly Usage

```python
# Calculate for your library
files_per_month = 100
duplicate_rate = 0.30  # 30% duplicates
unique_files = files_per_month * (1 - duplicate_rate)
requests_needed = unique_files * 1  # 1 request per file

print(f"Estimated requests: {requests_needed}/month")
print(f"Free tier limit: 500/day = 15,000/month")
print(f"Usage: {(requests_needed/15000)*100:.1f}%")
```

## 🎯 Advanced Configuration

### Auto-Delete Infected Files

```yaml
scanning:
  auto_delete_infected: true  # ⚠️ Use with caution!
```

**Warning:** Infected files are permanently deleted. Consider manual review first.

### Custom Timeout

For slow connections:

```yaml
scanning:
  virustotal_timeout: 120  # 2 minutes for upload
```

### Disable Scanning Temporarily

```yaml
scanning:
  enabled: false
```

Or environment variable:
```bash
export SCANNING_ENABLED=false
```

## 📞 Support

### VirusTotal Support
- Community: https://support.virustotal.com
- Premium support: support@virustotal.com

### Uploader Issues
- Check logs: `logs/uploader.log`
- API docs: http://your-server:5050/docs
- GitHub Issues: [your-repo]/issues

## ✅ Setup Checklist

- [ ] Created VirusTotal account
- [ ] Obtained API key
- [ ] Added key to `config.yaml`
- [ ] Set `scanning.enabled: true`
- [ ] Restarted application
- [ ] Tested with sample file
- [ ] Verified scan results
- [ ] Checked logs for errors
- [ ] Secured API key (0600 permissions)
- [ ] Documented key location
- [ ] Monitored API usage

---

**Congratulations! VirusTotal scanning is now active.** 🎉

Your Kavita library is now protected with enterprise-grade malware detection!



