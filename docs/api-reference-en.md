# Pooled Agent Service API Reference

## Overview

This document provides a detailed reference for the Pooled Agent Service REST API. It covers all endpoints, request/response formats, and error handling.

## Base URL

```
http://localhost:8000
```

## Authentication

Authentication is not required in the current version. JWT authentication is planned for future versions.

## Common Headers

### Request Headers
- `Content-Type: application/json` (when sending JSON payload)
- `Accept: application/json`

### Response Headers
- `X-Correlation-ID`: Unique request identifier
- `X-Process-Time`: Processing time (seconds)
- `Content-Type`: Response MIME type

## Endpoint Details

### 1. Root Endpoint

#### Get Service Information
Retrieve basic service information and metadata.

```http
GET /
```

**Response**
- **Status Code**: 200 OK
- **Content-Type**: application/json

```json
{
  "message": "Pooled Agent Service is running",
  "architecture": "pooled",
  "version": "0.1.0",
  "docs": "/docs",
  "health": "/health"
}
```

**Response Fields**
- `message` (string): Service running message
- `architecture` (string): Architecture type
- `version` (string): Service version
- `docs` (string): API documentation path
- `health` (string): Health check endpoint path

---

### 2. Health Check Endpoints

#### Basic Health Check
Check the basic operational status of the service.

```http
GET /health
```

**Response**
- **Status Code**: 200 OK
- **Content-Type**: application/json

```json
{
  "status": "healthy",
  "timestamp": "2024-06-25T10:30:00Z",
  "service": "pooled-agent-service",
  "version": "0.1.0"
}
```

**Response Fields**
- `status` (string): Health state ("healthy")
- `timestamp` (string): Check execution time (ISO 8601)
- `service` (string): Service name
- `version` (string): Service version

#### Readiness Check
Endpoint compatible with Kubernetes readiness probe.

```http
GET /health/ready
```

**Response**
- **Status Code**: 200 OK (ready) / 503 Service Unavailable (not ready)
- **Content-Type**: application/json

```json
{
  "status": "ready",
  "timestamp": "2024-06-25T10:30:00Z",
  "checks": {
    "database": "ok",
    "external_apis": "ok"
  }
}
```

**Response Fields**
- `status` (string): Readiness state ("ready" | "not_ready")
- `timestamp` (string): Check execution time
- `checks` (object): Check results for each dependent service
  - `database` (string): Database connection status
  - `external_apis` (string): External API connection status

#### Liveness Check
Endpoint compatible with Kubernetes liveness probe.

```http
GET /health/live
```

**Response**
- **Status Code**: 200 OK
- **Content-Type**: application/json

```json
{
  "status": "alive",
  "timestamp": "2024-06-25T10:30:00Z",
  "uptime_seconds": 3600.25
}
```

**Response Fields**
- `status` (string): Liveness state ("alive")
- `timestamp` (string): Check execution time
- `uptime_seconds` (number): Service uptime (seconds)

---

### 3. Blob Storage Endpoints

#### Get Blob Content
Retrieve file content from Azure Blob Storage.

```http
GET /blobs/{blob_name}
```

**Path Parameters**
- `blob_name` (string, required): Name of the blob to retrieve

**Query Parameters**
- `container` (string, optional): Container name (uses default container if omitted)
- `download` (boolean, optional): Force download flag (default: false)

**Request Example**
```http
GET /blobs/document.pdf?container=my-container&download=true
```

**Response**
- **Status Code**: 200 OK
- **Content-Type**: File MIME type

**Response Headers**
- `Content-Length`: File size (bytes)
- `ETag`: File ETag value
- `Last-Modified`: Last modification date
- `Content-Disposition`: Attachment filename when download is specified

**Response Body**
Binary file content

**Error Responses**
```json
// 404 Not Found
{
  "detail": "Blob 'nonexistent.pdf' not found in container 'documents'"
}

// 500 Internal Server Error
{
  "detail": "Internal server error"
}
```

#### Get Blob Streaming
Retrieve large files via streaming delivery.

```http
GET /blobs/{blob_name}/stream
```

**Path Parameters**
- `blob_name` (string, required): Name of the blob to retrieve

**Query Parameters**
- `container` (string, optional): Container name

**Response**
- **Status Code**: 200 OK
- **Content-Type**: File MIME type
- **Transfer-Encoding**: chunked

**Features**
- Memory-efficient delivery of large files
- Progressive download support

#### Get Blob Metadata
Retrieve blob metadata information.

```http
GET /blobs/{blob_name}/metadata
```

**Path Parameters**
- `blob_name` (string, required): Target blob name

**Query Parameters**
- `container` (string, optional): Container name

**Response**
- **Status Code**: 200 OK
- **Content-Type**: application/json

```json
{
  "name": "document.pdf",
  "container": "documents",
  "size": 1024000,
  "content_type": "application/pdf",
  "last_modified": "2024-06-25T10:30:00Z",
  "etag": "\"0x8D9A1B2C3D4E5F6\"",
  "metadata": {
    "author": "John Doe",
    "department": "Engineering"
  },
  "creation_time": "2024-06-25T09:00:00Z"
}
```

**Response Fields**
- `name` (string): Blob name
- `container` (string): Container name
- `size` (number): File size (bytes)
- `content_type` (string): MIME type
- `last_modified` (string): Last modification date (ISO 8601)
- `etag` (string): ETag value
- `metadata` (object): Custom metadata
- `creation_time` (string): Creation date (ISO 8601)

#### Check Blob Existence
Check blob existence (HEAD request).

```http
HEAD /blobs/{blob_name}
```

**Path Parameters**
- `blob_name` (string, required): Name of the blob to check

**Query Parameters**
- `container` (string, optional): Container name

**Response**
- **Status Code**: 200 OK (exists) / 404 Not Found (does not exist)
- **Content-Length**: 0

**Response Headers** (for 200 status)
- `Content-Length`: File size
- `Content-Type`: File MIME type
- `ETag`: ETag value
- `Last-Modified`: Last modification date

---

## Error Handling

### Error Response Format

All error responses are returned in the following format:

```json
{
  "detail": "Detailed error message"
}
```

### HTTP Status Codes

| Code | Name | Description | Occurrence Condition |
|------|------|-------------|---------------------|
| 200 | OK | Success | Request processed successfully |
| 404 | Not Found | Resource not found | Specified blob does not exist |
| 500 | Internal Server Error | Server internal error | Azure Storage connection error, etc. |
| 503 | Service Unavailable | Service unavailable | Dependent services unavailable (during readiness check) |

### Error Types

#### 404 Not Found
```json
{
  "detail": "Blob 'document.pdf' not found in container 'documents'"
}
```

#### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

#### 503 Service Unavailable (during readiness check)
```json
{
  "status": "not_ready",
  "timestamp": "2024-06-25T10:30:00Z",
  "checks": {
    "database": "error",
    "external_apis": "ok"
  }
}
```

---

## Usage Examples

### Using cURL

#### Basic Health Check
```bash
curl -X GET http://localhost:8000/health
```

#### Get Blob Content
```bash
curl -X GET http://localhost:8000/blobs/document.pdf
```

#### Download Blob
```bash
curl -X GET "http://localhost:8000/blobs/document.pdf?download=true" \
  -o downloaded_document.pdf
```

#### Get Blob Metadata
```bash
curl -X GET http://localhost:8000/blobs/document.pdf/metadata
```

#### Check Blob Existence
```bash
curl -I http://localhost:8000/blobs/document.pdf
```

### Using JavaScript Fetch API

#### Get Service Information
```javascript
const response = await fetch('http://localhost:8000/');
const data = await response.json();
console.log(data);
```

#### Get Blob Metadata
```javascript
const response = await fetch('http://localhost:8000/blobs/document.pdf/metadata');
if (response.ok) {
  const metadata = await response.json();
  console.log('File size:', metadata.size);
} else {
  console.error('Blob not found');
}
```

#### Download Blob
```javascript
const response = await fetch('http://localhost:8000/blobs/document.pdf?download=true');
if (response.ok) {
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'document.pdf';
  a.click();
} else {
  console.error('Download failed');
}
```

---

## Rate Limiting

Rate limiting is not implemented in the current version. It is planned for future versions.

## Versioning

API versioning is not currently implemented. When API changes occur, versions will be specified through new endpoint paths or headers.

---

**Last Updated**: June 25, 2024  
**API Version**: 0.1.0
