"""Database models and session management."""

from datetime import datetime
from typing import Optional
from pathlib import Path
import os
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Boolean, Text, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text

Base = declarative_base()


def get_database_path() -> str:
    """Get database file path.
    
    Looks for database in this order:
    1. Environment variable DATABASE_PATH
    2. Project root (safeuploader.db)
    3. Backend directory (uploader.db)
    """
    # Check environment variable first
    if os.getenv("DATABASE_PATH"):
        db_path = os.getenv("DATABASE_PATH")
    else:
        # Try project root first (parent of backend/)
        backend_dir = Path(__file__).parent.parent  # backend/
        project_root = backend_dir.parent  # project root
        
        # Check for safeuploader.db in project root (matches docker-compose)
        project_db = project_root / "safeuploader.db"
        if project_db.exists():
            db_path = str(project_db)
        else:
            # Fallback to uploader.db in backend directory
            db_path = str(backend_dir / "uploader.db")
    
    # Convert to absolute path and ensure parent directory exists
    db_path = Path(db_path).absolute()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to SQLite URL format
    # SQLite URLs need 3 or 4 slashes: sqlite:///path or sqlite+aiosqlite:///path
    return f"sqlite+aiosqlite:///{db_path}"


class Upload(Base):
    """Upload record model."""
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, nullable=False)
    original_filename = Column(String(255), nullable=False)
    sanitized_filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100), nullable=True)
    file_extension = Column(String(10), nullable=False)
    
    # Status tracking
    status = Column(String(50), default="quarantined", nullable=False)  # quarantined, scanning, scanned, metadata_pending, safe, infected, moved, failed
    quarantine_path = Column(String(500), nullable=False)
    final_path = Column(String(500), nullable=True)
    
    # Hashing for duplicate detection
    file_hash_sha256 = Column(String(64), nullable=True)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    scanned_at = Column(DateTime, nullable=True)
    moved_at = Column(DateTime, nullable=True)
    
    # Scan results (Step 2)
    scan_result = Column(String(50), nullable=True)  # safe, infected, error
    scan_details = Column(Text, nullable=True)  # JSON string
    
    # Metadata (Step 3)
    metadata_json = Column(Text, nullable=True)  # JSON string with extracted/edited metadata
    metadata_edited = Column(Boolean, default=False)
    metadata_extracted_at = Column(DateTime, nullable=True)
    metadata_verified_at = Column(DateTime, nullable=True)
    preview_generated = Column(Boolean, default=False)
    preview_path = Column(String(500), nullable=True)
    
    # Duplicate detection (Step 4)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(String(36), nullable=True)  # UUID of original file
    duplicate_reason = Column(String(255), nullable=True)  # Reason for duplicate rejection (exact_hash, name_conflict, etc.)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Authentication (user who uploaded)
    uploaded_by = Column(String(255), nullable=True)  # Kavita username


class Database:
    """Database connection manager."""

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database connection."""
        if database_url is None:
            database_url = get_database_path()
        
        self.engine = create_async_engine(
            database_url,
            echo=False,
            future=True,
        )
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def _migrate_schema(self, conn):
        """Automatically migrate database schema by adding missing columns."""
        from app.logger import app_logger
        
        # Check if uploads table exists
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='uploads'"
        ))
        table_exists = result.fetchone() is not None
        
        if not table_exists:
            # Table doesn't exist, create_all will handle it
            return
        
        # Get existing columns
        result = await conn.execute(text("PRAGMA table_info(uploads)"))
        existing_columns = {row[1] for row in result.fetchall()}
        
        # Define required columns with their SQL types (Step 3 & 4 additions + auth)
        required_columns = {
            'metadata_json': 'TEXT',
            'metadata_edited': 'BOOLEAN DEFAULT 0',
            'metadata_extracted_at': 'DATETIME',
            'metadata_verified_at': 'DATETIME',
            'preview_generated': 'BOOLEAN DEFAULT 0',
            'preview_path': 'VARCHAR(500)',
            'duplicate_reason': 'VARCHAR(255)',  # Step 4
            'uploaded_by': 'VARCHAR(255)',  # Authentication: username
        }
        
        # Add missing columns
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                try:
                    await conn.execute(text(
                        f"ALTER TABLE uploads ADD COLUMN {column_name} {column_type}"
                    ))
                    app_logger.info(f"Added missing column: {column_name}")
                except Exception as e:
                    app_logger.error(f"Failed to add column {column_name}: {e}")
                    raise

    async def init_db(self):
        """Create database tables and migrate schema."""
        from app.logger import app_logger
        
        try:
            async with self.engine.begin() as conn:
                # First, create any missing tables
                await conn.run_sync(Base.metadata.create_all)
                app_logger.info("Database tables created/verified")
                
                # Then, add any missing columns to existing tables
                await self._migrate_schema(conn)
                app_logger.info("Database schema migration completed")
        except Exception as e:
            app_logger.error(f"Database initialization failed: {e}", exc_info=True)
            raise

    async def get_session(self) -> AsyncSession:
        """Get async database session."""
        async with self.async_session_maker() as session:
            yield session


# Global database instance
db = Database()

