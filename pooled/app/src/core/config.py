"""
Application configuration module.
Handles environment variables and app settings.
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # App info
    app_name: str = "Pooled Agent Service"
    app_version: str = "0.1.0"
    description: str = "Multi-tenant AI Agent Service - Pooled Architecture"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # CORS settings
    cors_origins: List[str] = ["*"]  # TODO: Configure for production
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
