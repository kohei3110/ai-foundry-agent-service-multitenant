"""
Health check router module.
Handles HTTP routing for health endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..services.health_service import HealthService, HealthCheckInterface


def get_health_service() -> HealthCheckInterface:
    """Dependency injection for health service"""
    return HealthService()


router = APIRouter(
    prefix="/health",
    tags=["health"],
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is not ready"}
    }
)


@router.get("")
async def health_check(
    health_service: HealthCheckInterface = Depends(get_health_service)
):
    """Basic health check endpoint for load balancers and monitoring"""
    health_status = await health_service.get_basic_health()
    return JSONResponse(
        status_code=200,
        content=health_status
    )


@router.get("/ready")
async def readiness_check(
    health_service: HealthCheckInterface = Depends(get_health_service)
):
    """Readiness check endpoint for Kubernetes"""
    readiness_status = await health_service.get_readiness_status()
    
    # Return 503 if not ready
    status_code = 200 if readiness_status["status"] == "ready" else 503
    
    return JSONResponse(
        status_code=status_code,
        content=readiness_status
    )


@router.get("/live")
async def liveness_check(
    health_service: HealthCheckInterface = Depends(get_health_service)
):
    """Liveness check endpoint for Kubernetes"""
    liveness_status = await health_service.get_liveness_status()
    return JSONResponse(
        status_code=200,
        content=liveness_status
    )
