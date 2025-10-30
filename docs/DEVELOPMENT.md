# Development Guide

## Getting Started

### Prerequisites

- Ubuntu 24.04 LTS (or similar Linux distribution)
- Python 3.12+
- Node.js 18+ (20 LTS recommended)
- Git

### Initial Setup

```bash
# Clone repository
git clone <repository-url>
cd Kavita-Upload

# Run installer
chmod +x install.sh
./install.sh

# Or manual setup
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd ../frontend
npm install
```

### Development Workflow

#### Backend Development (serves the UI)

```bash
# Run backend with hot reload
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 5050
```

Access:
- Application (UI served by backend): http://localhost:5050
- API docs are disabled by default (production security). Enable only in development by setting `server.debug: true` and `api_protection.disable_docs: false` in `config.yaml`.

#### Frontend Build (no separate dev server required)

```bash
cd frontend
npm install
npm run build
# Backend automatically serves frontend/dist
```

### Project Structure

```
backend/
├── app/
│   ├── main.py          # FastAPI app, lifespan, middleware
│   ├── config.py        # Configuration with YAML and env vars
│   ├── database.py      # SQLAlchemy models
│   ├── routes.py        # API endpoints
│   ├── services.py      # Business logic (Steps 1-4)
│   ├── utils.py         # Helper functions
│   └── logger.py        # Logging setup
├── tests/
│   └── test_upload.py   # Test suite
└── requirements.txt

frontend/
├── src/
│   ├── components/      # React components
│   ├── services/        # API client
│   ├── App.jsx          # Main component
│   └── main.jsx         # Entry point
├── package.json
└── vite.config.js
```

## Architecture

### Backend Architecture

```
┌─────────────────────────────────────────────────────┐
│                     FastAPI App                      │
├─────────────────────────────────────────────────────┤
│  Middleware: CORS, Logging, Rate Limiting, Error    │
├─────────────────────────────────────────────────────┤
│                    Routes Layer                      │
│  - Configuration endpoint                            │
│  - Upload endpoint (Step 1)                         │
│  - Status endpoint                                   │
│  - Scan endpoint (Step 2 stub)                      │
│  - Metadata endpoints (Step 3 stub)                 │
│  - Duplicate & Move endpoints (Step 4 stub)         │
├─────────────────────────────────────────────────────┤
│                   Services Layer                     │
│  - UploadService: File upload & quarantine          │
│  - ScanningService: VirusTotal integration (stub)   │
│  - MetadataService: E-book parsing (stub)           │
│  - DuplicateService: Hash comparison (stub)         │
│  - MoveService: Final organization (stub)           │
├─────────────────────────────────────────────────────┤
│                    Utils Layer                       │
│  - Filename sanitization                            │
│  - File validation                                   │
│  - Hash calculation                                  │
│  - Permission management                             │
├─────────────────────────────────────────────────────┤
│                 Database (SQLite)                    │
│  - Upload records                                    │
│  - Status tracking                                   │
│  - Metadata storage                                  │
└─────────────────────────────────────────────────────┘
```

### Frontend Architecture

```
┌─────────────────────────────────────────────────────┐
│                      App.jsx                         │
│  - State management                                  │
│  - Configuration loading                             │
│  - Upload history                                    │
├─────────────────────────────────────────────────────┤
│                    Components                        │
│  ┌─────────────────────────────────────────────┐   │
│  │ Header: Navigation and branding              │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │ UploadZone: Drag-and-drop, validation       │   │
│  │  - File selection                            │   │
│  │  - Upload progress                           │   │
│  │  - Status display                            │   │
│  │  - Pipeline visualization                    │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │ UploadStatus: History item display          │   │
│  │  - Expandable details                        │   │
│  │  - Status indicator                          │   │
│  └─────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────┤
│                   API Service                        │
│  - Axios client                                      │
│  - Request/response handling                         │
│  - Error handling                                    │
└─────────────────────────────────────────────────────┘
```

## Adding New Features

### Step-by-Step Implementation Guide

#### Step 2: Virus Scanning (Example)

1. **Update Service** (`backend/app/services.py`):

```python
class ScanningService:
    @staticmethod
    async def scan_file(upload_uuid: str, db_session: AsyncSession) -> Dict[str, Any]:
        # Get upload record
        result = await db_session.execute(
            select(Upload).where(Upload.uuid == upload_uuid)
        )
        upload = result.scalar_one_or_none()
        
        if not upload:
            raise ValueError("Upload not found")
        
        # Upload to VirusTotal
        async with httpx.AsyncClient() as client:
            with open(upload.quarantine_path, 'rb') as f:
                files = {'file': f}
                response = await client.post(
                    'https://www.virustotal.com/api/v3/files',
                    headers={'x-apikey': config.scanning.virustotal_api_key},
                    files=files
                )
        
        # Poll for results (simplified)
        scan_id = response.json()['data']['id']
        
        # Update database
        upload.status = 'scanning'
        upload.scanned_at = datetime.utcnow()
        await db_session.commit()
        
        return {"scan_id": scan_id, "status": "scanning"}
```

2. **Update Route** (`backend/app/routes.py`):

```python
@router.post("/upload/{upload_uuid}/scan")
async def scan_upload(
    upload_uuid: str,
    db_session: AsyncSession = Depends(get_db_session),
):
    """Scan uploaded file for viruses/malware."""
    try:
        result = await ScanningService.scan_file(upload_uuid, db_session)
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

3. **Add Tests** (`backend/tests/test_scanning.py`):

```python
@pytest.mark.asyncio
async def test_scan_file(async_client, sample_upload):
    response = await async_client.post(f"/api/upload/{sample_upload}/scan")
    assert response.status_code == 200
    assert response.json()["success"] is True
```

4. **Update Frontend** (`frontend/src/components/UploadZone.jsx`):

```javascript
const handleScan = async (uuid) => {
  try {
    const result = await scanUpload(uuid)
    // Update UI with scan results
  } catch (error) {
    console.error('Scan failed:', error)
  }
}
```

## Testing

### Running Tests

```bash
# All tests
cd backend
source venv/bin/activate
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/test_upload.py

# Specific test
pytest tests/test_upload.py::TestUploadFile::test_upload_valid_file

# Watch mode (requires pytest-watch)
pip install pytest-watch
ptw
```

### Writing Tests

```python
# tests/test_new_feature.py
import pytest
from httpx import AsyncClient

class TestNewFeature:
    @pytest.mark.asyncio
    async def test_feature(self, async_client):
        """Test description."""
        response = await async_client.get("/api/endpoint")
        assert response.status_code == 200
```

### Test Fixtures

```python
@pytest.fixture
def sample_file():
    """Create test file."""
    return ("test.epub", b"content", "application/epub+zip")

@pytest.fixture(autouse=True)
def setup_teardown():
    """Setup and cleanup."""
    # Setup
    yield
    # Cleanup
```

## Database

### Migrations (Future)

Currently using SQLAlchemy with automatic table creation. For production:

1. Install Alembic:
```bash
pip install alembic
```

2. Initialize:
```bash
alembic init alembic
```

3. Create migration:
```bash
alembic revision --autogenerate -m "Add new column"
```

4. Apply migration:
```bash
alembic upgrade head
```

### Direct Database Access

```bash
# SQLite CLI
sqlite3 safeuploader.db

# Show tables
.tables

# Query uploads
SELECT * FROM uploads LIMIT 10;

# Check file count
SELECT status, COUNT(*) FROM uploads GROUP BY status;
```

## Configuration

### Configuration Priority

1. Environment variables (highest)
2. config.yaml
3. Default values (lowest)

### Adding New Config Options

1. Update `config.example.yaml`:
```yaml
new_feature:
  enabled: true
  setting: "value"
```

2. Update `backend/app/config.py`:
```python
class NewFeatureConfig(BaseSettings):
    enabled: bool = Field(default=True)
    setting: str = Field(default="value")
    
    model_config = SettingsConfigDict(env_prefix="NEW_FEATURE_")

class Config:
    def __init__(self, config_path: Optional[str] = None):
        # ...
        self.new_feature = NewFeatureConfig(**self._yaml_config.get("new_feature", {}))
```

3. Use in code:
```python
from app.config import config

if config.new_feature.enabled:
    # Use feature
    pass
```

## Logging

### Log Levels

- **DEBUG**: Detailed information for debugging
- **INFO**: General information (default)
- **WARNING**: Warning messages
- **ERROR**: Error messages
- **CRITICAL**: Critical failures

### Adding Logs

```python
from app.logger import app_logger

app_logger.info(
    "Event occurred",
    extra={
        "upload_uuid": uuid,
        "custom_field": value,
    }
)
```

### Viewing Logs

```bash
# Tail logs
tail -f logs/safeuploader.log

# Filter by level
grep '"level":"ERROR"' logs/safeuploader.log

# Pretty print JSON
tail -f logs/safeuploader.log | jq '.'

# Systemd logs
journalctl -u kavita-safeuploader -f
```

## Code Style

### Python

```bash
# Install tools
pip install black flake8 mypy

# Format code
black backend/app/

# Lint
flake8 backend/app/

# Type checking
mypy backend/app/
```

### JavaScript

```bash
# Lint
cd frontend
npm run lint

# Format (if using Prettier)
npm run format
```

## Debugging

### Backend Debugging

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use debugpy for VS Code
pip install debugpy
```

VS Code `launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "app.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "5050"
      ],
      "cwd": "${workspaceFolder}/backend"
    }
  ]
}
```

### Frontend Debugging

- Use React DevTools browser extension
- Use browser console
- Add `debugger;` statements

## Performance Optimization

### Backend

```python
# Use async/await consistently
async def process_file(file_path: str):
    async with aiofiles.open(file_path, 'rb') as f:
        content = await f.read()
    return content

# Database query optimization
from sqlalchemy import select
stmt = select(Upload).where(Upload.status == "quarantined").limit(100)
```

### Frontend

```javascript
// Memoize expensive calculations
const memoizedValue = useMemo(() => computeExpensiveValue(a, b), [a, b])

// Avoid unnecessary re-renders
const MemoizedComponent = React.memo(MyComponent)

// Code splitting
const LazyComponent = lazy(() => import('./Component'))
```

## Troubleshooting

### Common Issues

1. **Port already in use**:
```bash
sudo lsof -i :5050
kill -9 <PID>
```

2. **Database locked**:
```bash
# Stop all running instances
pkill -f uvicorn
rm safeuploader.db-shm safeuploader.db-wal
```

3. **Module not found**:
```bash
# Reinstall dependencies
cd backend
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **Frontend build fails**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

## Contributing

1. Fork repository
2. Create feature branch
3. Make changes
4. Add tests
5. Run test suite
6. Update documentation
7. Submit pull request

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [Vite](https://vitejs.dev/)

---

Happy coding! 🚀



