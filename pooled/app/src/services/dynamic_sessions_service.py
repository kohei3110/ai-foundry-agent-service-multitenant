"""
Container Apps Dynamic Sessions service module.
Handles code execution in Azure Container Apps dynamic sessions.
"""
import logging
import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import httpx
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.core.exceptions import AzureError

from ..core.config import settings

logger = logging.getLogger(__name__)


class DynamicSessionsError(Exception):
    """Base exception for dynamic sessions operations"""
    pass


class SessionNotFoundError(DynamicSessionsError):
    """Exception raised when a session is not found"""
    pass


class CodeExecutionError(DynamicSessionsError):
    """Exception raised when code execution fails"""
    pass


class DynamicSessionsInterface(ABC):
    """Interface for dynamic sessions operations"""

    @abstractmethod
    async def execute_code(self, session_id: str, code: str) -> Dict[str, Any]:
        """Execute code in a dynamic session"""
        pass

    @abstractmethod
    async def create_session(self, pool_id: str, **kwargs) -> Dict[str, Any]:
        """Create a new dynamic session"""
        pass

    @abstractmethod
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the status of a dynamic session"""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete a dynamic session"""
        pass


class AzureDynamicSessionsService(DynamicSessionsInterface):
    """Azure Container Apps Dynamic Sessions service implementation"""

    def __init__(
        self,
        base_url: str,
        pool_management_endpoint: str,
        client_id: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize the Azure Dynamic Sessions service.
        
        Args:
            base_url: Base URL for the dynamic sessions API
            pool_management_endpoint: Pool management endpoint URL
            client_id: Azure client ID for user-assigned managed identity
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.pool_management_endpoint = pool_management_endpoint.rstrip('/')
        self.timeout = timeout
        
        # Initialize managed identity credential
        if client_id:
            self.credential = ManagedIdentityCredential(client_id=client_id)
        else:
            self.credential = DefaultAzureCredential()
            
        logger.info(f"Initialized Azure Dynamic Sessions service with base URL: {self.base_url}")

    async def _get_access_token(self) -> str:
        """Get an access token for Azure management API"""
        try:
            token = self.credential.get_token("https://dynamicsessions.io/.default")
            return token.token
        except AzureError as e:
            logger.error(f"Failed to get access token: {e}")
            raise DynamicSessionsError(f"Authentication failed: {e}")

    async def execute_code(self, session_id: str, code: str) -> Dict[str, Any]:
        """
        Execute code in a Container Apps dynamic session.
        
        Args:
            session_id: The session identifier
            code: Python code to execute
            
        Returns:
            Dict containing execution results
            
        Raises:
            SessionNotFoundError: If the session doesn't exist
            CodeExecutionError: If code execution fails
            DynamicSessionsError: For other API errors
        """
        try:
            access_token = await self._get_access_token()
            
            url = f"{self.base_url}/code/execute"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "api-version": "2024-02-02-preview",
                "identifier": session_id
            }
            
            payload = {
                "properties": {
                    "codeInputType": "inline",
                    "executionType": "synchronous",
                    "code": code
                }
            }
            
            logger.info(f"Executing code in session: {session_id}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    params=params,
                    json=payload
                )
                
                if response.status_code == 404:
                    raise SessionNotFoundError(f"Session {session_id} not found")
                elif response.status_code == 400:
                    error_detail = response.text
                    raise CodeExecutionError(f"Code execution failed: {error_detail}")
                elif response.status_code >= 400:
                    response.raise_for_status()
                
                result = response.json()
                logger.info(f"Code execution completed for session: {session_id}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error executing code: {e}")
            raise DynamicSessionsError(f"HTTP error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Request error executing code: {e}")
            raise DynamicSessionsError(f"Request error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error executing code: {e}")
            raise DynamicSessionsError(f"Unexpected error: {e}")

    async def create_session(self, pool_id: str, **kwargs) -> Dict[str, Any]:
        """
        Create a new dynamic session in the specified pool.
        
        Args:
            pool_id: The session pool identifier
            **kwargs: Additional session creation parameters
            
        Returns:
            Dict containing session information
            
        Raises:
            DynamicSessionsError: For API errors
        """
        try:
            access_token = await self._get_access_token()
            
            url = f"{self.pool_management_endpoint}/session"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            params = {
                "api-version": "2025-02-02-preview",
                "identifier": "testid1"
            }
            
            payload = {
                "properties": kwargs
            }
            
            logger.info(f"Creating session in pool: testid1")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    params=params,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Session created in pool: {pool_id}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating session: {e}")
            raise DynamicSessionsError(f"HTTP error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Request error creating session: {e}")
            raise DynamicSessionsError(f"Request error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating session: {e}")
            raise DynamicSessionsError(f"Unexpected error: {e}")

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get the status of a dynamic session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Dict containing session status
            
        Raises:
            SessionNotFoundError: If the session doesn't exist
            DynamicSessionsError: For other API errors
        """
        try:
            access_token = await self._get_access_token()
            
            url = f"{self.base_url}/sessions/{session_id}"
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            
            params = {
                "api-version": "2024-02-02-preview"
            }
            
            logger.info(f"Getting status for session: {session_id}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 404:
                    raise SessionNotFoundError(f"Session {session_id} not found")
                
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Retrieved status for session: {session_id}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting session status: {e}")
            raise DynamicSessionsError(f"HTTP error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Request error getting session status: {e}")
            raise DynamicSessionsError(f"Request error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting session status: {e}")
            raise DynamicSessionsError(f"Unexpected error: {e}")

    async def delete_session(self, session_id: str) -> None:
        """
        Delete a dynamic session.
        
        Args:
            session_id: The session identifier
            
        Raises:
            SessionNotFoundError: If the session doesn't exist
            DynamicSessionsError: For other API errors
        """
        try:
            access_token = await self._get_access_token()
            
            url = f"{self.base_url}/sessions/{session_id}"
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            
            params = {
                "api-version": "2024-02-02-preview"
            }
            
            logger.info(f"Deleting session: {session_id}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    url,
                    headers=headers,
                    params=params
                )
                
                if response.status_code == 404:
                    raise SessionNotFoundError(f"Session {session_id} not found")
                
                response.raise_for_status()
                
                logger.info(f"Deleted session: {session_id}")
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error deleting session: {e}")
            raise DynamicSessionsError(f"HTTP error: {e}")
        except httpx.RequestError as e:
            logger.error(f"Request error deleting session: {e}")
            raise DynamicSessionsError(f"Request error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error deleting session: {e}")
            raise DynamicSessionsError(f"Unexpected error: {e}")
