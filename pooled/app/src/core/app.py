"""
Application factory module.
Creates and configures the FastAPI application.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from ..middleware.logging import LoggingMiddleware
from ..middleware.cors import CORSConfig
from ..routers import root, health, blob_storage


def create_app() -> FastAPI:
    """Application factory function"""
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        description=settings.description,
        version=settings.app_version,
        debug=settings.debug
    )
    
    # Add CORS middleware
    cors_config = CORSConfig(allow_origins=settings.cors_origins)
    app.add_middleware(
        CORSMiddleware,
        **cors_config.get_middleware_kwargs()
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    
    # Include routers
    app.include_router(root.router)
    app.include_router(health.router)
    app.include_router(blob_storage.router)
    
    return app
