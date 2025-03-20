# services/extraction.py
import logging
import time
from typing import List, Dict, Any
import io
import hashlib
from PIL import Image, ImageEnhance
import concurrent.futures

from services.gemini import call_gemini_api, get_extraction_prompt
from utils.helpers import encode_image
from utils.errors import ErrorType, get_error_message

logger = logging.getLogger("patient-care-api")

async def extract_patient_care_data(image_files: List[bytes], request_id: str) -> Dict[str, Any]:
    """
    Extract data from patient care form images
    
    Args:
        image_files: List of image bytes
        request_id: Request ID for logging
        
    Returns:
        Dict: Extracted data or error information
    """
    start_time = time.time()
    logger.info(f"[{request_id}] Starting extraction from {len(image_files)} images")
    
    # Check number of images
    if len(image_files) != 2:
        return {
            "error": True,
            "error_type": ErrorType.INSUFFICIENT_IMAGES,
            "error_details": {
                "received": len(image_files),
                "required": 2
            },
            "message": get_error_message(ErrorType.INSUFFICIENT_IMAGES)
        }
    
    # Check if images are duplicates
    if _are_duplicate_images(image_files[0], image_files[1]):
        return {
            "error": True,
            "error_type": ErrorType.DUPLICATE_IMAGES,
            "error_details": {
                "message": "The uploaded images appear to be duplicates"
            },
            "message": get_error_message(ErrorType.DUPLICATE_IMAGES)
        }
    
    # Preprocess images in parallel
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            preprocessed_images = list(executor.map(_preprocess_image, image_files))
        
        # Prepare request to Gemini API
        parts = []
        
        # Add images
        for img_bytes in preprocessed_images:
            parts.append(encode_image(img_bytes))
        
        # Add prompt
        parts.append({"text": get_extraction_prompt()})
        
        # Create request content
        contents = [{"role": "user", "parts": parts}]
        
        # Call Gemini API
        result, error = call_gemini_api(contents, request_id)
        
        if error:
            return {
                "error": True,
                "error_type": ErrorType.API_REQUEST_FAILED,
                "error_details": {"message": error},
                "message": get_error_message(ErrorType.API_REQUEST_FAILED, error)
            }
        
        # Log success
        processing_time = time.time() - start_time
        logger.info(f"[{request_id}] Extraction completed in {processing_time:.2f}s")
        
        return result
    
    except Exception as e:
        logger.error(f"[{request_id}] Error during extraction: {str(e)}", exc_info=True)
        return {
            "error": True,
            "error_type": ErrorType.PROCESSING_ERROR,
            "error_details": {"message": str(e)},
            "message": get_error_message(ErrorType.PROCESSING_ERROR, str(e))
        }

def _preprocess_image(image_bytes: bytes) -> bytes:
    """
    Preprocess image to improve quality for extraction
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        bytes: Processed image bytes
    """
    try:
        # Open image
        img = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Enhance contrast slightly
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.3)
        
        # Adjust brightness if needed
        # enhancer = ImageEnhance.Brightness(img)
        # img = enhancer.enhance(1.1)
        
        # Convert back to bytes
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=95)
        return output.getvalue()
    
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {str(e)}, using original image")
        return image_bytes

def _are_duplicate_images(img1_bytes: bytes, img2_bytes: bytes) -> bool:
    """
    Check if two images are duplicates
    
    Args:
        img1_bytes: First image bytes
        img2_bytes: Second image bytes
        
    Returns:
        bool: True if images are likely duplicates
    """
    # Calculate image hashes
    hash1 = hashlib.md5(img1_bytes).hexdigest()
    hash2 = hashlib.md5(img2_bytes).hexdigest()
    
    # If hashes match exactly, images are identical
    if hash1 == hash2:
        return True
    
    # Try more sophisticated comparison if needed
    try:
        # Compare image dimensions and basic features
        img1 = Image.open(io.BytesIO(img1_bytes))
        img2 = Image.open(io.BytesIO(img2_bytes))
        
        # If images have very similar dimensions and file sizes,
        # they might be duplicates or very similar images
        size_similarity = abs(len(img1_bytes) - len(img2_bytes)) / max(len(img1_bytes), len(img2_bytes))
        dimension_match = img1.size == img2.size
        
        # If dimensions match exactly and size is within 5%, likely duplicates
        if dimension_match and size_similarity < 0.05:
            return True
    
    except Exception as e:
        logger.warning(f"Error during duplicate image detection: {str(e)}")
    
    return False