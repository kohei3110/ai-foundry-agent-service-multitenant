"""
Unit tests for HealthService.
"""
import pytest
from unittest.mock import patch, AsyncMock
from src.services.health_service import HealthService


class TestHealthService:
    """Test cases for HealthService"""
    
    @pytest.fixture
    def health_service(self):
        """Create HealthService instance for testing"""
        return HealthService(service_name="test-service", version="1.0.0")
    
    @pytest.mark.unit
    async def test_get_basic_health(self, health_service):
        """Test basic health status"""
        result = await health_service.get_basic_health()
        
        assert result["status"] == "healthy"
        assert result["service"] == "test-service"
        assert result["version"] == "1.0.0"
        assert "timestamp" in result
        assert result["timestamp"].endswith("Z")
    
    @pytest.mark.unit
    async def test_get_liveness_status(self, health_service):
        """Test liveness status"""
        result = await health_service.get_liveness_status()
        
        assert result["status"] == "alive"
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert isinstance(result["uptime_seconds"], float)
        assert result["uptime_seconds"] >= 0
    
    @pytest.mark.unit
    async def test_get_readiness_status_all_healthy(self, health_service):
        """Test readiness status when all dependencies are healthy"""
        with patch.object(health_service, 'check_database', return_value=True), \
             patch.object(health_service, 'check_external_apis', return_value=True):
            
            result = await health_service.get_readiness_status()
            
            assert result["status"] == "ready"
            assert result["checks"]["database"] == "ok"
            assert result["checks"]["external_apis"] == "ok"
            assert "timestamp" in result
    
    @pytest.mark.unit
    async def test_get_readiness_status_database_unhealthy(self, health_service):
        """Test readiness status when database is unhealthy"""
        with patch.object(health_service, 'check_database', return_value=False), \
             patch.object(health_service, 'check_external_apis', return_value=True):
            
            result = await health_service.get_readiness_status()
            
            assert result["status"] == "not_ready"
            assert result["checks"]["database"] == "error"
            assert result["checks"]["external_apis"] == "ok"
    
    @pytest.mark.unit
    async def test_get_readiness_status_apis_unhealthy(self, health_service):
        """Test readiness status when external APIs are unhealthy"""
        with patch.object(health_service, 'check_database', return_value=True), \
             patch.object(health_service, 'check_external_apis', return_value=False):
            
            result = await health_service.get_readiness_status()
            
            assert result["status"] == "not_ready"
            assert result["checks"]["database"] == "ok"
            assert result["checks"]["external_apis"] == "error"
    
    @pytest.mark.unit
    async def test_get_readiness_status_all_unhealthy(self, health_service):
        """Test readiness status when all dependencies are unhealthy"""
        with patch.object(health_service, 'check_database', return_value=False), \
             patch.object(health_service, 'check_external_apis', return_value=False):
            
            result = await health_service.get_readiness_status()
            
            assert result["status"] == "not_ready"
            assert result["checks"]["database"] == "error"
            assert result["checks"]["external_apis"] == "error"
    
    @pytest.mark.unit
    async def test_check_database_default_implementation(self, health_service):
        """Test default database check implementation"""
        result = await health_service.check_database()
        assert result is True  # Default implementation returns True
    
    @pytest.mark.unit
    async def test_check_external_apis_default_implementation(self, health_service):
        """Test default external APIs check implementation"""
        result = await health_service.check_external_apis()
        assert result is True  # Default implementation returns True
    
    @pytest.mark.unit
    def test_service_initialization(self):
        """Test service initialization with custom parameters"""
        service = HealthService(service_name="custom-service", version="2.0.0")
        assert service.service_name == "custom-service"
        assert service.version == "2.0.0"
        assert hasattr(service, 'start_time')
    
    @pytest.mark.unit
    def test_service_initialization_defaults(self):
        """Test service initialization with default parameters"""
        service = HealthService()
        assert service.service_name == "pooled-agent-service"
        assert service.version == "0.1.0"
