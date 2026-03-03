import main


event = {
    "Records": [
        {
            "messageId": "db5",
            "receiptHandle": "AQ0",
            "body": '{"version": "0", "id": "36", "detail-type": "Object Created", "source": "aws.s3", "time": "2026-03-01T11:35:32Z", "region": "ap-southeast-1", "resources": ["arn:aws:s3:::y2s2-aiml-project-knowledge-store"], "detail": {"version": "0", "bucket": {"name": "y2s2-aiml-project-knowledge-store"}, "object": {"key": "test/Lab 6_DCN .pdf", "size": 259100, "etag": "389", "version-id": "o5d", "sequencer": "00"}, "request-id": "3N", "requester": "95", "reason": "PutObject"}}'
        }
    ]
}

main.lambda_handler(event, "None")
