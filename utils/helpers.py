# utils/helpers.py
import base64
from PIL import Image
import io
import re
import json
import logging

logger = logging.getLogger("patient-care-api")

def encode_image(image_bytes: bytes, mime_type: str = None) -> dict:
    """
    Encode image bytes to base64 for API request
    
    Args:
        image_bytes: Raw image bytes
        mime_type: MIME type of the image
        
    Returns:
        dict: Encoded image data
    """
    # Detect MIME type if not provided
    if not mime_type:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            mime_type = f"image/{img.format.lower()}" if img.format else "image/jpeg"
        except Exception as e:
            logger.warning(f"Failed to detect image format: {str(e)}")
            mime_type = "image/jpeg"
    
    # Encode image to base64
    encoded = base64.b64encode(image_bytes).decode()
    
    return {
        "inline_data": {
            "mime_type": mime_type,
            "data": encoded
        }
    }

def extract_json_from_text(text: str) -> str:
    """
    Extract JSON data from text that might have markdown formatting
    
    Args:
        text: Text containing JSON data
        
    Returns:
        str: Extracted JSON string
    """
    # Try to extract JSON from markdown code blocks
    json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    json_match = re.search(json_pattern, text, re.DOTALL)
    
    if json_match:
        return json_match.group(1).strip()
    
    # If no markdown block found, clean up the text and try to find JSON
    # Remove any leading/trailing backticks
    clean_text = re.sub(r'^```|```$', '', text.strip())
    
    # Try to find JSON object by looking for starting and ending braces
    json_obj_pattern = r'(\{[\s\S]*\})'
    json_obj_match = re.search(json_obj_pattern, clean_text, re.DOTALL)
    
    if json_obj_match:
        return json_obj_match.group(1).strip()
    
    # If still not found, return the original cleaned text
    return clean_text.strip()

def is_valid_json(json_str: str) -> bool:
    """
    Check if a string is valid JSON
    
    Args:
        json_str: String to check
        
    Returns:
        bool: True if valid JSON, False otherwise
    """
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError:
        return False