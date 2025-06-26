"""
Unit tests for dynamic sessions router.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from src.services.dynamic_sessions_service import (
    DynamicSessionsError,
    SessionNotFoundError,
    CodeExecutionError
)


class TestDynamicSessionsRouter:
    """Test cases for dynamic sessions router"""

    @pytest.fixture
    def mock_sessions_service(self):
        """Create a mock dynamic sessions service"""
        service = Mock()
        service.execute_code = AsyncMock()
        service.create_session = AsyncMock()
        service.get_session_status = AsyncMock()
        service.delete_session = AsyncMock()
        return service

    @pytest.mark.unit
    def test_execute_code_success(self, client, mock_sessions_service):
        """Test successful code execution"""
        # Mock service response
        mock_sessions_service.execute_code.return_value = {
            "properties": {
                "executionTimeMs": 150,
                "result": {"output": "Hello, World!"}
            }
        }

        with patch('src.routers.dynamic_sessions.get_dynamic_sessions_service', return_value=mock_sessions_service):
            response = client.post(
                "/sessions/test-session-123/execute",
                json={"code": "print('Hello, World!')"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "test-session-123"
            assert data["status"] == "completed"
            assert "result" in data

    @pytest.mark.unit
    def test_execute_code_session_not_found(self, client, mock_sessions_service):
        """Test code execution with non-existent session"""
        mock_sessions_service.execute_code.side_effect = SessionNotFoundError("Session not found")

        with patch('src.routers.dynamic_sessions.get_dynamic_sessions_service', return_value=mock_sessions_service):
            response = client.post(
                "/sessions/non-existent-session/execute",
                json={"code": "print('Hello, World!')"}
            )

            assert response.status_code == 404
            assert "Session not found" in response.json()["detail"]

    @pytest.mark.unit
    def test_execute_code_execution_error(self, client, mock_sessions_service):
        """Test code execution with execution error"""
        mock_sessions_service.execute_code.side_effect = CodeExecutionError("Syntax error")

        with patch('src.routers.dynamic_sessions.get_dynamic_sessions_service', return_value=mock_sessions_service):
            response = client.post(
                "/sessions/test-session-123/execute",
                json={"code": "invalid python code !!!"}
            )

            assert response.status_code == 400
            assert "Syntax error" in response.json()["detail"]

    @pytest.mark.unit
    def test_execute_code_simple_success(self, client, mock_sessions_service):
        """Test successful simple code execution"""
        mock_sessions_service.execute_code.return_value = {
            "properties": {
                "result": {"output": "Hello, World!"}
            }
        }

        with patch('src.routers.dynamic_sessions.get_dynamic_sessions_service', return_value=mock_sessions_service):
            response = client.post(
                "/sessions/test-session-123/execute/simple",
                json={"code": "print('Hello, World!')"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "test-session-123"
            assert data["status"] == "completed"

    @pytest.mark.unit
    def test_create_session_success(self, client, mock_sessions_service):
        """Test successful session creation"""
        mock_sessions_service.create_session.return_value = {
            "name": "session-456",
            "properties": {
                "provisioningState": "Succeeded",
                "createdTime": "2024-06-26T10:30:00Z"
            }
        }

        with patch('src.routers.dynamic_sessions.get_dynamic_sessions_service', return_value=mock_sessions_service):
            response = client.post(
                "/sessions/",
                json={
                    "pool_id": "test-pool",
                    "session_config": {"timeout": 3600}
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "session-456"
            assert data["status"] == "Succeeded"
            assert data["pool_id"] == "test-pool"

    @pytest.mark.unit
    def test_get_session_status_success(self, client, mock_sessions_service):
        """Test successful session status retrieval"""
        mock_sessions_service.get_session_status.return_value = {
            "properties": {
                "provisioningState": "Running",
                "createdTime": "2024-06-26T10:30:00Z"
            }
        }

        with patch('src.routers.dynamic_sessions.get_dynamic_sessions_service', return_value=mock_sessions_service):
            response = client.get("/sessions/test-session-123")

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == "test-session-123"
            assert data["status"] == "Running"

    @pytest.mark.unit
    def test_get_session_status_not_found(self, client, mock_sessions_service):
        """Test session status retrieval with non-existent session"""
        mock_sessions_service.get_session_status.side_effect = SessionNotFoundError("Session not found")

        with patch('src.routers.dynamic_sessions.get_dynamic_sessions_service', return_value=mock_sessions_service):
            response = client.get("/sessions/non-existent-session")

            assert response.status_code == 404
            assert "Session not found" in response.json()["detail"]

    @pytest.mark.unit
    def test_delete_session_success(self, client, mock_sessions_service):
        """Test successful session deletion"""
        mock_sessions_service.delete_session.return_value = None

        with patch('src.routers.dynamic_sessions.get_dynamic_sessions_service', return_value=mock_sessions_service):
            response = client.delete("/sessions/test-session-123")

            assert response.status_code == 200
            data = response.json()
            assert "deleted successfully" in data["message"]

    @pytest.mark.unit
    def test_delete_session_not_found(self, client, mock_sessions_service):
        """Test session deletion with non-existent session"""
        mock_sessions_service.delete_session.side_effect = SessionNotFoundError("Session not found")

        with patch('src.routers.dynamic_sessions.get_dynamic_sessions_service', return_value=mock_sessions_service):
            response = client.delete("/sessions/non-existent-session")

            assert response.status_code == 404
            assert "Session not found" in response.json()["detail"]

    @pytest.mark.unit
    def test_invalid_code_length(self, client, mock_sessions_service):
        """Test code execution with invalid code length"""
        with patch('src.routers.dynamic_sessions.get_dynamic_sessions_service', return_value=mock_sessions_service):
            # Test empty code
            response = client.post(
                "/sessions/test-session-123/execute",
                json={"code": ""}
            )
            assert response.status_code == 422

            # Test code that's too long (over 50000 characters)
            long_code = "print('x')" * 10000  # Creates a very long string
            response = client.post(
                "/sessions/test-session-123/execute",
                json={"code": long_code}
            )
            assert response.status_code == 422

    @pytest.mark.unit
    def test_dependency_injection(self):
        """Test dynamic sessions service dependency injection"""
        from src.routers.dynamic_sessions import get_dynamic_sessions_service
        
        service = get_dynamic_sessions_service()
        assert service is not None
        assert hasattr(service, 'execute_code')
        assert hasattr(service, 'create_session')
        assert hasattr(service, 'get_session_status')
        assert hasattr(service, 'delete_session')
