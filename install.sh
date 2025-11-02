#!/bin/bash
# Kavita Uploader Installer for Ubuntu 24.04 LTS
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

# Detect available Python version
detect_python_version() {
    log_info "Detecting available Python version..."
    
    # Try Python 3.13 first (latest stable), then 3.12, then 3.11
    for py_version in "3.13" "3.12" "3.11"; do
        if apt-cache show python${py_version} &>/dev/null; then
            PYTHON_VERSION=${py_version}
            log_success "Found Python ${PYTHON_VERSION} in repositories"
            return 0
        fi
    done
    
    # If no specific version found, use generic python3
    log_warning "No specific Python 3.x version found, using python3"
    PYTHON_VERSION="3"
    return 0
}

# Install system dependencies
install_dependencies() {
    log_info "Installing system dependencies..."
    
    sudo apt-get update
    
    # Detect available Python version
    detect_python_version
    
    # Install base dependencies (without nodejs/npm yet)
    # Use python3 if specific version not available
    if [ "$PYTHON_VERSION" = "3" ]; then
        log_info "Installing python3 and python3-venv..."
        sudo apt-get install -y \
            python3 \
            python3-venv \
            python3-pip \
            libmagic1 \
            curl \
            git \
            unzip \
            unrar
    else
        log_info "Installing python${PYTHON_VERSION} and python${PYTHON_VERSION}-venv..."
        sudo apt-get install -y \
            python${PYTHON_VERSION} \
            python${PYTHON_VERSION}-venv \
            python3-pip \
            libmagic1 \
            curl \
            git \
            unzip \
            unrar
    fi
    
    log_success "System dependencies installed"
}

# Install Node.js LTS (if needed)
install_nodejs() {
    
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
    
    # Determine Python command to use
    if [ "$PYTHON_VERSION" = "3" ]; then
        PYTHON_CMD="python3"
    else
        PYTHON_CMD="python${PYTHON_VERSION}"
    fi
    
    # Check if venv exists and is functional
    if [ -d "venv" ]; then
        log_info "Checking existing virtual environment..."
        # Test if venv is functional
        if [ -x "venv/bin/python" ]; then
            log_info "Virtual environment exists and is functional"
        else
            log_warning "Virtual environment exists but is broken, recreating..."
            rm -rf venv
            ${PYTHON_CMD} -m venv venv
            log_success "Virtual environment recreated"
        fi
    else
        log_info "Creating virtual environment with ${PYTHON_CMD}..."
        ${PYTHON_CMD} -m venv venv
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
    
    # Default ebooks folder structure - will be updated if user configures different paths
    mkdir -p ebooks/quarantine
    chmod 700 ebooks/quarantine
    
    mkdir -p ebooks/unsorted
    chmod 700 ebooks/unsorted
    
    # Create processed subfolder for Kavita (files go here, Kavita scans parent)
    mkdir -p ebooks/unsorted/processed
    chmod 700 ebooks/unsorted/processed
    
    mkdir -p ebooks/library
    chmod 755 ebooks/library
    
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
    
    if [ -f backend/uploader.db ]; then
            log_warning "Found existing database from previous installation"
            read -p "Delete old database? This will erase all upload records (files in quarantine will remain). (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                BACKUP_NAME="backend/uploader.db.backup.$(date +%Y%m%d_%H%M%S)"
                mv backend/uploader.db "$BACKUP_NAME"
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
    
    # Get installation directory (absolute path)
    INSTALL_DIR=$(pwd)
    INSTALL_DIR_ABS=$(realpath "$INSTALL_DIR" 2>/dev/null || echo "$INSTALL_DIR")
    
    # Default folder name for ebooks storage
    EBOOKS_FOLDER="ebooks"
    DEFAULT_QUARANTINE="${INSTALL_DIR_ABS}/${EBOOKS_FOLDER}/quarantine"
    DEFAULT_UNSORTED="${INSTALL_DIR_ABS}/${EBOOKS_FOLDER}/unsorted"
    DEFAULT_LIBRARY="${INSTALL_DIR_ABS}/${EBOOKS_FOLDER}/library"
    
    # Generate secret key
    SECRET_KEY=$(openssl rand -hex 32)
    
    # Prompt for configuration
    echo ""
    echo "=== Configuration Setup ==="
    echo ""
    
    read -p "Server port [5050]: " SERVER_PORT
    SERVER_PORT=${SERVER_PORT:-5050}
    
    echo ""
    echo "Folder paths (leave empty to use defaults):"
    echo ""
    
    read -p "Quarantine folder [${DEFAULT_QUARANTINE}]: " QUARANTINE_PATH
    QUARANTINE_PATH=${QUARANTINE_PATH:-${DEFAULT_QUARANTINE}}
    
    read -p "Unsorted folder [${DEFAULT_UNSORTED}]: " UNSORTED_PATH
    UNSORTED_PATH=${UNSORTED_PATH:-${DEFAULT_UNSORTED}}
    
    read -p "Library folder [${DEFAULT_LIBRARY}]: " LIBRARY_PATH
    LIBRARY_PATH=${LIBRARY_PATH:-${DEFAULT_LIBRARY}}
    
    # Convert absolute paths to relative paths from backend/ if they're within install dir
    # Otherwise keep as absolute
    QUARANTINE_REL=$(INSTALL_DIR_ABS="${INSTALL_DIR_ABS}" QUARANTINE_PATH="${QUARANTINE_PATH}" python3 -c "
import os
from pathlib import Path

try:
    install_dir = Path(os.environ['INSTALL_DIR_ABS']).resolve()
    backend_dir = install_dir / 'backend'
    target_path = Path(os.environ['QUARANTINE_PATH']).resolve()
    
    rel_path = os.path.relpath(target_path, backend_dir)
    
    if not str(target_path).startswith(str(install_dir)):
        print(os.environ['QUARANTINE_PATH'])
    else:
        print(rel_path)
except Exception:
    print(os.environ.get('QUARANTINE_PATH', '../ebooks/quarantine'))
" 2>/dev/null || echo "../${EBOOKS_FOLDER}/quarantine")
    
    UNSORTED_REL=$(INSTALL_DIR_ABS="${INSTALL_DIR_ABS}" UNSORTED_PATH="${UNSORTED_PATH}" python3 -c "
import os
from pathlib import Path

try:
    install_dir = Path(os.environ['INSTALL_DIR_ABS']).resolve()
    backend_dir = install_dir / 'backend'
    target_path = Path(os.environ['UNSORTED_PATH']).resolve()
    
    rel_path = os.path.relpath(target_path, backend_dir)
    
    if not str(target_path).startswith(str(install_dir)):
        print(os.environ['UNSORTED_PATH'])
    else:
        print(rel_path)
except Exception:
    print(os.environ.get('UNSORTED_PATH', '../ebooks/unsorted'))
" 2>/dev/null || echo "../${EBOOKS_FOLDER}/unsorted")
    
    LIBRARY_REL=$(INSTALL_DIR_ABS="${INSTALL_DIR_ABS}" LIBRARY_PATH="${LIBRARY_PATH}" python3 -c "
import os
from pathlib import Path

try:
    install_dir = Path(os.environ['INSTALL_DIR_ABS']).resolve()
    backend_dir = install_dir / 'backend'
    target_path = Path(os.environ['LIBRARY_PATH']).resolve()
    
    rel_path = os.path.relpath(target_path, backend_dir)
    
    if not str(target_path).startswith(str(install_dir)):
        print(os.environ['LIBRARY_PATH'])
    else:
        print(rel_path)
except Exception:
    print(os.environ.get('LIBRARY_PATH', '../ebooks/library'))
" 2>/dev/null || echo "../${EBOOKS_FOLDER}/library")
    
    # Store absolute paths for directory creation
    export QUARANTINE_ABS="${QUARANTINE_PATH}"
    export UNSORTED_ABS="${UNSORTED_PATH}"
    export LIBRARY_ABS="${LIBRARY_PATH}"
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Kavita Authentication (Optional)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Require users to log in with their Kavita credentials before uploading."
    echo "This allows you to track who uploaded which files."
    echo ""
    
    read -p "Enable Kavita authentication? (y/n) [n]: " ENABLE_KAVITA_AUTH
    ENABLE_KAVITA_AUTH=${ENABLE_KAVITA_AUTH:-n}
    
    if [[ $ENABLE_KAVITA_AUTH =~ ^[Yy]$ ]]; then
        read -p "Kavita server URL [http://localhost:5000]: " KAVITA_SERVER_URL
        KAVITA_SERVER_URL=${KAVITA_SERVER_URL:-http://localhost:5000}
        
        echo ""
        echo "Kavita API Key (optional):"
        echo "If you have a Kavita API key, you can use it for authentication."
        echo "Otherwise, users will log in with username/password."
        read -s -p "Enter Kavita API Key (leave empty to skip): " KAVITA_API_KEY
        echo ""
        
        if [ -n "$KAVITA_API_KEY" ]; then
            # Show last 5 characters for verification
            API_KEY_TAIL="${KAVITA_API_KEY: -5}"
            read -s -p "Confirm Kavita API Key (leave empty to skip): " KAVITA_API_KEY_CONFIRM
            echo ""
            
            if [ "$KAVITA_API_KEY" != "$KAVITA_API_KEY_CONFIRM" ]; then
                log_warning "API keys do not match. Will use username/password authentication instead."
                USE_API_KEY="false"
                KAVITA_API_KEY=""
            else
                log_info "API key verification: ...${API_KEY_TAIL}"
                USE_API_KEY="true"
            fi
        else
            USE_API_KEY="false"
            KAVITA_API_KEY=""
        fi
        
        read -p "Require authentication for uploads? (y/n) [y]: " REQUIRE_AUTH
        REQUIRE_AUTH=${REQUIRE_AUTH:-y}
        
        if [[ $REQUIRE_AUTH =~ ^[Yy]$ ]]; then
            REQUIRE_AUTH_VAL="true"
        else
            REQUIRE_AUTH_VAL="false"
        fi
        
        # Generate session secret
        AUTH_SECRET=$(openssl rand -hex 32)
        
        KAVITA_ENABLED="true"
    else
        KAVITA_SERVER_URL="http://localhost:5000"
        KAVITA_API_KEY=""
        USE_API_KEY="false"
        REQUIRE_AUTH_VAL="false"
        AUTH_SECRET=$(openssl rand -hex 32)
        KAVITA_ENABLED="false"
    fi
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
        
        if [ -z "$VIRUSTOTAL_KEY" ]; then
            log_warning "No API key provided. Scanning will be disabled."
            SCANNING_ENABLED="false"
            VIRUSTOTAL_KEY=""
        else
            # Show last 5 characters for verification
            API_KEY_TAIL="${VIRUSTOTAL_KEY: -5}"
            read -s -p "Confirm VirusTotal API Key: " VIRUSTOTAL_KEY_CONFIRM
            echo ""
            
            if [ "$VIRUSTOTAL_KEY" != "$VIRUSTOTAL_KEY_CONFIRM" ]; then
                log_warning "API keys do not match. Scanning will be disabled."
                SCANNING_ENABLED="false"
                VIRUSTOTAL_KEY=""
            else
                log_info "API key verification: ...${API_KEY_TAIL}"
                SCANNING_ENABLED="true"
                log_success "VirusTotal API key configured"
            fi
        fi
    else
        SCANNING_ENABLED="false"
        VIRUSTOTAL_KEY=""
        log_info "Scanning disabled - you can enable it later in config.yaml"
    fi
    
    # Create config.yaml
    cat > config.yaml <<EOF
# Kavita Uploader Configuration
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
  quarantine: "${QUARANTINE_REL}"
  unsorted: "${UNSORTED_REL}"
  library: "${LIBRARY_REL}"

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
  unsorted_dir: "${UNSORTED_REL}"
  kavita_library_dirs:
    - "${LIBRARY_REL}"
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

kavita:
  enabled: ${KAVITA_ENABLED}
  server_url: "${KAVITA_SERVER_URL}"
  api_key: "${KAVITA_API_KEY}"
  use_api_key: ${USE_API_KEY}
  verify_ssl: true
  timeout: 10

auth:
  require_auth: ${REQUIRE_AUTH_VAL}
  session_secret: "${AUTH_SECRET}"
  token_expiry_hours: 24
  cookie_name: "kavita_uploader_token"

logging:
  level: "INFO"
  format: "json"
  console_format: "text"
  console_level: "INFO"
  file: "logs/uploader.log"
  max_bytes: 10485760
  backup_count: 5
EOF
    
    log_success "Configuration file created: config.yaml"
}

# Ensure directories from config.yaml exist with proper permissions
ensure_config_directories() {
    log_info "Ensuring directories from config.yaml exist..."
    
    USER=$(whoami)
    INSTALL_DIR=$(pwd)
    
    # Read config.yaml and extract directory paths
    if [ -f "config.yaml" ]; then
        # Check if PyYAML is available
        if python3 -c "import yaml" 2>/dev/null; then
            # Use Python to parse YAML (more reliable than grep/sed)
            DIRS_TO_CREATE=$(
                python3 << 'PYEOF'
import yaml
import os
from pathlib import Path

try:
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f) or {}
    
    install_dir = os.getcwd()
    backend_dir = os.path.join(install_dir, 'backend')
    dirs = set()
    
    # Extract folder paths (these are always directories)
    # Paths in config are relative to backend/ directory (where app runs)
    folders = config.get('folders', {})
    if folders:
        for key in ['quarantine', 'unsorted', 'library']:
            path = folders.get(key, '')
            if path and not path.startswith('${'):
                if os.path.isabs(path):
                    dirs.add(path)
                else:
                    # Resolve relative path from backend/ directory
                    resolved_path = os.path.abspath(os.path.join(backend_dir, path))
                    dirs.add(resolved_path)
    
    # Extract moving.unsorted_dir
    moving = config.get('moving', {})
    if moving:
        unsorted_dir = moving.get('unsorted_dir', '')
        if unsorted_dir and not unsorted_dir.startswith('${'):
            if os.path.isabs(unsorted_dir):
                dirs.add(unsorted_dir)
            else:
                # Resolve relative path from backend/ directory
                resolved_path = os.path.abspath(os.path.join(backend_dir, unsorted_dir))
                dirs.add(resolved_path)
    
    # Extract logging.file parent directory (relative to backend/)
    logging = config.get('logging', {})
    if logging:
        log_file = logging.get('file', '')
        if log_file and not log_file.startswith('${'):
            if os.path.isabs(log_file):
                dirs.add(os.path.dirname(log_file))
            else:
                # Resolve relative path from backend/ directory
                resolved_path = os.path.abspath(os.path.join(backend_dir, log_file))
                dirs.add(os.path.dirname(resolved_path))
    
    # Extract manifest_path parent directory (relative to backend/)
    if moving:
        manifest = moving.get('manifest_path', '')
        if manifest and not manifest.startswith('${'):
            if os.path.isabs(manifest):
                dirs.add(os.path.dirname(manifest))
            else:
                # Resolve relative path from backend/ directory
                resolved_path = os.path.abspath(os.path.join(backend_dir, manifest))
                dirs.add(os.path.dirname(resolved_path))
    
    # Filter out empty strings and print one per line
    for d in sorted(dirs):
        if d:
            print(d)
except Exception as e:
    # Fallback: just return empty if parsing fails
    pass
PYEOF
            )
        else
            # Fallback: simple grep/sed approach for basic paths
            log_warning "PyYAML not available, using basic directory detection"
            DIRS_TO_CREATE=""
            for key in quarantine unsorted library; do
                path=$(grep -E "^  ${key}:" config.yaml | sed -E 's/^[^:]+:[[:space:]]*"?([^"]*)"?/\1/' | xargs)
                if [ -n "$path" ] && [[ "$path" != *"\${"* ]]; then
                    if [[ "$path" != /* ]]; then
                        path="$INSTALL_DIR/$path"
                    fi
                    DIRS_TO_CREATE="${DIRS_TO_CREATE}${path}"$'\n'
                fi
            done
            
            # Also get unsorted_dir from moving section
            unsorted_dir=$(grep -A 10 "^moving:" config.yaml | grep -E "^  unsorted_dir:" | sed -E 's/^[^:]+:[[:space:]]*"?([^"]*)"?/\1/' | xargs)
            if [ -n "$unsorted_dir" ] && [[ "$unsorted_dir" != *"\${"* ]]; then
                if [[ "$unsorted_dir" != /* ]]; then
                    unsorted_dir="$INSTALL_DIR/$unsorted_dir"
                fi
                DIRS_TO_CREATE="${DIRS_TO_CREATE}${unsorted_dir}"$'\n'
            fi
            
            # Get logs directory from logging.file
            log_file=$(grep -A 10 "^logging:" config.yaml | grep -E "^  file:" | sed -E 's/^[^:]+:[[:space:]]*"?([^"]*)"?/\1/' | xargs)
            if [ -n "$log_file" ] && [[ "$log_file" != *"\${"* ]]; then
                if [[ "$log_file" != /* ]]; then
                    log_file="$INSTALL_DIR/$log_file"
                fi
                log_dir=$(dirname "$log_file")
                DIRS_TO_CREATE="${DIRS_TO_CREATE}${log_dir}"$'\n'
            fi
        fi
        
        # Create directories with proper ownership
        while IFS= read -r dir_path; do
            [ -z "$dir_path" ] && continue
            
            # Normalize path
            dir_path=$(realpath -m "$dir_path" 2>/dev/null || echo "$dir_path")
            
            if [ ! -d "$dir_path" ]; then
                log_info "Creating directory: $dir_path"
                # Create parent directories first
                sudo mkdir -p "$dir_path"
                # Set ownership to user
                sudo chown -R ${USER}:${USER} "$dir_path"
                sudo chmod 755 "$dir_path"
                log_success "Created directory: $dir_path"
            else
                # Ensure ownership is correct even if directory exists
                sudo chown -R ${USER}:${USER} "$dir_path" 2>/dev/null || true
            fi
            
            # If this is the unsorted directory, also create the processed subfolder
            if grep -q "unsorted" <<< "$dir_path" 2>/dev/null || [[ "$dir_path" == *"unsorted"* ]]; then
                processed_dir="${dir_path}/processed"
                if [ ! -d "$processed_dir" ]; then
                    log_info "Creating processed subfolder for Kavita: $processed_dir"
                    sudo mkdir -p "$processed_dir"
                    sudo chown -R ${USER}:${USER} "$processed_dir"
                    sudo chmod 755 "$processed_dir"
                    log_success "Created processed subfolder: $processed_dir"
                fi
            fi
        done <<< "$DIRS_TO_CREATE"
        
        log_success "Configuration directories verified"
    else
        log_warning "config.yaml not found, skipping directory verification"
    fi
}

# Create systemd service
create_systemd_service() {
    log_info "Creating systemd service..."
    
    INSTALL_DIR=$(pwd)
    USER=$(whoami)
    
    # Read root_path from config.yaml if it exists
    ROOT_PATH_ENV=""
    if [ -f "config.yaml" ]; then
        ROOT_PATH=$(grep -E "^  root_path:" config.yaml | sed -E 's/^[^:]+:[[:space:]]*"?([^"]*)"?/\1/' | xargs)
        if [ -n "$ROOT_PATH" ] && [ "$ROOT_PATH" != '""' ]; then
            ROOT_PATH_ENV="Environment=\"SERVER_ROOT_PATH=${ROOT_PATH}\""
        fi
    fi
    
    sudo tee /etc/systemd/system/kavita-uploader.service > /dev/null <<EOF
[Unit]
Description=Kavita Uploader
After=network.target

[Service]
Type=simple
User=${USER}
Group=${USER}
WorkingDirectory=${INSTALL_DIR}/backend
Environment=PYTHONPATH=${INSTALL_DIR}/backend
Environment="PATH=${INSTALL_DIR}/backend/venv/bin"
ExecStart=${INSTALL_DIR}/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port ${SERVER_PORT:-5050}
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    
    log_success "Systemd service created"
    log_info "To enable auto-start: sudo systemctl enable kavita-uploader"
    log_info "To start service: sudo systemctl start kavita-uploader"
}

# Fix any problematic code patterns before building
fix_code_issues() {
    log_info "Checking and fixing code issues..."
    
    # Fix main.py if it has the old upload_service.initialize() pattern
    if [ -f "backend/app/main.py" ]; then
        if grep -q "upload_service.initialize()" backend/app/main.py 2>/dev/null; then
            log_warning "Found old upload_service.initialize() call - fixing..."
            # Replace await upload_service.initialize() with config.ensure_directories()
            sed -i 's/await upload_service\.initialize()/config.ensure_directories()/g' backend/app/main.py
            log_success "Fixed upload_service.initialize() call in main.py"
        fi
        
        # Fix any _ensure_directories() being awaited incorrectly
        if grep -q "await.*_ensure_directories()" backend/app/main.py 2>/dev/null || \
           grep -q "await.*_ensure_directories()" backend/app/*.py 2>/dev/null; then
            log_warning "Found problematic await _ensure_directories() - fixing..."
            # Remove await from _ensure_directories() calls (it's synchronous)
            find backend/app -name "*.py" -type f -exec sed -i 's/await\s*self\._ensure_directories()/self._ensure_directories()/g' {} \;
            find backend/app -name "*.py" -type f -exec sed -i 's/await\s*_ensure_directories()/_ensure_directories()/g' {} \;
            log_success "Fixed _ensure_directories() await calls"
        fi
    fi
    
    log_success "Code issues checked"
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
    echo "   sudo systemctl start kavita-uploader"
    echo "   sudo systemctl enable kavita-uploader  # Auto-start on boot"
    echo ""
    echo "🌐 Access the application:"
    echo "   Web Interface: http://localhost:${SERVER_PORT:-5050}"
    echo "   API Documentation: http://localhost:${SERVER_PORT:-5050}/docs"
    echo ""
    echo "📋 Useful commands:"
    echo "   View logs: journalctl -u kavita-uploader -f"
    echo "   Stop service: sudo systemctl stop kavita-uploader"
    echo "   Restart service: sudo systemctl restart kavita-uploader"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  ⚠️  IMPORTANT: Kavita Setup Required"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "1. Set Kavita Permissions:"
    echo "   Find your Kavita user: ps aux | grep Kavita"
    echo "   Then run:"
    echo "   sudo usermod -a -G $(whoami) kavita"
    echo "   chmod -R 750 ${UNSORTED_ABS}"
    echo ""
    echo "2. Configure Kavita Library:"
    echo "   • Add a library in Kavita pointing to: ${UNSORTED_ABS}"
    echo "   • Files will be saved to: ${UNSORTED_ABS}/processed/"
    echo "   • DO NOT configure Kavita to scan the 'processed' subfolder"
    echo "   • Kavita will automatically scan all subfolders"
    echo ""
    echo "📖 For more information, see README.md and INSTALL_NOTES.md"
    echo ""
}

# Main installation flow
main() {
    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║  Kavita Uploader Installer v0.1.0 ║"
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
    
    # Create user-specified directories from config (ensure_config_directories handles this)
    ensure_config_directories
    fix_code_issues
    build_frontend
    create_systemd_service
    
    # Verify installation
    echo ""
    verify_installation
    
    display_completion
}

# Run main function
main

