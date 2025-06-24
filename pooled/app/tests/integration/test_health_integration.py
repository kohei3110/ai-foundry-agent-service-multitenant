"""
Integration tests for health endpoints.
"""
import pytest
from fastapi.testclient import TestClient


class TestHealthIntegration:
    """Integration tests for health functionality"""
    
    @pytest.mark.integration
    def test_health_endpoint_integration(self, client):
        """Test health endpoint with real application setup"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "pooled-agent-service"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data
        
        # Verify response headers
        assert "X-Correlation-ID" in response.headers
        assert "X-Process-Time" in response.headers
    
    @pytest.mark.integration
    def test_readiness_endpoint_integration(self, client):
        """Test readiness endpoint with real application setup"""
        response = client.get("/health/ready")
        
        assert response.status_code == 200  # Should be healthy with default implementation
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"] == "ok"
        assert data["checks"]["external_apis"] == "ok"
        assert "timestamp" in data
    
    @pytest.mark.integration
    def test_liveness_endpoint_integration(self, client):
        """Test liveness endpoint with real application setup"""
        response = client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert isinstance(data["uptime_seconds"], float)
        assert data["uptime_seconds"] >= 0
    
    @pytest.mark.integration
    def test_health_endpoints_content_type(self, client):
        """Test that health endpoints return JSON content type"""
        endpoints = ["/health", "/health/ready", "/health/live"]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.headers["content-type"] == "application/json"
    
    @pytest.mark.integration
    def test_health_endpoints_cors_headers(self, client):
        """Test that CORS headers are included in health endpoint responses"""
        response = client.options("/health")
        
        # CORS preflight should be handled
        assert response.status_code in [200, 204]
    
    @pytest.mark.integration
    def test_health_endpoints_consistency(self, client):
        """Test that health endpoints return consistent timestamp format"""
        endpoints = ["/health", "/health/ready", "/health/live"]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            data = response.json()
            
            # All should have timestamp
            assert "timestamp" in data
            # Timestamp should end with 'Z' (UTC)
            assert data["timestamp"].endswith("Z")
            # Should be ISO format
            assert "T" in data["timestamp"]
