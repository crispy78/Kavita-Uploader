#!/bin/bash
# Kavita SafeUploader Installer for Ubuntu 24.04 LTS
# This script automates the installation and configuration process

set -e  # Exit on any error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on Ubuntu 24.04
check_os() {
    log_info "Checking operating system..."
    
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [ "$ID" = "ubuntu" ] && [ "$VERSION_ID" = "24.04" ]; then
            log_success "Ubuntu 24.04 LTS detected"
        else
            log_warning "This script is designed for Ubuntu 24.04 LTS (detected: $ID $VERSION_ID)"
            read -p "Continue anyway? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    else
        log_error "Cannot determine OS version"
        exit 1
    fi
}

# Check if running as non-root user
check_user() {
    if [ "$EUID" -eq 0 ]; then
        log_error "Please do not run this script as root"
        log_info "Run as your regular user. The script will use sudo when needed."
        exit 1
    fi
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    sudo apt-get update
    
    # Install base dependencies (without nodejs/npm yet)
    sudo apt-get install -y \
        python3.12 \
        python3.12-venv \
        python3-pip \
        libmagic1 \
        curl \
        git \
        unzip \
        unrar
    
    log_success "System dependencies installed"
}

# Install Node.js LTS (if needed)
install_nodejs() {
    log_info "Checking Node.js version..."
    
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node -v | cut -d 'v' -f 2 | cut -d '.' -f 1)
        if [ "$NODE_VERSION" -ge 18 ]; then
            log_success "Node.js $(node -v) detected"
            
            # Check if npm is available
            if command -v npm &> /dev/null; then
                log_success "npm $(npm -v) detected"
                return
            fi
        fi
    fi
    
    log_info "Installing Node.js 20 LTS from NodeSource..."
    log_info "This includes npm bundled with Node.js"
    
    # NodeSource setup script
    if [ ! -f /etc/apt/sources.list.d/nodesource.list ]; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    fi
    
    # Install nodejs (includes npm)
    sudo apt-get install -y nodejs
    
    log_success "Node.js installed: $(node -v)"
    log_success "npm installed: $(npm -v)"
}

# Setup Python virtual environment
setup_python_venv() {
    log_info "Setting up Python virtual environment..."
    
    cd backend
    
    # Check if venv exists and is functional
    if [ -d "venv" ]; then
        log_info "Checking existing virtual environment..."
        # Test if venv is functional
        if [ -x "venv/bin/python" ]; then
            log_info "Virtual environment exists and is functional"
        else
            log_warning "Virtual environment exists but is broken, recreating..."
            rm -rf venv
            python3.12 -m venv venv
            log_success "Virtual environment recreated"
        fi
    else
        log_info "Creating virtual environment..."
        python3.12 -m venv venv
        log_success "Virtual environment created"
    fi
    
    # Always activate the venv before installing packages
    source venv/bin/activate
    
    # Verify we're in the venv
    which pip
    
    # Upgrade pip and install dependencies within venv
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    
    log_success "Python dependencies installed"
    
    deactivate
    cd ..
}

# Setup frontend
setup_frontend() {
    log_info "Setting up frontend..."
    
    cd frontend
    
    # Always do a clean install to avoid corrupted node_modules issues
    # Especially with symlinks that can break when copying between systems
    if [ -d "node_modules" ]; then
        log_info "Removing existing node_modules to ensure clean install..."
        rm -rf node_modules package-lock.json
    fi
    
    log_info "Installing frontend dependencies (this may take a minute)..."
    npm install
    
    # Verify installation
    if [ -f "node_modules/vite/dist/node/cli.js" ]; then
        log_success "Frontend dependencies installed successfully"
    else
        log_error "Frontend installation failed - vite not found"
        exit 1
    fi
    
    cd ..
}

# Create directories with secure permissions
create_directories() {
    log_info "Creating directories..."
    
    mkdir -p backend/quarantine
    chmod 700 backend/quarantine
    
    mkdir -p backend/unsorted
    chmod 700 backend/unsorted
    
    mkdir -p backend/library
    chmod 755 backend/library
    
    mkdir -p backend/logs
    chmod 755 backend/logs
    
    # Create log subdirectories for Step 2 and Step 3
    mkdir -p backend/logs/files
    chmod 755 backend/logs/files
    
    mkdir -p backend/logs/scans
    chmod 755 backend/logs/scans
    
    log_success "Directories created with secure permissions"
}

# Clean up old database (for fresh install)
cleanup_old_database() {
    log_info "Checking for old database..."
    
    if [ -f backend/safeuploader.db ]; then
        log_warning "Found existing database from previous installation"
        read -p "Delete old database? This will erase all upload records (files in quarantine will remain). (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            BACKUP_NAME="backend/safeuploader.db.backup.$(date +%Y%m%d_%H%M%S)"
            mv backend/safeuploader.db "$BACKUP_NAME"
            log_success "Old database backed up to: $BACKUP_NAME"
        else
            log_info "Keeping existing database (automatic migration will add new columns)"
        fi
    else
        log_info "No existing database found (clean install)"
    fi
}

# Generate configuration
generate_config() {
    log_info "Generating configuration..."
    
    # Generate secret key
    SECRET_KEY=$(openssl rand -hex 32)
    
    # Prompt for configuration
    echo ""
    echo "=== Configuration Setup ==="
    echo ""
    
    read -p "Server port [5050]: " SERVER_PORT
    SERVER_PORT=${SERVER_PORT:-5050}
    
    read -p "Path to Kavita library folder [./library]: " LIBRARY_PATH
    LIBRARY_PATH=${LIBRARY_PATH:-./library}
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  VirusTotal Integration (Step 2)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "VirusTotal scans files for malware using 70+ antivirus engines."
    echo "Get a free API key at: https://www.virustotal.com/gui/join-us"
    echo ""
    echo "Features:"
    echo "  • Automatic malware scanning"
    echo "  • Hash-based duplicate detection"
    echo "  • Reuse of previous scan results"
    echo "  • Free tier: 4 requests/minute, 500/day"
    echo ""
    
    read -p "Enable VirusTotal scanning? (y/n) [n]: " ENABLE_SCANNING
    ENABLE_SCANNING=${ENABLE_SCANNING:-n}
    
    if [[ $ENABLE_SCANNING =~ ^[Yy]$ ]]; then
        echo ""
        read -s -p "Enter your VirusTotal API Key: " VIRUSTOTAL_KEY
        echo ""
        read -s -p "Confirm API Key: " VIRUSTOTAL_KEY_CONFIRM
        echo ""
        
        if [ "$VIRUSTOTAL_KEY" != "$VIRUSTOTAL_KEY_CONFIRM" ]; then
            log_warning "API keys do not match. Scanning will be disabled."
            SCANNING_ENABLED="false"
            VIRUSTOTAL_KEY=""
        elif [ -z "$VIRUSTOTAL_KEY" ]; then
            log_warning "No API key provided. Scanning will be disabled."
            SCANNING_ENABLED="false"
        else
            SCANNING_ENABLED="true"
            log_success "VirusTotal API key configured"
        fi
    else
        SCANNING_ENABLED="false"
        VIRUSTOTAL_KEY=""
        log_info "Scanning disabled - you can enable it later in config.yaml"
    fi
    
    # Create config.yaml
    cat > config.yaml <<EOF
# Kavita SafeUploader Configuration
# Generated by installer on $(date)

server:
  host: "0.0.0.0"
  port: ${SERVER_PORT}
  debug: false
  cors_origins:
    - "http://localhost:${SERVER_PORT}"
    - "http://localhost:5173"
  secret_key: "${SECRET_KEY}"

folders:
  quarantine: "./quarantine"
  unsorted: "./unsorted"
  library: "${LIBRARY_PATH}"

upload:
  max_file_size_mb: 25
  allowed_extensions:
    - "epub"
    - "pdf"
    - "cbz"
    - "cbr"
    - "mobi"
    - "azw3"
  allowed_mime_types:
    - "application/epub+zip"
    - "application/pdf"
    - "application/x-cbr"
    - "application/x-cbz"
    - "application/zip"
    - "application/vnd.amazon.ebook"
    - "application/x-mobipocket-ebook"

security:
  enable_rate_limiting: true
  rate_limit_uploads_per_minute: 10
  enable_csrf_protection: true
  file_permissions_mode: 384  # 0o600 in decimal
  directory_permissions_mode: 448  # 0o700 in decimal
  sanitize_filenames: true

scanning:
  enabled: ${SCANNING_ENABLED}
  provider: virustotal
  virustotal_api_key: "${VIRUSTOTAL_KEY}"
  virustotal_timeout: 60
  polling_interval_sec: 30
  max_retries: 20
  auto_delete_infected: false
  auto_skip_known_hashes: true

metadata:
  enabled: true
  extract_on_upload: false
  allow_user_editing: true
  required_fields:
    - "title"
    - "author"
  auto_save_on_no_changes: true
  preview_settings:
    max_pages: 3
    width: 1024
    height: 768

duplicate_detection:
  enabled: true
  hash_algorithm: sha256
  check_by_hash: true
  check_by_size: true
  check_by_name: false
  discard_exact_hash: true
  rename_duplicates: true
  rename_pattern: "{name}_{timestamp}{ext}"

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

moving:
  enabled: true
  unsorted_dir: "./unsorted"
  kavita_library_dirs:
    - "${LIBRARY_PATH}"
  rename_on_name_conflict: true
  rename_pattern: "{title} - {author} (duplicate_{timestamp}){ext}"
  discard_on_exact_duplicate: true
  keep_duplicate_log: true
  verify_integrity_post_move: true
  dry_run: false
  checksum_manifest: true
  manifest_path: "logs/manifest.csv"
  log_moves: true
  atomic_operations: true
  cleanup_quarantine_on_success: true
  notification:
    email_enabled: false
    email_recipients: []
    webhook_enabled: false
    webhook_url: ""

disk_protection:
  enabled: true
  min_free_space_percent: 10.0
  reserve_space_bytes: 1073741824
  max_quarantine_size_bytes: 10737418240
  max_single_upload_size_mb: 100
  auto_cleanup_enabled: true
  auto_cleanup_age_hours: 72
  cleanup_interval_minutes: 60
  emergency_cleanup_threshold_percent: 5.0
  alert_threshold_percent: 15.0

api_protection:
  enabled: true
  require_header: true
  header_name: "X-UI-Request"
  header_value: "1"
  disable_docs: true
  allow_docs_in_debug: true

logging:
  level: "INFO"
  format: "json"
  console_format: "text"
  console_level: "INFO"
  file: "logs/safeuploader.log"
  max_bytes: 10485760
  backup_count: 5
EOF
    
    log_success "Configuration file created: config.yaml"
}

# Create systemd service
create_systemd_service() {
    log_info "Creating systemd service..."
    
    INSTALL_DIR=$(pwd)
    USER=$(whoami)
    
    sudo tee /etc/systemd/system/kavita-safeuploader.service > /dev/null <<EOF
[Unit]
Description=Kavita SafeUploader
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${INSTALL_DIR}
Environment="PATH=${INSTALL_DIR}/backend/venv/bin"
ExecStart=${INSTALL_DIR}/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${SERVER_PORT:-5050}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    
    log_success "Systemd service created"
    log_info "To enable auto-start: sudo systemctl enable kavita-safeuploader"
    log_info "To start service: sudo systemctl start kavita-safeuploader"
}

# Build frontend for production
build_frontend() {
    log_info "Building frontend for production..."
    
    # Ensure we're in the right directory
    if [ ! -d "frontend" ]; then
        log_error "Frontend directory not found!"
        exit 1
    fi
    
    cd frontend
    
    # Clean old build
    if [ -d "dist" ]; then
        log_info "Cleaning old build..."
        rm -rf dist
    fi
    
    # Verify node_modules exists
    if [ ! -d "node_modules" ]; then
        log_error "node_modules not found! Run setup_frontend first."
        exit 1
    fi
    
    # Ensure node_modules/.bin has execute permissions
    if [ -d "node_modules/.bin" ]; then
        chmod -R +x node_modules/.bin/
    fi
    
    # Build frontend with explicit error checking
    log_info "Running npm run build..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if ! npm run build 2>&1; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        log_error "Frontend build failed! Check output above for errors."
        cd ..
        exit 1
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Verify build output exists
    if [ ! -f "dist/index.html" ]; then
        log_error "Build completed but dist/index.html not found!"
        cd ..
        exit 1
    fi
    
    # Count built files for verification
    local file_count=$(find dist -type f | wc -l)
    log_info "Build created $file_count files in dist/"
    
    cd ..
    
    log_success "Frontend built successfully"
}

# Display completion message
# Verify installation
verify_installation() {
    log_info "Verifying installation..."
    
    local errors=0
    
    # Check Python dependencies
    log_info "Checking Python dependencies..."
    cd backend
    source venv/bin/activate
    
    python3 << 'EOF'
import sys
try:
    import fastapi
    import sqlalchemy
    import aiofiles
    import magic
    import fitz  # PyMuPDF
    import ebooklib
    from PIL import Image
    import rarfile
except ImportError as e:
    print(f"ERROR: Missing dependency: {e}")
    sys.exit(1)
EOF
    
    if [ $? -eq 0 ]; then
        log_success "All Python dependencies installed"
    else
        log_error "Missing Python dependencies"
        errors=$((errors + 1))
    fi
    
    cd ..
    
    # Check frontend build
    log_info "Checking frontend build..."
    if [ -f "frontend/dist/index.html" ]; then
        log_success "Frontend built successfully"
    else
        log_error "Frontend build missing"
        errors=$((errors + 1))
    fi
    
    # Check required directories
    log_info "Checking required directories..."
    local all_dirs_ok=true
    for dir in backend/quarantine backend/unsorted backend/logs backend/logs/files backend/logs/scans; do
        if [ ! -d "$dir" ]; then
            log_error "Missing directory: $dir"
            all_dirs_ok=false
            errors=$((errors + 1))
        fi
    done
    
    if [ "$all_dirs_ok" = true ]; then
        log_success "All required directories present"
    fi
    
    # Check config file
    log_info "Checking configuration..."
    if [ -f "config.yaml" ]; then
        log_success "Configuration file created"
    else
        log_error "Configuration file missing"
        errors=$((errors + 1))
    fi
    
    echo ""
    if [ $errors -eq 0 ]; then
        log_success "✓ Installation verification passed!"
        return 0
    else
        log_error "✗ Installation verification found $errors issue(s)"
        return 1
    fi
}

display_completion() {
    echo ""
    echo "============================================"
    log_success "Installation completed successfully!"
    echo "============================================"
    echo ""
    echo "📁 Installation directory: $(pwd)"
    echo "⚙️  Configuration file: config.yaml"
    echo ""
    echo "🚀 To start the application:"
    echo ""
    echo "   Development mode (with hot reload):"
    echo "   cd $(pwd)/backend"
    echo "   source venv/bin/activate"
    echo "   uvicorn app.main:app --reload --host 0.0.0.0 --port ${SERVER_PORT:-5050}"
    echo ""
    echo "   Production mode (systemd):"
    echo "   sudo systemctl start kavita-safeuploader"
    echo "   sudo systemctl enable kavita-safeuploader  # Auto-start on boot"
    echo ""
    echo "🌐 Access the application:"
    echo "   Web Interface: http://localhost:${SERVER_PORT:-5050}"
    echo "   API Documentation: http://localhost:${SERVER_PORT:-5050}/docs"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs: journalctl -u kavita-safeuploader -f"
    echo "   Stop service: sudo systemctl stop kavita-safeuploader"
    echo "   Restart service: sudo systemctl restart kavita-safeuploader"
    echo ""
    echo "📖 For more information, see README.md and INSTALL_NOTES.md"
    echo ""
}

# Main installation flow
main() {
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║  Kavita SafeUploader Installer v0.1.0 ║"
    echo "║  Ubuntu 24.04 LTS                      ║"
    echo "╚════════════════════════════════════════╝"
    echo ""
    
    check_user
    check_os
    
    log_info "Starting installation..."
    echo ""
    
    install_dependencies
    install_nodejs
    setup_python_venv
    setup_frontend
    create_directories
    cleanup_old_database
    generate_config
    build_frontend
    create_systemd_service
    
    # Verify installation
    echo ""
    verify_installation
    
    display_completion
}

# Run main function
main

