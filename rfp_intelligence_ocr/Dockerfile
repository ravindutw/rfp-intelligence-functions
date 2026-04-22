FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd --system nonroot \
 && useradd --system --gid nonroot rwapps

# Pre-download EasyOCR models. Override languages at build time if needed:
# docker build --build-arg OCR_LANGUAGES="en,si,ta" .
ARG OCR_LANGUAGES="en"
RUN mkdir -p /opt/easyocr \
 && python -c "import easyocr; \
langs='${OCR_LANGUAGES}'.split(','); \
easyocr.Reader(langs, gpu=False, model_storage_directory='/opt/easyocr', download_enabled=True)" \
 && chown -R rwapps:nonroot /opt/easyocr

ENV EASYOCR_MODULE_PATH=/opt/easyocr

RUN chown -R rwapps:nonroot /app

USER rwapps

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]