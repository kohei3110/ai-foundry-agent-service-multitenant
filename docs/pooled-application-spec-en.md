# Pooled Agent Service Technical Specification

## 1. Overview

### 1.1 Project Overview
- **Project Name**: Pooled Agent Service
- **Version**: 0.1.0
- **Description**: Multi-tenant AI Agent Service - Pooled Architecture
- **Architecture Pattern**: Pooled Architecture (Shared Resource Model)
- **Implementation Language**: Python 3.12+
- **Framework**: FastAPI
- **Package Manager**: uv

### 1.2 Purpose
To provide a scalable and efficient multi-tenant application using pooled architecture, where multiple tenants can utilize AI agent services on shared resources.

### 1.3 Key Features
- Azure Blob Storage file access functionality (SAS authentication)
- SAS token generation functionality
- Health check functionality (Kubernetes compatible)
- CORS support
- Structured logging
- Automatic API documentation generation (OpenAPI/Swagger)

## 2. Architecture Design

### 2.1 Overall Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway / Load Balancer              │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                   Pooled Agent Service                       │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐      │
│  │   Router      │ │  Middleware   │ │   Service     │      │
│  │               │ │               │ │               │      │
│  │ • Root        │ │ • CORS        │ │ • Blob Storage│      │
│  │ • Health      │ │ • Logging     │ │ • Health      │      │
│  │ • Blob Storage│ │               │ │               │      │
│  └───────────────┘ └───────────────┘ └───────────────┘      │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                   Azure Blob Storage                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Layered Architecture
```
src/
├── core/               # Application Core Layer
├── routers/            # Presentation Layer
├── services/           # Business Logic Layer
└── middleware/         # Infrastructure Layer
```

### 2.3 Design Principles
- **SOLID Principles**: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **Dependency Injection**: Improved testability through dependency injection
- **Interface Segregation**: Modularity through abstraction
- **Factory Pattern**: Configuration management through application factory

## 3. API Specification

### 3.1 Endpoint List

| Method | Path | Description | Authentication |
|--------|------|-------------|----------------|
| GET | / | Root endpoint (service information) | Not required |
| GET | /health | Basic health check | Not required |
| GET | /health/ready | Kubernetes readiness probe | Not required |
| GET | /health/live | Kubernetes liveness probe | Not required |
| GET | /blobs/{blob_name} | Get blob content (SAS authentication) | Not required |
| GET | /blobs/{blob_name}/stream | Get blob streaming (SAS authentication) | Not required |
| GET | /blobs/{blob_name}/metadata | Get blob metadata (SAS authentication) | Not required |
| GET | /blobs/{blob_name}/sas | Generate SAS token | Not required |
| HEAD | /blobs/{blob_name} | Check blob existence (SAS authentication) | Not required |

### 3.2 Detailed API Specification

#### 3.2.1 Root Endpoint
```http
GET /
```

**Response Example:**
```json
{
  "message": "Pooled Agent Service is running",
  "architecture": "pooled",
  "version": "0.1.0",
  "docs": "/docs",
  "health": "/health"
}
```

#### 3.2.2 Health Check Endpoints

##### Basic Health Check
```http
GET /health
```

**Response Example:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "pooled-agent-service",
  "version": "0.1.0"
}
```

##### Readiness Check
```http
GET /health/ready
```

**Response Example:**
```json
{
  "status": "ready",
  "timestamp": "2024-01-15T10:30:00Z",
  "checks": {
    "database": "ok",
    "external_apis": "ok"
  }
}
```

##### Liveness Check
```http
GET /health/live
```

**Response Example:**
```json
{
  "status": "alive",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime_seconds": 3600.25
}
```

#### 3.2.3 Blob Storage Endpoints

##### Get Blob Content
```http
GET /blobs/{blob_name}?container={container_name}&download={boolean}
```

**Parameters:**
- `blob_name` (path): Name of the blob to retrieve
- `container` (query, optional): Container name (uses default if omitted)
- `download` (query, optional): Force download flag

**Response Headers:**
- `Content-Length`: File size
- `Content-Type`: MIME type
- `ETag`: File ETag
- `Last-Modified`: Last modification date
- `Content-Disposition`: Attachment file specification for downloads

##### Get Blob Streaming
```http
GET /blobs/{blob_name}/stream?container={container_name}
```

**Features:**
- Streaming delivery of large files
- Memory-efficient transfer

##### Get Blob Metadata
```http
GET /blobs/{blob_name}/metadata?container={container_name}
```

**Response Example:**
```json
{
  "name": "document.pdf",
  "container": "documents",
  "size": 1024000,
  "content_type": "application/pdf",
  "last_modified": "2024-01-15T10:30:00Z",
  "etag": "\"0x8D9A1B2C3D4E5F6\"",
  "metadata": {},
  "creation_time": "2024-01-15T09:00:00Z"
}
```

##### Check Blob Existence
```http
HEAD /blobs/{blob_name}?container={container_name}
```

**Response:**
- 200: Blob exists
- 404: Blob does not exist

## 4. Configuration Specification

### 4.1 Environment Variables

| Variable Name | Type | Default Value | Description |
|---------------|------|---------------|-------------|
| `APP_NAME` | string | "Pooled Agent Service" | Application name |
| `APP_VERSION` | string | "0.1.0" | Application version |
| `HOST` | string | "0.0.0.0" | Server host |
| `PORT` | int | 8000 | Server port |
| `DEBUG` | bool | false | Debug mode |
| `CORS_ORIGINS` | list | ["*"] | CORS allowed origins |
| `LOG_LEVEL` | string | "INFO" | Log level |
| `AZURE_STORAGE_ACCOUNT_NAME` | string | "" | Azure Storage account name |
| `AZURE_STORAGE_ACCOUNT_KEY` | string | "" | Azure Storage account key |
| `AZURE_STORAGE_CONNECTION_STRING` | string | "" | Azure Storage connection string |
| `AZURE_STORAGE_CONTAINER_NAME` | string | "documents" | Default container name |

### 4.2 Authentication Methods

Azure Blob Storage authentication is selected in the following priority order:

1. **Connection String**: When `AZURE_STORAGE_CONNECTION_STRING` is configured
2. **Account Key**: When `AZURE_STORAGE_ACCOUNT_NAME` and `AZURE_STORAGE_ACCOUNT_KEY` are configured
3. **Default Authentication**: Uses `DefaultAzureCredential` (Managed Identity, Azure CLI, etc.)

## 5. Error Handling

### 5.1 Error Response Format
```json
{
  "detail": "Error message"
}
```

### 5.2 Error Codes

| HTTP Status | Description | Occurrence Condition |
|-------------|-------------|---------------------|
| 200 | Success | Normal processing |
| 404 | Not Found | Blob not found |
| 500 | Internal Server Error | Server internal error |
| 503 | Service Unavailable | Service not ready |

### 5.3 Custom Exceptions

- `BlobStorageError`: General error for Blob Storage operations
- `BlobNotFoundError`: Error when blob is not found

## 6. Logging Specification

### 6.1 Log Format
```
{timestamp} - {logger_name} - {level} - {message}
```

### 6.2 Log Levels
- **DEBUG**: Detailed debug information
- **INFO**: General information (default)
- **WARNING**: Warning
- **ERROR**: Error

### 6.3 Structured Logging
Each request includes the following information:
- `correlation_id`: Request identifier
- `method`: HTTP method
- `path`: Request path
- `status_code`: Response status
- `process_time`: Processing time

### 6.4 Response Headers
- `X-Correlation-ID`: Request identifier
- `X-Process-Time`: Processing time (seconds)

## 7. Security Specification

### 7.1 CORS Configuration
- Allows all origins by default (for development)
- Requires proper origin restrictions in production

### 7.2 Azure Blob Storage Security
- Supports multiple authentication methods
- Access control based on principle of least privilege
- Connection information managed through environment variables

### 7.3 Log Security
- Avoids logging sensitive information
- Request tracking through correlation IDs

## 8. Performance Specification

### 8.1 Streaming Support
- Memory-efficient delivery of large files
- Stream processing using BytesIO

### 8.2 Asynchronous Processing
- High concurrency through FastAPI's asynchronous processing
- Efficient processing of I/O bound tasks

## 9. Dependencies

### 9.1 Main Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| fastapi | >=0.115.13 | Web framework |
| uvicorn | >=0.34.3 | ASGI server |
| pydantic | >=2.0.0,<3.0.0 | Data validation |
| pydantic-settings | >=2.0.0 | Configuration management |
| azure-storage-blob | >=12.19.0 | Azure Blob Storage |
| azure-identity | >=1.15.0 | Azure authentication |

### 9.2 Test Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| pytest | >=7.0.0 | Test framework |
| pytest-asyncio | >=0.21.0 | Async testing |
| pytest-cov | >=4.0.0 | Coverage measurement |
| httpx | >=0.25.0 | HTTP client |
| pytest-mock | >=3.10.0 | Mocking |

## 10. Deployment Specification

### 10.1 Docker Support
- Containerization through Dockerfile
- Multi-stage build support

### 10.2 Kubernetes Support
- Provides health check endpoints
- Readiness/Liveness probe support

### 10.3 Environment-specific Configuration
- Configuration management through environment variables
- .env file support

## 11. Operations Specification

### 11.1 Monitoring Items
- Health check endpoints
- Response time
- Error rate
- System resource usage

### 11.2 Metrics
- Request count
- Response time distribution
- Error occurrence rate
- Blob Storage access status

### 11.3 Log Monitoring
- Search and analysis through structured logs
- Request tracking through correlation IDs
- Error pattern detection

## 12. Future Extension Plans

### 12.1 Authentication Features
- JWT token authentication
- OAuth 2.0 / OpenID Connect
- Multi-tenant authentication

### 12.2 Additional Features
- File upload functionality
- Blob Storage write operations
- File conversion functionality

### 12.3 Performance Improvements
- Cache functionality
- CDN integration
- Database integration

### 12.4 Operations Features
- Metrics collection
- Distributed tracing
- Alert functionality

---

**Last Updated**: June 25, 2025  
**Version**: 1.1  
**Author**: System Generated Documentation
