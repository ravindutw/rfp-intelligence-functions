import os

import boto3
from botocore.exceptions import ClientError

class AWSSecretsManager:

    @staticmethod
    def get_secret(secret_name: str):
        aws_region = os.environ['AWS_REGION']

        # Create a Secrets Manager client
        session = boto3.session.Session()
        client = session.client(
            service_name='secretsmanager',
            region_name=aws_region
        )

        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )
        except ClientError as e:
            # For a list of exceptions thrown, see
            # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
            print(e)
            raise e

        return get_secret_value_response['SecretString']