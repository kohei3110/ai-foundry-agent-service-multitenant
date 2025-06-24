"""
CORS middleware configuration module.
Handles Cross-Origin Resource Sharing settings.
"""
from fastapi.middleware.cors import CORSMiddleware
from typing import List


class CORSConfig:
    """CORS configuration class"""
    
    def __init__(
        self,
        allow_origins: List[str] = None,
        allow_credentials: bool = True,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None
    ):
        self.allow_origins = allow_origins or ["*"]  # TODO: Configure for production
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods or ["*"]
        self.allow_headers = allow_headers or ["*"]
    
    def get_middleware_kwargs(self) -> dict:
        """Get middleware configuration as kwargs"""
        return {
            "allow_origins": self.allow_origins,
            "allow_credentials": self.allow_credentials,
            "allow_methods": self.allow_methods,
            "allow_headers": self.allow_headers
        }
