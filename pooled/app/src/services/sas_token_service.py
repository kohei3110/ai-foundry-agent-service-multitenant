"""
SAS Token service module.
Handles generation and management of SAS tokens for Azure Blob Storage access.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import AzureError

logger = logging.getLogger(__name__)


class SasTokenError(Exception):
    """Custom exception for SAS token operations"""
    pass


class SasTokenInterface(ABC):
    """Interface for SAS token operations (Dependency Inversion Principle)"""
    
    @abstractmethod
    async def generate_blob_read_sas(
        self, 
        blob_name: str, 
        container_name: Optional[str] = None,
        expires_in_hours: int = 1
    ) -> str:
        """Generate SAS token for blob read access"""
        pass
    
    @abstractmethod
    async def get_blob_url_with_sas(
        self, 
        blob_name: str, 
        container_name: Optional[str] = None,
        expires_in_hours: int = 1
    ) -> str:
        """Get blob URL with SAS token"""
        pass


class AzureSasTokenService(SasTokenInterface):
    """Azure SAS Token service implementation"""
    
    def __init__(
        self,
        account_name: str,
        account_key: str,
        default_container: str = "documents"
    ):
        self.account_name = account_name
        self.account_key = account_key
        self.default_container = default_container
        
        if not account_name or not account_key:
            raise SasTokenError("Account name and account key are required for SAS token generation")
    
    async def generate_blob_read_sas(
        self, 
        blob_name: str, 
        container_name: Optional[str] = None,
        expires_in_hours: int = 1
    ) -> str:
        """Generate SAS token for blob read access"""
        container = container_name or self.default_container
        
        try:
            logger.info(f"Generating SAS token for blob: {blob_name} in container: {container}")
            
            # Set expiry time
            expiry_time = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
            
            # Define permissions (read only)
            permissions = BlobSasPermissions(read=True)
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=container,
                blob_name=blob_name,
                account_key=self.account_key,
                permission=permissions,
                expiry=expiry_time
            )
            
            logger.info(f"Successfully generated SAS token for blob: {blob_name}")
            return sas_token
            
        except AzureError as e:
            logger.error(f"Azure error generating SAS token for blob {blob_name}: {e}")
            raise SasTokenError(f"Failed to generate SAS token for blob '{blob_name}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error generating SAS token for blob {blob_name}: {e}")
            raise SasTokenError(f"Unexpected error generating SAS token for blob '{blob_name}': {e}")
    
    async def get_blob_url_with_sas(
        self, 
        blob_name: str, 
        container_name: Optional[str] = None,
        expires_in_hours: int = 1
    ) -> str:
        """Get blob URL with SAS token"""
        container = container_name or self.default_container
        
        try:
            # Generate SAS token
            sas_token = await self.generate_blob_read_sas(blob_name, container, expires_in_hours)
            
            # Construct blob URL with SAS token
            blob_url = f"https://{self.account_name}.blob.core.windows.net/{container}/{blob_name}?{sas_token}"
            
            logger.info(f"Generated blob URL with SAS for: {blob_name}")
            return blob_url
            
        except SasTokenError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating blob URL with SAS for {blob_name}: {e}")
            raise SasTokenError(f"Unexpected error creating blob URL with SAS for '{blob_name}': {e}")
