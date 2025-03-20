# utils/errors.py
from enum import Enum

class ErrorType(str, Enum):
    """Enum for error types"""
    INSUFFICIENT_IMAGES = "INSUFFICIENT_IMAGES"
    INVALID_IMAGES = "INVALID_IMAGES"
    IMAGE_QUALITY_ISSUE = "IMAGE_QUALITY_ISSUE"
    INCONSISTENT_INFORMATION = "INCONSISTENT_INFORMATION"
    DUPLICATE_IMAGES = "DUPLICATE_IMAGES"
    JSON_PARSING_ERROR = "JSON_PARSING_ERROR"
    API_REQUEST_FAILED = "API_REQUEST_FAILED"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    INVALID_FILE_FORMAT = "INVALID_FILE_FORMAT"

ERROR_MESSAGES = {
    ErrorType.INSUFFICIENT_IMAGES: "Cần chính xác 2 hình ảnh",
    ErrorType.INVALID_IMAGES: "Hình ảnh không phải là phiếu chăm sóc hợp lệ",
    ErrorType.IMAGE_QUALITY_ISSUE: "Chất lượng hình ảnh không đủ để trích xuất thông tin",
    ErrorType.INCONSISTENT_INFORMATION: "Thông tin giữa hai hình ảnh không khớp nhau",
    ErrorType.DUPLICATE_IMAGES: "Hai hình ảnh giống nhau, cần cung cấp mặt trước và mặt sau",
    ErrorType.JSON_PARSING_ERROR: "Không thể phân tích kết quả thành JSON",
    ErrorType.API_REQUEST_FAILED: "Lỗi khi gọi API",
    ErrorType.PROCESSING_ERROR: "Lỗi xử lý",
    ErrorType.INVALID_FILE_FORMAT: "File không phải là hình ảnh hợp lệ"
}

def get_error_message(error_type: str, additional_info: str = None) -> str:
    """
    Get error message based on error type
    
    Args:
        error_type: Type of error
        additional_info: Additional error information
        
    Returns:
        str: Error message
    """
    message = ERROR_MESSAGES.get(error_type, "Lỗi không xác định")
    
    if additional_info:
        message = f"{message}: {additional_info}"
        
    return message