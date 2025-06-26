"""
Integration tests for dynamic sessions service.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import httpx

from src.services.dynamic_sessions_service import (
    AzureDynamicSessionsService,
    DynamicSessionsError,
    SessionNotFoundError,
    CodeExecutionError
)


class TestAzureDynamicSessionsService:
    """Test cases for Azure Dynamic Sessions service"""

    @pytest.fixture
    def service(self):
        """Create a test service instance"""
        return AzureDynamicSessionsService(
            base_url="https://test.sessions.azure.com",
            pool_management_endpoint="https://management.azure.com/test",
            client_id="test-client-id"
        )

    @pytest.fixture
    def mock_credential(self):
        """Create a mock credential"""
        credential = Mock()
        token = Mock()
        token.token = "test-access-token"
        credential.get_token.return_value = token
        return credential

    @pytest.mark.integration
    async def test_execute_code_success(self, service, mock_credential):
        """Test successful code execution"""
        # Mock the credential
        service.credential = mock_credential

        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "properties": {
                "executionTimeMs": 150,
                "result": {"output": "Hello, World!"}
            }
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await service.execute_code("test-session", "print('Hello, World!')")

            assert result["properties"]["executionTimeMs"] == 150
            assert result["properties"]["result"]["output"] == "Hello, World!"

    @pytest.mark.integration
    async def test_execute_code_session_not_found(self, service, mock_credential):
        """Test code execution with non-existent session"""
        service.credential = mock_credential

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Session not found", request=Mock(), response=mock_response
        )

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(SessionNotFoundError):
                await service.execute_code("non-existent-session", "print('test')")

    @pytest.mark.integration
    async def test_execute_code_execution_error(self, service, mock_credential):
        """Test code execution with execution error"""
        service.credential = mock_credential

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Syntax error in code"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(CodeExecutionError) as exc_info:
                await service.execute_code("test-session", "invalid python code !!!")

            assert "Syntax error in code" in str(exc_info.value)

    @pytest.mark.integration
    async def test_create_session_success(self, service, mock_credential):
        """Test successful session creation"""
        service.credential = mock_credential

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "new-session-123",
            "properties": {
                "provisioningState": "Succeeded",
                "createdTime": "2024-06-26T10:30:00Z"
            }
        }
        mock_response.raise_for_status = Mock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = await service.create_session("test-pool", timeout=3600)

            assert result["name"] == "new-session-123"
            assert result["properties"]["provisioningState"] == "Succeeded"

    @pytest.mark.integration
    async def test_get_session_status_success(self, service, mock_credential):
        """Test successful session status retrieval"""
        service.credential = mock_credential

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "properties": {
                "provisioningState": "Running",
                "createdTime": "2024-06-26T10:30:00Z"
            }
        }
        mock_response.raise_for_status = Mock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = await service.get_session_status("test-session")

            assert result["properties"]["provisioningState"] == "Running"

    @pytest.mark.integration
    async def test_delete_session_success(self, service, mock_credential):
        """Test successful session deletion"""
        service.credential = mock_credential

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.delete = AsyncMock(return_value=mock_response)

            # Should not raise any exception
            await service.delete_session("test-session")

    @pytest.mark.integration
    async def test_authentication_error(self, service):
        """Test authentication error handling"""
        # Mock credential to raise an error
        service.credential = Mock()
        service.credential.get_token.side_effect = Exception("Authentication failed")

        with pytest.raises(DynamicSessionsError) as exc_info:
            await service.execute_code("test-session", "print('test')")

        assert "Authentication failed" in str(exc_info.value)

    @pytest.mark.integration
    async def test_network_error(self, service, mock_credential):
        """Test network error handling"""
        service.credential = mock_credential

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.RequestError("Network error")
            )

            with pytest.raises(DynamicSessionsError) as exc_info:
                await service.execute_code("test-session", "print('test')")

            assert "Request error" in str(exc_info.value)
