"""
Root router module.
Handles main application endpoints.
"""
from fastapi import APIRouter

router = APIRouter(
    tags=["root"]
)


@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Pooled Agent Service is running",
        "architecture": "pooled",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }
