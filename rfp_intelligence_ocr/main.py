# RFP Intelligence Project
# OCE
# © 2026-Y2-S2-KU-DS-15
# Version:

from fastapi import FastAPI
from routers.ocr_router import router as ocr_router
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="OCR Service",
    description="EasyOCR + OpenCV + Gemini Post-processing Service",
    version="1.0.0"
)

app.include_router(ocr_router)

@app.get("/")
async def root():
    return {
        "message": "OCR Service is running",
        "docs": "/docs",
        "endpoints": {
            "process": "POST /ocr/process",
            "health": "GET /ocr/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
