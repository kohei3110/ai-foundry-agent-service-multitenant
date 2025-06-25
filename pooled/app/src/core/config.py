"""
Application configuration module.
Handles environment variables and app settings.
"""
import os
from typing import List
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False
    )
    
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
    
    # Azure Blob Storage settings
    azure_storage_account_name: str = ""
    azure_storage_account_key: str = ""
    azure_storage_connection_string: str = ""
    azure_storage_container_name: str = "documents"


# Global settings instance
settings = Settings()
