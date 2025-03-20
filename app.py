# app.py
import os
import base64
import re
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import google.generativeai as genai
import logging
from PIL import Image
import io
import json
import time
from datetime import datetime
import uuid

# Cấu hình logging
import sys
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Sử dụng stdout thay vì stderr mặc định
        logging.FileHandler("api.log", encoding="utf-8")  # Chỉ định encoding utf-8
    ]
)
logger = logging.getLogger("patient-care-api")

# Tải API key từ biến môi trường
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY không được cấu hình")
    raise EnvironmentError("GEMINI_API_KEY phải được cấu hình trong biến môi trường")

# Tạo ứng dụng FastAPI
app = FastAPI(
    title="API trích xuất thông tin phiếu chăm sóc bệnh nhân",
    description="API trích xuất thông tin từ hình ảnh phiếu chăm sóc bệnh nhân sử dụng Google Gemini",
    version="1.0.0"
)

# Thêm CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Thay thế bằng domain cụ thể trong production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo Gemini client
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.0-pro-exp-02-05"))

# Đọc prompt từ file
PROMPT_PATH = os.getenv("PROMPT_PATH", "prompt.txt")

try:
    with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
        EXTRACTION_PROMPT = f.read()
    logger.info(f"Đã đọc prompt từ {PROMPT_PATH}")
except Exception as e:
    logger.error(f"Không thể đọc prompt từ {PROMPT_PATH}: {str(e)}")
    EXTRACTION_PROMPT = """Bạn là một trợ lý AI chuyên trích xuất thông tin từ hình ảnh phiếu chăm sóc bệnh nhân..."""  # Mặc định prompt rút gọn - cần thay thế bằng prompt đầy đủ

# Class cho response
class ExtractionResponse(BaseModel):
    request_id: str
    timestamp: str
    status: str
    data: Dict[str, Any]

# Class cho lỗi
class ErrorResponse(BaseModel):
    request_id: str
    timestamp: str
    status: str = "error"
    error: Dict[str, Any]

# Tạo ID cho mỗi request
def generate_request_id():
    return str(uuid.uuid4())

# Hàm trích xuất thông tin từ hình ảnh
async def extract_patient_care_data(image_files: List[bytes], request_id: str):
    """
    Trích xuất thông tin từ hình ảnh phiếu chăm sóc bệnh nhân
    
    Args:
        image_files: Danh sách byte data của các hình ảnh
        request_id: ID của request
        
    Returns:
        Dict: Dữ liệu trích xuất hoặc thông tin lỗi
    """
    start_time = time.time()
    logger.info(f"[{request_id}] Bắt đầu trích xuất dữ liệu từ {len(image_files)} hình ảnh")
    
    # Kiểm tra số lượng hình ảnh
    if len(image_files) != 2:
        logger.warning(f"[{request_id}] Số lượng hình ảnh không hợp lệ: {len(image_files)}")
        return {
            "error": True,
            "error_type": "INSUFFICIENT_IMAGES",
            "error_details": {
                "received": len(image_files),
                "required": 2
            },
            "message": f"Cần chính xác 2 hình ảnh, đã nhận {len(image_files)}"
        }
    
    # Chuẩn bị hình ảnh
    try:
        parts = []
        for idx, image_bytes in enumerate(image_files):
            # Xác định định dạng hình ảnh (mặc định là JPEG)
            try:
                img = Image.open(io.BytesIO(image_bytes))
                mime_type = f"image/{img.format.lower()}" if img.format else "image/jpeg"
            except:
                mime_type = "image/jpeg"
                
            # Thêm vào parts
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": base64.b64encode(image_bytes).decode()
                }
            })
        
        # Thêm prompt
        parts.append({"text": EXTRACTION_PROMPT})
        
        # Tạo nội dung request
        contents = [
            {
                "role": "user",
                "parts": parts
            }
        ]
        
        # Gọi API Gemini
        logger.info(f"[{request_id}] Gửi request tới Gemini API")
        response = model.generate_content(contents)
        
        # Xử lý phản hồi
        response_text = response.text
        
        # Tìm và trích xuất JSON từ phản hồi
        json_pattern = r'```json(.*?)```'
        json_match = re.search(json_pattern, response_text, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(1).strip()
        else:
            # Nếu không tìm thấy định dạng markdown, thử coi toàn bộ văn bản là JSON
            json_str = response_text.strip()
        
        try:
            result = json.loads(json_str)
            
            # Ghi log thời gian xử lý
            processing_time = time.time() - start_time
            logger.info(f"[{request_id}] Trích xuất thành công trong {processing_time:.2f} giây")
            
            return result
        except json.JSONDecodeError as e:
            logger.error(f"[{request_id}] Lỗi phân tích JSON: {str(e)}")
            return {
                "error": True,
                "error_type": "JSON_PARSING_ERROR",
                "error_details": {
                    "response_excerpt": response_text[:500] + "..." if len(response_text) > 500 else response_text
                },
                "message": f"Không thể phân tích kết quả thành JSON: {str(e)}"
            }
            
    except Exception as e:
        logger.error(f"[{request_id}] Lỗi: {str(e)}", exc_info=True)
        return {
            "error": True,
            "error_type": "API_REQUEST_FAILED",
            "message": f"Lỗi khi trích xuất dữ liệu: {str(e)}"
        }

# Route trích xuất từ hình ảnh upload
@app.post("/api/v1/extract", 
         summary="Trích xuất thông tin từ hình ảnh phiếu chăm sóc",
         description="Upload chính xác 2 hình ảnh (mặt trước và mặt sau của phiếu chăm sóc) để trích xuất thông tin")
async def extract_from_uploads(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(..., description="Tải lên 2 hình ảnh: mặt trước và mặt sau của phiếu chăm sóc")
):
    request_id = generate_request_id()
    timestamp = datetime.now().isoformat()
    
    # Kiểm tra số lượng file
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
    
    # Đọc files
    try:
        image_data = []
        for file in files:
            content = await file.read()
            
            # Kiểm tra xem file có phải là hình ảnh không
            try:
                Image.open(io.BytesIO(content))
                image_data.append(content)
            except:
                return JSONResponse(
                    status_code=400,
                    content=ErrorResponse(
                        request_id=request_id,
                        timestamp=timestamp,
                        error={
                            "type": "INVALID_FILE_FORMAT",
                            "message": f"File '{file.filename}' không phải là hình ảnh hợp lệ",
                            "details": {
                                "filename": file.filename
                            }
                        }
                    ).dict()
                )
        
        # Trích xuất dữ liệu
        result = await extract_patient_care_data(image_data, request_id)
        
        # Định dạng response
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

# Route health check
@app.get("/health", 
        summary="Kiểm tra trạng thái API",
        description="Endpoint để kiểm tra xem API có hoạt động bình thường không")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

# Main execution
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000)
