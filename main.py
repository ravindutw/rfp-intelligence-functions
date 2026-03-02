# RFP Intelligence Project
# Embedding Function
# © 2026-Y2-S2-KU-DS-15
# Version 2.0

import os
import json
from embedding_pipeline.vector_db import MilvusDB
from embedding_pipeline.embedding import EmbeddingManager
from embedding_pipeline.docs import Docs
from cloud_kit.aws.sm_handler import AWSSecretsManager


GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_LOCATION = os.environ.get("GCP_REGION")
MILVUS_SECRET_NAME = os.environ.get("MILVUS_SECRET_NAME")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP"))
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL")
ALLOWED_FILE_EXTENSIONS = os.environ.get("ALLOWED_FILE_EXTENSIONS")


def lambda_handler(event, context):
    body = json.loads(event['Records'][0]['body'])
    object_path = body["detail"]["object"]["key"]
    file_ext = object_path.split('.')[-1]

    allowed_ext_json = json.loads(ALLOWED_FILE_EXTENSIONS)

    milvus_secret = AWSSecretsManager.get_secret(MILVUS_SECRET_NAME)

    if file_ext in allowed_ext_json["ext_list"]:
        _run_embedding_pipeline(milvus_secret, object_path, file_ext)
    else:
        raise ValueError("Invalid file extension")


def _run_embedding_pipeline(milvus_secret, object_path, file_ext):
    chunks = Docs.chunk(object_path, CHUNK_SIZE, CHUNK_OVERLAP, file_ext)

    embedding_manager = EmbeddingManager(EMBEDDING_MODEL, GCP_PROJECT_ID, GCP_LOCATION)

    vector_db = MilvusDB()
    vector_db.connect(milvus_secret)

    _add_to_vector_db(vector_db, embedding_manager, chunks)


def _add_to_vector_db(vector_db, embedding_manager, text_chunks):
    sanitized_chunks = vector_db.sanitize_metadata_keys(documents=text_chunks)

    texts = [doc.page_content for doc in sanitized_chunks]
    metadata = [doc.metadata for doc in sanitized_chunks]

    embeddings = embedding_manager.embed_documents(texts)

    embedding_dim = len(embeddings[0])
    vector_db.init_collection(embedding_dim)

    vector_db.add_documents(texts, embeddings, metadata)
    print("Added to vector store")