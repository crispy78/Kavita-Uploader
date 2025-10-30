"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import config
from app.database import db
from app.logger import app_logger, setup_logger
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    # Startup
    app_logger.info("Starting Kavita Uploader...")
    
    # Ensure directories exist with secure permissions
    config.ensure_directories()
    
    # Initialize database
    await db.init_db()
    app_logger.info("Database initialized")
    
    # Setup logger with config
    setup_logger(
        "safeuploader",
        log_level=config.logging.level,
        log_file=config.logging.file,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count,
        log_format=config.logging.format,
    )
    
    app_logger.info(
        f"Server starting on {config.server.host}:{config.server.port}"
    )
    
    yield
    
    # Shutdown
    app_logger.info("Shutting down Kavita Uploader...")


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Create FastAPI application
# Docs toggle based on API protection and debug
docs_disabled = config.api_protection.disable_docs and not (config.api_protection.allow_docs_in_debug and config.server.debug)

app = FastAPI(
    title="Kavita Uploader",
    description="Secure e-book upload application for Kavita",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if docs_disabled else "/docs",
    redoc_url=None if docs_disabled else "/redoc",
    openapi_url=None if docs_disabled else "/openapi.json",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    app_logger.info(
        f"{request.method} {request.url.path}",
        extra={"ip_address": request.client.host if request.client else "unknown"}
    )
    response = await call_next(request)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    app_logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={"path": request.url.path}
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
        }
    )


# Include API routes
app.include_router(router, prefix="/api")


@app.get("/api")
async def api_root():
    """API root endpoint - returns API information."""
    return {
        "name": "Kavita Uploader API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "quarantine_configured": config.folders.quarantine,
        "unsorted_configured": config.folders.unsorted,
    }


# Mount static files for frontend (production)
# In development, frontend is served by Vite dev server
try:
    from pathlib import Path
    static_path = Path(__file__).parent.parent.parent / "frontend" / "dist"
    if static_path.exists():
        app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")
        app_logger.info(f"Serving frontend from {static_path}")
except Exception as e:
    app_logger.warning(f"Frontend static files not mounted: {e}")

