import main

event = """{
    "version": "0",
    "id": "36a55530-2e60-0376-b25e-14766273946e",
    "detail-type": "Object Created",
    "source": "aws.s3",
    "account": "958373515238",
    "time": "2026-03-01T11:35:32Z",
    "region": "ap-southeast-1",
    "resources": [
        "arn:aws:s3:::y2s2-aiml-project-knowledge-store"
    ],
    "detail": {
        "version": "0",
        "bucket": {
            "name": "y2s2-aiml-project-knowledge-store"
        },
        "object": {
            "key": "test/DCN_Lab_1.pdf",
            "size": 259100,
            "etag": "3891b1aadd98c7cd247db1ac6abe1ef5",
            "version-id": "o5dDWf6HqYB8RT.gO6ZNAzzCOP9Asrz9",
            "sequencer": "0069A424844233A7BD"
        },
        "request-id": "3N47W9VDXMEB2FER",
        "requester": "958373515238",
        "reason": "PutObject"
    }
}"""

main.lambda_handler(event, "None")