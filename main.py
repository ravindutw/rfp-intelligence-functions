# RFP Intelligence Project
# Embedding Function
# © 2026-Y2-S2-KU-DS-15
# Version 1.0

import os
import cloud_kit

PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
LOCATION = os.environ.get("GCP_REGION")
MILVUS_COLLECTION_NAME = os.environ.get("MILVUS_COLLECTION_NAME")
MILVUS_HOST = os.environ.get("MILVUS_HOST")

def lambda_handler(event, context):

    file_name = event.get('file_name')