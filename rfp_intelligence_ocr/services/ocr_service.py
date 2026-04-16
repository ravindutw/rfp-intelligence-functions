import easyocr
from google import genai
from typing import Optional
from config.settings import settings
from utils.image_utils import preprocess_image
import logging
import asyncio

logger = logging.getLogger(__name__)

reader = easyocr.Reader(
    settings.OCR_LANGUAGES,
    gpu=settings.USE_GPU,
    verbose=False
)

gemini_client: Optional[genai.Client] = None

if settings.GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info(f"✅ Gemini post-processing enabled → {settings.GEMINI_MODEL}")
    except Exception as e:
        logger.error(f"Failed to initialize Gemini: {e}")

FALLBACK_MODELS = [
    settings.GEMINI_MODEL,
    "gemini-2.5-flash-lite",
    "gemini-1.5-flash",
    "gemini-2.0-flash"
]

async def call_gemini_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Call Gemini with exponential backoff + model fallback on 503"""
    for attempt in range(max_retries):
        for model_name in FALLBACK_MODELS:
            try:
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                return response.text.strip()

            except Exception as e:
                error_str = str(e).lower()
                if "503" in error_str or "unavailable" in error_str or "high demand" in error_str:
                    logger.warning(f"Model {model_name} returned 503 (attempt {attempt+1}). Trying next model...")
                    await asyncio.sleep(1)  
                    continue
                else:
                    logger.error(f"Gemini error with {model_name}: {e}")
                    break

        if attempt < max_retries - 1:
            wait = (2 ** attempt) * 2
            logger.info(f"Retrying Gemini in {wait}s...")
            await asyncio.sleep(wait)

    raise RuntimeError("All Gemini models and retries failed due to high demand.")


async def process_ocr_image(image_bytes: bytes, original_filename: str) -> str:
    try:
        processed_img = preprocess_image(image_bytes)

        results = reader.readtext(
            processed_img,
            detail=0,
            paragraph=True,
            batch_size=1,
            width_ths=0.7,
            height_ths=0.7
        )

        raw_text = "\n".join(results) if results else ""

        extracted_text = raw_text

        if gemini_client and raw_text.strip():
            try:
                prompt = """You are an expert OCR correction specialist for old printed documents (1970s-1980s style).

Fix ALL common OCR errors while staying 100% faithful to the original:
- Correct spelling, broken/merged words, bad character recognition (l/1, rn/m, O/0, etc.)
- Fix spacing, punctuation, and sentence flow
- Restore proper paragraphs and structure
- Do NOT add, remove, or interpret content
- Do NOT modernize language unless it's a clear OCR mistake

Raw OCR text:

{raw_text}

Return only the fully cleaned and corrected article text:"""

                formatted_prompt = prompt.format(raw_text=raw_text)

                cleaned = await call_gemini_with_retry(formatted_prompt)

                if cleaned and len(cleaned) > 100:
                    extracted_text = cleaned
                    logger.info(f"✅ Gemini cleaned OCR for {original_filename}")
                else:
                    logger.warning("Gemini returned suspiciously short output")

            except Exception as e:
                logger.warning(f"Gemini post-processing failed (falling back to raw text): {e}")

        return extracted_text

    except Exception as e:
        logger.error(f"OCR processing failed for {original_filename}: {str(e)}")
        raise
