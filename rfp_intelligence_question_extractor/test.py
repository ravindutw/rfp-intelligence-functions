import main

def extract ():
    event = {
        "Records": [
            {
                "receiptHandle": "AQ0",
                "body": '{"rfp_id":"cd3e23b2-3999-489b-8a25-5dd19a5322af", "user_id":"00000000-0000-0000-0000-000000000000","s3_path":"rfp/cd3e23b2-3999-489b-8a25-5dd19a5322af-rfp_a0000002-0002-0002-0002-000000000002_1774944673027.pdf","event":"qe_event","timestamp":"2026-04-06 21:46:02"}'
            }
        ]
    }

    main.lambda_handler(event, "None")

extract()