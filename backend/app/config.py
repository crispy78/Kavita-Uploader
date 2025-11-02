"""Configuration management with YAML and environment variable support."""

import os
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseSettings):
    """Server configuration."""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=5050)
    debug: bool = Field(default=False)
    cors_origins: List[str] = Field(default=["http://localhost:5050", "http://localhost:5173"])
    secret_key: str = Field(default="INSECURE-CHANGE-THIS")

    model_config = SettingsConfigDict(env_prefix="SERVER_")


class FoldersConfig(BaseSettings):
    """Folder paths configuration."""
    quarantine: str = Field(default="../ebooks/quarantine")
    unsorted: str = Field(default="../ebooks/unsorted")
    library: str = Field(default="../ebooks/library")

    model_config = SettingsConfigDict(env_prefix="FOLDERS_")


class UploadConfig(BaseSettings):
    """Upload configuration."""
    max_file_size_mb: int = Field(default=25)
    allowed_extensions: List[str] = Field(
        default=["epub", "pdf", "cbz", "cbr", "mobi", "azw3"]
    )
    allowed_mime_types: List[str] = Field(
        default=[
            "application/epub+zip",
            "application/pdf",
            "application/x-cbr",
            "application/x-cbz",
            "application/zip",
            "application/vnd.amazon.ebook",
            "application/x-mobipocket-ebook",
        ]
    )

    model_config = SettingsConfigDict(env_prefix="UPLOAD_")


class SecurityConfig(BaseSettings):
    """Security configuration."""
    enable_rate_limiting: bool = Field(default=True)
    rate_limit_uploads_per_minute: int = Field(default=10)
    enable_csrf_protection: bool = Field(default=True)
    file_permissions_mode: int = Field(default=0o600)
    directory_permissions_mode: int = Field(default=0o700)
    sanitize_filenames: bool = Field(default=True)

    model_config = SettingsConfigDict(env_prefix="SECURITY_")


class ScanningConfig(BaseSettings):
    """Scanning configuration (Step 2)."""
    enabled: bool = Field(default=False)
    provider: str = Field(default="virustotal")
    virustotal_api_key: str = Field(default="")
    virustotal_timeout: int = Field(default=60)
    polling_interval_sec: int = Field(default=30)
    max_retries: int = Field(default=20)
    auto_delete_infected: bool = Field(default=False)
    auto_skip_known_hashes: bool = Field(default=True)

    model_config = SettingsConfigDict(env_prefix="SCANNING_")


class PreviewSettings(BaseModel):
    """Preview settings nested in metadata config."""
    max_pages: int = Field(default=3)
    width: int = Field(default=1024)
    height: int = Field(default=768)


class MetadataConfig(BaseSettings):
    """Metadata configuration (Step 3)."""
    enabled: bool = Field(default=True)
    extract_on_upload: bool = Field(default=False)
    allow_user_editing: bool = Field(default=True)
    required_fields: List[str] = Field(default=["title", "author"])
    auto_save_on_no_changes: bool = Field(default=True)
    preview_settings: PreviewSettings = Field(default_factory=PreviewSettings)

    model_config = SettingsConfigDict(env_prefix="METADATA_")


class DuplicateDetectionConfig(BaseSettings):
    """Duplicate detection configuration (Step 2)."""
    enabled: bool = Field(default=True)
    hash_algorithm: str = Field(default="sha256")
    check_by_hash: bool = Field(default=True)
    check_by_size: bool = Field(default=True)
    check_by_name: bool = Field(default=False)
    discard_exact_hash: bool = Field(default=True)
    rename_duplicates: bool = Field(default=True)
    rename_pattern: str = Field(default="{name}_{timestamp}{ext}")

    model_config = SettingsConfigDict(env_prefix="DUPLICATE_DETECTION_")


class PreviewConfig(BaseSettings):
    """Preview configuration (Step 2 stub, Step 3 full)."""
    enabled: bool = Field(default=True)
    max_pages: int = Field(default=3)
    width: int = Field(default=1024)
    height: int = Field(default=768)
    supported_types: List[str] = Field(default=["pdf", "epub"])
    cache_previews: bool = Field(default=True)
    preview_format: str = Field(default="base64")
    auto_cleanup_hours: int = Field(default=24)

    model_config = SettingsConfigDict(env_prefix="PREVIEW_")


class NotificationSettings(BaseModel):
    """Notification settings nested in moving config."""
    email_enabled: bool = Field(default=False)
    email_recipients: List[str] = Field(default_factory=list)
    webhook_enabled: bool = Field(default=False)
    webhook_url: str = Field(default="")


class MovingConfig(BaseSettings):
    """Moving configuration (Step 4)."""
    enabled: bool = Field(default=True)
    unsorted_dir: str = Field(default="../ebooks/unsorted")
    kavita_library_dirs: List[str] = Field(default_factory=lambda: ["../ebooks/library"])
    rename_on_name_conflict: bool = Field(default=True)
    rename_pattern: str = Field(default="{title} - {author} (duplicate_{timestamp}){ext}")
    discard_on_exact_duplicate: bool = Field(default=True)
    keep_duplicate_log: bool = Field(default=True)
    verify_integrity_post_move: bool = Field(default=True)
    dry_run: bool = Field(default=False)
    checksum_manifest: bool = Field(default=True)
    manifest_path: str = Field(default="logs/manifest.csv")
    log_moves: bool = Field(default=True)
    atomic_operations: bool = Field(default=True)
    cleanup_quarantine_on_success: bool = Field(default=True)
    notification: NotificationSettings = Field(default_factory=NotificationSettings)

    model_config = SettingsConfigDict(env_prefix="MOVING_")


class DiskProtectionConfig(BaseSettings):
    """Disk space protection configuration."""
    enabled: bool = Field(default=True)
    min_free_space_percent: float = Field(default=10.0)  # Minimum 10% free space
    reserve_space_bytes: int = Field(default=1073741824)  # 1 GB reserve
    max_quarantine_size_bytes: int = Field(default=10737418240)  # 10 GB max quarantine
    max_single_upload_size_mb: int = Field(default=100)  # 100 MB per upload
    auto_cleanup_enabled: bool = Field(default=True)
    auto_cleanup_age_hours: int = Field(default=72)  # 3 days
    cleanup_interval_minutes: int = Field(default=60)  # Run cleanup hourly
    emergency_cleanup_threshold_percent: float = Field(default=5.0)  # Trigger emergency at 5% free
    alert_threshold_percent: float = Field(default=15.0)  # Alert at 15% free

    model_config = SettingsConfigDict(env_prefix="DISK_PROTECTION_")


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    level: str = Field(default="INFO")
    format: str = Field(default="json")
    console_format: str = Field(default="text")
    console_level: str = Field(default="INFO")
    file: str = Field(default="logs/uploader.log")
    max_bytes: int = Field(default=10485760)
    backup_count: int = Field(default=5)

    model_config = SettingsConfigDict(env_prefix="LOGGING_")


class ApiProtectionConfig(BaseSettings):
    """API protection configuration."""
    enabled: bool = Field(default=True)
    require_header: bool = Field(default=True)
    header_name: str = Field(default="X-UI-Request")
    header_value: str = Field(default="1")
    disable_docs: bool = Field(default=True)
    allow_docs_in_debug: bool = Field(default=True)

    model_config = SettingsConfigDict(env_prefix="API_PROTECTION_")


class KavitaConfig(BaseSettings):
    """Kavita server configuration for authentication."""
    enabled: bool = Field(default=False)  # Enable to require Kavita login
    server_url: str = Field(default="http://localhost:5000")  # Kavita server URL
    api_key: str = Field(default="")  # Optional: Kavita API key (if using API key auth)
    use_api_key: bool = Field(default=False)  # Use API key instead of username/password
    verify_ssl: bool = Field(default=True)  # Verify SSL certificates
    timeout: int = Field(default=10)  # Request timeout in seconds

    model_config = SettingsConfigDict(env_prefix="KAVITA_")


class AuthConfig(BaseSettings):
    """Authentication configuration."""
    require_auth: bool = Field(default=False)  # Require authentication for uploads
    session_secret: str = Field(default="INSECURE-CHANGE-THIS")  # Secret for JWT tokens
    token_expiry_hours: int = Field(default=24)  # Token expiry in hours
    cookie_name: str = Field(default="kavita_uploader_token")  # Cookie name for token

    model_config = SettingsConfigDict(env_prefix="AUTH_")


class Config:
    """Main configuration class with YAML and environment variable support."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration from YAML file and environment variables.
        
        Environment variables override YAML settings following 12-factor principles.
        """
        # Determine config file path
        if config_path:
            self.config_path = config_path
        elif os.getenv("CONFIG_PATH"):
            self.config_path = os.getenv("CONFIG_PATH")
        else:
            # Look for config.yaml in project root (parent of backend/)
            backend_dir = Path(__file__).parent.parent  # Go up from app/ to backend/
            project_root = backend_dir.parent  # Go up from backend/ to project root
            self.config_path = str(project_root / "config.yaml")
            
            # Fallback to current directory if not found in project root
            if not os.path.exists(self.config_path):
                self.config_path = "config.yaml"
        
        self._yaml_config = {}

        # Load YAML configuration if file exists
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                self._yaml_config = yaml.safe_load(f) or {}
        else:
            print(f"WARNING: Config file not found at {self.config_path}, using defaults")

        # Initialize all configuration sections
        # Environment variables will automatically override YAML values
        self.server = ServerConfig(**self._yaml_config.get("server", {}))
        self.folders = FoldersConfig(**self._yaml_config.get("folders", {}))
        self.upload = UploadConfig(**self._yaml_config.get("upload", {}))
        self.security = SecurityConfig(**self._yaml_config.get("security", {}))
        self.scanning = ScanningConfig(**self._yaml_config.get("scanning", {}))
        self.metadata = MetadataConfig(**self._yaml_config.get("metadata", {}))
        self.duplicate_detection = DuplicateDetectionConfig(
            **self._yaml_config.get("duplicate_detection", {})
        )
        self.preview = PreviewConfig(**self._yaml_config.get("preview", {}))
        self.moving = MovingConfig(**self._yaml_config.get("moving", {}))
        self.disk_protection = DiskProtectionConfig(**self._yaml_config.get("disk_protection", {}))
        self.logging = LoggingConfig(**self._yaml_config.get("logging", {}))
        self.api_protection = ApiProtectionConfig(**self._yaml_config.get("api_protection", {}))
        self.kavita = KavitaConfig(**self._yaml_config.get("kavita", {}))
        self.auth = AuthConfig(**self._yaml_config.get("auth", {}))

    def ensure_directories(self):
        """Create necessary directories with secure permissions."""
        directories = [
            self.folders.quarantine,
            self.folders.unsorted,
            Path(self.logging.file).parent,
        ]

        for directory in directories:
            path = Path(directory)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                # Set secure directory permissions
                os.chmod(path, self.security.directory_permissions_mode)

    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.upload.max_file_size_mb * 1024 * 1024
    
    @property
    def quarantine_dir(self) -> str:
        """Get quarantine directory path."""
        return self.folders.quarantine


# Global configuration instance
config = Config()

