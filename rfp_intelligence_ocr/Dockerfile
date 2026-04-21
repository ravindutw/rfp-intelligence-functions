FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd --system nonroot \
  && useradd --system \
     --gid nonroot rwapps

RUN chown -R rwapps:nonroot /app

USER rwapps

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]