# Security Policy

## Security Design Overview

Kavita Uploader implements a defense-in-depth security approach with multiple layers of protection.

## Security Features

### 1. Upload Validation (Step 1 - Implemented)

#### File Size Validation
- Configurable maximum file size (default: 25 MB)
- Backend enforcement prevents large file attacks
- Client-side pre-validation for UX

#### File Type Validation
- Extension whitelist enforcement
- MIME type verification using libmagic
- Dual validation (extension + MIME) prevents bypass

#### Content Validation
- Empty file rejection
- File content integrity checks
- SHA256 hash calculation for all uploads

### 2. Filename Security

#### Sanitization Process
```python
# Path traversal prevention
filename = os.path.basename(filename)  # Remove directory components

# Character sanitization
filename = re.sub(r'[^\w\s\-\.]', '_', filename)  # Allow only safe chars

# Length limiting
if len(name) > 200:
    name = name[:200]  # Prevent buffer overflow attacks
```

#### UUID-based Storage
- Files stored with random UUID names
- Original filename stored in database only
- Prevents filename-based attacks

### 3. File System Security

#### Quarantine Isolation
- Separate quarantine directory
- Files never directly accessible via web routes
- Temporary storage until validation complete

#### Restrictive Permissions
```bash
Quarantine directory: 0700 (owner only, no group/world access)
Quarantined files:    0600 (owner read/write only)
```

#### Directory Structure
```
/app
├── quarantine/        # 0700 - Untrusted uploads
├── unsorted/          # 0700 - Validated, awaiting organization
├── library/           # 0755 - Final destination (Kavita readable)
└── logs/              # 0755 - Log files
```

### 4. Rate Limiting

- IP-based rate limiting using slowapi
- Configurable limits per endpoint
- Default: 10 uploads per minute per IP
- Protection against DoS attacks

### 5. Logging and Auditing

#### Structured JSON Logging
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "logger": "uploader",
  "message": "File uploaded successfully",
  "upload_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "book.epub",
  "file_size": 1048576,
  "ip_address": "192.168.1.100",
  "status": "quarantined"
}
```

#### What We Log
- All upload attempts (success and failure)
- IP addresses for rate limiting and audit
- File metadata (name, size, type, hash)
- Processing pipeline stages
- Errors with stack traces

### 6. Future Security Features (Steps 2-4)

#### Step 2: Virus Scanning
- VirusTotal API integration
- Automatic malware detection
- Infected file quarantine
- Scan result tracking

#### Step 3: Metadata Validation
- E-book metadata extraction
- Content validation
- Embedded script detection (future)

#### Step 4: Duplicate Detection
- Hash-based duplicate prevention
- Size comparison
- Filename collision handling

## Known Security Considerations

### Current Limitations

1. **CSRF Protection**: Configured but not fully implemented
   - Framework support in place
   - Frontend token integration pending
   - Low risk for file upload endpoint

2. **HTTPS/TLS**: Not included
   - Should be terminated at reverse proxy (nginx/Caddy)
   - See deployment recommendations below

3. **Authentication**: Not implemented
   - Designed for trusted network use
   - Should be behind reverse proxy with auth
   - Or implement authentication in Step 5

4. **Virus Scanning**: Step 2 not yet implemented
   - Manual review of uploaded files recommended
   - VirusTotal integration coming in Step 2

## Deployment Recommendations

### 1. Network Isolation

```bash
# Firewall: Only allow from trusted networks
sudo ufw allow from 192.168.1.0/24 to any port 5050

# Or bind to localhost and use reverse proxy
SERVER_HOST=127.0.0.1
```

### 2. Reverse Proxy (Recommended)

#### Nginx Example
```nginx
server {
    listen 443 ssl http2;
    server_name upload.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # File upload size
    client_max_body_size 26M;
    
    location / {
        proxy_pass http://localhost:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Caddy Example
```caddy
upload.example.com {
    reverse_proxy localhost:5050
    
    # Automatic HTTPS
    tls your@email.com
    
    # Security headers
    header {
        X-Frame-Options "SAMEORIGIN"
        X-Content-Type-Options "nosniff"
        X-XSS-Protection "1; mode=block"
    }
}
```

### 3. Authentication Layer

#### Basic Auth (Nginx)
```nginx
location / {
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:5050;
}
```

#### OAuth2 Proxy
Use oauth2-proxy for Google/GitHub/etc authentication:
```bash
docker run -p 4180:4180 \
  -e OAUTH2_PROXY_CLIENT_ID=xxx \
  -e OAUTH2_PROXY_CLIENT_SECRET=xxx \
  quay.io/oauth2-proxy/oauth2-proxy
```

### 4. File System Security

```bash
# Run as dedicated user
sudo useradd -r -s /bin/false kavita-upload

# Restrict directory permissions
sudo chown -R kavita-upload:kavita-upload /app
sudo chmod 700 /app/quarantine /app/unsorted

# AppArmor/SELinux policies (advanced)
# Confine the application to specific directories
```

### 5. Monitoring and Alerting

```bash
# Monitor logs for suspicious activity
tail -f logs/uploader.log | jq 'select(.level == "ERROR")'

# Alert on failed uploads
grep "Upload failed" logs/uploader.log | mail -s "Upload Failures" admin@example.com

# Monitor quarantine directory size
watch -n 60 'du -sh quarantine/'
```

## Reporting Security Issues

If you discover a security vulnerability, please:

1. **DO NOT** open a public GitHub issue
2. Email security concerns to: security@example.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and provide a fix timeline.

## Security Update Policy

- **Critical**: Patch within 24 hours
- **High**: Patch within 7 days
- **Medium**: Patch within 30 days
- **Low**: Patch in next release

## Security Checklist for Deployment

- [ ] Change default `server.secret_key` in config.yaml
- [ ] Use HTTPS with valid certificate
- [ ] Enable firewall rules
- [ ] Configure rate limiting appropriately
- [ ] Set up authentication (reverse proxy or application level)
- [ ] Enable VirusTotal scanning (Step 2)
- [ ] Review and restrict CORS origins
- [ ] Set up log rotation and monitoring
- [ ] Regular security updates (apt update && apt upgrade)
- [ ] Backup configuration and database
- [ ] Test disaster recovery procedures
- [ ] Document access control policies
- [ ] Set up intrusion detection (fail2ban, etc.)

## Compliance Considerations

### GDPR/Privacy
- IP addresses are logged for security purposes
- File metadata stored in database
- Implement data retention policy
- Provide user data deletion mechanism

### File Retention
```yaml
# Example retention policy
retention:
  quarantine_days: 7      # Delete after 7 days if not processed
  logs_days: 90           # Keep logs for 90 days
  database_cleanup: true  # Remove old records
```

## Security Best Practices

1. **Principle of Least Privilege**: Run with minimal permissions
2. **Defense in Depth**: Multiple security layers
3. **Fail Secure**: Deny by default
4. **Keep Updated**: Regular dependency updates
5. **Audit Regularly**: Review logs and access patterns
6. **Test Security**: Run security scans and penetration tests
7. **Document Everything**: Keep security documentation current

## Security Testing

```bash
# Run security-focused tests
pytest tests/test_upload.py -k security

# Check for known vulnerabilities
pip install safety
safety check

# Scan Docker image (if using containers)
docker scan kavita-uploader

# Static analysis
pip install bandit
bandit -r backend/app/
```

## References

- [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [VirusTotal API Documentation](https://developers.virustotal.com/reference)
- [12-Factor App Configuration](https://12factor.net/config)

---

Last Updated: 2024-10-28



