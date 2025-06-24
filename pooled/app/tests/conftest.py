"""
Test configuration and fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from src.core import create_app
from src.services.health_service import HealthCheckInterface


class MockHealthService(HealthCheckInterface):
    """Mock health service for testing"""
    
    def __init__(self, db_healthy: bool = True, api_healthy: bool = True):
        self.db_healthy = db_healthy
        self.api_healthy = api_healthy
        self.service_name = "test-service"
        self.version = "test-version"
    
    async def check_database(self) -> bool:
        return self.db_healthy
    
    async def check_external_apis(self) -> bool:
        return self.api_healthy
    
    async def get_basic_health(self):
        return {
            "status": "healthy",
            "timestamp": "2023-01-01T00:00:00Z",
            "service": self.service_name,
            "version": self.version
        }
    
    async def get_readiness_status(self):
        db_ok = await self.check_database()
        api_ok = await self.check_external_apis()
        return {
            "status": "ready" if db_ok and api_ok else "not_ready",
            "timestamp": "2023-01-01T00:00:00Z",
            "checks": {
                "database": "ok" if db_ok else "error",
                "external_apis": "ok" if api_ok else "error"
            }
        }
    
    async def get_liveness_status(self):
        return {
            "status": "alive",
            "timestamp": "2023-01-01T00:00:00Z",
            "uptime_seconds": 123.45
        }


@pytest.fixture
def app():
    """Create test app"""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_health_service():
    """Create mock health service"""
    return MockHealthService()


@pytest.fixture
def mock_unhealthy_db_service():
    """Create mock health service with unhealthy database"""
    return MockHealthService(db_healthy=False)


@pytest.fixture
def mock_unhealthy_api_service():
    """Create mock health service with unhealthy external APIs"""
    return MockHealthService(api_healthy=False)
