# api/routes.py
import uuid
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import logging
from PIL import Image
import io

from api.models import ExtractionResponse, ErrorResponse
from services.extraction import extract_patient_care_data

# Create router
router = APIRouter()
logger = logging.getLogger("patient-care-api")

def generate_request_id():
    """Generate unique request ID"""
    return str(uuid.uuid4())

@router.post("/extract", 
         summary="Extract information from patient care form images",
         description="Upload exactly 2 images (front and back of the patient care form) to extract information")
async def extract_from_uploads(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Upload 2 images: front and back of the patient care form")
):
    """
    Extract information from uploaded patient care form images
    
    Args:
        background_tasks: Background tasks manager
        files: List of uploaded files
        
    Returns:
        ExtractionResponse or ErrorResponse
    """
    request_id = generate_request_id()
    timestamp = datetime.now().isoformat()
    
    # Check number of files
    if len(files) != 2:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                request_id=request_id,
                timestamp=timestamp,
                error={
                    "type": "INSUFFICIENT_IMAGES",
                    "message": f"Cần chính xác 2 hình ảnh, đã nhận {len(files)}",
                    "details": {
                        "received": len(files),
                        "required": 2
                    }
                }
            ).dict()
        )
    
    # Process files
    try:
        image_data = []
        for file in files:
            content = await file.read()
            
            # Validate image
            try:
                Image.open(io.BytesIO(content))
                image_data.append(content)
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content=ErrorResponse(
                        request_id=request_id,
                        timestamp=timestamp,
                        error={
                            "type": "INVALID_FILE_FORMAT",
                            "message": f"File '{file.filename}' không phải là hình ảnh hợp lệ",
                            "details": {
                                "filename": file.filename,
                                "error": str(e)
                            }
                        }
                    ).dict()
                )
        
        # Extract data
        result = await extract_patient_care_data(image_data, request_id)
        
        # Format response
        if "error" in result and result["error"]:
            return JSONResponse(
                status_code=400 if result["error_type"] in ["INSUFFICIENT_IMAGES", "INVALID_IMAGES", "INCONSISTENT_INFORMATION", "IMAGE_QUALITY_ISSUE", "DUPLICATE_IMAGES"] else 500,
                content=ErrorResponse(
                    request_id=request_id,
                    timestamp=timestamp,
                    error={
                        "type": result["error_type"],
                        "message": result["message"],
                        "details": result.get("error_details", {})
                    }
                ).dict()
            )
        else:
            return ExtractionResponse(
                request_id=request_id,
                timestamp=timestamp,
                status="success",
                data=result
            )
        
    except Exception as e:
        logger.error(f"[{request_id}] Lỗi khi xử lý request: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                request_id=request_id,
                timestamp=timestamp,
                error={
                    "type": "PROCESSING_ERROR",
                    "message": f"Lỗi khi xử lý request: {str(e)}",
                    "details": {}
                }
            ).dict()
        )