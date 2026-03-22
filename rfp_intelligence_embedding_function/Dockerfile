# Use the official AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.13

# Copy requirements file
COPY requirements.txt ${LAMBDA_TASK_ROOT}/rfp_intelligence_embedding_function/

# Install Python dependencies
RUN pip install -r rfp_intelligence_embedding_function/requirements.txt

# Copy all source code (excluding tests and other unnecessary files)
COPY __init__.py ${LAMBDA_TASK_ROOT}/rfp_intelligence_embedding_function/
COPY main.py ${LAMBDA_TASK_ROOT}/rfp_intelligence_embedding_function/
COPY cloud_kit ${LAMBDA_TASK_ROOT}/rfp_intelligence_embedding_function/cloud_kit/
COPY embedding_pipeline ${LAMBDA_TASK_ROOT}/rfp_intelligence_embedding_function/embedding_pipeline/

# Set the CMD to your handler
CMD ["rfp_intelligence_embedding_function.main.lambda_handler"]
