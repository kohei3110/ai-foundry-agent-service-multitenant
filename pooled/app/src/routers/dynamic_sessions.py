"""
Dynamic Sessions router module.
Handles HTTP routing for Container Apps dynamic sessions endpoints.
"""
import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from ..services.dynamic_sessions_service import (
    DynamicSessionsInterface,
    AzureDynamicSessionsService,
    DynamicSessionsError,
    SessionNotFoundError,
    CodeExecutionError
)
from ..core.config import settings

logger = logging.getLogger(__name__)


class CodeExecutionRequest(BaseModel):
    """Request model for code execution"""
    code: str = Field(..., description="Python code to execute", min_length=1, max_length=50000)
    

class SessionCreationRequest(BaseModel):
    """Request model for session creation"""
    pool_id: str = Field(..., description="Session pool identifier")
    session_config: Dict[str, Any] = Field(default_factory=dict, description="Additional session configuration")


class CodeExecutionResponse(BaseModel):
    """Response model for code execution"""
    session_id: str
    status: str
    result: Dict[str, Any]
    execution_time_ms: Optional[int] = None


class SessionResponse(BaseModel):
    """Response model for session operations"""
    session_id: str
    status: str
    pool_id: Optional[str] = None
    created_at: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


def get_dynamic_sessions_service() -> DynamicSessionsInterface:
    """Dependency injection for dynamic sessions service"""
    # These would typically come from environment variables or configuration
    base_url = getattr(settings, 'container_apps_dynamic_sessions_base_url', 
                      'https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.App/sessionPools/{pool_name}')
    pool_management_endpoint = getattr(settings, 'container_apps_pool_management_endpoint',
                                     'https://management.azure.com/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.App')
    
    return AzureDynamicSessionsService(
        base_url=base_url,
        pool_management_endpoint=pool_management_endpoint,
        client_id=settings.azure_client_id
    )


router = APIRouter(
    prefix="/sessions",
    tags=["dynamic-sessions"],
    responses={
        404: {"description": "Session not found"},
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"},
    }
)


@router.post("/{session_id}/execute", response_model=CodeExecutionResponse)
async def execute_code(
    session_id: str,
    request: CodeExecutionRequest,
    sessions_service: DynamicSessionsInterface = Depends(get_dynamic_sessions_service)
):
    """
    Execute Python code in a Container Apps dynamic session.
    
    This endpoint allows you to execute Python code within an existing dynamic session.
    The session must already exist and be in a ready state.
    
    Args:
        session_id: Unique identifier for the dynamic session
        request: Code execution request containing the Python code to execute
        
    Returns:
        CodeExecutionResponse containing execution results and status
        
    Raises:
        HTTPException: 
            - 404 if session not found
            - 400 if code execution fails
            - 500 for internal server errors
    """
    try:
        logger.info(f"Executing code in session: {session_id}")
        
        # Execute code in the dynamic session
        result = await sessions_service.execute_code(session_id, request.code)
        
        logger.info(f"Code execution completed for session: {session_id}")
        
        return CodeExecutionResponse(
            session_id=session_id,
            status="completed",
            result=result,
            execution_time_ms=result.get("properties", {}).get("executionTimeMs")
        )
        
    except SessionNotFoundError as e:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except CodeExecutionError as e:
        logger.error(f"Code execution error in session {session_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except DynamicSessionsError as e:
        logger.error(f"Dynamic sessions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error executing code in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=SessionResponse)
async def create_session(
    request: SessionCreationRequest,
    sessions_service: DynamicSessionsInterface = Depends(get_dynamic_sessions_service)
):
    """
    Create a new dynamic session in the specified pool.
    
    Args:
        request: Session creation request containing pool ID and configuration
        
    Returns:
        SessionResponse containing session information
        
    Raises:
        HTTPException: 
            - 400 for invalid requests
            - 500 for internal server errors
    """
    try:
        logger.info(f"Creating session in pool: {request.pool_id}")
        
        # Create session in the specified pool
        result = await sessions_service.create_session(
            request.pool_id, 
            **request.session_config
        )
        
        session_id = result.get("name") or result.get("id", "unknown")
        logger.info(f"Session created: {session_id}")
        
        return SessionResponse(
            session_id=session_id,
            status=result.get("properties", {}).get("provisioningState", "unknown"),
            pool_id=request.pool_id,
            created_at=result.get("properties", {}).get("createdTime"),
            properties=result.get("properties", {})
        )
        
    except DynamicSessionsError as e:
        logger.error(f"Dynamic sessions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error creating session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_status(
    session_id: str,
    sessions_service: DynamicSessionsInterface = Depends(get_dynamic_sessions_service)
):
    """
    Get the status and details of a dynamic session.
    
    Args:
        session_id: Unique identifier for the dynamic session
        
    Returns:
        SessionResponse containing session status and details
        
    Raises:
        HTTPException: 
            - 404 if session not found
            - 500 for internal server errors
    """
    try:
        logger.info(f"Getting status for session: {session_id}")
        
        # Get session status
        result = await sessions_service.get_session_status(session_id)
        
        logger.info(f"Retrieved status for session: {session_id}")
        
        return SessionResponse(
            session_id=session_id,
            status=result.get("properties", {}).get("provisioningState", "unknown"),
            created_at=result.get("properties", {}).get("createdTime"),
            properties=result.get("properties", {})
        )
        
    except SessionNotFoundError as e:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except DynamicSessionsError as e:
        logger.error(f"Dynamic sessions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error getting session status {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    sessions_service: DynamicSessionsInterface = Depends(get_dynamic_sessions_service)
):
    """
    Delete a dynamic session.
    
    Args:
        session_id: Unique identifier for the dynamic session
        
    Returns:
        Success message
        
    Raises:
        HTTPException: 
            - 404 if session not found
            - 500 for internal server errors
    """
    try:
        logger.info(f"Deleting session: {session_id}")
        
        # Delete the session
        await sessions_service.delete_session(session_id)
        
        logger.info(f"Session deleted: {session_id}")
        
        return {"message": f"Session {session_id} deleted successfully"}
        
    except SessionNotFoundError as e:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except DynamicSessionsError as e:
        logger.error(f"Dynamic sessions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error deleting session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{session_id}/execute/simple")
async def execute_code_simple(
    session_id: str,
    code: str = Body(..., embed=True, description="Python code to execute"),
    sessions_service: DynamicSessionsInterface = Depends(get_dynamic_sessions_service)
):
    """
    Simplified endpoint for executing Python code in a dynamic session.
    
    This is a simplified version of the execute endpoint that accepts code as a simple string.
    
    Args:
        session_id: Unique identifier for the dynamic session
        code: Python code to execute as a string
        
    Returns:
        Execution results
        
    Raises:
        HTTPException: 
            - 404 if session not found
            - 400 if code execution fails
            - 500 for internal server errors
    """
    try:
        logger.info(f"Executing simple code in session: {session_id}")
        
        # Execute code in the dynamic session
        result = await sessions_service.execute_code(session_id, code)
        
        logger.info(f"Simple code execution completed for session: {session_id}")
        
        return {
            "session_id": session_id,
            "status": "completed",
            "result": result
        }
        
    except SessionNotFoundError as e:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except CodeExecutionError as e:
        logger.error(f"Code execution error in session {session_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except DynamicSessionsError as e:
        logger.error(f"Dynamic sessions error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception as e:
        logger.error(f"Unexpected error executing simple code in session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
