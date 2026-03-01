# RFP Intelligence Project
# Embedding Function
# © 2026-Y2-S2-KU-DS-15
# Version 1.0

import os
import json
from cloud_kit.gcp import vertex_handler
from embedding_pipeline.vector_db import MilvusDB
from embedding_pipeline.embedding import EmbeddingManager
from embedding_pipeline.docs import Docs

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
GCP_LOCATION = os.environ.get("GCP_REGION")
MILVUS_COLLECTION_NAME = os.environ.get("MILVUS_COLLECTION_NAME")
MILVUS_HOST = os.environ.get("MILVUS_HOST")

def lambda_handler(event, context):

    body = json.loads(event['Records'][0]['body'])
    object_path = body["detail"]["object"]["key"]
    file_ext = object_path.split('.')[-1]

    vertex_handler.init_vertex_ai(GCP_PROJECT_ID, GCP_LOCATION)

    chunks = Docs.chunk(object_path, 500, 50, file_ext)

    embedding = EmbeddingManager(provider="gemini")
    embedding_model = embedding.get_embedding_model()

    vector_db = MilvusDB.init_vector_db(embedding_model)

    _add_to_vector_db(vector_db, chunks)



def _add_to_vector_db(vector_store, text_chunk):
    vector_store.add_documents(documents=text_chunk)