# RFP Intelligence Project
# Embedding Function
# © 2026-Y2-S2-KU-DS-15
# Version: 1.2.0

import os
import json
import traceback

from embedding_pipeline.vector_db import get_vector_db
from embedding_pipeline.embedding import EmbeddingManager
from cloud_kit.aws.sm_handler import AWSSecretsManager
from cloud_kit.aws.s3_handler import S3Handler
from embedding_pipeline.chunker import Chunker


GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_LOCATION = os.environ.get("GCP_REGION")
AWS_REGION = os.environ.get("AWS_REGION_NAME")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 500))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", 50))
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL")
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME")
EMBEDDING_DIMENSIONS = int(os.environ.get("EMBEDDING_DIMENSIONS", 1536))
ALLOWED_FILE_EXTENSIONS = os.environ.get("ALLOWED_FILE_EXTENSIONS", '{"ext_list": ["pdf"]}')

VECTOR_DB_PROVIDER = os.environ.get("VECTOR_DB_PROVIDER")
MILVUS_SECRET_NAME = os.environ.get("MILVUS_SECRET_NAME")
PGVECTOR_SECRET_NAME = os.environ.get("PGVECTOR_SECRET_NAME")

VERSION = "1.2.0"


def lambda_handler(event, context):
    try:
        print("RFP Intelligence Project Embedding Function")
        print(f"Version: {VERSION}")
        print(f"Vector DB Provider: {VECTOR_DB_PROVIDER}")
        print(f"Embedding Provider: {EMBEDDING_MODEL}")

        _validate_env()

        body = json.loads(event['Records'][0]['body'])
        object_path = body["detail"]["object"]["key"]
        file_ext = object_path.split('.')[-1]

        allowed_ext_json = json.loads(ALLOWED_FILE_EXTENSIONS)

        db_secret = _get_db_secret(VECTOR_DB_PROVIDER)

        if file_ext in allowed_ext_json["ext_list"]:
            _run_embedding_pipeline(db_secret, object_path, file_ext)
            return {"statusCode": 200}
        else:
            raise ValueError("Invalid file extension")

    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        return {"statusCode": 200}


def _validate_env():
    # Required regardless of provider
    if VECTOR_DB_PROVIDER is None or EMBEDDING_MODEL is None or EMBEDDING_MODEL_NAME is None:
        raise ValueError("VECTOR_DB_PROVIDER, EMBEDDING_MODEL, and EMBEDDING_MODEL_NAME must be set")

    if PGVECTOR_SECRET_NAME is None:
        raise ValueError("PGVECTOR_SECRET_NAME is not set")

    # Provider-specific requirements
    if EMBEDDING_MODEL == "gemini":
        if GCP_PROJECT_ID is None or GCP_LOCATION is None:
            raise ValueError("GCP_PROJECT_ID and GCP_REGION must be set for the Gemini provider")
    elif EMBEDDING_MODEL == "cohere":
        # AWS_REGION is optional — boto3 falls back to the Lambda runtime region.
        # IAM role credentials are picked up automatically.
        pass
    else:
        raise ValueError(f"Unsupported EMBEDDING_MODEL: {EMBEDDING_MODEL}")


def _get_db_secret(provider):
    if provider == "milvus":
        return AWSSecretsManager.get_secret(MILVUS_SECRET_NAME)
    if provider == "pgvector":
        return AWSSecretsManager.get_secret(PGVECTOR_SECRET_NAME)
    raise ValueError(f"Invalid vector DB provider: {provider}")


def _run_embedding_pipeline(db_secret, object_path, file_ext):
    docs = S3Handler().get_file(object_path, file_ext)
    chunks = Chunker.chunk_documents(docs, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"Split into {len(chunks)} chunks.")

    embedding = EmbeddingManager(
        provider=EMBEDDING_MODEL,
        model_name=EMBEDDING_MODEL_NAME,
        project_id=GCP_PROJECT_ID,
        location=GCP_LOCATION,
        region=AWS_REGION,
        output_dimensionality=EMBEDDING_DIMENSIONS,
    )
    embedding_model = embedding.get_embedding_model()

    db_class = get_vector_db(VECTOR_DB_PROVIDER)
    vector_db = db_class.init_vector_db(embedding_model, db_secret)

    _add_to_vector_db(db_class, vector_db, chunks)


def _add_to_vector_db(db_class, vector_store, text_chunk):
    sanitized_chunks = db_class().sanitize_metadata_keys(documents=text_chunk)
    vector_store.add_documents(documents=sanitized_chunks)
    print("Added to vector store")