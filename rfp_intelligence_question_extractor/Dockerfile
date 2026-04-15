# Use the official AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.12

# Copy requirements file
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install -r requirements.txt

# Pre-download NLTK data required by 'unstructured' to avoid runtime downloads
RUN pip install nltk && \
    python -c "import nltk; nltk.download('punkt', download_dir='/tmp/nltk_data'); nltk.download('punkt_tab', download_dir='/tmp/nltk_data'); nltk.download('averaged_perceptron_tagger', download_dir='/tmp/nltk_data'); nltk.download('averaged_perceptron_tagger_eng', download_dir='/tmp/nltk_data')" && \
    mv /tmp/nltk_data ${LAMBDA_TASK_ROOT}/nltk_data

# Set NLTK_DATA so it finds the pre-downloaded data
ENV NLTK_DATA=${LAMBDA_TASK_ROOT}/nltk_data

# Copy all source code (excluding tests and other unnecessary files)
COPY __init__.py ${LAMBDA_TASK_ROOT}/
COPY cloud_kit ${LAMBDA_TASK_ROOT}/cloud_kit/
COPY db_manager.py ${LAMBDA_TASK_ROOT}/
COPY extractor.py ${LAMBDA_TASK_ROOT}/
COPY invoke_inference.py ${LAMBDA_TASK_ROOT}/
COPY main.py ${LAMBDA_TASK_ROOT}/
COPY models.py ${LAMBDA_TASK_ROOT}/
COPY prompt.txt ${LAMBDA_TASK_ROOT}/
COPY certs ${LAMBDA_TASK_ROOT}/certs/

# Set the CMD to your handler
CMD ["main.lambda_handler"]
