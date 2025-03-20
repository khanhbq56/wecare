# api/models.py
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class ExtractionResponse(BaseModel):
    """Response model for successful extraction"""
    request_id: str
    timestamp: str
    status: str
    data: Dict[str, Any]

class ErrorResponse(BaseModel):
    """Response model for errors"""
    request_id: str
    timestamp: str
    status: str = "error"
    error: Dict[str, Any]