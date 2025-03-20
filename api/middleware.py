# api/middleware.py
import time
from fastapi import FastAPI, Request
import logging

logger = logging.getLogger("patient-care-api")

def add_middleware(app: FastAPI):
    """
    Add custom middleware to the FastAPI application
    
    Args:
        app: FastAPI application
    """
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """
        Middleware to log request details and timing
        """
        request_id = request.headers.get("X-Request-ID", "unknown")
        start_time = time.time()
        
        # Log request information
        logger.info(f"[{request_id}] Request started: {request.method} {request.url.path}")
        
        # Process the request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log response information
        logger.info(
            f"[{request_id}] Request completed: {response.status_code} in {process_time:.2f}s"
        )
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        return response