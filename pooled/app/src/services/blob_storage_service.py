"""
Azure Blob Storage service module.
Handles blob storage operations following single responsibility principle.
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO
from io import BytesIO
import httpx

from azure.storage.blob import BlobServiceClient, BlobClient
from azure.core.exceptions import ResourceNotFoundError, AzureError
from azure.identity import DefaultAzureCredential

from .sas_token_service import SasTokenInterface, AzureSasTokenService, SasTokenError

logger = logging.getLogger(__name__)


class BlobStorageError(Exception):
    """Custom exception for blob storage operations"""
    pass


class BlobNotFoundError(BlobStorageError):
    """Exception raised when blob is not found"""
    pass


class BlobStorageInterface(ABC):
    """Interface for blob storage operations (Dependency Inversion Principle)"""
    
    @abstractmethod
    async def get_blob(self, blob_name: str, container_name: Optional[str] = None) -> bytes:
        """Get blob content as bytes"""
        pass
    
    @abstractmethod
    async def get_blob_stream(self, blob_name: str, container_name: Optional[str] = None) -> BinaryIO:
        """Get blob content as stream"""
        pass
    
    @abstractmethod
    async def get_blob_metadata(self, blob_name: str, container_name: Optional[str] = None) -> Dict[str, Any]:
        """Get blob metadata"""
        pass
    
    @abstractmethod
    async def blob_exists(self, blob_name: str, container_name: Optional[str] = None) -> bool:
        """Check if blob exists"""
        pass


class AzureBlobStorageService(BlobStorageInterface):
    """Azure Blob Storage service implementation with SAS token support"""
    
    def __init__(
        self,
        account_name: str = "",
        account_key: str = "",
        connection_string: str = "",
        default_container: str = "documents"
    ):
        self.account_name = account_name
        self.account_key = account_key
        self.default_container = default_container
        self._blob_service_client = self._create_blob_service_client(
            account_name, account_key, connection_string
        )
        
        # Initialize SAS token service if account key is available
        self._sas_service = None
        if account_name and account_key:
            self._sas_service = AzureSasTokenService(
                account_name=account_name,
                account_key=account_key,
                default_container=default_container
            )
    
    def _create_blob_service_client(
        self, 
        account_name: str, 
        account_key: str, 
        connection_string: str
    ) -> BlobServiceClient:
        """Create blob service client with appropriate authentication"""
        try:
            if connection_string:
                logger.info("Using connection string for Azure Blob Storage authentication")
                return BlobServiceClient.from_connection_string(connection_string)
            elif account_name and account_key:
                logger.info("Using account key for Azure Blob Storage authentication")
                account_url = f"https://{account_name}.blob.core.windows.net"
                return BlobServiceClient(account_url=account_url, credential=account_key)
            elif account_name:
                logger.info("Using default credentials for Azure Blob Storage authentication")
                account_url = f"https://{account_name}.blob.core.windows.net"
                return BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())
            else:
                raise BlobStorageError("No valid authentication method provided for Azure Blob Storage")
        except Exception as e:
            logger.error(f"Failed to create blob service client: {e}")
            raise BlobStorageError(f"Failed to initialize blob storage client: {e}")
    
    async def get_blob(self, blob_name: str, container_name: Optional[str] = None) -> bytes:
        """Get blob content as bytes using SAS token"""
        container = container_name or self.default_container
        
        try:
            logger.info(f"Retrieving blob: {blob_name} from container: {container}")
            
            # Use SAS token for secure access if available
            if self._sas_service:
                blob_url = await self._sas_service.get_blob_url_with_sas(blob_name, container)
                
                # Download using HTTP client with SAS URL
                async with httpx.AsyncClient() as client:
                    response = await client.get(blob_url)
                    response.raise_for_status()
                    content = response.content
            else:
                # Fallback to direct blob client (requires appropriate authentication)
                blob_client = self._blob_service_client.get_blob_client(
                    container=container, 
                    blob=blob_name
                )
                
                # Download blob content
                blob_data = blob_client.download_blob()
                content = blob_data.readall()
            
            logger.info(f"Successfully retrieved blob: {blob_name}, size: {len(content)} bytes")
            return content
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Blob not found: {blob_name} in container: {container}")
                raise BlobNotFoundError(f"Blob '{blob_name}' not found in container '{container}'")
            else:
                logger.error(f"HTTP error retrieving blob {blob_name}: {e}")
                raise BlobStorageError(f"Failed to retrieve blob '{blob_name}': {e}")
        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {blob_name} in container: {container}")
            raise BlobNotFoundError(f"Blob '{blob_name}' not found in container '{container}'")
        except (AzureError, SasTokenError) as e:
            logger.error(f"Azure/SAS error retrieving blob {blob_name}: {e}")
            raise BlobStorageError(f"Failed to retrieve blob '{blob_name}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving blob {blob_name}: {e}")
            raise BlobStorageError(f"Unexpected error retrieving blob '{blob_name}': {e}")
    
    async def get_blob_stream(self, blob_name: str, container_name: Optional[str] = None) -> BinaryIO:
        """Get blob content as stream using SAS token"""
        container = container_name or self.default_container
        
        try:
            logger.info(f"Streaming blob: {blob_name} from container: {container}")
            
            # Use SAS token for secure access if available
            if self._sas_service:
                blob_url = await self._sas_service.get_blob_url_with_sas(blob_name, container)
                
                # Stream using HTTP client with SAS URL
                async with httpx.AsyncClient() as client:
                    response = await client.get(blob_url)
                    response.raise_for_status()
                    return BytesIO(response.content)
            else:
                # Fallback to direct blob client access
                content = await self.get_blob(blob_name, container)
                return BytesIO(content)
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Blob not found: {blob_name} in container: {container}")
                raise BlobNotFoundError(f"Blob '{blob_name}' not found in container '{container}'")
            else:
                logger.error(f"HTTP error streaming blob {blob_name}: {e}")
                raise BlobStorageError(f"Failed to stream blob '{blob_name}': {e}")
        except (SasTokenError, BlobStorageError, BlobNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error streaming blob {blob_name}: {e}")
            raise BlobStorageError(f"Unexpected error streaming blob '{blob_name}': {e}")
    
    async def get_blob_metadata(self, blob_name: str, container_name: Optional[str] = None) -> Dict[str, Any]:
        """Get blob metadata using SAS token or direct access"""
        container = container_name or self.default_container
        
        try:
            logger.info(f"Retrieving metadata for blob: {blob_name} from container: {container}")
            
            # Use SAS token for secure access if available
            if self._sas_service:
                blob_url = await self._sas_service.get_blob_url_with_sas(blob_name, container)
                
                # Get metadata using HEAD request with SAS URL
                async with httpx.AsyncClient() as client:
                    response = await client.head(blob_url)
                    response.raise_for_status()
                    
                    # Extract metadata from headers
                    metadata = {
                        "name": blob_name,
                        "container": container,
                        "size": int(response.headers.get("content-length", 0)),
                        "content_type": response.headers.get("content-type", "application/octet-stream"),
                        "last_modified": response.headers.get("last-modified"),
                        "etag": response.headers.get("etag", "").strip('"'),
                        "metadata": {},  # Custom metadata would need additional API call
                        "creation_time": response.headers.get("x-ms-creation-time"),
                    }
            else:
                # Fallback to direct blob client access
                blob_client = self._blob_service_client.get_blob_client(
                    container=container, 
                    blob=blob_name
                )
                
                # Get blob properties
                properties = blob_client.get_blob_properties()
                
                metadata = {
                    "name": blob_name,
                    "container": container,
                    "size": properties.size,
                    "content_type": properties.content_settings.content_type,
                    "last_modified": properties.last_modified.isoformat() if properties.last_modified else None,
                    "etag": properties.etag,
                    "metadata": properties.metadata or {},
                    "creation_time": properties.creation_time.isoformat() if properties.creation_time else None,
                }
            
            logger.info(f"Successfully retrieved metadata for blob: {blob_name}")
            return metadata
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Blob not found: {blob_name} in container: {container}")
                raise BlobNotFoundError(f"Blob '{blob_name}' not found in container '{container}'")
            else:
                logger.error(f"HTTP error retrieving metadata for blob {blob_name}: {e}")
                raise BlobStorageError(f"Failed to retrieve metadata for blob '{blob_name}': {e}")
        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {blob_name} in container: {container}")
            raise BlobNotFoundError(f"Blob '{blob_name}' not found in container '{container}'")
        except (AzureError, SasTokenError) as e:
            logger.error(f"Azure/SAS error retrieving metadata for blob {blob_name}: {e}")
            raise BlobStorageError(f"Failed to retrieve metadata for blob '{blob_name}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving metadata for blob {blob_name}: {e}")
            raise BlobStorageError(f"Unexpected error retrieving metadata for blob '{blob_name}': {e}")
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {blob_name} in container: {container}")
            raise BlobNotFoundError(f"Blob '{blob_name}' not found in container '{container}'")
        except AzureError as e:
            logger.error(f"Azure error retrieving metadata for blob {blob_name}: {e}")
            raise BlobStorageError(f"Failed to retrieve metadata for blob '{blob_name}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving metadata for blob {blob_name}: {e}")
            raise BlobStorageError(f"Unexpected error retrieving metadata for blob '{blob_name}': {e}")
    
    async def blob_exists(self, blob_name: str, container_name: Optional[str] = None) -> bool:
        """Check if blob exists using SAS token or direct access"""
        container = container_name or self.default_container
        
        try:
            # Use SAS token for secure access if available
            if self._sas_service:
                blob_url = await self._sas_service.get_blob_url_with_sas(blob_name, container)
                
                # Check existence using HEAD request with SAS URL
                async with httpx.AsyncClient() as client:
                    response = await client.head(blob_url)
                    exists = response.status_code == 200
            else:
                # Fallback to direct blob client access
                blob_client = self._blob_service_client.get_blob_client(
                    container=container, 
                    blob=blob_name
                )
                
                exists = blob_client.exists()
            
            logger.info(f"Blob existence check: {blob_name} in {container}: {exists}")
            return exists
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.info(f"Blob existence check: {blob_name} in {container}: False")
                return False
            else:
                logger.error(f"HTTP error checking blob existence {blob_name}: {e}")
                raise BlobStorageError(f"Failed to check existence of blob '{blob_name}': {e}")
        except (AzureError, SasTokenError) as e:
            logger.error(f"Azure/SAS error checking blob existence {blob_name}: {e}")
            raise BlobStorageError(f"Failed to check existence of blob '{blob_name}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking blob existence {blob_name}: {e}")
            raise BlobStorageError(f"Unexpected error checking existence of blob '{blob_name}': {e}")
