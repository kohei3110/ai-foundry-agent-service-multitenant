"""
Unit tests for blob storage router endpoints.
"""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from src.services.blob_storage_service import BlobNotFoundError, BlobStorageError


class MockBlobStorageService:
    """Mock blob storage service for testing"""
    
    def __init__(self, should_fail: bool = False, not_found: bool = False):
        self.should_fail = should_fail
        self.not_found = not_found
    
    async def get_blob(self, blob_name: str, container_name: str = None):
        if self.not_found:
            raise BlobNotFoundError(f"Blob '{blob_name}' not found")
        if self.should_fail:
            raise BlobStorageError("Storage service error")
        return b"test content"
    
    async def get_blob_stream(self, blob_name: str, container_name: str = None):
        if self.not_found:
            raise BlobNotFoundError(f"Blob '{blob_name}' not found")
        if self.should_fail:
            raise BlobStorageError("Storage service error")
        from io import BytesIO
        return BytesIO(b"test content")
    
    async def get_blob_metadata(self, blob_name: str, container_name: str = None):
        if self.not_found:
            raise BlobNotFoundError(f"Blob '{blob_name}' not found")
        if self.should_fail:
            raise BlobStorageError("Storage service error")
        return {
            "name": blob_name,
            "container": container_name or "test-container",
            "size": 12,
            "content_type": "text/plain",
            "last_modified": "2023-01-01T00:00:00Z",
            "etag": "test-etag",
            "metadata": {},
            "creation_time": "2023-01-01T00:00:00Z"
        }
    
    async def blob_exists(self, blob_name: str, container_name: str = None):
        if self.should_fail:
            raise BlobStorageError("Storage service error")
        return not self.not_found


class TestBlobStorageRouter:
    """Test cases for blob storage router"""
    
    @pytest.fixture
    def mock_blob_service(self):
        """Create mock blob storage service"""
        return MockBlobStorageService()
    
    @pytest.fixture
    def mock_not_found_service(self):
        """Create mock blob storage service that returns not found"""
        return MockBlobStorageService(not_found=True)
    
    @pytest.fixture
    def mock_error_service(self):
        """Create mock blob storage service that fails"""
        return MockBlobStorageService(should_fail=True)
    
    @pytest.mark.unit
    def test_get_blob_content_success(self, client, mock_blob_service):
        """Test successful blob content retrieval"""
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_blob_service):
            response = client.get("/blobs/test-blob.txt")
            
            assert response.status_code == 200
            assert response.content == b"test content"
            assert response.headers["content-type"] == "text/plain"
            assert "content-length" in response.headers
    
    @pytest.mark.unit
    def test_get_blob_content_with_container(self, client, mock_blob_service):
        """Test blob content retrieval with custom container"""
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_blob_service):
            response = client.get("/blobs/test-blob.txt?container=custom-container")
            
            assert response.status_code == 200
            assert response.content == b"test content"
    
    @pytest.mark.unit
    def test_get_blob_content_download(self, client, mock_blob_service):
        """Test blob content retrieval with download flag"""
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_blob_service):
            response = client.get("/blobs/test-blob.txt?download=true")
            
            assert response.status_code == 200
            assert response.content == b"test content"
            assert "attachment" in response.headers.get("content-disposition", "")
    
    @pytest.mark.unit
    def test_get_blob_content_not_found(self, client, mock_not_found_service):
        """Test blob content retrieval when blob not found"""
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_not_found_service):
            response = client.get("/blobs/nonexistent.txt")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]
    
    @pytest.mark.unit
    def test_get_blob_content_storage_error(self, client, mock_error_service):
        """Test blob content retrieval with storage error"""
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_error_service):
            response = client.get("/blobs/test-blob.txt")
            
            assert response.status_code == 500
            assert "Internal server error" in response.json()["detail"]
    
    @pytest.mark.unit
    def test_get_blob_stream_success(self, client, mock_blob_service):
        """Test successful blob stream retrieval"""
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_blob_service):
            response = client.get("/blobs/test-blob.txt/stream")
            
            assert response.status_code == 200
            assert response.content == b"test content"
            assert response.headers["content-type"] == "text/plain"
    
    @pytest.mark.unit
    def test_get_blob_stream_not_found(self, client, mock_not_found_service):
        """Test blob stream retrieval when blob not found"""
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_not_found_service):
            response = client.get("/blobs/nonexistent.txt/stream")
            
            assert response.status_code == 404
    
    @pytest.mark.unit
    def test_get_blob_metadata_success(self, client, mock_blob_service):
        """Test successful blob metadata retrieval"""
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_blob_service):
            response = client.get("/blobs/test-blob.txt/metadata")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "test-blob.txt"
            assert data["size"] == 12
            assert data["content_type"] == "text/plain"
            assert "etag" in data
    
    @pytest.mark.unit
    def test_get_blob_metadata_with_container(self, client, mock_blob_service):
        """Test blob metadata retrieval with custom container"""
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_blob_service):
            response = client.get("/blobs/test-blob.txt/metadata?container=custom-container")
            
            assert response.status_code == 200
            data = response.json()
            assert data["container"] == "custom-container"
    
    @pytest.mark.unit
    def test_get_blob_metadata_not_found(self, client, mock_not_found_service):
        """Test blob metadata retrieval when blob not found"""
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_not_found_service):
            response = client.get("/blobs/nonexistent.txt/metadata")
            
            assert response.status_code == 404
    
    @pytest.mark.unit
    def test_check_blob_exists_success(self, client, mock_blob_service):
        """Test successful blob existence check"""
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_blob_service):
            response = client.head("/blobs/test-blob.txt")
            
            assert response.status_code == 200
            assert "content-length" in response.headers
            assert "content-type" in response.headers
    
    @pytest.mark.unit
    def test_check_blob_exists_not_found(self, client, mock_not_found_service):
        """Test blob existence check when blob not found"""
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_not_found_service):
            response = client.head("/blobs/nonexistent.txt")
            
            assert response.status_code == 404
    
    @pytest.mark.unit
    def test_check_blob_exists_storage_error(self, client, mock_error_service):
        """Test blob existence check with storage error"""
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_error_service):
            response = client.head("/blobs/test-blob.txt")
            
            assert response.status_code == 500
    
    @pytest.mark.unit
    def test_dependency_injection(self):
        """Test blob storage service dependency injection"""
        from src.routers.blob_storage import get_blob_storage_service
        from src.services.blob_storage_service import BlobStorageInterface
        
        # Mock the settings to avoid Azure authentication
        with patch('src.routers.blob_storage.settings') as mock_settings:
            mock_settings.azure_storage_account_name = "test"
            mock_settings.azure_storage_account_key = "test"
            mock_settings.azure_storage_connection_string = None
            mock_settings.azure_storage_container_name = "test"
            
            with patch('src.routers.blob_storage.AzureBlobStorageService') as mock_service_class:
                mock_service_instance = AsyncMock()
                mock_service_class.return_value = mock_service_instance
                
                service = get_blob_storage_service()
                
                assert service is mock_service_instance
                mock_service_class.assert_called_once_with(
                    account_name="test",
                    account_key="test", 
                    connection_string=None,
                    default_container="test"
                )
        
        with patch('src.routers.blob_storage.AzureBlobStorageService') as mock_service:
            service = get_blob_storage_service()
            assert mock_service.called
