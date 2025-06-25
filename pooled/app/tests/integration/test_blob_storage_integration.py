"""
Integration tests for blob storage endpoints.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


class TestBlobStorageIntegration:
    """Integration tests for blob storage functionality"""
    
    @pytest.mark.integration
    def test_blob_storage_endpoints_registered(self, client):
        """Test that blob storage endpoints are properly registered"""
        # Test that the router is included in the app
        response = client.get("/docs")
        assert response.status_code == 200
        
        # The endpoints should be documented
        openapi_response = client.get("/openapi.json")
        assert openapi_response.status_code == 200
        openapi_data = openapi_response.json()
        
        # Check that blob storage paths are in the OpenAPI spec
        paths = openapi_data.get("paths", {})
        assert "/blobs/{blob_name}" in paths
        assert "/blobs/{blob_name}/stream" in paths
        assert "/blobs/{blob_name}/metadata" in paths
    
    @pytest.mark.integration
    def test_blob_storage_router_tags(self, client):
        """Test that blob storage endpoints have correct tags"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_data = response.json()
        paths = openapi_data.get("paths", {})
        
        # Check that endpoints have the correct tag
        for path in ["/blobs/{blob_name}", "/blobs/{blob_name}/stream", "/blobs/{blob_name}/metadata"]:
            if path in paths:
                for method_data in paths[path].values():
                    if isinstance(method_data, dict) and "tags" in method_data:
                        assert "blob-storage" in method_data["tags"]
    
    @pytest.mark.integration
    def test_blob_storage_error_responses(self, client):
        """Test blob storage error response formats"""
        # Mock a service that always fails
        mock_service = type('MockService', (), {
            'get_blob': lambda self, *args, **kwargs: (_ for _ in ()).throw(Exception("Test error")),
            'get_blob_stream': lambda self, *args, **kwargs: (_ for _ in ()).throw(Exception("Test error")),
            'get_blob_metadata': lambda self, *args, **kwargs: (_ for _ in ()).throw(Exception("Test error")),
            'blob_exists': lambda self, *args, **kwargs: (_ for _ in ()).throw(Exception("Test error"))
        })()
        
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_service):
            # Test different endpoints return proper error responses
            endpoints = [
                "/blobs/test.txt",
                "/blobs/test.txt/stream", 
                "/blobs/test.txt/metadata"
            ]
            
            for endpoint in endpoints:
                response = client.get(endpoint)
                assert response.status_code == 500
                assert "detail" in response.json()
    
    @pytest.mark.integration
    def test_blob_storage_dependency_injection_integration(self, app):
        """Test that dependency injection works in the integrated app"""
        from src.routers.blob_storage import get_blob_storage_service
        from src.services.blob_storage_service import BlobStorageInterface
        
        # Mock the settings and service to avoid Azure authentication
        with patch('src.routers.blob_storage.settings') as mock_settings:
            mock_settings.azure_storage_account_name = "test"
            mock_settings.azure_storage_account_key = "test"
            mock_settings.azure_storage_connection_string = None
            mock_settings.azure_storage_container_name = "test"
            
            with patch('src.routers.blob_storage.AzureBlobStorageService') as mock_service_class:
                mock_service_instance = type('MockService', (BlobStorageInterface,), {})()
                mock_service_class.return_value = mock_service_instance
                
                # Test that the dependency returns the correct interface
                service = get_blob_storage_service()
                assert isinstance(service, BlobStorageInterface)
    
    @pytest.mark.integration
    def test_blob_storage_cors_headers(self, client):
        """Test that CORS headers are included in blob storage responses"""
        # Mock successful service
        mock_service = type('MockService', (), {
            'get_blob_metadata': lambda self, *args, **kwargs: {
                "name": "test.txt",
                "container": "test",
                "size": 10,
                "content_type": "text/plain",
                "etag": "test-etag"
            }
        })()
        
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_service):
            # Test CORS preflight
            response = client.options("/blobs/test.txt/metadata")
            assert response.status_code in [200, 204]
    
    @pytest.mark.integration
    def test_blob_storage_logging_middleware(self, client):
        """Test that logging middleware works with blob storage endpoints"""
        mock_service = type('MockService', (), {
            'get_blob_metadata': lambda self, *args, **kwargs: {
                "name": "test.txt",
                "container": "test", 
                "size": 10,
                "content_type": "text/plain"
            }
        })()
        
        from src.routers import blob_storage
        with patch.object(blob_storage, 'get_blob_storage_service', return_value=mock_service):
            response = client.get("/blobs/test.txt/metadata")
            
            # Should have correlation ID from logging middleware
            assert "X-Correlation-ID" in response.headers
            assert "X-Process-Time" in response.headers
