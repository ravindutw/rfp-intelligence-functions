# RFP Intelligence Project
# Embedding Function
# © 2026-Y2-S2-KU-DS-15
# Version 1.0

import os
import json
from embedding_pipeline.vector_db import MilvusDB
from embedding_pipeline.embedding import EmbeddingManager
from cloud_kit.aws.sm_handler import AWSSecretsManager
from cloud_kit.aws.s3_handler import S3Handler
from embedding_pipeline.chunker import Chunker


GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_LOCATION = os.environ.get("GCP_REGION")
MILVUS_SECRET_NAME = os.environ.get("MILVUS_SECRET_NAME")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP"))
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL")
ALLOWED_FILE_EXTENSIONS = os.environ.get("ALLOWED_FILE_EXTENSIONS")
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME")

VERSION = "Beta-1.1"

def lambda_handler(event, context):
    try:
        print("RFP Intelligence Project Embedding Function")
        print(f"Version: {VERSION}")

        body = json.loads(event['Records'][0]['body'])
        object_path = body["detail"]["object"]["key"]
        file_ext = object_path.split('.')[-1]

        allowed_ext_json = json.loads(ALLOWED_FILE_EXTENSIONS)

        milvus_secret = AWSSecretsManager.get_secret(MILVUS_SECRET_NAME)

        if file_ext in allowed_ext_json["ext_list"]:
            _run_embedding_pipeline(milvus_secret, object_path, file_ext)

            return {"statusCode": 200}

        else:
            raise ValueError("Invalid file extension")

    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 200}


def _run_embedding_pipeline(milvus_secret, object_path, file_ext):
    docs = S3Handler().get_file(object_path, file_ext)
    chunks = Chunker.chunk_documents(docs, CHUNK_SIZE, CHUNK_OVERLAP)
    print(f"Split into {len(chunks)} chunks.")
    #chunks = Docs.chunk(object_path, CHUNK_SIZE, CHUNK_OVERLAP, file_ext)

    embedding = EmbeddingManager(EMBEDDING_MODEL, GCP_PROJECT_ID, GCP_LOCATION, EMBEDDING_MODEL_NAME)
    embedding_model = embedding.get_embedding_model()

    vector_db = MilvusDB.init_vector_db(embedding_model, milvus_secret)

    _add_to_vector_db(vector_db, chunks)


def _add_to_vector_db(vector_store, text_chunk):
    sanitized_chunks = MilvusDB().sanitize_metadata_keys(documents=text_chunk)
    vector_store.add_documents(documents=sanitized_chunks)
    print("Added to vector store")