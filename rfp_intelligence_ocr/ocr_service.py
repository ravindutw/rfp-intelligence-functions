import os
from typing import Optional, Dict
from fastapi import FastAPI, UploadFile, File, HTTPException
import cv2
import numpy as np
import easyocr
from google import genai

app = FastAPI(title="EasyOCR + OpenCV + Gemini OCR Service")

reader = easyocr.Reader(
    ['en'],
    gpu=False,
    verbose=False
)

gemini_client: Optional[genai.Client] = None
gemini_model_name = "gemini-2.5-flash"  # Updated to a valid model name

# Get API key from environment variable (safer than hardcoding)
api_key = os.environ.get("GOOGLE_API_KEY")
if api_key:
    try:
        # Updated initialization method for newer google-genai library
        gemini_client = genai.Client(api_key=api_key)
        print(f"✅ Gemini post-processing enabled → {gemini_model_name}")
    except Exception as e:
        print(f"Failed to initialize Gemini: {e}")
else:
    print("⚠️ GOOGLE_API_KEY not set → Gemini post-processing disabled")


@app.post("/process")
async def process_ocr(file: UploadFile = File(...)) -> Dict[str, str]:
    """
    Endpoint called by Spring Boot.
    Expects multipart/form-data with key 'file' containing the image.
    Returns {"extracted_text": "..."}
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files allowed")

    try:
        # Read image bytes
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            raise ValueError("Failed to decode image")

        # ─── OpenCV Preprocessing ───
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        kernel = np.array([[-1, -1, -1],
                           [-1,  9, -1],
                           [-1, -1, -1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)

        # ─── EasyOCR ───
        results = reader.readtext(
            sharpened,
            detail=0,           # return only text strings
            paragraph=True,     # group into paragraphs
            batch_size=1
        )

        extracted_text = "\n".join(results) if results else ""

        # ─── Gemini Post-processing ───
        if gemini_client and extracted_text.strip():
            try:
                prompt = f"""Fix common OCR errors only.
Correct spelling, punctuation, broken words, spacing.
Keep original meaning, structure and line breaks.
Do NOT add new information or guess missing content.

Raw OCR output:
{extracted_text}

Cleaned version:"""

                # Updated API call for newer google-genai library
                response = gemini_client.models.generate_content(
                    model=gemini_model_name,
                    contents=prompt  # Can pass string directly
                )

                cleaned = response.text.strip()
                if cleaned:
                    extracted_text = cleaned

            except Exception as e:
                print(f"Gemini post-processing failed (using raw text): {e}")

        return {"extracted_text": extracted_text}

    except Exception as e:
        print(f"OCR processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")


@app.get("/")
async def root():
    return {"message": "EasyOCR + Gemini service is running. POST image to /process"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True
    )