"""
Blob Storage router module.
Handles HTTP routing for blob storage endpoints.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from fastapi.responses import StreamingResponse

from ..services.blob_storage_service import (
    BlobStorageInterface, 
    AzureBlobStorageService,
    BlobNotFoundError,
    BlobStorageError
)
from ..services.sas_token_service import SasTokenInterface, AzureSasTokenService, SasTokenError
from ..core.config import settings

logger = logging.getLogger(__name__)


def get_blob_storage_service() -> BlobStorageInterface:
    """Dependency injection for blob storage service"""
    return AzureBlobStorageService(
        account_name=settings.azure_storage_account_name,
        account_key=settings.azure_storage_account_key,
        connection_string=settings.azure_storage_connection_string,
        default_container=settings.azure_storage_container_name,
        client_id=settings.azure_client_id
    )


def get_sas_token_service() -> SasTokenInterface:
    """Dependency injection for SAS token service"""
    if not settings.azure_storage_account_name or not settings.azure_storage_account_key:
        raise HTTPException(
            status_code=500, 
            detail="SAS token service requires account name and key configuration"
        )
    return AzureSasTokenService(
        account_name=settings.azure_storage_account_name,
        account_key=settings.azure_storage_account_key,
        default_container=settings.azure_storage_container_name
    )


router = APIRouter(
    prefix="/blobs",
    tags=["blob-storage"],
    responses={
        404: {"description": "Blob not found"},
        500: {"description": "Internal server error"},
    }
)


@router.get("/{blob_name}")
async def get_blob_content(
    blob_name: str,
    container: Optional[str] = Query(None, description="Container name (optional)"),
    download: bool = Query(False, description="Force download as attachment"),
    blob_service: BlobStorageInterface = Depends(get_blob_storage_service)
):
    """
    Get blob content from Azure Blob Storage
    
    - **blob_name**: Name of the blob to retrieve
    - **container**: Container name (optional, uses default if not specified)
    - **download**: If true, forces download as attachment
    """
    try:
        logger.info(f"Request to get blob: {blob_name} from container: {container}")
        
        # Get blob content and metadata
        content = await blob_service.get_blob(blob_name, container)
        metadata = await blob_service.get_blob_metadata(blob_name, container)
        
        # Determine content type
        content_type = metadata.get("content_type", "application/octet-stream")
        
        # Create response headers
        headers = {
            "Content-Length": str(len(content)),
            "ETag": metadata.get("etag", ""),
            "Last-Modified": metadata.get("last_modified", ""),
        }
        
        # Add content disposition for downloads
        if download:
            headers["Content-Disposition"] = f'attachment; filename="{blob_name}"'
        
        logger.info(f"Successfully serving blob: {blob_name}, size: {len(content)} bytes")
        
        return Response(
            content=content,
            media_type=content_type,
            headers=headers
        )
        
    except BlobNotFoundError as e:
        logger.warning(f"Blob not found: {blob_name}")
        raise HTTPException(status_code=404, detail=str(e))
    except (BlobStorageError, SasTokenError) as e:
        logger.error(f"Blob storage/SAS error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error retrieving blob {blob_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{blob_name}/stream")
async def get_blob_stream(
    blob_name: str,
    container: Optional[str] = Query(None, description="Container name (optional)"),
    blob_service: BlobStorageInterface = Depends(get_blob_storage_service)
):
    """
    Get blob content as a streaming response
    
    - **blob_name**: Name of the blob to retrieve
    - **container**: Container name (optional, uses default if not specified)
    """
    try:
        logger.info(f"Request to stream blob: {blob_name} from container: {container}")
        
        # Get blob stream and metadata
        stream = await blob_service.get_blob_stream(blob_name, container)
        metadata = await blob_service.get_blob_metadata(blob_name, container)
        
        # Determine content type
        content_type = metadata.get("content_type", "application/octet-stream")
        
        # Create streaming response
        headers = {
            "Content-Length": str(metadata.get("size", 0)),
            "ETag": metadata.get("etag", ""),
            "Last-Modified": metadata.get("last_modified", ""),
        }
        
        logger.info(f"Successfully streaming blob: {blob_name}")
        
        return StreamingResponse(
            stream,
            media_type=content_type,
            headers=headers
        )
        
    except BlobNotFoundError as e:
        logger.warning(f"Blob not found: {blob_name}")
        raise HTTPException(status_code=404, detail=str(e))
    except (BlobStorageError, SasTokenError) as e:
        logger.error(f"Blob storage/SAS error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error streaming blob {blob_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{blob_name}/metadata")
async def get_blob_metadata(
    blob_name: str,
    container: Optional[str] = Query(None, description="Container name (optional)"),
    blob_service: BlobStorageInterface = Depends(get_blob_storage_service)
):
    """
    Get blob metadata from Azure Blob Storage
    
    - **blob_name**: Name of the blob to get metadata for
    - **container**: Container name (optional, uses default if not specified)
    """
    try:
        logger.info(f"Request to get metadata for blob: {blob_name} from container: {container}")
        
        metadata = await blob_service.get_blob_metadata(blob_name, container)
        
        logger.info(f"Successfully retrieved metadata for blob: {blob_name}")
        return metadata
        
    except BlobNotFoundError as e:
        logger.warning(f"Blob not found: {blob_name}")
        raise HTTPException(status_code=404, detail=str(e))
    except (BlobStorageError, SasTokenError) as e:
        logger.error(f"Blob storage/SAS error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error getting metadata for blob {blob_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.head("/{blob_name}")
async def check_blob_exists(
    blob_name: str,
    container: Optional[str] = Query(None, description="Container name (optional)"),
    blob_service: BlobStorageInterface = Depends(get_blob_storage_service)
):
    """
    Check if blob exists (HEAD request)
    
    - **blob_name**: Name of the blob to check
    - **container**: Container name (optional, uses default if not specified)
    """
    try:
        logger.info(f"Request to check existence of blob: {blob_name} from container: {container}")
        
        exists = await blob_service.blob_exists(blob_name, container)
        
        if exists:
            # Get metadata for headers
            metadata = await blob_service.get_blob_metadata(blob_name, container)
            headers = {
                "Content-Length": str(metadata.get("size", 0)),
                "Content-Type": metadata.get("content_type", "application/octet-stream"),
                "ETag": metadata.get("etag", ""),
                "Last-Modified": metadata.get("last_modified", ""),
            }
            return Response(status_code=200, headers=headers)
        else:
            raise HTTPException(status_code=404, detail=f"Blob '{blob_name}' not found")
            
    except BlobNotFoundError:
        raise HTTPException(status_code=404, detail=f"Blob '{blob_name}' not found")
    except (BlobStorageError, SasTokenError) as e:
        logger.error(f"Blob storage/SAS error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error checking blob existence {blob_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{blob_name}/sas")
async def get_blob_sas_token(
    blob_name: str,
    container: Optional[str] = Query(None, description="Container name (optional)"),
    expires_in_hours: int = Query(1, description="SAS token expiry time in hours (default: 1)"),
    sas_service: SasTokenInterface = Depends(get_sas_token_service)
):
    """
    Generate SAS token for blob access
    
    - **blob_name**: Name of the blob to generate SAS token for
    - **container**: Container name (optional, uses default if not specified)
    - **expires_in_hours**: SAS token expiry time in hours (default: 1, max: 24)
    """
    try:
        # Validate expiry time
        if expires_in_hours < 1 or expires_in_hours > 24:
            raise HTTPException(
                status_code=400, 
                detail="expires_in_hours must be between 1 and 24"
            )
        
        logger.info(f"Request to generate SAS token for blob: {blob_name} from container: {container}")
        
        # Generate SAS token
        sas_token = await sas_service.generate_blob_read_sas(blob_name, container, expires_in_hours)
        blob_url = await sas_service.get_blob_url_with_sas(blob_name, container, expires_in_hours)
        
        response_data = {
            "blob_name": blob_name,
            "container": container or sas_service.default_container,
            "sas_token": sas_token,
            "blob_url": blob_url,
            "expires_in_hours": expires_in_hours
        }
        
        logger.info(f"Successfully generated SAS token for blob: {blob_name}")
        return response_data
        
    except SasTokenError as e:
        logger.error(f"SAS token error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate SAS token")
    except Exception as e:
        logger.error(f"Unexpected error generating SAS token for blob {blob_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
