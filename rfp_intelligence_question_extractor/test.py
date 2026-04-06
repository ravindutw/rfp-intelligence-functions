import main

def extract ():
    event = {
        "Records": [
            {
                "messageId": "db5",
                "receiptHandle": "AQ0",
                "body": '{"rfp_id":"0ba31e5f-6844-4edb-aa9b-d52f98b54c4a","s3_path":"rfp/0ba31e5f-6844-4edb-aa9b-d52f98b54c4a-rfp_1_1774357735812.pdf","event":"qe_event","timestamp":"2026-04-06 21:46:02"}'
            }
        ]
    }

    main.lambda_handler(event, "None")

extract()