"""
Unit tests for health router endpoints.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.routers.health import router, get_health_service
from tests.conftest import MockHealthService


class TestHealthRouter:
    """Test cases for health router"""
    
    @pytest.fixture
    def health_client(self, app):
        """Create test client with health router"""
        return TestClient(app)
    
    @pytest.mark.unit
    def test_health_endpoint_success(self, health_client, mock_health_service):
        """Test /health endpoint returns 200 with healthy status"""
        with patch('src.routers.health.get_health_service', return_value=mock_health_service):
            response = health_client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "test-service"  # Mock service returns this name
            assert data["version"] == "test-version"
            assert "timestamp" in data
    
    @pytest.mark.unit
    def test_readiness_endpoint_success(self, health_client, mock_health_service):
        """Test /health/ready endpoint returns 200 when ready"""
        with patch('src.routers.health.get_health_service', return_value=mock_health_service):
            response = health_client.get("/health/ready")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
            assert data["checks"]["database"] == "ok"
            assert data["checks"]["external_apis"] == "ok"
            assert "timestamp" in data
    
    @pytest.mark.unit
    def test_readiness_endpoint_not_ready_database(self, health_client, mock_unhealthy_db_service):
        """Test /health/ready endpoint returns 503 when database is unhealthy"""
        with patch('src.routers.health.get_health_service', return_value=mock_unhealthy_db_service):
            response = health_client.get("/health/ready")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not_ready"
            assert data["checks"]["database"] == "error"
            assert data["checks"]["external_apis"] == "ok"
    
    @pytest.mark.unit
    def test_readiness_endpoint_not_ready_apis(self, health_client, mock_unhealthy_api_service):
        """Test /health/ready endpoint returns 503 when external APIs are unhealthy"""
        with patch('src.routers.health.get_health_service', return_value=mock_unhealthy_api_service):
            response = health_client.get("/health/ready")
            
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not_ready"
            assert data["checks"]["database"] == "ok"
            assert data["checks"]["external_apis"] == "error"
    
    @pytest.mark.unit
    def test_liveness_endpoint_success(self, health_client, mock_health_service):
        """Test /health/live endpoint returns 200 with alive status"""
        with patch('src.routers.health.get_health_service', return_value=mock_health_service):
            response = health_client.get("/health/live")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "alive"
            assert "timestamp" in data
            assert "uptime_seconds" in data
            assert isinstance(data["uptime_seconds"], float)
    
    @pytest.mark.unit
    def test_health_endpoints_include_correlation_id(self, health_client, mock_health_service):
        """Test that health endpoints include correlation ID in response headers"""
        with patch('src.routers.health.get_health_service', return_value=mock_health_service):
            response = health_client.get("/health")
            
            assert "X-Correlation-ID" in response.headers
            assert "X-Process-Time" in response.headers
    
    @pytest.mark.unit
    def test_dependency_injection(self):
        """Test health service dependency injection"""
        service = get_health_service()
        assert service is not None
        assert hasattr(service, 'get_basic_health')
        assert hasattr(service, 'get_readiness_status')
        assert hasattr(service, 'get_liveness_status')
