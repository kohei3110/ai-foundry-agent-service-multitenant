"""
Main application entry point.
Uses application factory pattern for better testability and configuration.
"""
from src.core import create_app, settings

# Create the application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
