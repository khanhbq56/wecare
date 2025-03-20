# api/config.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai

from utils.logging import setup_logging
from api.routes import router
from api.middleware import add_middleware
from services.gemini import validate_gemini_api_key

def initialize_app() -> FastAPI:
    """
    Initialize and configure the FastAPI application
    
    Returns:
        FastAPI: Configured FastAPI application
    """
    # Initialize logging
    logger = setup_logging()
    
    # Validate Gemini API key
    gemini_api_key = validate_gemini_api_key()
    
    # Configure Gemini
    genai.configure(api_key=gemini_api_key)
    
    # Create FastAPI app
    app = FastAPI(
        title="Patient Care Data Extraction API",
        description="API for extracting data from patient care forms",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Replace with specific origins in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    add_middleware(app)
    
    # Include routers
    app.include_router(router, prefix="/api/v1")
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        from datetime import datetime
        return {
            "status": "ok",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
    
    return app