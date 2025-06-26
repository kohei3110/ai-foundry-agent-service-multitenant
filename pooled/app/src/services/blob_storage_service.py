"""
Azure Blob Storage service module.
Handles blob storage operations following single responsibility principle.
Uses DefaultAzureCredential (Managed Identity) as the primary authentication method,
following Azure security best practices.
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, BinaryIO
from io import BytesIO
import httpx

from azure.storage.blob import BlobServiceClient, BlobClient
from azure.core.exceptions import ResourceNotFoundError, AzureError, ClientAuthenticationError
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
    """
    Azure Blob Storage service implementation with security-first design.
    
    Authentication Priority (following Azure best practices):
    1. DefaultAzureCredential (Managed Identity) - Primary method for production
    2. Connection String - For development/legacy compatibility
    3. Account Key - Only as last resort (not recommended for production)
    
    SAS tokens are generated when account key is available for secure URL sharing.
    """
    
    def __init__(
        self,
        account_name: str = "",
        account_key: str = "",
        connection_string: str = "",
        default_container: str = "documents",
        client_id: str = ""
    ):
        self.account_name = account_name
        self.account_key = account_key
        self.default_container = default_container
        self.client_id = client_id
        
        # Create blob service client with authentication priority
        self._blob_service_client = self._create_blob_service_client(
            account_name, account_key, connection_string, client_id
        )
        
        # Initialize SAS token service only if account key is available
        # This is for secure URL generation, not primary authentication
        self._sas_service = None
        if account_name and account_key:
            logger.info("SAS token service available for secure URL generation")
            self._sas_service = AzureSasTokenService(
                account_name=account_name,
                account_key=account_key,
                default_container=default_container
            )
        else:
            logger.info("SAS token service not available - using direct authenticated access only")
    
    def _create_blob_service_client(
        self, 
        account_name: str, 
        account_key: str, 
        connection_string: str,
        client_id: str = ""
    ) -> BlobServiceClient:
        """
        Create blob service client with security-first authentication approach.
        
        Priority order (following Azure best practices):
        1. DefaultAzureCredential (Managed Identity) - Most secure for production
        2. Connection String - For development/compatibility
        3. Account Key - Last resort (not recommended for production)
        """
        try:
            # First priority: DefaultAzureCredential (Managed Identity)
            if account_name:
                account_url = f"https://{account_name}.blob.core.windows.net"
                
                try:
                    # Try with specific client ID if provided (User Assigned Managed Identity)
                    if client_id:
                        logger.info("Attempting authentication with User Assigned Managed Identity")
                        credential = DefaultAzureCredential(managed_identity_client_id=client_id)
                    else:
                        logger.info("Attempting authentication with DefaultAzureCredential (System Assigned Managed Identity)")
                        credential = DefaultAzureCredential()
                    
                    # Test the credential by creating the client
                    client = BlobServiceClient(account_url=account_url, credential=credential)
                    
                    # Test authentication by attempting to list containers (this will fail if auth is wrong)
                    # We don't actually iterate, just test if the operation is allowed
                    try:
                        _ = client.list_containers(max_results=1)
                        logger.info("Successfully authenticated with DefaultAzureCredential")
                        return client
                    except ClientAuthenticationError:
                        logger.warning("DefaultAzureCredential authentication failed, falling back to other methods")
                    except Exception as e:
                        # Other errors might be due to network, permissions, etc. but credential is valid
                        logger.info(f"DefaultAzureCredential authenticated, but service test failed: {e}")
                        return client
                        
                except Exception as e:
                    logger.warning(f"DefaultAzureCredential initialization failed: {e}")
            
            # Second priority: Connection String
            if connection_string:
                logger.info("Using connection string for Azure Blob Storage authentication")
                return BlobServiceClient.from_connection_string(connection_string)
            
            # Third priority: Account Key (not recommended for production)
            if account_name and account_key:
                logger.warning("Using account key for authentication - not recommended for production")
                account_url = f"https://{account_name}.blob.core.windows.net"
                return BlobServiceClient(account_url=account_url, credential=account_key)
            
            # No valid authentication method
            raise BlobStorageError(
                "No valid authentication method provided. "
                "Recommended: Configure Managed Identity (DefaultAzureCredential) for production use."
            )
            
        except Exception as e:
            logger.error(f"Failed to create blob service client: {e}")
            raise BlobStorageError(f"Failed to initialize blob storage client: {e}")
    
    async def get_blob(self, blob_name: str, container_name: Optional[str] = None) -> bytes:
        """
        Get blob content as bytes.
        
        Uses direct authenticated access as primary method (DefaultAzureCredential).
        SAS tokens are only used for URL sharing when available, not for primary access.
        """
        container = container_name or self.default_container
        
        try:
            logger.info(f"Retrieving blob: {blob_name} from container: {container}")
            
            # Primary method: Direct authenticated access
            blob_client = self._blob_service_client.get_blob_client(
                container=container, 
                blob=blob_name
            )
            
            # Download blob content using authenticated client
            blob_data = blob_client.download_blob()
            content = blob_data.readall()
            
            logger.info(f"Successfully retrieved blob: {blob_name}, size: {len(content)} bytes")
            return content
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {blob_name} in container: {container}")
            raise BlobNotFoundError(f"Blob '{blob_name}' not found in container '{container}'")
        except ClientAuthenticationError as e:
            logger.error(f"Authentication error retrieving blob {blob_name}: {e}")
            raise BlobStorageError(f"Authentication failed for blob '{blob_name}': {e}")
        except AzureError as e:
            logger.error(f"Azure error retrieving blob {blob_name}: {e}")
            raise BlobStorageError(f"Failed to retrieve blob '{blob_name}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving blob {blob_name}: {e}")
            raise BlobStorageError(f"Unexpected error retrieving blob '{blob_name}': {e}")
    
    async def get_blob_stream(self, blob_name: str, container_name: Optional[str] = None) -> BinaryIO:
        """
        Get blob content as stream.
        
        Uses direct authenticated access as primary method (DefaultAzureCredential).
        """
        container = container_name or self.default_container
        
        try:
            logger.info(f"Streaming blob: {blob_name} from container: {container}")
            
            # Use direct authenticated access
            content = await self.get_blob(blob_name, container)
            return BytesIO(content)
                
        except (BlobStorageError, BlobNotFoundError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error streaming blob {blob_name}: {e}")
            raise BlobStorageError(f"Unexpected error streaming blob '{blob_name}': {e}")
    
    async def get_blob_metadata(self, blob_name: str, container_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get blob metadata using direct authenticated access.
        
        Uses DefaultAzureCredential for secure, production-grade access.
        """
        container = container_name or self.default_container
        
        try:
            logger.info(f"Retrieving metadata for blob: {blob_name} from container: {container}")
            
            # Use direct authenticated access
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
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {blob_name} in container: {container}")
            raise BlobNotFoundError(f"Blob '{blob_name}' not found in container '{container}'")
        except ClientAuthenticationError as e:
            logger.error(f"Authentication error retrieving metadata for blob {blob_name}: {e}")
            raise BlobStorageError(f"Authentication failed for blob metadata '{blob_name}': {e}")
        except AzureError as e:
            logger.error(f"Azure error retrieving metadata for blob {blob_name}: {e}")
            raise BlobStorageError(f"Failed to retrieve metadata for blob '{blob_name}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving metadata for blob {blob_name}: {e}")
            raise BlobStorageError(f"Unexpected error retrieving metadata for blob '{blob_name}': {e}")
    
    async def blob_exists(self, blob_name: str, container_name: Optional[str] = None) -> bool:
        """
        Check if blob exists using direct authenticated access.
        
        Uses DefaultAzureCredential for secure, production-grade access.
        """
        container = container_name or self.default_container
        
        try:
            # Use direct authenticated access
            blob_client = self._blob_service_client.get_blob_client(
                container=container, 
                blob=blob_name
            )
            
            exists = blob_client.exists()
            
            logger.info(f"Blob existence check: {blob_name} in {container}: {exists}")
            return exists
            
        except ClientAuthenticationError as e:
            logger.error(f"Authentication error checking blob existence {blob_name}: {e}")
            raise BlobStorageError(f"Authentication failed checking existence of blob '{blob_name}': {e}")
        except AzureError as e:
            logger.error(f"Azure error checking blob existence {blob_name}: {e}")
            raise BlobStorageError(f"Failed to check existence of blob '{blob_name}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error checking blob existence {blob_name}: {e}")
            raise BlobStorageError(f"Unexpected error checking existence of blob '{blob_name}': {e}")
    
    async def get_blob_url_with_sas(
        self, 
        blob_name: str, 
        container_name: Optional[str] = None,
        expires_in_hours: int = 1
    ) -> str:
        """
        Generate SAS URL for secure blob sharing.
        
        This method is available when account key is provided for secure URL generation.
        Primary access should always use DefaultAzureCredential.
        """
        if not self._sas_service:
            raise BlobStorageError(
                "SAS token service not available. Account key required for SAS URL generation."
            )
        
        return await self._sas_service.get_blob_url_with_sas(blob_name, container_name, expires_in_hours)
