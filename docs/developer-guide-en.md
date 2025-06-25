# Pooled Agent Service Developer Guide

## Table of Contents
1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Local Development](#local-development)
4. [Testing](#testing)
5. [Debugging](#debugging)
6. [Coding Standards](#coding-standards)
7. [Contributing](#contributing)

## Development Environment Setup

### Prerequisites
- Python 3.12 or higher
- Git
- Docker (for container execution)
- Azure CLI (for Azure resource access)

### 1. Clone Repository
```bash
git clone <repository-url>
cd ai-foundry-agent-service-multitenant/pooled/app
```

### 2. Install uv Package Manager
```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Create Virtual Environment and Install Dependencies
```bash
# Install with development dependencies
uv sync --extra test

# Or install production dependencies only
uv sync
```

### 4. Configure Environment Variables
Create a `.env` file with necessary environment variables:

```bash
# .env file example
APP_NAME="Pooled Agent Service"
DEBUG=true
LOG_LEVEL=DEBUG

# Azure Storage configuration
AZURE_STORAGE_ACCOUNT_NAME=your_storage_account
AZURE_STORAGE_ACCOUNT_KEY=your_account_key
# or
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
AZURE_STORAGE_CONTAINER_NAME=documents
```

## Project Structure

```
pooled/app/
├── src/                    # Application source code
│   ├── core/              # Application core
│   │   ├── __init__.py
│   │   ├── app.py         # FastAPI application factory
│   │   └── config.py      # Configuration management
│   ├── routers/           # HTTP routing
│   │   ├── __init__.py
│   │   ├── root.py        # Root endpoints
│   │   ├── health.py      # Health checks
│   │   └── blob_storage.py # Blob Storage API
│   ├── services/          # Business logic
│   │   ├── __init__.py
│   │   ├── blob_storage_service.py
│   │   └── health_service.py
│   └── middleware/        # Middleware
│       ├── __init__.py
│       ├── cors.py        # CORS configuration
│       └── logging.py     # Logging middleware
├── tests/                 # Test code
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── conftest.py       # pytest configuration
├── main.py               # Application entry point
├── pyproject.toml        # Project configuration
├── uv.lock              # Dependency lock
├── Dockerfile           # Docker configuration
└── README.md            # Project description
```

### Architecture Features

#### 1. Layered Architecture
- **Router Layer**: HTTP request processing and routing
- **Service Layer**: Business logic implementation
- **Core Layer**: Application configuration and factory

#### 2. SOLID Principles Application
- **Single Responsibility**: Each class has a single responsibility
- **Open/Closed**: Open for extension, closed for modification
- **Liskov Substitution**: Derived classes are substitutable for base classes
- **Interface Segregation**: Interface segregation
- **Dependency Inversion**: Dependency inversion

#### 3. Dependency Injection
Using FastAPI's `Depends` for dependency injection:

```python
@router.get("/{blob_name}")
async def get_blob_content(
    blob_name: str,
    blob_service: BlobStorageInterface = Depends(get_blob_storage_service)
):
    # ...
```

## Local Development

### 1. Start Development Server
```bash
# Start using uv
uv run python main.py

# Or run directly
python main.py

# Start with reload functionality
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Check API Documentation
After starting the development server, you can access API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

### 3. Check Logs
The application outputs structured logs:

```
2024-06-25 10:30:00,123 - src.routers.blob_storage - INFO - Request to get blob: document.pdf from container: documents
2024-06-25 10:30:00,150 - src.middleware.logging - INFO - Request completed - GET /blobs/document.pdf - 200
```

Each request is assigned a unique correlation ID, which can be checked in response headers.

## Testing

### Test Structure
```
tests/
├── unit/              # Unit tests
│   ├── test_services/
│   ├── test_routers/
│   └── test_core/
├── integration/       # Integration tests
│   ├── test_api/
│   └── test_blob_storage/
└── conftest.py       # Common test configuration
```

### 1. Running Tests

#### Run All Tests
```bash
uv run pytest
```

#### Run Unit Tests Only
```bash
uv run pytest tests/unit/
```

#### Run Tests with Coverage
```bash
uv run pytest --cov=src --cov-report=html
```

### 2. Writing Tests

#### Unit Test Example
```python
import pytest
from unittest.mock import AsyncMock
from src.services.blob_storage_service import AzureBlobStorageService

@pytest.mark.asyncio
async def test_get_blob_success():
    # Arrange
    service = AzureBlobStorageService("account", "key", "", "container")
    service._blob_service_client = AsyncMock()
    
    # Act
    result = await service.get_blob("test.txt")
    
    # Assert
    assert result is not None
```

#### Integration Test Example
```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
```

### 3. Mocking
Use `pytest-mock` for Azure service mocking:

```python
def test_blob_service_with_mock(mocker):
    mock_client = mocker.patch('azure.storage.blob.BlobServiceClient')
    # Test logic
```

## Debugging

### 1. IDE Configuration

#### VS Code
`.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "program": "main.py",
            "console": "integratedTerminal",
            "env": {
                "DEBUG": "true",
                "LOG_LEVEL": "DEBUG"
            }
        }
    ]
}
```

### 2. Adjust Log Level
Set to DEBUG level for detailed logs during development:

```bash
export LOG_LEVEL=DEBUG
```

### 3. Profiling
Debug performance issues:

```python
import cProfile
import pstats

# Run profiling
cProfile.run('your_function()', 'profile_output')
stats = pstats.Stats('profile_output')
stats.sort_stats('cumulative').print_stats(10)
```

## Coding Standards

### 1. PEP 8 Compliance
```bash
# Run formatter
uv run black src/
uv run isort src/

# Run linter
uv run flake8 src/
uv run mypy src/
```

### 2. Type Hints
Add type hints to all functions and methods:

```python
from typing import Optional, Dict, Any

async def get_blob_metadata(
    self, 
    blob_name: str, 
    container_name: Optional[str] = None
) -> Dict[str, Any]:
    # Implementation
```

### 3. Docstring Convention
Use Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """Example function with Google-style docstring.

    Args:
        param1: The first parameter.
        param2: The second parameter.

    Returns:
        The return value. True for success, False otherwise.

    Raises:
        ValueError: If param1 is empty.
    """
```

### 4. Log Messages
Use structured logging and prevent sensitive information leakage:

```python
logger.info(f"Processing blob: {blob_name}", extra={
    "blob_name": blob_name,
    "container": container_name,
    "user_id": user_id  # Exclude sensitive information
})
```

### 5. Error Handling
Proper exception handling and re-raising:

```python
try:
    result = await external_service.call()
except ExternalServiceError as e:
    logger.error(f"External service error: {e}")
    raise CustomServiceError(f"Failed to call external service: {e}")
```

## Contributing

### 1. Development Flow
1. Create or check issues
2. Create feature branch
3. Implement and test
4. Create pull request
5. Code review
6. Merge

### 2. Branch Conventions
```bash
# Feature branch
feature/issue-123-add-upload-api

# Bug fix branch
bugfix/issue-456-fix-auth-error

# Hotfix
hotfix/critical-security-patch
```

### 3. Commit Messages
```bash
# Format
type(scope): subject

# Examples
feat(blob): add file upload functionality
fix(health): correct readiness check logic
docs(api): update API documentation
test(integration): add blob storage integration tests
```

### 4. Pull Request
- [ ] Tests are passing
- [ ] Documentation is updated
- [ ] Code review is completed
- [ ] Conflicts are resolved

### 5. Code Review Points
- SOLID principles compliance
- Security considerations
- Performance impact
- Test coverage
- Documentation consistency

## Troubleshooting

### Common Issues

#### 1. Azure Storage Connection Error
```bash
# Check connection string
az storage account show-connection-string --name <account-name>

# Check authentication
az login
```

#### 2. Dependency Errors
```bash
# Reinstall dependencies
uv sync --reinstall
```

#### 3. Port Conflicts
```bash
# Check port usage
lsof -i :8000

# Start on different port
uv run uvicorn main:app --port 8001
```

### Debugging Tips
1. Set log level to DEBUG
2. Track requests with correlation ID
3. Check storage access logs in Azure Portal
4. Verify network connectivity

---

**Last Updated**: June 25, 2024  
**Version**: 1.0
