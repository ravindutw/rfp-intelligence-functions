# Use the official AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.14

# Copy requirements file
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy all source code (excluding tests and other unnecessary files)
COPY __init__.py ${LAMBDA_TASK_ROOT}/
COPY main.py ${LAMBDA_TASK_ROOT}/
COPY cloud_kit ${LAMBDA_TASK_ROOT}/cloud_kit/
COPY embedding_pipeline ${LAMBDA_TASK_ROOT}/embedding_pipeline/

# Set the CMD to your handler
CMD ["main.lambda_handler"]
