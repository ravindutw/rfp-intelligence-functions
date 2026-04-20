import main
import time
from cloud_kit.aws.sm_handler import AWSSecretsManager
import os
import json


def embed (file_):
    event = {
        "Records": [
            {
                "messageId": "db5",
                "receiptHandle": "AQ0",
                "body": '{"version": "0", "id": "36", "detail-type": "Object Created", "source": "aws.s3", "time": "2026-03-01T11:35:32Z", "region": "ap-southeast-1", "resources": ["arn:aws:s3:::rfpi-knowledge-store-981268234198-ap-southeast-1-an"], "detail": {"version": "0", "bucket": {"name": "rfpi-knowledge-store-981268234198-ap-southeast-1-an"}, "object": {"key": "' + file_ +'", "size": 259100, "etag": "389", "version-id": "o5d", "sequencer": "00"}, "request-id": "3N", "requester": "95", "reason": "PutObject"}}'
            }
        ]
    }

    main.lambda_handler(event, "None")


"""
file_names = [
    "MN-DN11-034 (NETWORKING - PHYSICAL LAYER).pdf",
    "MN-PS21-165 (MEASUREMENT SCALES).pdf",
    "MN-AI21-230 (ACTIVATION FUNCTIONS).pdf",
    "MN-DN11-041 (NETWORKING - LINK LAYER).pdf",
    "MN-PS21-173 (STATISTICS SPECIAL POINTS).pdf",
    "MN-AI21-231 (SUPERVISED LEARNING).pdf",
    "MN-DN11-056 (NETWORKING - NETWORK LAYER - 2).pdf",
    "MN-PS21-184 (PROBABILITY RULES 1).pdf",
    "MN-DA12-084 (ASYMPTOTIC NOTATIONS).pdf",
    "MN-DN11-058 (SUBNETTING).pdf",
    "MN-PS21-185 (STATISTICS EQUATIONS).pdf",
    "MN-DD21-232 (DB SCHEMA REFINEMENT).pdf",
    "MN-DN11-068 (ROUTING).pdf",
    "MN-PS21-186 (STATISTICS - TYPES OF VARIABLES).pdf",
    "MN-DM12-077 (NUMBER NOTATIONS).pdf",
    "MN-DN11-069 (NETWORK SECURITY).pdf",
    "MN-PS21-199 (PROBABILITY DISTRIBUTIONS EQUATIONS).pdf",
    "MN-DM12-110 (MATHEMATICAL INDUCTION).pdf",
    "MN-DN11-070 (TRANSPORT LAYER).pdf",
    "MN-PS21-200 (DISCRETE PROBABILITY DISTRIBUTIONS).pdf",
    "MN-DN11-029 (DATA COMMUNICATION BASICS).pdf",
    "MN-FC11-049 (DIGITAL LOGIC - COMBINATIONAL CIRCUITS).pdf",
    "MN-PS21-217 (PROBABILITY DENSITY FUNCTION).pdf",
    "MN-DN11-033 (PROTOCOL ARCHITECTURE).pdf",
    "MN-FC11-059 (PROCESSOR COMPONENTS).pdf",
    "MN-PS21-218 (CONTINUOUS DISTRIBUTIONS).pdf"
]
"""

file_names = [
    "MN-DA12-084 (ASYMPTOTIC NOTATIONS).pdf"
]


for file in file_names:
    embed(file)
    print(f"Embedding {file}...")
    time.sleep(2)


"""
PGVECTOR_SECRET_NAME = os.environ.get("PGVECTOR_SECRET_NAME")
secret = AWSSecretsManager.get_secret(PGVECTOR_SECRET_NAME)
print(secret)
"""

