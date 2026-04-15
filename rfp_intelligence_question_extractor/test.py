import main

def extract ():
    event = {
        "Records": [
            {
                "receiptHandle": "AQ0",
                "body": '{"rfp_id":"0dab98ea-07ff-4722-90cd-ace2c54e24ab", "user_id":"736169af-fef1-4ec2-9c12-704efb97d0cc","s3_path":"rfp/0dab98ea-07ff-4722-90cd-ace2c54e24ab-rfp-1.pdf","event":"qe_event","timestamp":"2026-04-06 21:46:02"}'
            }
        ]
    }

    main.lambda_handler(event, "None")

extract()