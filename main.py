# RFP Intelligence Project
# Embedding Function
# © 2026-Y2-S2-KU-DS-15
# Version 1.0

import os
import json
from cloud_kit.gcp.vertex_handler import VertexAI
from embedding_pipeline.vector_db import MilvusDB
from embedding_pipeline.embedding import EmbeddingManager
from embedding_pipeline.docs import Docs
from cloud_kit.aws.sm_handler import AWSSecretsManager

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_LOCATION = os.environ.get("GCP_REGION")
MILVUS_SECRET_NAME = os.environ.get("MILVUS_SECRET_NAME")
CHUNK_SIZE = os.environ.get("CHUNK_SIZE")
CHUNK_OVERLAP = os.environ.get("CHUNK_OVERLAP")
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
    VertexAI.init_vertex_ai(GCP_PROJECT_ID, GCP_LOCATION)

    chunks = Docs.chunk(object_path, CHUNK_SIZE, CHUNK_OVERLAP, file_ext)

    embedding = EmbeddingManager(provider=EMBEDDING_MODEL)
    embedding_model = embedding.get_embedding_model()

    vector_db = MilvusDB.init_vector_db(embedding_model, milvus_secret)

    _add_to_vector_db(vector_db, chunks)


def _add_to_vector_db(vector_store, text_chunk):
    vector_store.add_documents(documents=text_chunk)