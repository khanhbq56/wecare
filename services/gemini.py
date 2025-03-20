# services/gemini.py
import os
import logging
import google.generativeai as genai
from typing import List, Dict, Any, Tuple, Optional
import time
from concurrent.futures import ThreadPoolExecutor
import json

from utils.helpers import extract_json_from_text, is_valid_json

logger = logging.getLogger("patient-care-api")

def validate_gemini_api_key() -> str:
    """
    Validate that Gemini API key is set
    
    Returns:
        str: Gemini API key
    
    Raises:
        EnvironmentError: If API key is not set
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable not found")
        raise EnvironmentError("GEMINI_API_KEY must be set in environment variables")
    return api_key

def get_gemini_model():
    """
    Get configured Gemini model
    
    Returns:
        GenerativeModel: Gemini model instance
    """
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-pro-exp-02-05")
    
    # Get model with appropriate settings
    model = genai.GenerativeModel(
        model_name,
        generation_config={
            "temperature": 0,  # Lower temperature for more deterministic responses
            "top_p": 0.95,
            "top_k": 0,
        }
    )
    
    return model

def get_extraction_prompt() -> str:
    """
    Get prompt for extracting data from patient care forms
    
    Returns:
        str: Extraction prompt
    """
    prompt_path = os.getenv("PROMPT_PATH", "prompt.txt")
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
        logger.info(f"Successfully loaded prompt from {prompt_path}")
        return prompt
    except Exception as e:
        logger.error(f"Failed to load prompt from {prompt_path}: {str(e)}")
        return """Bạn là một trợ lý AI chuyên trích xuất thông tin từ hình ảnh phiếu chăm sóc bệnh nhân..."""

def call_gemini_api(contents: List[Dict], request_id: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Call Gemini API with the provided contents
    
    Args:
        contents: Request contents
        request_id: Request ID for logging
        
    Returns:
        Tuple containing:
            - Dict: Parsed JSON result if successful
            - str: Error message if failed
    """
    start_time = time.time()
    model = get_gemini_model()
    
    try:
        logger.info(f"[{request_id}] Calling Gemini API")
        response = model.generate_content(contents)
        
        # Extract response text
        response_text = response.text
        
        # Try to extract JSON from response
        json_str = extract_json_from_text(response_text)
        
        # Parse JSON
        try:
            result = json.loads(json_str)
            
            # Log success
            processing_time = time.time() - start_time
            logger.info(f"[{request_id}] Gemini API call successful in {processing_time:.2f}s")
            
            return result, None
            
        except json.JSONDecodeError as e:
            logger.error(f"[{request_id}] Failed to parse JSON: {str(e)}")
            return None, f"Failed to parse Gemini response as JSON: {str(e)}. Response text: {response_text[:500]}..."
    
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"[{request_id}] Gemini API call failed after {processing_time:.2f}s: {str(e)}")
        return None, f"Gemini API call failed: {str(e)}"