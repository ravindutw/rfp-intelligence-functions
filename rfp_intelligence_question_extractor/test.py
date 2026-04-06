import main

def extract ():
    event = {
        "Records": [
            {
                "messageId": "db5",
                "receiptHandle": "AQ0",
                "body": '{"event": "qe_event", "rfp_id": "32bbad69-22c1-467d-81d5-a7c33e21c977", "s3_path": "rfpi-documents-981268234198-ap-southeast-1-an/32bbad69-22c1-467d-81d5-a7c33e21c977-rfp_a0000002-0002-0002-0002-000000000002_1774944684208.pdf","timestamp": "2026-04-15 11:30:00+00"}'
            }
        ]
    }

    main.lambda_handler(event, "None")

extract()