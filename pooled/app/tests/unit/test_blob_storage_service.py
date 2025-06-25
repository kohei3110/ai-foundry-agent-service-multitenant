"""
Unit tests for Blob Storage Service.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from io import BytesIO

from src.services.blob_storage_service import (
    AzureBlobStorageService,
    BlobStorageError,
    BlobNotFoundError
)


class TestAzureBlobStorageService:
    """Test cases for AzureBlobStorageService"""
    
    @pytest.fixture
    def mock_blob_service_client(self):
        """Create mock blob service client"""
        mock_client = Mock()
        mock_client.get_blob_client.return_value = Mock()
        return mock_client
    
    @pytest.fixture
    def blob_service(self, mock_blob_service_client):
        """Create blob service instance with mocked client"""
        with patch('src.services.blob_storage_service.BlobServiceClient') as mock_class:
            mock_class.from_connection_string.return_value = mock_blob_service_client
            service = AzureBlobStorageService(
                connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test;EndpointSuffix=core.windows.net",
                default_container="test-container"
            )
            service._blob_service_client = mock_blob_service_client
            return service
    
    @pytest.mark.unit
    async def test_get_blob_success(self, blob_service, mock_blob_service_client):
        """Test successful blob retrieval"""
        # Arrange
        blob_name = "test-blob.txt"
        expected_content = b"test content"
        
        mock_blob_client = Mock()
        mock_download_blob = Mock()
        mock_download_blob.readall.return_value = expected_content
        mock_blob_client.download_blob.return_value = mock_download_blob
        
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client
        
        # Act
        result = await blob_service.get_blob(blob_name)
        
        # Assert
        assert result == expected_content
        mock_blob_service_client.get_blob_client.assert_called_once_with(
            container="test-container", 
            blob=blob_name
        )
        mock_blob_client.download_blob.assert_called_once()
    
    @pytest.mark.unit
    async def test_get_blob_with_custom_container(self, blob_service, mock_blob_service_client):
        """Test blob retrieval with custom container"""
        # Arrange
        blob_name = "test-blob.txt"
        container_name = "custom-container"
        expected_content = b"test content"
        
        mock_blob_client = Mock()
        mock_download_blob = Mock()
        mock_download_blob.readall.return_value = expected_content
        mock_blob_client.download_blob.return_value = mock_download_blob
        
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client
        
        # Act
        result = await blob_service.get_blob(blob_name, container_name)
        
        # Assert
        assert result == expected_content
        mock_blob_service_client.get_blob_client.assert_called_once_with(
            container=container_name, 
            blob=blob_name
        )
    
    @pytest.mark.unit
    async def test_get_blob_not_found(self, blob_service, mock_blob_service_client):
        """Test blob not found error"""
        # Arrange
        from azure.core.exceptions import ResourceNotFoundError
        
        blob_name = "nonexistent-blob.txt"
        
        mock_blob_client = Mock()
        mock_blob_client.download_blob.side_effect = ResourceNotFoundError("Blob not found")
        
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client
        
        # Act & Assert
        with pytest.raises(BlobNotFoundError) as exc_info:
            await blob_service.get_blob(blob_name)
        
        assert "not found" in str(exc_info.value)
    
    @pytest.mark.unit
    async def test_get_blob_stream(self, blob_service, mock_blob_service_client):
        """Test blob stream retrieval"""
        # Arrange
        blob_name = "test-blob.txt"
        expected_content = b"test content"
        
        mock_blob_client = Mock()
        mock_download_blob = Mock()
        mock_download_blob.readall.return_value = expected_content
        mock_blob_client.download_blob.return_value = mock_download_blob
        
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client
        
        # Act
        result = await blob_service.get_blob_stream(blob_name)
        
        # Assert
        assert isinstance(result, BytesIO)
        assert result.read() == expected_content
    
    @pytest.mark.unit
    async def test_get_blob_metadata_success(self, blob_service, mock_blob_service_client):
        """Test successful blob metadata retrieval"""
        # Arrange
        blob_name = "test-blob.txt"
        
        mock_blob_client = Mock()
        mock_properties = Mock()
        mock_properties.size = 1024
        mock_properties.content_settings.content_type = "text/plain"
        mock_properties.last_modified = None
        mock_properties.etag = "test-etag"
        mock_properties.metadata = {"key": "value"}
        mock_properties.creation_time = None
        
        mock_blob_client.get_blob_properties.return_value = mock_properties
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client
        
        # Act
        result = await blob_service.get_blob_metadata(blob_name)
        
        # Assert
        assert result["name"] == blob_name
        assert result["container"] == "test-container"
        assert result["size"] == 1024
        assert result["content_type"] == "text/plain"
        assert result["etag"] == "test-etag"
        assert result["metadata"] == {"key": "value"}
    
    @pytest.mark.unit
    async def test_blob_exists_true(self, blob_service, mock_blob_service_client):
        """Test blob exists check returns True"""
        # Arrange
        blob_name = "existing-blob.txt"
        
        mock_blob_client = Mock()
        mock_blob_client.exists.return_value = True
        
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client
        
        # Act
        result = await blob_service.blob_exists(blob_name)
        
        # Assert
        assert result is True
        mock_blob_client.exists.assert_called_once()
    
    @pytest.mark.unit
    async def test_blob_exists_false(self, blob_service, mock_blob_service_client):
        """Test blob exists check returns False"""
        # Arrange
        blob_name = "nonexistent-blob.txt"
        
        mock_blob_client = Mock()
        mock_blob_client.exists.return_value = False
        
        mock_blob_service_client.get_blob_client.return_value = mock_blob_client
        
        # Act
        result = await blob_service.blob_exists(blob_name)
        
        # Assert
        assert result is False
    
    @pytest.mark.unit
    def test_create_blob_service_client_with_connection_string(self):
        """Test blob service client creation with connection string"""
        # Arrange
        connection_string = "DefaultEndpointsProtocol=https;AccountName=test;AccountKey=test"
        
        with patch('src.services.blob_storage_service.BlobServiceClient') as mock_class:
            mock_client = Mock()
            mock_class.from_connection_string.return_value = mock_client
            
            # Act
            service = AzureBlobStorageService(connection_string=connection_string)
            
            # Assert
            mock_class.from_connection_string.assert_called_once_with(connection_string)
    
    @pytest.mark.unit
    def test_create_blob_service_client_with_account_key(self):
        """Test blob service client creation with account name and key"""
        # Arrange
        account_name = "testaccount"
        account_key = "testkey"
        
        with patch('src.services.blob_storage_service.BlobServiceClient') as mock_class:
            mock_client = Mock()
            mock_class.return_value = mock_client
            
            # Act
            service = AzureBlobStorageService(
                account_name=account_name,
                account_key=account_key
            )
            
            # Assert
            expected_url = f"https://{account_name}.blob.core.windows.net"
            mock_class.assert_called_once_with(
                account_url=expected_url,
                credential=account_key
            )
    
    @pytest.mark.unit
    def test_create_blob_service_client_no_credentials(self):
        """Test blob service client creation without credentials raises error"""
        # Act & Assert
        with pytest.raises(BlobStorageError) as exc_info:
            AzureBlobStorageService()
        
        assert "No valid authentication method" in str(exc_info.value)
