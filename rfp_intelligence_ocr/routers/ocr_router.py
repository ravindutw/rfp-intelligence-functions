from fastapi import APIRouter, UploadFile, File, HTTPException
from services.ocr_service import process_ocr_image, gemini_client
from typing import Dict

router = APIRouter(prefix="/ocr", tags=["OCR"])

@router.post("/process")
async def process_image(
    file: UploadFile = File(...)
) -> Dict[str, str]:
    """
    Endpoint called by Spring Boot OcrService.
    Expects multipart/form-data with key 'file'.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    try:
        contents = await file.read()
        extracted_text = await process_ocr_image(contents, file.filename or "unknown")

        return {"extracted_text": extracted_text}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {str(e)}"
        )


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "ocr_engine": "EasyOCR + OpenCV",
        "gemini_enabled": bool(gemini_client)
    }
