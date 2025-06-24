"""
Health check service module.
Handles all health-related business logic.
"""
import time
from datetime import datetime
from typing import Dict, Any
from abc import ABC, abstractmethod


class HealthCheckInterface(ABC):
    """Interface for health check operations (Dependency Inversion Principle)"""
    
    @abstractmethod
    async def check_database(self) -> bool:
        pass
    
    @abstractmethod
    async def check_external_apis(self) -> bool:
        pass


class HealthService(HealthCheckInterface):
    """Health service implementation"""
    
    def __init__(self, service_name: str = "pooled-agent-service", version: str = "0.1.0"):
        self.service_name = service_name
        self.version = version
        self.start_time = time.time()
    
    async def get_basic_health(self) -> Dict[str, Any]:
        """Get basic health status"""
        return {
            "status": "healthy",
            "timestamp": self._get_current_timestamp(),
            "service": self.service_name,
            "version": self.version
        }
    
    async def get_readiness_status(self) -> Dict[str, Any]:
        """Get readiness status with dependency checks"""
        database_ok = await self.check_database()
        external_apis_ok = await self.check_external_apis()
        
        return {
            "status": "ready" if database_ok and external_apis_ok else "not_ready",
            "timestamp": self._get_current_timestamp(),
            "checks": {
                "database": "ok" if database_ok else "error",
                "external_apis": "ok" if external_apis_ok else "error"
            }
        }
    
    async def get_liveness_status(self) -> Dict[str, Any]:
        """Get liveness status"""
        return {
            "status": "alive",
            "timestamp": self._get_current_timestamp(),
            "uptime_seconds": round(time.time() - self.start_time, 2)
        }
    
    async def check_database(self) -> bool:
        """Check database connectivity"""
        # TODO: Implement actual database check
        # Example: await database.execute("SELECT 1")
        return True
    
    async def check_external_apis(self) -> bool:
        """Check external API connectivity"""
        # TODO: Implement actual external API checks
        # Example: async with httpx.AsyncClient() as client:
        #     response = await client.get("https://api.example.com/health")
        #     return response.status_code == 200
        return True
    
    def _get_current_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format"""
        return datetime.utcnow().isoformat() + "Z"
